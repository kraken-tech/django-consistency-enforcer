import importlib.resources
import pathlib
from collections.abc import Iterator

import django_consistency_enforcer_test_driver as test_helpers
import pytest
from django import http
from django.apps import apps
from django.conf import settings
from django.urls import resolvers

from django_consistency_enforcer import errors as enforcer_errors
from django_consistency_enforcer import urls as enforcer


class _CustomInvalidRequestAnnotation(enforcer_errors.InvalidRequestAnnotation):
    @property
    def expect(self) -> str:
        return "http.HttpRequest"

    @property
    def expanded_note(self) -> Iterator[str]:
        yield "In our example we have no specific request annotation"


class _CustomCheckPositionalArgsAreCorrectFunctionScenario[T_Pattern: enforcer.Pattern](
    enforcer.CheckPositionalArgsAreCorrectFunctionScenario[T_Pattern]
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


# The test replaces $PROJECT with absolute path to where this repository is checked out
_expected = r"""
[RequiredArgOnViewNotAlwaysRequiredByPattern]
  module = $PROJECT/example/djangoexample/views.py
  function = with_extra_args
  missing_from_urlpatterns = ['not_in_url']
  url patterns >>
    0 >
      module = $PROJECT/example/djangoexample/urls.py
      regex = ^/
    1 >
      module = $PROJECT/example/djangoexample/urls.py
      regex = ^/with\-extra\-args\Z
 :: Found arguments on the view that are not provided by any of the patterns that lead to that view
 :: You likely want to use Unpack on the kwargs with a NotRequired on these args
 :: Or give them default values if you have provided explicit keywords to the function

[RequiredArgOnViewNotAlwaysRequiredByPattern]
  module = $PROJECT/example/djangoexample/views.py
  class = IncorrectView
  method = post
  missing_from_urlpatterns = ['not_in_url']
  url patterns >>
    0 >
      module = $PROJECT/example/djangoexample/urls.py
      regex = ^/
    1 >
      module = $PROJECT/example/djangoexample/urls.py
      regex = ^/incorrect\-view/(?P<should_be_int>[0-9]+)\Z
 :: Found arguments on the view that are not provided by any of the patterns that lead to that view
 :: You likely want to use Unpack on the kwargs with a NotRequired on these args
 :: Or give them default values if you have provided explicit keywords to the function

[ViewDoesNotAcceptCapturedArg]
  Originating:
    module = $PROJECT/example/djangoexample/urls.py
    regex = ^/missing\-specific\-args/(?P<missing>[^/]+)/(?P<in_url>[0-9]+)\Z
  module = $PROJECT/example/djangoexample/views.py
  function = missing_specific_args
  Missing captured arg: missing
    module = $PROJECT/example/djangoexample/urls.py
    regex = ^/missing\-specific\-args/(?P<missing>[^/]+)/(?P<in_url>[0-9]+)\Z
 :: There are args in the pattern that the view is not aware of
 :: You likely want to add those extra arguments to the view!

[ViewDoesNotAcceptCapturedArg]
  Originating:
    module = $PROJECT/example/djangoexample/urls.py
    regex = ^/incorrect\-view/(?P<should_be_int>[0-9]+)\Z
  module = $PROJECT/example/djangoexample/views.py
  class = IncorrectView
  method = post
  Missing captured arg: should_be_int
    module = $PROJECT/example/djangoexample/urls.py
    regex = ^/incorrect\-view/(?P<should_be_int>[0-9]+)\Z
 :: There are args in the pattern that the view is not aware of
 :: You likely want to add those extra arguments to the view!

[InvalidArgAnnotations]
  Originating:
    module = $PROJECT/example/djangoexample/urls.py
    regex = ^/wrong\-type/(?P<should_be_int>[0-9]+)\Z
  module = $PROJECT/example/djangoexample/views.py
  function = wrong_type
  Found some args that have incorrect annotations:
    * Expected 'should_be_int' to be '<class 'int'>', found '<class 'str'>'
  :: When we defined url patterns we end up using converters that can change what
  :: type the view gets and we want to mirror this in our dispatch related signatures

[InvalidArgAnnotations]
  Originating:
    module = $PROJECT/example/djangoexample/urls.py
    regex = ^/incorrect\-view/(?P<should_be_int>[0-9]+)\Z
  module = $PROJECT/example/djangoexample/views.py
  class = IncorrectView
  method = get
  Found some args that have incorrect annotations:
    * Expected 'should_be_int' to be '<class 'int'>', found '<class 'str'>'
  :: When we defined url patterns we end up using converters that can change what
  :: type the view gets and we want to mirror this in our dispatch related signatures
"""


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

    with pytest.raises(enforcer_errors.FoundInvalidPatterns) as exc:
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
                _CustomCheckPositionalArgsAreCorrectFunctionScenario[enforcer.ViewPattern](),
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

    errors = "\n\n".join(exc.value.errors.by_most_repeated)
    expected = _expected.replace(
        "$PROJECT",
        str(pathlib.Path(str(importlib.resources.files("django_consistency_enforcer"))).parent),
    )

    pytest.LineMatcher(errors.strip().split("\n")).fnmatch_lines(expected.strip().split("\n"))
