from collections.abc import Callable
from typing import NotRequired, TypedDict, Unpack

import django_consistency_enforcer_test_driver as test_helpers
import pytest
from django import http
from django.views import generic

from django_consistency_enforcer import errors as enforcer_errors
from django_consistency_enforcer import urls as enforcer


class TestRequiredArgsAreCorrectAnnotion:
    def runCheck(
        self,
        function: enforcer.DispatchFunction,
        *,
        cb: Callable[..., object] | None = None,
        parts: list[enforcer.RawPatternPart],
    ) -> None:
        if function.view_class:
            assert cb is None
            assert issubclass(function.view_class, generic.View)
            cb = function.view_class.as_view()
        else:
            assert cb is not None

        pattern = test_helpers.patterns.from_raw_pattern(
            enforcer.RawPattern.from_parts(
                parts,
                where=enforcer.Where(name="w0", module="m0", namespace="n0", regex="r0"),
                callback=cb,
            ),
        )

        with test_helpers.checkers.expect_zero_or_one_errors() as errors:
            enforcer.CheckHasCorrectAnnotationsFunctionScenario().run(
                errors=errors, auth_user_model=object, pattern=pattern, function=function
            )

    def test_it_likes_when_func_required_args_are_correct(self) -> None:
        def my_view(request: http.HttpRequest, *, one: int, two: str) -> http.HttpResponse:
            return http.HttpResponse("hi")

        self.runCheck(
            enforcer.DispatchFunction.from_callback(
                my_view, positional=test_helpers.views.generic_view_positional
            ),
            cb=my_view,
            parts=[
                enforcer.RawPatternPart(
                    groups=1,
                    captured={"one": test_helpers.comparators.CapturedInt()},
                    where=enforcer.Where(module="m1", name="name1", namespace="n1", regex="r1"),
                ),
                enforcer.RawPatternPart(
                    groups=1,
                    captured={"two": test_helpers.comparators.CapturedString()},
                    where=enforcer.Where(module="m2", name="name2", namespace="n2", regex="r2"),
                ),
            ],
        )

    def test_it_complains_when_func_required_args_are_incorrect(self) -> None:
        def my_view(request: http.HttpRequest, *, one: int, two: str) -> http.HttpResponse:
            return http.HttpResponse("hi")

        parts = [
            enforcer.RawPatternPart(
                groups=1,
                captured={"one": test_helpers.comparators.CapturedString()},
                where=enforcer.Where(module="m1", name="w1", namespace="n1", regex="r1"),
            ),
            enforcer.RawPatternPart(
                groups=1,
                captured={"two": test_helpers.comparators.CapturedInt()},
                where=enforcer.Where(module="m2", name="w2", namespace="n2", regex="r2"),
            ),
        ]

        with pytest.raises(enforcer_errors.InvalidArgAnnotations) as e:
            self.runCheck(
                enforcer.DispatchFunction.from_callback(
                    my_view, positional=test_helpers.views.generic_view_positional
                ),
                cb=my_view,
                parts=parts,
            )

        test_helpers.checkers.expect_invalid_django_pattern_error(
            e.value,
            f"""
            [InvalidArgAnnotations]
              Originating:
                module = m0
                name = w0
                namespace = n0
                regex = r0
              module = {__file__}
              function = my_view
              Found some args that have incorrect annotations:
                * Expected 'one' to be '<class 'str'>', found '<class 'int'>'
                * Expected 'two' to be '<class 'int'>', found '<class 'str'>'
              :: When we defined url patterns we end up using converters that can change what
              :: type the view gets and we want to mirror this in our dispatch related signatures
            """,
        )

    def test_it_complains_when_typed_dict_required_args_are_incorrect(self) -> None:
        class MyView(generic.View):
            class _Args(TypedDict):
                three: int
                four: NotRequired[str]

            def get(self, request: http.HttpRequest, **kwargs: Unpack[_Args]) -> http.HttpResponse:
                return http.HttpResponse("hi")

        parts = [
            enforcer.RawPatternPart(
                groups=1,
                captured={"three": test_helpers.comparators.CapturedString()},
                where=enforcer.Where(module="m1", name="w1", namespace="n1", regex="r1"),
            ),
            enforcer.RawPatternPart(
                groups=1,
                captured={"four": test_helpers.comparators.CapturedInt()},
                where=enforcer.Where(module="m2", name="w2", namespace="n2", regex="r2"),
            ),
        ]

        with pytest.raises(enforcer_errors.InvalidArgAnnotations) as e:
            self.runCheck(
                enforcer.DispatchFunction.from_callback(
                    MyView.get, MyView, positional=test_helpers.views.generic_view_positional
                ),
                parts=parts,
            )

        test_helpers.checkers.expect_invalid_django_pattern_error(
            e.value,
            f"""
            [InvalidArgAnnotations]
              Originating:
                module = m0
                name = w0
                namespace = n0
                regex = r0
              module = {__file__}
              class = MyView
              method = get
              Found some args that have incorrect annotations:
                * Expected 'three' to be '<class 'str'>', found '<class 'int'>'
                * Expected 'four' to be '<class 'int'>', found '<class 'str'>'
              :: When we defined url patterns we end up using converters that can change what
              :: type the view gets and we want to mirror this in our dispatch related signatures
            """,
        )
