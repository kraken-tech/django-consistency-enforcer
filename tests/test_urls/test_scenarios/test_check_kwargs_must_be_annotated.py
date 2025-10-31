from collections.abc import Callable
from typing import Any, TypedDict, Unpack

import django_consistency_enforcer_test_driver as test_helpers
import pytest
from django import http

from django_consistency_enforcer import errors as enforcer_errors
from django_consistency_enforcer import urls as enforcer


class TestCheckKwargsMustBeAnnotatedFunctionScenario:
    def runCheck(
        self, callback: Callable[..., http.HttpResponse], *, allows_object: bool, allows_any: bool
    ) -> None:
        pattern = test_helpers.patterns.from_raw_pattern(
            enforcer.RawPattern.from_parts(
                [
                    enforcer.RawPatternPart(
                        groups=0,
                        captured={},
                        default_arg_names=set(),
                        where=enforcer.Where.empty(),
                    ),
                ],
                where=enforcer.Where.empty(),
                callback=callback,
            ),
        )

        function = enforcer.DispatchFunction.from_callback(
            callback=callback, view_class=None, positional=(("request", http.HttpRequest),)
        )

        with test_helpers.checkers.expect_zero_or_one_errors() as errors:
            enforcer.CheckKwargsMustBeAnnotatedFunctionScenario(
                allows_any=allows_any, allows_object=allows_object
            ).run(errors=errors, auth_user_model=object, pattern=pattern, function=function)

    def test_it_complains_if_kwargs_is_any_and_not_allowed(self) -> None:
        def my_view(request: http.HttpRequest, **kwargs: Any) -> http.HttpResponse:
            return http.HttpResponse("hi")

        # With allows_any it doesn't complain
        self.runCheck(my_view, allows_any=True, allows_object=True)
        self.runCheck(my_view, allows_any=True, allows_object=False)

        # Without allows_any it does complain
        with pytest.raises(enforcer_errors.KwargsMustBeAnnotated) as e:
            self.runCheck(my_view, allows_any=False, allows_object=True)

        test_helpers.checkers.expect_invalid_django_pattern_error(
            e.value,
            f"""
            [KwargsMustBeAnnotated]
              module = {__file__}
              function = my_view
              :: Please ensure `**kwargs` has an annotation using typing.Unpack or specify keyword arguments explicitly
              :: or use `**kwargs: object`
            """,
        )

        with pytest.raises(enforcer_errors.KwargsMustBeAnnotated) as e:
            self.runCheck(my_view, allows_any=False, allows_object=False)

        test_helpers.checkers.expect_invalid_django_pattern_error(
            e.value,
            f"""
            [KwargsMustBeAnnotated]
              module = {__file__}
              function = my_view
              :: Please ensure `**kwargs` has an annotation using typing.Unpack or specify keyword arguments explicitly
            """,
        )

    def test_it_complains_if_kwargs_is_object_and_not_allowed(self) -> None:
        def my_view(request: http.HttpRequest, **kwargs: object) -> http.HttpResponse:
            return http.HttpResponse("hi")

        # With allows_object it doesn't complain
        self.runCheck(my_view, allows_any=True, allows_object=True)
        self.runCheck(my_view, allows_any=False, allows_object=True)

        # Without allows_object it does complain
        with pytest.raises(enforcer_errors.KwargsMustBeAnnotated) as e:
            self.runCheck(my_view, allows_any=False, allows_object=False)

        test_helpers.checkers.expect_invalid_django_pattern_error(
            e.value,
            f"""
            [KwargsMustBeAnnotated]
              module = {__file__}
              function = my_view
              :: Please ensure `**kwargs` has an annotation using typing.Unpack or specify keyword arguments explicitly
            """,
        )

        with pytest.raises(enforcer_errors.KwargsMustBeAnnotated) as e:
            self.runCheck(my_view, allows_any=True, allows_object=False)

        test_helpers.checkers.expect_invalid_django_pattern_error(
            e.value,
            f"""
            [KwargsMustBeAnnotated]
              module = {__file__}
              function = my_view
              :: Please ensure `**kwargs` has an annotation using typing.Unpack or specify keyword arguments explicitly
              :: or use `**kwargs: Any` from the typing module
            """,
        )

    def test_it_complains_if_kwargs_is_not_object_or_any_or_unpack(self) -> None:
        def my_view(request: http.HttpRequest, **kwargs: str) -> http.HttpResponse:
            return http.HttpResponse("hi")

        with pytest.raises(enforcer_errors.KwargsMustBeAnnotated) as e:
            self.runCheck(my_view, allows_any=True, allows_object=True)

        test_helpers.checkers.expect_invalid_django_pattern_error(
            e.value,
            f"""
            [KwargsMustBeAnnotated]
              module = {__file__}
              function = my_view
              :: Please ensure `**kwargs` has an annotation using typing.Unpack or specify keyword arguments explicitly
              :: or use `**kwargs: object`
              :: or use `**kwargs: Any` from the typing module
            """,
        )

        with pytest.raises(enforcer_errors.KwargsMustBeAnnotated) as e:
            self.runCheck(my_view, allows_any=False, allows_object=False)

        test_helpers.checkers.expect_invalid_django_pattern_error(
            e.value,
            f"""
            [KwargsMustBeAnnotated]
              module = {__file__}
              function = my_view
              :: Please ensure `**kwargs` has an annotation using typing.Unpack or specify keyword arguments explicitly
            """,
        )

        with pytest.raises(enforcer_errors.KwargsMustBeAnnotated) as e:
            self.runCheck(my_view, allows_any=True, allows_object=False)

        test_helpers.checkers.expect_invalid_django_pattern_error(
            e.value,
            f"""
            [KwargsMustBeAnnotated]
              module = {__file__}
              function = my_view
              :: Please ensure `**kwargs` has an annotation using typing.Unpack or specify keyword arguments explicitly
              :: or use `**kwargs: Any` from the typing module
            """,
        )

        with pytest.raises(enforcer_errors.KwargsMustBeAnnotated) as e:
            self.runCheck(my_view, allows_any=False, allows_object=True)

        test_helpers.checkers.expect_invalid_django_pattern_error(
            e.value,
            f"""
            [KwargsMustBeAnnotated]
              module = {__file__}
              function = my_view
              :: Please ensure `**kwargs` has an annotation using typing.Unpack or specify keyword arguments explicitly
              :: or use `**kwargs: object`
            """,
        )

    def test_it_likes_explicit_args(self) -> None:
        def my_view(request: http.HttpRequest, *, one: str, two: int) -> http.HttpResponse:
            return http.HttpResponse("hi")

        self.runCheck(my_view, allows_any=True, allows_object=True)
        self.runCheck(my_view, allows_any=False, allows_object=False)
        self.runCheck(my_view, allows_any=True, allows_object=False)
        self.runCheck(my_view, allows_any=False, allows_object=True)

    def test_it_likes_explicit_unpack(self) -> None:
        class _UrlArgs(TypedDict):
            one: str
            two: int

        def my_view(request: http.HttpRequest, **kwargs: Unpack[_UrlArgs]) -> http.HttpResponse:
            return http.HttpResponse("hi")

        self.runCheck(my_view, allows_any=True, allows_object=True)
        self.runCheck(my_view, allows_any=False, allows_object=False)
        self.runCheck(my_view, allows_any=True, allows_object=False)
        self.runCheck(my_view, allows_any=False, allows_object=True)
