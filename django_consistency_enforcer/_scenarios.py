from __future__ import annotations

import abc
import typing
from collections.abc import Sequence
from typing import Any, Generic

import attrs

from . import _display, _errors, _functions, _view_patterns


class PatternScenario(Generic[_view_patterns.T_Pattern], abc.ABC):  # noqa: UP046
    @property
    @abc.abstractmethod
    def exit_early(self) -> bool: ...

    @abc.abstractmethod
    def run(
        self,
        *,
        errors: _errors.ErrorContainer,
        auth_user_model: type,
        pattern: _view_patterns.T_Pattern,
    ) -> None: ...


class FunctionScenario(Generic[_view_patterns.T_Pattern], abc.ABC):  # noqa: UP046
    @property
    @abc.abstractmethod
    def exit_early(self) -> bool: ...

    @abc.abstractmethod
    def run(
        self,
        *,
        errors: _errors.ErrorContainer,
        auth_user_model: type,
        pattern: _view_patterns.T_Pattern,
        function: _functions.DispatchFunction,
    ) -> None: ...


@attrs.frozen
class CheckPositionalArgsAreCorrectFunctionScenario(
    FunctionScenario[_view_patterns.T_Pattern], abc.ABC
):
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
    ) -> _errors.MismatchedRequiredArgs.Incorrect | None: ...


@attrs.frozen
class CheckRequiredArgsMatchUrlPatternFunctionScenario(
    FunctionScenario[_view_patterns.T_ViewPattern], abc.ABC
):
    exit_early: bool = False

    def run(
        self,
        *,
        errors: _errors.ErrorContainer,
        auth_user_model: type,
        pattern: _view_patterns.T_ViewPattern,
        function: _functions.DispatchFunction,
    ) -> None:
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
        errors.add(error)


@attrs.frozen
class CheckAcceptsArgsFunctionScenario(FunctionScenario[_view_patterns.T_ViewPattern]):
    exit_early: bool = False

    def run(
        self,
        *,
        errors: _errors.ErrorContainer,
        auth_user_model: type,
        pattern: _view_patterns.T_ViewPattern,
        function: _functions.DispatchFunction,
    ) -> None:
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
        errors.add(error)


@attrs.frozen
class CheckViewClassRequestAnnotationScenario(PatternScenario[_view_patterns.T_ViewPattern]):
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
        errors.add(error)

    def annotation_is_valid(
        self,
        *,
        errors: _errors.ErrorContainer,
        auth_user_model: type,
        annotation: object,
        pattern: _view_patterns.T_ViewPattern,
    ) -> bool:
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
    exit_early: bool = False

    def run(
        self,
        *,
        errors: _errors.ErrorContainer,
        auth_user_model: type,
        pattern: _view_patterns.T_ViewPattern,
        function: _functions.DispatchFunction,
    ) -> None:
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
        errors.add(error)


@attrs.frozen
class CheckKwargsMustBeAnnotatedFunctionScenario(FunctionScenario[_view_patterns.T_Pattern]):
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
        errors.add(error)
