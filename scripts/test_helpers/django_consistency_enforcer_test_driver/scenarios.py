from collections.abc import Callable, Iterator, Sequence
from typing import Self

import attrs
from django import http

from django_consistency_enforcer import errors as enforcer_errors
from django_consistency_enforcer import urls as enforcer


@attrs.frozen
class AlwaysMistypedCheckPositionalArgsAreCorrectFunctionScenario(
    enforcer.CheckPositionalArgsAreCorrectFunctionScenario
):
    disallow_var_args: bool = False
    enforce_keyword_args: bool = False

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
            name=name, got=got_annotation, want=str(want_annotation), add_auth_message=False
        )


@attrs.frozen
class StubPattern(enforcer.Pattern):
    name: str
    parts: Sequence[enforcer.RawPatternPart] = attrs.field(factory=tuple)
    callback: Callable[..., object] = attrs.field(default=lambda request: http.HttpResponse("hi"))
    where: enforcer.Where = attrs.field(factory=enforcer.Where.empty)

    _dispatch_functions: Sequence[enforcer.DispatchFunction] = attrs.field(factory=tuple)

    def exclude(self, *, auth_user_model: type) -> bool:
        return False

    def exclude_function(
        self, *, auth_user_model: type, function: enforcer.DispatchFunction
    ) -> bool:
        return False

    def relevant_functions(self) -> Iterator[enforcer.DispatchFunction]:
        yield from self._dispatch_functions


@attrs.frozen
class StubPatternScenario(enforcer.PatternScenario[StubPattern]):
    name: str

    _on_run: Callable[[tuple[Self, StubPattern]], None]
    _pattern_to_error: Callable[[StubPattern], enforcer_errors.InvalidPattern | None] = (
        attrs.field(default=lambda p: None)
    )
    exit_early: bool = False

    def run(
        self: Self,
        *,
        errors: enforcer_errors.ErrorContainer,
        auth_user_model: type,
        pattern: StubPattern,
    ) -> None:
        self._on_run((self, pattern))
        error = self._pattern_to_error(pattern)
        if error:
            errors.add(error)


@attrs.frozen
class StubFunctionScenario(enforcer.FunctionScenario[StubPattern]):
    name: str

    _on_run: Callable[[tuple[Self, StubPattern, enforcer.DispatchFunction]], None]
    _pattern_and_function_to_error: Callable[
        [StubPattern, enforcer.DispatchFunction], enforcer_errors.InvalidPattern | None
    ] = attrs.field(default=lambda p, f: None)
    exit_early: bool = False

    def run(
        self: Self,
        *,
        errors: enforcer_errors.ErrorContainer,
        auth_user_model: type,
        pattern: StubPattern,
        function: enforcer.DispatchFunction,
    ) -> None:
        self._on_run((self, pattern, function))
        error = self._pattern_and_function_to_error(pattern, function)
        if error:
            errors.add(error)
