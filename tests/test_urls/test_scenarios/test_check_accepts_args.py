from typing import NotRequired, TypedDict, Unpack

import django_consistency_enforcer_test_driver as test_helpers
import pytest
from django import http
from django.views import generic

from django_consistency_enforcer import errors as enforcer_errors
from django_consistency_enforcer import urls as enforcer


class TestRequiredArgsInPatternNotOnView:
    def test_complains_if_missing_default_arg(self) -> None:
        def my_view(request: http.HttpRequest, *, one: int = 1) -> http.HttpResponse:
            return http.HttpResponse("hi")

        pattern = test_helpers.patterns.from_raw_pattern(
            enforcer.RawPattern.from_parts(
                [
                    enforcer.RawPatternPart(
                        groups=0,
                        captured={},
                        default_arg_names={"two"},
                        where=enforcer.Where(name="w1", module="m1", namespace="n1", regex="r1"),
                    ),
                ],
                where=enforcer.Where(name="w0", module="m0", namespace="n0", regex="r0"),
                callback=my_view,
            ),
        )

        with pytest.raises(enforcer_errors.ViewDoesNotAcceptCapturedArg) as e:
            # nosemgrep: semgrep.only-one-statement-in-pytest-raises
            with test_helpers.checkers.expect_zero_or_one_errors() as errors:
                enforcer.CheckAcceptsArgsFunctionScenario().run(
                    errors=errors,
                    auth_user_model=object,
                    pattern=pattern,
                    function=enforcer.DispatchFunction.from_callback(
                        my_view, positional=test_helpers.views.generic_view_positional
                    ),
                )

        test_helpers.checkers.expect_invalid_django_pattern_error(
            e.value,
            f"""
            [ViewDoesNotAcceptCapturedArg]
              Originating:
                module = m1
                name = w1
                namespace = n1
                regex = r1
              module = {__file__}
              function = my_view
              Missing captured arg: two
                module = m1
                name = w1
                namespace = n1
                regex = r1
             :: There are args in the pattern that the view is not aware of
             :: You likely want to add those extra arguments to the view!
            """,
        )

    def test_func_with_missing_args(self) -> None:
        def my_view(request: http.HttpRequest, *, one: int = 1, two: str) -> http.HttpResponse:
            return http.HttpResponse("hi")

        pattern = test_helpers.patterns.from_raw_pattern(
            enforcer.RawPattern.from_parts(
                [
                    enforcer.RawPatternPart(
                        groups=1,
                        captured={"two": enforcer.CapturedArg(annotation=str)},
                        where=enforcer.Where(name="w1", module="m1", namespace="n1", regex="r1"),
                    ),
                    enforcer.RawPatternPart(
                        groups=2,
                        captured={
                            "one": enforcer.CapturedArg(annotation=str),
                            "three": enforcer.CapturedArg(annotation=int),
                        },
                        where=enforcer.Where(name="w2", module="m2", namespace="n2", regex="r2"),
                    ),
                ],
                where=enforcer.Where(name="w0", module="m0", namespace="n0", regex="r0"),
                callback=my_view,
            ),
        )

        with pytest.raises(enforcer_errors.ViewDoesNotAcceptCapturedArg) as e:
            # nosemgrep: semgrep.only-one-statement-in-pytest-raises
            with test_helpers.checkers.expect_zero_or_one_errors() as errors:
                enforcer.CheckAcceptsArgsFunctionScenario().run(
                    errors=errors,
                    auth_user_model=object,
                    pattern=pattern,
                    function=enforcer.DispatchFunction.from_callback(
                        my_view, positional=test_helpers.views.generic_view_positional
                    ),
                )

        test_helpers.checkers.expect_invalid_django_pattern_error(
            e.value,
            f"""
            [ViewDoesNotAcceptCapturedArg]
              Originating:
                module = m2
                name = w2
                namespace = n2
                regex = r2
              module = {__file__}
              function = my_view
              Missing captured arg: three
                module = m2
                name = w2
                namespace = n2
                regex = r2
             :: There are args in the pattern that the view is not aware of
             :: You likely want to add those extra arguments to the view!
            """,
        )

    def test_class_with_missing_args(self) -> None:
        class MyViewParent(generic.View):
            def get(self, request: http.HttpRequest, *, one: str) -> http.HttpResponse:
                return http.HttpResponse("hi")

            class _PostArgs(TypedDict):
                one: NotRequired[int]
                two: str

            def post(
                self, request: http.HttpRequest, **kwargs: Unpack[_PostArgs]
            ) -> http.HttpResponse:
                return http.HttpResponse("hi")

        class MyView(MyViewParent):
            def trace(self, request: http.HttpRequest, *, three: int) -> http.HttpResponse:
                return http.HttpResponse("hi")

        pattern = test_helpers.patterns.from_raw_pattern(
            enforcer.RawPattern.from_parts(
                [
                    enforcer.RawPatternPart(
                        groups=1,
                        captured={"two": enforcer.CapturedArg(annotation=str)},
                        where=enforcer.Where(name="w1", module="m1", namespace="n1", regex="r1"),
                    ),
                    enforcer.RawPatternPart(
                        groups=2,
                        captured={
                            "one": enforcer.CapturedArg(annotation=str),
                            "three": enforcer.CapturedArg(annotation=int),
                        },
                        where=enforcer.Where(name="w2", module="m2", namespace="n2", regex="r2"),
                    ),
                ],
                where=enforcer.Where(name="w0", module="m0", namespace="n0", regex="r0"),
                callback=MyView.as_view(),
            ),
        )

        with pytest.raises(enforcer_errors.ViewDoesNotAcceptCapturedArg) as e:
            # nosemgrep: semgrep.only-one-statement-in-pytest-raises
            with test_helpers.checkers.expect_zero_or_one_errors() as errors:
                enforcer.CheckAcceptsArgsFunctionScenario().run(
                    errors=errors,
                    auth_user_model=object,
                    pattern=pattern,
                    function=enforcer.DispatchFunction.from_callback(
                        MyView.get, MyView, positional=test_helpers.views.generic_view_positional
                    ),
                )

        test_helpers.checkers.expect_invalid_django_pattern_error(
            e.value,
            f"""
            [ViewDoesNotAcceptCapturedArg]
              Originating:
                module = m2
                name = w2
                namespace = n2
                regex = r2
              module = {__file__}
              class = MyViewParent
              method = get
              Missing captured arg: two
                module = m1
                name = w1
                namespace = n1
                regex = r1
              Missing captured arg: three
                module = m2
                name = w2
                namespace = n2
                regex = r2
             :: There are args in the pattern that the view is not aware of
             :: You likely want to add those extra arguments to the view!
            """,
        )

        with pytest.raises(enforcer_errors.ViewDoesNotAcceptCapturedArg) as e:
            # nosemgrep: semgrep.only-one-statement-in-pytest-raises
            with test_helpers.checkers.expect_zero_or_one_errors() as errors:
                enforcer.CheckAcceptsArgsFunctionScenario().run(
                    errors=errors,
                    auth_user_model=object,
                    pattern=pattern,
                    function=enforcer.DispatchFunction.from_callback(
                        MyView.post, MyView, positional=test_helpers.views.generic_view_positional
                    ),
                )

        test_helpers.checkers.expect_invalid_django_pattern_error(
            e.value,
            f"""
            [ViewDoesNotAcceptCapturedArg]
              Originating:
                module = m2
                name = w2
                namespace = n2
                regex = r2
              module = {__file__}
              class = MyViewParent
              method = post
              Missing captured arg: three
                module = m2
                name = w2
                namespace = n2
                regex = r2
             :: There are args in the pattern that the view is not aware of
             :: You likely want to add those extra arguments to the view!
            """,
        )

        with pytest.raises(enforcer_errors.ViewDoesNotAcceptCapturedArg) as e:
            # nosemgrep: semgrep.only-one-statement-in-pytest-raises
            with test_helpers.checkers.expect_zero_or_one_errors() as errors:
                enforcer.CheckAcceptsArgsFunctionScenario().run(
                    errors=errors,
                    auth_user_model=object,
                    pattern=pattern,
                    function=enforcer.DispatchFunction.from_callback(
                        MyView.trace, MyView, positional=test_helpers.views.generic_view_positional
                    ),
                )

        test_helpers.checkers.expect_invalid_django_pattern_error(
            e.value,
            f"""
            [ViewDoesNotAcceptCapturedArg]
              Originating:
                module = m2
                name = w2
                namespace = n2
                regex = r2
              module = {__file__}
              class = MyView
              method = trace
              Missing captured arg: two
                module = m1
                name = w1
                namespace = n1
                regex = r1
              Missing captured arg: one
                module = m2
                name = w2
                namespace = n2
                regex = r2
             :: There are args in the pattern that the view is not aware of
             :: You likely want to add those extra arguments to the view!
            """,
        )
