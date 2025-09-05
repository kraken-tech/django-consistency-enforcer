from collections.abc import Callable
from typing import TypedDict, Unpack

import attrs
import django_consistency_enforcer_test_driver as test_helpers
import pytest
from django import http
from django.views import generic

from django_consistency_enforcer import errors as enforcer_errors
from django_consistency_enforcer import urls as enforcer


class TestRequiredArgsAreCorrect:
    def runCheck(
        self,
        function: enforcer.DispatchFunction,
        *,
        cb: Callable[..., object] | None = None,
        scenario: enforcer.CheckPositionalArgsAreCorrectFunctionScenario,
        auth_user_model: type | None = None,
    ) -> None:
        if function.view_class:
            assert cb is None
            assert issubclass(function.view_class, generic.View)
            cb = function.view_class.as_view()
        else:
            assert cb is not None

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
                callback=cb,
            ),
        )
        if auth_user_model is None:

            class _UserType:
                pass

            auth_user_model = _UserType

        with test_helpers.checkers.expect_zero_or_one_errors() as errors:
            scenario.run(
                errors=errors,
                auth_user_model=auth_user_model,
                pattern=pattern,
                function=function,
            )

    def test_it_likes_when_func_required_args_are_correct(self) -> None:
        def my_view(
            request: http.HttpRequest, *args: object, **kwargs: object
        ) -> http.HttpResponse:
            return http.HttpResponse("hi")

        self.runCheck(
            enforcer.DispatchFunction.from_callback(
                my_view, positional=test_helpers.views.generic_view_positional
            ),
            cb=my_view,
            scenario=test_helpers.scenarios.AlwaysMistypedCheckPositionalArgsAreCorrectFunctionScenario(),
        )

    def test_it_can_complain_about_the_existence_of_star_args(self) -> None:
        def my_view(
            request: http.HttpRequest, *args: object, **kwargs: object
        ) -> http.HttpResponse:
            return http.HttpResponse("hi")

        with pytest.raises(enforcer_errors.MismatchedRequiredArgs) as e:
            self.runCheck(
                enforcer.DispatchFunction.from_callback(
                    my_view, positional=test_helpers.views.generic_view_positional
                ),
                cb=my_view,
                scenario=test_helpers.scenarios.AlwaysMistypedCheckPositionalArgsAreCorrectFunctionScenario(
                    disallow_var_args=True
                ),
            )

        test_helpers.checkers.expect_invalid_django_pattern_error(
            e.value,
            f"""
            [MismatchedRequiredArgs]
              module = {__file__}
              function = my_view
              Found some problems with the arguments to some functions:
                * Please remove the var args '*args' from the function signature and ensure all arguments are explicit
              :: We want to create consistency around the names and types of the positional
              :: arguments to specific functions on the Django views
            """,
        )

    def test_it_can_enforce_that_all_args_are_keyword_only(self) -> None:
        def my_view(request: http.HttpRequest, one: int) -> http.HttpResponse:
            return http.HttpResponse("hi")

        with pytest.raises(enforcer_errors.MismatchedRequiredArgs) as e:
            self.runCheck(
                enforcer.DispatchFunction.from_callback(
                    my_view, positional=test_helpers.views.generic_view_positional
                ),
                cb=my_view,
                scenario=test_helpers.scenarios.AlwaysMistypedCheckPositionalArgsAreCorrectFunctionScenario(
                    enforce_keyword_args=True
                ),
            )

        test_helpers.checkers.expect_invalid_django_pattern_error(
            e.value,
            f"""
            [MismatchedRequiredArgs]
              module = {__file__}
              function = my_view
              Found some problems with the arguments to some functions:
                * Please ensure the 'one' argument comes after a lone '*' so that it is defined as keyword only
              :: We want to create consistency around the names and types of the positional
              :: arguments to specific functions on the Django views
            """,
        )

    def test_it_allows_unpack_when_enforcing_keyword_only_and_no_varags(self) -> None:
        class _UrlArgs(TypedDict):
            one: int

        def my_view(request: http.HttpRequest, **kwargs: Unpack[_UrlArgs]) -> http.HttpResponse:
            return http.HttpResponse("hi")

        self.runCheck(
            enforcer.DispatchFunction.from_callback(
                my_view, positional=test_helpers.views.generic_view_positional
            ),
            cb=my_view,
            scenario=test_helpers.scenarios.AlwaysMistypedCheckPositionalArgsAreCorrectFunctionScenario(
                enforce_keyword_args=True, disallow_var_args=True
            ),
        )

    def test_it_complains_if_required_args_are_missing_raw_patterns_from_func(self) -> None:
        def my_view(*args: object, **kwargs: object) -> http.HttpResponse:
            return http.HttpResponse("hi")

        with pytest.raises(enforcer_errors.MismatchedRequiredArgs) as e:
            self.runCheck(
                enforcer.DispatchFunction.from_callback(
                    my_view, positional=test_helpers.views.generic_view_positional
                ),
                cb=my_view,
                scenario=test_helpers.scenarios.AlwaysMistypedCheckPositionalArgsAreCorrectFunctionScenario(),
            )

        test_helpers.checkers.expect_invalid_django_pattern_error(
            e.value,
            f"""
            [MismatchedRequiredArgs]
              module = {__file__}
              function = my_view
              Found some problems with the arguments to some functions:
                * Missing required positional argument: request
              :: We want to create consistency around the names and types of the positional
              :: arguments to specific functions on the Django views
            """,
        )

    def test_it_likes_when_function_required_args_are_correct(self) -> None:
        class MyView(generic.View):
            def blah(
                self, request: http.HttpRequest, *args: object, **kwargs: object
            ) -> http.HttpResponse:
                return http.HttpResponse("hi")

        self.runCheck(
            enforcer.DispatchFunction.from_callback(
                MyView.blah, MyView, positional=test_helpers.views.generic_view_positional
            ),
            scenario=test_helpers.scenarios.AlwaysMistypedCheckPositionalArgsAreCorrectFunctionScenario(),
        )

    def test_it_complains_when_required_args_are_missing_or_not_positional(self) -> None:
        class MyView(generic.View):
            def blah(self, *args: object, **kwargs: object) -> http.HttpResponse:
                return http.HttpResponse("hi")

            def meh(self, *, request: http.HttpRequest) -> http.HttpResponse:
                return http.HttpResponse("request must be positional!")

        with pytest.raises(enforcer_errors.MismatchedRequiredArgs) as e:
            self.runCheck(
                enforcer.DispatchFunction.from_callback(
                    MyView.blah, MyView, positional=test_helpers.views.generic_view_positional
                ),
                scenario=test_helpers.scenarios.AlwaysMistypedCheckPositionalArgsAreCorrectFunctionScenario(),
            )

        test_helpers.checkers.expect_invalid_django_pattern_error(
            e.value,
            f"""
            [MismatchedRequiredArgs]
              module = {__file__}
              class = MyView
              method = blah
              Found some problems with the arguments to some functions:
                * Missing required positional argument: request
              :: We want to create consistency around the names and types of the positional
              :: arguments to specific functions on the Django views
            """,
        )

        with pytest.raises(enforcer_errors.MismatchedRequiredArgs) as e:
            self.runCheck(
                enforcer.DispatchFunction.from_callback(
                    MyView.meh, MyView, positional=test_helpers.views.generic_view_positional
                ),
                scenario=test_helpers.scenarios.AlwaysMistypedCheckPositionalArgsAreCorrectFunctionScenario(),
            )

        test_helpers.checkers.expect_invalid_django_pattern_error(
            e.value,
            f"""
            [MismatchedRequiredArgs]
              module = {__file__}
              class = MyView
              method = meh
              Found some problems with the arguments to some functions:
                * Missing required positional argument: request
              :: We want to create consistency around the names and types of the positional
              :: arguments to specific functions on the Django views
            """,
        )

    def test_it_complains_when_wrong_name(self) -> None:
        class MyView(generic.View):
            def blah(
                self, one: http.HttpRequest, *args: object, **kwargs: object
            ) -> http.HttpResponse:
                return http.HttpResponse("hi")

        with pytest.raises(enforcer_errors.MismatchedRequiredArgs) as e:
            self.runCheck(
                enforcer.DispatchFunction.from_callback(
                    MyView.blah, MyView, positional=(("two", http.HttpRequest),)
                ),
                scenario=test_helpers.scenarios.AlwaysMistypedCheckPositionalArgsAreCorrectFunctionScenario(),
            )

        test_helpers.checkers.expect_invalid_django_pattern_error(
            e.value,
            f"""
            [MismatchedRequiredArgs]
              module = {__file__}
              class = MyView
              method = blah
              Found some problems with the arguments to some functions:
                * The first argument should be named two, but got one
              :: We want to create consistency around the names and types of the positional
              :: arguments to specific functions on the Django views
            """,
        )

    def test_it_complains_when_wrong_type(self) -> None:
        class _Authenticated[T_User]:
            user: T_User

        class _User:
            pass

        called: list[object] = []

        @attrs.frozen(kw_only=True)
        class _StubCheckPositionalArgsAreCorrectFunctionScenario(
            enforcer.CheckPositionalArgsAreCorrectFunctionScenario
        ):
            def is_mistyped(
                self,
                *,
                function: enforcer.DispatchFunction,
                want_annotation: object,
                got_annotation: object,
                auth_user_model: type,
                name: str,
                position: int,
            ) -> enforcer_errors.MismatchedRequiredArgs.Incorrect | None:
                called.append(
                    (
                        function,
                        want_annotation,
                        got_annotation,
                        auth_user_model,
                        name,
                        position,
                    )
                )
                return enforcer_errors.MismatchedRequiredArgs.Incorrect.mistyped(
                    name="n1", got="a1", want="w1", add_auth_message=False
                )

        class MyView(generic.View):
            def blah(self, one: int, *args: object, **kwargs: object) -> http.HttpResponse:
                return http.HttpResponse("hi")

            def meh(
                self,
                request: _Authenticated[_User],
                *args: object,
                **kwargs: object,
            ) -> http.HttpResponse:
                return http.HttpResponse("hi")

        function = enforcer.DispatchFunction.from_callback(
            MyView.blah, MyView, positional=(("one", http.HttpRequest),)
        )

        with pytest.raises(enforcer_errors.MismatchedRequiredArgs) as e:
            self.runCheck(
                function,
                scenario=_StubCheckPositionalArgsAreCorrectFunctionScenario(
                    disallow_var_args=False, enforce_keyword_args=False
                ),
                auth_user_model=_User,
            )

        test_helpers.checkers.expect_invalid_django_pattern_error(
            e.value,
            f"""
            [MismatchedRequiredArgs]
              module = {__file__}
              class = MyView
              method = blah
              Found some problems with the arguments to some functions:
                * The 'n1' argument needs to be 'w1' but it's 'a1'
              :: We want to create consistency around the names and types of the positional
              :: arguments to specific functions on the Django views
            """,
        )

        assert called == [(function, http.HttpRequest, int, _User, "one", 0)]
