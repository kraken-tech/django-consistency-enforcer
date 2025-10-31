from collections.abc import Iterator, Sequence

import django_consistency_enforcer_test_driver as test_helpers
import pytest
from django import http
from django.views import generic

from django_consistency_enforcer import errors as enforcer_errors
from django_consistency_enforcer import urls as enforcer


class TestViewRequestAnnotation:
    def runCheck(
        self,
        view_class: type[generic.View],
        *,
        user_type: type,
        acceptable: Sequence[object],
        acceptable_containers: Sequence[object],
    ) -> None:
        pattern = test_helpers.patterns.from_raw_pattern(
            enforcer.RawPattern.from_parts(
                [
                    enforcer.RawPatternPart(
                        groups=0,
                        captured={},
                        where=enforcer.Where(name="w1", module="m1", namespace="n1", regex="r1"),
                    ),
                ],
                where=enforcer.Where(name="w0", module="m0", namespace="n0", regex="r0"),
                callback=view_class.as_view(),
            ),
        )

        class StubInvalidRequestAnnotation(enforcer_errors.InvalidRequestAnnotation):
            @property
            def expect(self) -> str:
                """
                Return a simple string representing what the type should be
                """
                if self.acceptable_annotations:
                    assert (
                        len(self.acceptable_annotations) == 1
                        and not self.acceptable_request_annotation_containers
                    )
                    return str(self.acceptable_annotations[0])
                else:
                    assert len(self.acceptable_request_annotation_containers) == 1
                    return f"{self.acceptable_request_annotation_containers[0]}-[{self.expected_user_type}]"

            @property
            def expanded_note(self) -> Iterator[str]:
                yield "..expanded note.."

        with test_helpers.checkers.expect_zero_or_one_errors() as errors:
            enforcer.CheckViewClassRequestAnnotationScenario(
                error_class=StubInvalidRequestAnnotation,
                acceptable_annotations=acceptable,
                acceptable_request_annotation_containers=acceptable_containers,
            ).run(errors=errors, auth_user_model=user_type, pattern=pattern)

    def test_is_happy_with_acceptable_types(self) -> None:
        class MyView(generic.View):
            request: http.HttpRequest

        self.runCheck(
            MyView, user_type=int, acceptable=(http.HttpRequest,), acceptable_containers=()
        )

        class MyView2(generic.View):
            request: bool  # type: ignore[assignment]

        self.runCheck(MyView2, user_type=int, acceptable=(bool,), acceptable_containers=())

    def test_is_unhappy_with_not_acceptable_types(self) -> None:
        class MyView(generic.View):
            request: int  # type: ignore[assignment]

        with pytest.raises(enforcer_errors.InvalidRequestAnnotation) as e:
            self.runCheck(
                MyView, user_type=int, acceptable=(http.HttpRequest,), acceptable_containers=()
            )

        test_helpers.checkers.expect_invalid_django_pattern_error(
            e.value,
            f"""
            [InvalidRequestAnnotation]
              Originating:
                module = m0
                name = w0
                namespace = n0
                regex = r0
              module = {__file__}
              class = MyView
              error = The annotation is not using a valid type
                  (<class 'int'>)
              expect = <class 'django.http.request.HttpRequest'>
            ..expanded note..
            """,
        )

    def test_is_happy_with_filled_acceptable_containers(self) -> None:
        class _Authenticated[T_User]:
            user: T_User

        class MyView(generic.View):
            request: _Authenticated[int]  # type: ignore[assignment]

        self.runCheck(
            MyView,
            user_type=int,
            acceptable=(),
            acceptable_containers=(_Authenticated,),
        )

    def test_is_unhappy_with_incorrectly_unfilled_acceptable_containers(self) -> None:
        class _Authenticated[T_User]:
            user: T_User

        class MyView(generic.View):
            request: _Authenticated  # type: ignore[assignment,type-arg]

        with pytest.raises(enforcer_errors.InvalidRequestAnnotation) as e:
            self.runCheck(
                MyView,
                user_type=int,
                acceptable=(),
                acceptable_containers=(_Authenticated,),
            )

        test_helpers.checkers.expect_invalid_django_pattern_error(
            e.value,
            f"""
            [InvalidRequestAnnotation]
              Originating:
                module = m0
                name = w0
                namespace = n0
                regex = r0
              module = {__file__}
              class = MyView
              error = The annotation is not specifying a user model
              expect = {_Authenticated}-[<class 'int'>]
            ..expanded note..
            """,
        )

    def test_is_unhappy_with_incorrectly_filled_acceptable_containers(self) -> None:
        class _Authenticated[T_User]:
            user: T_User

        class MyView(generic.View):
            request: _Authenticated[str]  # type: ignore[assignment]

        with pytest.raises(enforcer_errors.InvalidRequestAnnotation) as e:
            self.runCheck(
                MyView,
                user_type=int,
                acceptable=(),
                acceptable_containers=(_Authenticated,),
            )

        test_helpers.checkers.expect_invalid_django_pattern_error(
            e.value,
            f"""
            [InvalidRequestAnnotation]
              Originating:
                module = m0
                name = w0
                namespace = n0
                regex = r0
              module = {__file__}
              class = MyView
              error = The annotation is specifying the wrong user model
              expect = {_Authenticated}-[<class 'int'>]
            ..expanded note..
            """,
        )
