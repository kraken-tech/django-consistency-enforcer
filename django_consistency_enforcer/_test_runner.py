from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Generic, Protocol, Self

import attrs

from . import _errors, _raw_patterns, _scenarios, _view_patterns


class PatternMaker(Protocol[_view_patterns.T_CO_Pattern]):
    """
    Represents a constructor that returns an instance of a Pattern subclass.
    """

    def __call__(
        self, *, raw_pattern: _raw_patterns.RawPattern
    ) -> _view_patterns.T_CO_Pattern: ...


class RawPatternExcluder(Protocol):
    """
    Represents a callable that is used to determine if a pattern should be excluded
    from analysis.
    """

    def __call__(self, *, raw_pattern: _raw_patterns.RawPattern) -> bool: ...


@attrs.frozen
class TestRunner(Generic[_view_patterns.T_Pattern]):  # noqa: UP046
    """
    This object is used to orchestrate the whole test, performing discovery and
    running the scenarios.
    """

    _patterns: Sequence[_view_patterns.T_Pattern]

    @classmethod
    def from_raw_patterns(
        cls,
        *,
        raw_patterns: Iterable[_raw_patterns.RawPattern],
        raw_pattern_excluder: RawPatternExcluder | None = None,
        pattern_maker: PatternMaker[_view_patterns.T_Pattern],
    ) -> Self:
        """
        Create an instance given all the raw patterns that are relevant, the ability
        to exclude patterns, and the ability to create fully realised pattern
        objects from the non excluded raw patterns.
        """
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
        """
        Run pattern and function scenarios against the patterns we know about,
        providing also the type used by Django to for authenticated of users.

        Will collect errors from scenarios and raise them as a group if:

        - Any scenario has `exit_early=True` and fails.
        - Any errors are found after all the pattern scenarios are run which
          happens before any function scenarios are run.
        - Any errors are found after all the functional scenarios are run.

        Note that the test runner will use `pattern.exclude` to skip any patterns
        that do not want to be analysed, and `pattern.exclude_function` to
        skip any functions that should not be analysed.
        """
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
