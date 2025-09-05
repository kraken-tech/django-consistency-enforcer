from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Generic, Protocol, Self

import attrs

from . import _errors, _raw_patterns, _scenarios, _view_patterns


class PatternMaker(Protocol[_view_patterns.T_CO_Pattern]):
    def __call__(
        self, *, raw_pattern: _raw_patterns.RawPattern
    ) -> _view_patterns.T_CO_Pattern: ...


class RawPatternExcluder(Protocol):
    def __call__(self, *, raw_pattern: _raw_patterns.RawPattern) -> bool: ...


@attrs.frozen
class TestRunner(Generic[_view_patterns.T_Pattern]):  # noqa: UP046
    _patterns: Sequence[_view_patterns.T_Pattern]

    @classmethod
    def from_raw_patterns(
        cls,
        *,
        raw_patterns: Iterable[_raw_patterns.RawPattern],
        raw_pattern_excluder: RawPatternExcluder | None = None,
        pattern_maker: PatternMaker[_view_patterns.T_Pattern],
    ) -> Self:
        errors = _errors.ErrorContainer()
        patterns: list[_view_patterns.T_Pattern] = []

        for raw_pattern in raw_patterns:
            if raw_pattern_excluder is not None and raw_pattern_excluder(raw_pattern=raw_pattern):
                continue

            try:
                pattern = pattern_maker(raw_pattern=raw_pattern)
            except _errors.InvalidPattern as e:
                errors.add(e)
            else:
                patterns.append(pattern)

        if any(errors):
            raise _errors.FoundInvalidPatterns(errors=errors)

        return cls(patterns=patterns)

    def run_scenarios(
        self,
        *,
        auth_user_model: type,
        pattern_scenarios: Sequence[_scenarios.PatternScenario[_view_patterns.T_Pattern]],
        function_scenarios: Sequence[_scenarios.FunctionScenario[_view_patterns.T_Pattern]],
    ) -> None:
        errors = _errors.ErrorContainer()

        for pattern_scenario in pattern_scenarios:
            for pattern in self._patterns:
                if pattern.exclude(auth_user_model=auth_user_model):
                    continue

                pattern_scenario.run(
                    errors=errors, pattern=pattern, auth_user_model=auth_user_model
                )

            if pattern_scenario.exit_early and any(errors):
                raise _errors.FoundInvalidPatterns(errors=errors)

        for function_scenario in function_scenarios:
            for pattern in self._patterns:
                if pattern.exclude(auth_user_model=auth_user_model):
                    continue

                for function in pattern.relevant_functions():
                    if pattern.exclude_function(
                        auth_user_model=auth_user_model, function=function
                    ):
                        continue

                    function_scenario.run(
                        errors=errors,
                        pattern=pattern,
                        auth_user_model=auth_user_model,
                        function=function,
                    )

            if function_scenario.exit_early and any(errors):
                raise _errors.FoundInvalidPatterns(errors=errors)

        if any(errors):
            raise _errors.FoundInvalidPatterns(errors=errors)
