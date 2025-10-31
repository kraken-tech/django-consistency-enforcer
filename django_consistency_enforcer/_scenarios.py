from __future__ import annotations

import abc
import typing
from collections.abc import Sequence
from typing import Any, Generic

import attrs

from . import _display, _errors, _functions, _view_patterns


class PatternScenario(Generic[_view_patterns.T_Pattern], abc.ABC):  # noqa: UP046
    """
    Represents a check that is run on a specific pattern.
    """

    @property
    @abc.abstractmethod
    def exit_early(self) -> bool:
        """
        Used to indicate that if this scenario fails, no other pattern scenarios
        should be run.
        """

    @abc.abstractmethod
    def run(
        self,
        *,
        errors: _errors.ErrorContainer,
        auth_user_model: type,
        pattern: _view_patterns.T_Pattern,
    ) -> None:
        """
        This is where the logic for the check needs to go.
        """


class FunctionScenario(Generic[_view_patterns.T_Pattern], abc.ABC):  # noqa: UP046
    """
    Represents a check that is run on a specific Django view.
    """

    @property
    @abc.abstractmethod
    def exit_early(self) -> bool:
        """
        Used to indicate that if this scenario fails, no other pattern scenarios
        should be run.
        """

    @abc.abstractmethod
    def run(
        self,
        *,
        errors: _errors.ErrorContainer,
        auth_user_model: type,
        pattern: _view_patterns.T_Pattern,
        function: _functions.DispatchFunction,
    ) -> None:
        """
        This is where the logic for the check needs to go.
        """


@attrs.frozen
class CheckPositionalArgsAreCorrectFunctionScenario(
    FunctionScenario[_view_patterns.T_Pattern], abc.ABC
):
    """
    This is a scenario that checks that the positional arguments on a view are
    correct.

    This view needs to be subclass'd with an implementation for `is_mistyped`.
    """

    disallow_var_args: bool = True
    enforce_keyword_args: bool = True
    exit_early: bool = False

    def run(
        self,
        *,
        errors: _errors.ErrorContainer,
        auth_user_model: type,
        pattern: _view_patterns.T_Pattern,
        function: _functions.DispatchFunction,
    ) -> None:
        """
        This check looks at all the function_args and:

        * Skips the `self` argument
        * Matches the positional arguments found on the view against the
          required arguments defined by `function`

          - Complains about `*args` if `self.disallow_var_args`
          - Complains about a missing `*` after required positional args if
            `self.enforce_keyword_args`
          - Calls into `is_mistyped` to get an error if the annotation on the
            argument is neither `Any` or the expected annotation for that argument.
        """
        incorrect: list[_errors.MismatchedRequiredArgs.Incorrect] = []
        positional = list(function.positional)

        position = -1
        for arg in function.function_args:
            if arg.is_self:
                continue

            position += 1
            if positional:
                name, annotation = positional.pop(0)
                if arg.is_variable_positional:
                    incorrect.append(_errors.MismatchedRequiredArgs.Incorrect.missing(name))
                    break

                elif arg.keyword_only:
                    incorrect.append(_errors.MismatchedRequiredArgs.Incorrect.missing(name))

                elif arg.name != name:
                    incorrect.append(
                        _errors.MismatchedRequiredArgs.Incorrect.misnamed(
                            index=position, want=name, got=arg.name
                        )
                    )
                elif arg.annotation not in (Any, annotation):
                    result = self.is_mistyped(
                        name=name,
                        position=position,
                        function=function,
                        got_annotation=arg.annotation,
                        want_annotation=annotation,
                        auth_user_model=auth_user_model,
                    )
                    if result is not None:
                        incorrect.append(result)
            else:
                if arg.keyword_only:
                    break

                if arg.is_variable_positional and self.disallow_var_args:
                    incorrect.append(
                        _errors.MismatchedRequiredArgs.Incorrect.no_var_args(name=arg.name)
                    )

                elif self.enforce_keyword_args:
                    incorrect.append(
                        _errors.MismatchedRequiredArgs.Incorrect.make_keyword_only(name=arg.name)
                    )

        if incorrect:
            self.add_error(
                errors=errors,
                error=_errors.MismatchedRequiredArgs(function=function, incorrect=incorrect),
            )

    def add_error(
        self, *, errors: _errors.ErrorContainer, error: _errors.MismatchedRequiredArgs
    ) -> None:
        """
        Add an error to come out of the scenario.
        """
        errors.add(error)

    @abc.abstractmethod
    def is_mistyped(
        self,
        *,
        function: _functions.DispatchFunction,
        want_annotation: object,
        got_annotation: object,
        auth_user_model: type,
        name: str,
        position: int,
    ) -> _errors.MismatchedRequiredArgs.Incorrect | None:
        """
        Used to determine what error is appropriate when the annotation doesn't
        match for any of the required positional arguments.

        This is abstract cause deciding that is likely project specific.
        """


@attrs.frozen
class CheckRequiredArgsMatchUrlPatternFunctionScenario(
    FunctionScenario[_view_patterns.T_ViewPattern]
):
    """
    Checks that the arguments that are required by a function are found in
    the pattern that routes to the view.
    """

    exit_early: bool = False

    def run(
        self,
        *,
        errors: _errors.ErrorContainer,
        auth_user_model: type,
        pattern: _view_patterns.T_ViewPattern,
        function: _functions.DispatchFunction,
    ) -> None:
        """
        Discover the arguments that must be passed into the function and complain
        about any that are missing from the pattern.
        """
        missing: set[str] = set()

        positional = list(function.positional)

        for arg in function.function_args:
            if arg.is_self:
                continue

            if positional:
                positional.pop(0)
                continue

            if (
                arg.required
                and not any(arg.name in part.captured for part in pattern.parts)
                and not any(arg.name in part.default_arg_names for part in pattern.parts)
            ):
                missing.add(arg.name)

        if missing:
            self.add_error(
                errors=errors,
                error=_errors.RequiredArgOnViewNotAlwaysRequiredByPattern(
                    pattern_wheres=[part.where for part in pattern.parts],
                    function_where=function.display,
                    missing_args=missing,
                ),
            )

    def add_error(
        self,
        *,
        errors: _errors.ErrorContainer,
        error: _errors.RequiredArgOnViewNotAlwaysRequiredByPattern,
    ) -> None:
        """
        Add an error to come out of the scenario.
        """
        errors.add(error)


@attrs.frozen
class CheckAcceptsArgsFunctionScenario(FunctionScenario[_view_patterns.T_ViewPattern]):
    """
    Checks that all the arguments in the pattern are accepted by the function.
    """

    exit_early: bool = False

    def run(
        self,
        *,
        errors: _errors.ErrorContainer,
        auth_user_model: type,
        pattern: _view_patterns.T_ViewPattern,
        function: _functions.DispatchFunction,
    ) -> None:
        """
        If the function has a `**kwargs: object` or `**kwargs: Any` then
        no errors because the function takes in anything.

        Otherwise we gather the keyword arguments on the function and match them
        to the captured args found on the pattern.
        """
        if function.allows_arbitrary:
            return

        available: set[str] = set()
        missing: list[tuple[_display.Where, str]] = []

        positional = list(function.positional)
        for arg in function.function_args:
            if arg.is_self:
                continue

            if positional:
                positional.pop(0)
                continue

            if arg.is_variable_keywords or arg.is_variable_positional:
                continue

            available.add(arg.name)

        for part in pattern.parts:
            for name in (*part.captured, *part.default_arg_names):
                if name not in available:
                    missing.append((part.where, name))

        if missing:
            self.add_error(
                errors=errors,
                error=_errors.ViewDoesNotAcceptCapturedArg(
                    where=pattern.where,
                    missing=missing,
                    function_where=function.display,
                ),
            )

    def add_error(
        self, *, errors: _errors.ErrorContainer, error: _errors.ViewDoesNotAcceptCapturedArg
    ) -> None:
        """
        Add an error to come out of the scenario.
        """
        errors.add(error)


@attrs.frozen
class CheckViewClassRequestAnnotationScenario(PatternScenario[_view_patterns.T_ViewPattern]):
    """
    Check that the view class has an annotation for `request` that is correct.
    """

    acceptable_annotations: Sequence[object]
    acceptable_request_annotation_containers: Sequence[object]
    error_class: type[_errors.InvalidRequestAnnotation]

    exit_early: bool = False

    def run(
        self,
        *,
        errors: _errors.ErrorContainer,
        auth_user_model: type,
        pattern: _view_patterns.T_ViewPattern,
    ) -> None:
        """
        If the pattern is not a view class method or there is no request annotation
        on the class then there is nothing to check and we exit.

        Otherwise we defer to `annotation_is_valid` to determine if the annotation
        is correct.
        """
        if pattern.view_class is None:
            return

        request_annotation = typing.get_type_hints(pattern.view_class).get("request")
        if request_annotation is None:
            return

        # typing.get_type_hints should already deal with string annotations
        assert not isinstance(request_annotation, str)

        if not self.annotation_is_valid(
            errors=errors,
            auth_user_model=auth_user_model,
            annotation=request_annotation,
            pattern=pattern,
        ):
            self.add_error(
                errors=errors,
                error=self.error_class(
                    view_class=pattern.view_class,
                    request_annotation=request_annotation,
                    where=pattern.where,
                    expected_user_type=auth_user_model,
                    class_where=pattern.display_view_class,
                    acceptable_annotations=self.acceptable_annotations,
                    acceptable_request_annotation_containers=self.acceptable_request_annotation_containers,
                ),
            )

    def add_error(
        self, *, errors: _errors.ErrorContainer, error: _errors.InvalidRequestAnnotation
    ) -> None:
        """
        Add an error to come out of the scenario.
        """
        errors.add(error)

    def annotation_is_valid(
        self,
        *,
        errors: _errors.ErrorContainer,
        auth_user_model: type,
        annotation: object,
        pattern: _view_patterns.T_ViewPattern,
    ) -> bool:
        """
        Return whether the annotation found for `request` is valid.

        This can be subclass'd when a project has it's own specific rules.
        """
        origin = typing.get_origin(annotation)
        args = typing.get_args(annotation)

        if annotation in self.acceptable_annotations:
            return True

        return bool(
            origin in self.acceptable_request_annotation_containers
            and args
            and args[0] == auth_user_model
        )


@attrs.frozen
class CheckHasCorrectAnnotationsFunctionScenario(FunctionScenario[_view_patterns.T_ViewPattern]):
    """
    Check that the annotations on the function args match the types provided by
    the converters used in the captured groups of the pattern.
    """

    exit_early: bool = False

    def run(
        self,
        *,
        errors: _errors.ErrorContainer,
        auth_user_model: type,
        pattern: _view_patterns.T_ViewPattern,
        function: _functions.DispatchFunction,
    ) -> None:
        """
        This matches the annotations on the function args to the annotations on
        the captured args on the pattern.
        """
        args_by_name = {function_arg.name: function_arg for function_arg in function.function_args}

        incorrect: list[tuple[str, object, object]] = []

        for part in pattern.parts:
            for name, captured_arg in part.captured.items():
                if (found := args_by_name.get(name)) and not found.matches(
                    captured_arg.annotation
                ):
                    incorrect.append((name, found.annotation, captured_arg.annotation))

        if incorrect:
            self.add_error(
                errors=errors,
                error=_errors.InvalidArgAnnotations(
                    function_where=function.display,
                    where=pattern.where,
                    incorrect=incorrect,
                ),
            )

    def add_error(
        self, *, errors: _errors.ErrorContainer, error: _errors.InvalidArgAnnotations
    ) -> None:
        """
        Add an error to come out of the scenario.
        """
        errors.add(error)


@attrs.frozen
class CheckKwargsMustBeAnnotatedFunctionScenario(FunctionScenario[_view_patterns.T_Pattern]):
    """
    Check that a `**kwargs` on the django view is annotated correctly.
    """

    allows_object: bool = False
    allows_any: bool = False
    exit_early: bool = False

    def run(
        self,
        *,
        errors: _errors.ErrorContainer,
        auth_user_model: type,
        pattern: _view_patterns.T_Pattern,
        function: _functions.DispatchFunction,
    ) -> None:
        """
        Ensure that the annotation is correct

        - Annotation of `object` is correct only if `self.allows_object`
        - Annotation of `Any` is correct only if `self.allows_any`
        - Otherwise complain because the only valid annotation otherwise is
          a `TypedDict` and those are already unpacked when we create the function
          objects.
        """
        for arg in function.function_args:
            if not arg.is_variable_keywords:
                continue

            if self.allows_object and arg.annotation == object:
                continue

            if self.allows_any and arg.annotation == Any:
                continue

            self.add_error(
                errors=errors,
                error=_errors.KwargsMustBeAnnotated(
                    function=function,
                    arg_name=arg.name,
                    allows_object=self.allows_object,
                    allows_any=self.allows_any,
                ),
            )

    def add_error(
        self, *, errors: _errors.ErrorContainer, error: _errors.KwargsMustBeAnnotated
    ) -> None:
        """
        Add an error to come out of the scenario.
        """
        errors.add(error)
