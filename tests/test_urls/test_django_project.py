from collections.abc import Iterator

import django_consistency_enforcer_test_driver as test_helpers
from django import http
from django.apps import apps
from django.conf import settings
from django.urls import resolvers

from django_consistency_enforcer import errors as enforcer_errors
from django_consistency_enforcer import urls as enforcer


class _CustomInvalidRequestAnnotation(enforcer_errors.InvalidRequestAnnotation):
    def expect(self) -> str:
        return "http.HttpRequest"

    @property
    def expanded_note(self) -> Iterator[str]:
        yield "In our example we have no specific request annotation"


class _CustomCheckPositionalArgsAreCorrectFunctionScenario(
    enforcer.CheckPositionalArgsAreCorrectFunctionScenario[enforcer.Pattern]
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
        return enforcer_errors.MismatchedRequiredArgs.Incorrect.mistyped(
            name=name, want=str(want_annotation), got=got_annotation
        )


def test_it_works_on_a_django_project() -> None:
    try:
        test_runner = enforcer.TestRunner.from_raw_patterns(
            raw_patterns=enforcer.all_django_patterns(resolver=resolvers.get_resolver()),
            raw_pattern_excluder=lambda raw_pattern: False,
            pattern_maker=test_helpers.patterns.from_raw_pattern,
        )
    except enforcer_errors.FoundInvalidPatterns as e:
        raise AssertionError(
            "Found invalid patterns in ROOT_URLCONF\n\n" + "\n\n".join(e.errors.by_most_repeated)
        ) from e

    auth_user_model = apps.get_model(settings.AUTH_USER_MODEL)

    try:
        test_runner.run_scenarios(
            auth_user_model=auth_user_model,
            pattern_scenarios=(
                #
                # Ensure the request annotation on the class is correct
                enforcer.CheckViewClassRequestAnnotationScenario(
                    acceptable_annotations=(http.HttpRequest,),
                    acceptable_request_annotation_containers=(http.HttpRequest,),
                    error_class=_CustomInvalidRequestAnnotation,
                ),
            ),
            function_scenarios=(
                #
                # Make sure kwargs has an annotation that makes sense
                enforcer.CheckKwargsMustBeAnnotatedFunctionScenario(
                    # Exit before other checks in case it's a case of the kwargs
                    # Trying to be an Unpack[SomeTypeDict] and forgetting the Unpack
                    exit_early=True,
                ),
                #
                # Make sure the positional args are correct
                _CustomCheckPositionalArgsAreCorrectFunctionScenario(),
                #
                # Make sure that if the view has a required arg, that this arg is provided by the
                # pattern
                enforcer.CheckRequiredArgsMatchUrlPatternFunctionScenario(),
                #
                # Make sure the view accepts every captured argument
                enforcer.CheckAcceptsArgsFunctionScenario(),
                #
                # Make sure the view has the correct annotations
                enforcer.CheckHasCorrectAnnotationsFunctionScenario(),
            ),
        )
    except enforcer_errors.FoundInvalidPatterns as e:
        raise AssertionError(
            "Found some django views with problems\n\n" + "\n\n".join(e.errors.by_most_repeated)
        ) from e
