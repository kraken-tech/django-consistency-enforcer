from typing import NotRequired, TypedDict, Unpack

import django_consistency_enforcer_test_driver as test_helpers
import pytest
from django import http
from django.views import generic

from django_consistency_enforcer import errors as enforcer_errors
from django_consistency_enforcer import urls as enforcer


class TestRequiredArgsOnViewNotInPattern:
    def test_is_fine_if_arg_in_default_args(self) -> None:
        def my_view(request: http.HttpRequest, *, one: int = 1, two: str) -> http.HttpResponse:
            return http.HttpResponse("hi")

        pattern = test_helpers.patterns.from_raw_pattern(
            enforcer.RawPattern.from_parts(
                [
                    enforcer.RawPatternPart(
                        groups=0,
                        captured={},
                        default_arg_names={"two"},
                        where=enforcer.Where.empty(),
                    ),
                ],
                where=enforcer.Where.empty(),
                callback=my_view,
            ),
        )

        with test_helpers.checkers.expect_zero_or_one_errors() as errors:
            enforcer.CheckRequiredArgsMatchUrlPatternFunctionScenario().run(
                errors=errors,
                auth_user_model=object,
                pattern=pattern,
                function=enforcer.DispatchFunction.from_callback(
                    my_view, positional=test_helpers.views.generic_view_positional
                ),
            )

    def test_func_is_fine_with_non_required_args_not_in_patterns(self) -> None:
        def my_view(request: http.HttpRequest, *, one: int = 1, two: str) -> http.HttpResponse:
            return http.HttpResponse("hi")

        pattern = test_helpers.patterns.from_raw_pattern(
            enforcer.RawPattern.from_parts(
                [
                    enforcer.RawPatternPart(
                        groups=1,
                        captured={"two": enforcer.CapturedArg(annotation=str)},
                        where=enforcer.Where.empty(),
                    ),
                ],
                where=enforcer.Where.empty(),
                callback=my_view,
            ),
        )

        with test_helpers.checkers.expect_zero_or_one_errors() as errors:
            enforcer.CheckRequiredArgsMatchUrlPatternFunctionScenario().run(
                errors=errors,
                auth_user_model=object,
                pattern=pattern,
                function=enforcer.DispatchFunction.from_callback(
                    my_view, positional=test_helpers.views.generic_view_positional
                ),
            )

    def test_class_is_fine_with_non_required_args_not_in_patterns(self) -> None:
        class MyView(generic.View):
            def get(self, request: http.HttpRequest, *, two: str) -> http.HttpResponse:
                return http.HttpResponse("hi")

            def post(
                self, request: http.HttpRequest, *, one: int = 1, two: str
            ) -> http.HttpResponse:
                return http.HttpResponse("hi")

        pattern = test_helpers.patterns.from_raw_pattern(
            enforcer.RawPattern.from_parts(
                [
                    enforcer.RawPatternPart(
                        groups=1,
                        captured={"two": enforcer.CapturedArg(annotation=str)},
                        where=enforcer.Where.empty(),
                    ),
                ],
                where=enforcer.Where.empty(),
                callback=MyView.as_view(),
            ),
        )

        with test_helpers.checkers.expect_zero_or_one_errors() as errors:
            enforcer.CheckRequiredArgsMatchUrlPatternFunctionScenario().run(
                errors=errors,
                auth_user_model=object,
                pattern=pattern,
                function=enforcer.DispatchFunction.from_callback(
                    MyView.get, MyView, positional=test_helpers.views.generic_view_positional
                ),
            )

        with test_helpers.checkers.expect_zero_or_one_errors() as errors:
            enforcer.CheckRequiredArgsMatchUrlPatternFunctionScenario().run(
                errors=errors,
                auth_user_model=object,
                pattern=pattern,
                function=enforcer.DispatchFunction.from_callback(
                    MyView.post, MyView, positional=test_helpers.views.generic_view_positional
                ),
            )

    def test_func_is_not_fine_with_required_args_not_in_patterns(self) -> None:
        def my_view(request: http.HttpRequest, *, one: int, two: str) -> http.HttpResponse:
            return http.HttpResponse("hi")

        pattern = test_helpers.patterns.from_raw_pattern(
            enforcer.RawPattern.from_parts(
                [
                    enforcer.RawPatternPart(
                        groups=0,
                        captured={},
                        where=enforcer.Where(name="w1", module="m1", namespace="n1", regex="r1"),
                    ),
                    enforcer.RawPatternPart(
                        groups=2,
                        captured={"two": enforcer.CapturedArg(annotation=str)},
                        where=enforcer.Where(name="w2", module="m2", namespace="n2", regex="r2"),
                    ),
                ],
                where=enforcer.Where(name="w0", module="m0", namespace="n0", regex="r0"),
                callback=my_view,
            ),
        )

        with pytest.raises(enforcer_errors.RequiredArgOnViewNotAlwaysRequiredByPattern) as e:
            # nosemgrep: semgrep.only-one-statement-in-pytest-raises
            with test_helpers.checkers.expect_zero_or_one_errors() as errors:
                enforcer.CheckRequiredArgsMatchUrlPatternFunctionScenario().run(
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
            [RequiredArgOnViewNotAlwaysRequiredByPattern]
              module = {__file__}
              function = my_view
              missing_from_urlpatterns = ['one']
              url patterns >>
                0 >
                  module = m1
                  name = w1
                  namespace = n1
                  regex = r1
                1 >
                  module = m2
                  name = w2
                  namespace = n2
                  regex = r2
             :: Found arguments on the view that are not provided by any of the patterns that lead to that view
             :: You likely want to use Unpack on the kwargs with a NotRequired on these args
             :: Or give them default values if you have provided explicit keywords to the function
            """,
        )

    def test_class_is_not_fine_with_non_required_args_not_in_patterns(self) -> None:
        class MyViewParent(generic.View):
            def get(self, request: http.HttpRequest, *, two: str) -> http.HttpResponse:
                return http.HttpResponse("hi")

            def post(self, request: http.HttpRequest, *, one: int, two: str) -> http.HttpResponse:
                return http.HttpResponse("hi")

        class MyView(MyViewParent):
            class _PutArgs(TypedDict):
                three: bool
                two: str
                four: int
                five: NotRequired[str]

            def put(
                self, request: http.HttpRequest, **kwargs: Unpack[_PutArgs]
            ) -> http.HttpResponse:
                return http.HttpResponse("hi")

        pattern = test_helpers.patterns.from_raw_pattern(
            enforcer.RawPattern.from_parts(
                [
                    enforcer.RawPatternPart(
                        groups=0,
                        captured={},
                        where=enforcer.Where(name="w1", module="m1", namespace="n1", regex="r1"),
                    ),
                    enforcer.RawPatternPart(
                        groups=2,
                        captured={"two": enforcer.CapturedArg(annotation=str)},
                        where=enforcer.Where(name="w2", module="m2", namespace="n2", regex="r2"),
                    ),
                ],
                where=enforcer.Where(name="w0", module="m0", namespace="n0", regex="r0"),
                callback=MyView.as_view(),
            ),
        )

        with test_helpers.checkers.expect_zero_or_one_errors() as errors:
            enforcer.CheckRequiredArgsMatchUrlPatternFunctionScenario().run(
                errors=errors,
                auth_user_model=object,
                pattern=pattern,
                function=enforcer.DispatchFunction.from_callback(
                    MyView.get, MyView, positional=test_helpers.views.generic_view_positional
                ),
            )

        with pytest.raises(enforcer_errors.RequiredArgOnViewNotAlwaysRequiredByPattern) as e:
            # nosemgrep: semgrep.only-one-statement-in-pytest-raises
            with test_helpers.checkers.expect_zero_or_one_errors() as errors:
                enforcer.CheckRequiredArgsMatchUrlPatternFunctionScenario().run(
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
            [RequiredArgOnViewNotAlwaysRequiredByPattern]
              module = {__file__}
              class = MyViewParent
              method = post
              missing_from_urlpatterns = ['one']
              url patterns >>
                0 >
                  module = m1
                  name = w1
                  namespace = n1
                  regex = r1
                1 >
                  module = m2
                  name = w2
                  namespace = n2
                  regex = r2
             :: Found arguments on the view that are not provided by any of the patterns that lead to that view
             :: You likely want to use Unpack on the kwargs with a NotRequired on these args
             :: Or give them default values if you have provided explicit keywords to the function
            """,
        )

        with pytest.raises(enforcer_errors.RequiredArgOnViewNotAlwaysRequiredByPattern) as e:
            # nosemgrep: semgrep.only-one-statement-in-pytest-raises
            with test_helpers.checkers.expect_zero_or_one_errors() as errors:
                enforcer.CheckRequiredArgsMatchUrlPatternFunctionScenario().run(
                    errors=errors,
                    auth_user_model=object,
                    pattern=pattern,
                    function=enforcer.DispatchFunction.from_callback(
                        MyView.put, MyView, positional=test_helpers.views.generic_view_positional
                    ),
                )

        test_helpers.checkers.expect_invalid_django_pattern_error(
            e.value,
            f"""
            [RequiredArgOnViewNotAlwaysRequiredByPattern]
              module = {__file__}
              class = MyView
              method = put
              missing_from_urlpatterns = ['four', 'three']
              url patterns >>
                0 >
                  module = m1
                  name = w1
                  namespace = n1
                  regex = r1
                1 >
                  module = m2
                  name = w2
                  namespace = n2
                  regex = r2
             :: Found arguments on the view that are not provided by any of the patterns that lead to that view
             :: You likely want to use Unpack on the kwargs with a NotRequired on these args
             :: Or give them default values if you have provided explicit keywords to the function
            """,
        )
