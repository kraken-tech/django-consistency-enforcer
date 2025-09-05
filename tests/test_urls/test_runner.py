from collections.abc import Sequence

import attrs
import django_consistency_enforcer_test_driver as test_helpers
import pytest

from django_consistency_enforcer import errors as enforcer_errors
from django_consistency_enforcer import urls as enforcer


class TestFromRawPatterns:
    def test_it_has_the_ability_to_collect_patterns(self) -> None:
        raw_pattern_1 = enforcer.RawPattern.from_parts(
            [
                enforcer.RawPatternPart(
                    groups=1,
                    captured={"greeting": test_helpers.comparators.CapturedString()},
                    where=enforcer.Where.empty(),
                ),
            ],
            where=enforcer.Where.empty(),
            callback=test_helpers.views.my_view2,
        )
        raw_pattern_2 = enforcer.RawPattern.from_parts(
            [
                enforcer.RawPatternPart(
                    groups=0,
                    captured={},
                    where=enforcer.Where.empty(),
                ),
            ],
            where=enforcer.Where.empty(),
            callback=test_helpers.views.my_view,
        )
        raw_pattern_3 = enforcer.RawPattern.from_parts(
            [enforcer.RawPatternPart(groups=0, captured={}, where=enforcer.Where.empty())],
            where=enforcer.Where.empty(),
            callback=test_helpers.views.my_view,
        )

        called: list[object] = []
        made: list[enforcer.ViewPattern] = []

        def _excluder(*, raw_pattern: enforcer.RawPattern) -> bool:
            called.append(("excluder", raw_pattern))
            return raw_pattern is raw_pattern_2

        def _pattern_maker(*, raw_pattern: enforcer.RawPattern) -> enforcer.ViewPattern:
            called.append(("pattern_maker", raw_pattern))
            made.append(test_helpers.patterns.from_raw_pattern(raw_pattern))
            return made[-1]

        test_runner = enforcer.TestRunner.from_raw_patterns(
            raw_patterns=[raw_pattern_1, raw_pattern_2, raw_pattern_3],
            raw_pattern_excluder=_excluder,
            pattern_maker=_pattern_maker,
        )

        assert list(test_runner._patterns) == made

        assert called == [
            ("excluder", raw_pattern_1),
            ("pattern_maker", raw_pattern_1),
            ("excluder", raw_pattern_2),
            ("excluder", raw_pattern_3),
            ("pattern_maker", raw_pattern_3),
        ]

    def test_it_raises_errors_from_making_patterns(self) -> None:
        raw_pattern_1 = enforcer.RawPattern.from_parts(
            [
                enforcer.RawPatternPart(
                    groups=1,
                    captured={"greeting": test_helpers.comparators.CapturedString()},
                    where=enforcer.Where.empty(),
                ),
            ],
            where=enforcer.Where.empty(),
            callback=test_helpers.views.my_view2,
        )
        raw_pattern_2 = enforcer.RawPattern.from_parts(
            [
                enforcer.RawPatternPart(
                    groups=0,
                    captured={},
                    where=enforcer.Where.empty(),
                ),
            ],
            where=enforcer.Where.empty(),
            callback=test_helpers.views.my_view,
        )
        raw_pattern_3 = enforcer.RawPattern.from_parts(
            [enforcer.RawPatternPart(groups=0, captured={}, where=enforcer.Where.empty())],
            where=enforcer.Where.empty(),
            callback=test_helpers.views.my_view,
        )
        raw_pattern_4 = enforcer.RawPattern.from_parts(
            [enforcer.RawPatternPart(groups=0, captured={}, where=enforcer.Where.empty())],
            where=enforcer.Where.empty(),
            callback=test_helpers.views.my_view,
        )

        called: list[object] = []
        made: list[enforcer.ViewPattern] = []

        error1 = enforcer_errors.InvalidPattern("one")
        error2 = enforcer_errors.InvalidPattern("two")

        def _excluder(*, raw_pattern: enforcer.RawPattern) -> bool:
            called.append(("excluder", raw_pattern))
            return False

        def _pattern_maker(*, raw_pattern: enforcer.RawPattern) -> enforcer.ViewPattern:
            called.append(("pattern_maker", raw_pattern))
            if raw_pattern is raw_pattern_2:
                raise error1

            if raw_pattern is raw_pattern_3:
                raise error2

            made.append(test_helpers.patterns.from_raw_pattern(raw_pattern))
            return made[-1]

        with pytest.raises(enforcer_errors.FoundInvalidPatterns) as e:
            enforcer.TestRunner.from_raw_patterns(
                raw_patterns=[raw_pattern_1, raw_pattern_2, raw_pattern_3, raw_pattern_4],
                raw_pattern_excluder=_excluder,
                pattern_maker=_pattern_maker,
            )

        assert called == [
            ("excluder", raw_pattern_1),
            ("pattern_maker", raw_pattern_1),
            ("excluder", raw_pattern_2),
            ("pattern_maker", raw_pattern_2),
            ("excluder", raw_pattern_3),
            ("pattern_maker", raw_pattern_3),
            ("excluder", raw_pattern_4),
            ("pattern_maker", raw_pattern_4),
        ]

        assert list(e.value.errors) == [error1, error2]

    def test_it_only_catches_invalid_pattern_errors(self) -> None:
        raw_pattern_1 = enforcer.RawPattern.from_parts(
            [
                enforcer.RawPatternPart(
                    groups=1,
                    captured={"greeting": test_helpers.comparators.CapturedString()},
                    where=enforcer.Where.empty(),
                ),
            ],
            where=enforcer.Where.empty(),
            callback=test_helpers.views.my_view2,
        )
        raw_pattern_2 = enforcer.RawPattern.from_parts(
            [
                enforcer.RawPatternPart(
                    groups=0,
                    captured={},
                    where=enforcer.Where.empty(),
                ),
            ],
            where=enforcer.Where.empty(),
            callback=test_helpers.views.my_view,
        )
        raw_pattern_3 = enforcer.RawPattern.from_parts(
            [enforcer.RawPatternPart(groups=0, captured={}, where=enforcer.Where.empty())],
            where=enforcer.Where.empty(),
            callback=test_helpers.views.my_view,
        )
        raw_pattern_4 = enforcer.RawPattern.from_parts(
            [enforcer.RawPatternPart(groups=0, captured={}, where=enforcer.Where.empty())],
            where=enforcer.Where.empty(),
            callback=test_helpers.views.my_view,
        )

        called: list[object] = []
        made: list[enforcer.ViewPattern] = []

        error1 = enforcer_errors.InvalidPattern("one")
        error2 = AttributeError("two")

        def _excluder(*, raw_pattern: enforcer.RawPattern) -> bool:
            called.append(("excluder", raw_pattern))
            return False

        def _pattern_maker(*, raw_pattern: enforcer.RawPattern) -> enforcer.ViewPattern:
            called.append(("pattern_maker", raw_pattern))
            if raw_pattern is raw_pattern_2:
                raise error1

            if raw_pattern is raw_pattern_3:
                raise error2

            made.append(test_helpers.patterns.from_raw_pattern(raw_pattern))
            return made[-1]

        with pytest.raises(AttributeError) as e:
            enforcer.TestRunner.from_raw_patterns(
                raw_patterns=[raw_pattern_1, raw_pattern_2, raw_pattern_3, raw_pattern_4],
                raw_pattern_excluder=_excluder,
                pattern_maker=_pattern_maker,
            )

        assert called == [
            ("excluder", raw_pattern_1),
            ("pattern_maker", raw_pattern_1),
            ("excluder", raw_pattern_2),
            ("pattern_maker", raw_pattern_2),
            ("excluder", raw_pattern_3),
            ("pattern_maker", raw_pattern_3),
        ]
        assert e.value is error2


class TestRunPatternScenarios:
    def test_it_runs_pattern_scenarios_and_collects_all_errors(self) -> None:
        p1 = test_helpers.scenarios.StubPattern(name="p1")
        p2 = test_helpers.scenarios.StubPattern(name="p2")
        p3 = test_helpers.scenarios.StubPattern(name="p3")
        p4 = test_helpers.scenarios.StubPattern(name="p4")

        test_runner = enforcer.TestRunner(patterns=(p1, p2, p3, p4))

        called: list[object] = []

        @attrs.frozen
        class Error(enforcer_errors.InvalidPattern):
            value: str

            def __str__(self) -> str:
                return self.value

        e1 = Error("b")
        e2 = Error("a")
        # e3 is deliberately same as e1
        e3 = Error("b")

        scenario1 = test_helpers.scenarios.StubPatternScenario(name="s1", on_run=called.append)
        scenario2 = test_helpers.scenarios.StubPatternScenario(
            name="s2",
            on_run=called.append,
            pattern_to_error=lambda p: e1 if p is p2 else e2 if p is p3 else None,
        )
        scenario3 = test_helpers.scenarios.StubPatternScenario(
            name="s3", on_run=called.append, pattern_to_error=lambda p: e3 if p == p4 else None
        )

        with pytest.raises(enforcer_errors.FoundInvalidPatterns) as e:
            test_runner.run_scenarios(
                auth_user_model=object,
                pattern_scenarios=(scenario1, scenario2, scenario3),
                function_scenarios=(),
            )

        assert called == [
            (scenario1, p1),
            (scenario1, p2),
            (scenario1, p3),
            (scenario1, p4),
            (scenario2, p1),
            (scenario2, p2),
            (scenario2, p3),
            (scenario2, p4),
            (scenario3, p1),
            (scenario3, p2),
            (scenario3, p3),
            (scenario3, p4),
        ]
        assert list(e.value.errors) == [e1, e2]
        assert list(e.value.errors.by_most_repeated) == ["b", "a"]

    def test_it_runs_pattern_scenarios_and_collects_all_errors_even_if_exit_early_with_no_errors(
        self,
    ) -> None:
        p1 = test_helpers.scenarios.StubPattern(name="p1")
        p2 = test_helpers.scenarios.StubPattern(name="p2")
        p3 = test_helpers.scenarios.StubPattern(name="p3")
        p4 = test_helpers.scenarios.StubPattern(name="p4")

        test_runner = enforcer.TestRunner(patterns=(p1, p2, p3, p4))

        called: list[object] = []

        @attrs.frozen
        class Error(enforcer_errors.InvalidPattern):
            value: str

            def __str__(self) -> str:
                return self.value

        e1 = Error("a")

        scenario1 = test_helpers.scenarios.StubPatternScenario(name="s1", on_run=called.append)
        # exit_early is True, but no errors, so it goes to scenario3 afterwards
        scenario2 = test_helpers.scenarios.StubPatternScenario(
            name="s2", on_run=called.append, exit_early=True
        )
        scenario3 = test_helpers.scenarios.StubPatternScenario(
            name="s3", on_run=called.append, pattern_to_error=lambda p: e1 if p == p4 else None
        )

        with pytest.raises(enforcer_errors.FoundInvalidPatterns) as e:
            test_runner.run_scenarios(
                auth_user_model=object,
                pattern_scenarios=(scenario1, scenario2, scenario3),
                function_scenarios=(),
            )

        assert called == [
            (scenario1, p1),
            (scenario1, p2),
            (scenario1, p3),
            (scenario1, p4),
            (scenario2, p1),
            (scenario2, p2),
            (scenario2, p3),
            (scenario2, p4),
            (scenario3, p1),
            (scenario3, p2),
            (scenario3, p3),
            (scenario3, p4),
        ]
        assert list(e.value.errors) == [e1]
        assert list(e.value.errors.by_most_repeated) == ["a"]

    def test_it_runs_pattern_scenarios_and_collects_all_errors_till_exit_early_with_errors(
        self,
    ) -> None:
        p1 = test_helpers.scenarios.StubPattern(name="p1")
        p2 = test_helpers.scenarios.StubPattern(name="p2")
        p3 = test_helpers.scenarios.StubPattern(name="p3")
        p4 = test_helpers.scenarios.StubPattern(name="p4")

        test_runner = enforcer.TestRunner(patterns=(p1, p2, p3, p4))

        called: list[object] = []

        @attrs.frozen
        class Error(enforcer_errors.InvalidPattern):
            value: str

            def __str__(self) -> str:
                return self.value

        e1 = Error("a")
        e2 = Error("b")
        e3 = Error("c")

        scenario1 = test_helpers.scenarios.StubPatternScenario(name="s1", on_run=called.append)
        # exit_early is True with errors, so it does not go to scenario3 afterwards
        scenario2 = test_helpers.scenarios.StubPatternScenario(
            name="s2",
            exit_early=True,
            on_run=called.append,
            pattern_to_error=lambda p: e1 if p == p2 else e2 if p == p3 else None,
        )
        scenario3 = test_helpers.scenarios.StubPatternScenario(
            name="s3", on_run=called.append, pattern_to_error=lambda p: e3 if p == p4 else None
        )

        with pytest.raises(enforcer_errors.FoundInvalidPatterns) as e:
            test_runner.run_scenarios(
                auth_user_model=object,
                pattern_scenarios=(scenario1, scenario2, scenario3),
                function_scenarios=(),
            )

        assert called == [
            (scenario1, p1),
            (scenario1, p2),
            (scenario1, p3),
            (scenario1, p4),
            (scenario2, p1),
            (scenario2, p2),
            (scenario2, p3),
            (scenario2, p4),
        ]
        assert list(e.value.errors) == [e1, e2]
        assert list(e.value.errors.by_most_repeated) == ["a", "b"]


class TestRunFunctionScenarios:
    def test_it_runs_function_scenarios_and_collects_all_errors_if_pattern_scenarios_succeed(
        self,
    ) -> None:
        f1 = enforcer.DispatchFunction.from_callback(lambda: None, positional=())
        f2 = enforcer.DispatchFunction.from_callback(lambda: None, positional=())
        f3 = enforcer.DispatchFunction.from_callback(lambda: None, positional=())
        f4 = enforcer.DispatchFunction.from_callback(lambda: None, positional=())
        f5 = enforcer.DispatchFunction.from_callback(lambda: None, positional=())

        p1 = test_helpers.scenarios.StubPattern(name="p1", dispatch_functions=(f1, f2))
        p2 = test_helpers.scenarios.StubPattern(name="p2", dispatch_functions=(f3,))
        p3 = test_helpers.scenarios.StubPattern(name="p3", dispatch_functions=(f4, f5))

        test_runner = enforcer.TestRunner(patterns=(p1, p2, p3))

        called: list[object] = []

        @attrs.frozen
        class Error(enforcer_errors.InvalidPattern):
            value: str

            def __str__(self) -> str:
                return self.value

        e1 = Error("a")
        e2 = Error("b")
        e3 = Error("c")

        scenario1 = test_helpers.scenarios.StubPatternScenario(name="s1", on_run=called.append)
        scenario2 = test_helpers.scenarios.StubFunctionScenario(
            name="s2",
            on_run=called.append,
            pattern_and_function_to_error=lambda p, f: (
                e1 if (p, f) == (p1, f2) else e2 if (p, f) == (p2, f3) else None
            ),
        )
        scenario3 = test_helpers.scenarios.StubFunctionScenario(
            name="s3",
            on_run=called.append,
            pattern_and_function_to_error=lambda p, f: e3 if (p, f) == (p3, f5) else None,
        )

        with pytest.raises(enforcer_errors.FoundInvalidPatterns) as e:
            test_runner.run_scenarios(
                auth_user_model=object,
                pattern_scenarios=(scenario1,),
                function_scenarios=(scenario2, scenario3),
            )

        assert called == [
            (scenario1, p1),
            (scenario1, p2),
            (scenario1, p3),
            (scenario2, p1, f1),
            (scenario2, p1, f2),
            (scenario2, p2, f3),
            (scenario2, p3, f4),
            (scenario2, p3, f5),
            (scenario3, p1, f1),
            (scenario3, p1, f2),
            (scenario3, p2, f3),
            (scenario3, p3, f4),
            (scenario3, p3, f5),
        ]
        assert list(e.value.errors) == [e1, e2, e3]

    def test_it_does_get_to_function_scenarios_if_pattern_scenarios_fail_without_exit_early(
        self,
    ) -> None:
        f1 = enforcer.DispatchFunction.from_callback(lambda: None, positional=())
        f2 = enforcer.DispatchFunction.from_callback(lambda: None, positional=())
        f3 = enforcer.DispatchFunction.from_callback(lambda: None, positional=())
        f4 = enforcer.DispatchFunction.from_callback(lambda: None, positional=())
        f5 = enforcer.DispatchFunction.from_callback(lambda: None, positional=())

        p1 = test_helpers.scenarios.StubPattern(name="p1", dispatch_functions=(f1, f2))
        p2 = test_helpers.scenarios.StubPattern(name="p2", dispatch_functions=(f3,))
        p3 = test_helpers.scenarios.StubPattern(name="p3", dispatch_functions=(f4, f5))

        test_runner = enforcer.TestRunner(patterns=(p1, p2, p3))

        called: list[object] = []

        @attrs.frozen
        class Error(enforcer_errors.InvalidPattern):
            value: str

            def __str__(self) -> str:
                return self.value

        e1 = Error("a")
        e2 = Error("b")

        scenario1 = test_helpers.scenarios.StubPatternScenario(
            name="s1", on_run=called.append, pattern_to_error=lambda p: e1 if p == p2 else None
        )
        scenario2 = test_helpers.scenarios.StubFunctionScenario(
            name="s2",
            on_run=called.append,
            pattern_and_function_to_error=lambda p, f: e2 if (p, f) == (p1, f2) else None,
        )
        scenario3 = test_helpers.scenarios.StubFunctionScenario(name="s3", on_run=called.append)

        with pytest.raises(enforcer_errors.FoundInvalidPatterns) as e:
            test_runner.run_scenarios(
                auth_user_model=object,
                pattern_scenarios=(scenario1,),
                function_scenarios=(scenario2, scenario3),
            )

        assert called == [
            (scenario1, p1),
            (scenario1, p2),
            (scenario1, p3),
            (scenario2, p1, f1),
            (scenario2, p1, f2),
            (scenario2, p2, f3),
            (scenario2, p3, f4),
            (scenario2, p3, f5),
            (scenario3, p1, f1),
            (scenario3, p1, f2),
            (scenario3, p2, f3),
            (scenario3, p3, f4),
            (scenario3, p3, f5),
        ]
        assert list(e.value.errors) == [e1, e2]

    def test_it_does_not_get_to_function_scenarios_if_pattern_scenarios_fail_with_exit_early(
        self,
    ) -> None:
        f1 = enforcer.DispatchFunction.from_callback(lambda: None, positional=())
        f2 = enforcer.DispatchFunction.from_callback(lambda: None, positional=())
        f3 = enforcer.DispatchFunction.from_callback(lambda: None, positional=())
        f4 = enforcer.DispatchFunction.from_callback(lambda: None, positional=())
        f5 = enforcer.DispatchFunction.from_callback(lambda: None, positional=())

        p1 = test_helpers.scenarios.StubPattern(name="p1", dispatch_functions=(f1, f2))
        p2 = test_helpers.scenarios.StubPattern(name="p2", dispatch_functions=(f3,))
        p3 = test_helpers.scenarios.StubPattern(name="p3", dispatch_functions=(f4, f5))

        test_runner = enforcer.TestRunner(patterns=(p1, p2, p3))

        called: list[object] = []

        @attrs.frozen
        class Error(enforcer_errors.InvalidPattern):
            value: str

            def __str__(self) -> str:
                return self.value

        e1 = Error("a")
        e2 = Error("b")

        # exit_early is True and there are errors, so we don't get to function scenarios
        scenario1 = test_helpers.scenarios.StubPatternScenario(
            name="s1",
            on_run=called.append,
            exit_early=True,
            pattern_to_error=lambda p: e1 if p == p2 else None,
        )
        scenario2 = test_helpers.scenarios.StubFunctionScenario(
            name="s2",
            on_run=called.append,
            pattern_and_function_to_error=lambda p, f: e2 if (p, f) == (p1, f2) else None,
        )
        scenario3 = test_helpers.scenarios.StubFunctionScenario(name="s3", on_run=called.append)

        with pytest.raises(enforcer_errors.FoundInvalidPatterns) as e:
            test_runner.run_scenarios(
                auth_user_model=object,
                pattern_scenarios=(scenario1,),
                function_scenarios=(scenario2, scenario3),
            )

        assert called == [
            (scenario1, p1),
            (scenario1, p2),
            (scenario1, p3),
        ]
        assert list(e.value.errors) == [e1]

    def test_it_does_not_progress_to_next_function_scenario_if_one_fails_with_exit_early(
        self,
    ) -> None:
        f1 = enforcer.DispatchFunction.from_callback(lambda: None, positional=())
        f2 = enforcer.DispatchFunction.from_callback(lambda: None, positional=())
        f3 = enforcer.DispatchFunction.from_callback(lambda: None, positional=())
        f4 = enforcer.DispatchFunction.from_callback(lambda: None, positional=())
        f5 = enforcer.DispatchFunction.from_callback(lambda: None, positional=())

        p1 = test_helpers.scenarios.StubPattern(name="p1", dispatch_functions=(f1, f2))
        p2 = test_helpers.scenarios.StubPattern(name="p2", dispatch_functions=(f3,))
        p3 = test_helpers.scenarios.StubPattern(name="p3", dispatch_functions=(f4, f5))

        test_runner = enforcer.TestRunner(patterns=(p1, p2, p3))

        called: list[object] = []

        @attrs.frozen
        class Error(enforcer_errors.InvalidPattern):
            value: str

            def __str__(self) -> str:
                return self.value

        e1 = Error("a")
        e2 = Error("b")

        scenario1 = test_helpers.scenarios.StubPatternScenario(
            name="s1", on_run=called.append, pattern_to_error=lambda p: e1 if p == p2 else None
        )

        # exit_early is True and there are errors, so we don't get to the next scenario
        scenario2 = test_helpers.scenarios.StubFunctionScenario(
            name="s2",
            on_run=called.append,
            exit_early=True,
            pattern_and_function_to_error=lambda p, f: e2 if (p, f) == (p1, f2) else None,
        )
        scenario3 = test_helpers.scenarios.StubFunctionScenario(name="s3", on_run=called.append)

        with pytest.raises(enforcer_errors.FoundInvalidPatterns) as e:
            test_runner.run_scenarios(
                auth_user_model=object,
                pattern_scenarios=(scenario1,),
                function_scenarios=(scenario2, scenario3),
            )

        assert called == [
            (scenario1, p1),
            (scenario1, p2),
            (scenario1, p3),
            (scenario2, p1, f1),
            (scenario2, p1, f2),
            (scenario2, p2, f3),
            (scenario2, p3, f4),
            (scenario2, p3, f5),
        ]
        assert list(e.value.errors) == [e1, e2]


def test_it_can_exclude_patterns_and_functions() -> None:
    # Giving names to everything makes the diff much more useful when the test reveals a bug

    def c1() -> None:
        pass

    def c2() -> None:
        pass

    def c3() -> None:
        pass

    def c4() -> None:
        pass

    def c5() -> None:
        pass

    def c6() -> None:
        pass

    def c7() -> None:
        pass

    def c8() -> None:
        pass

    def c9() -> None:
        pass

    f1 = enforcer.DispatchFunction.from_callback(c1, positional=())
    f2 = enforcer.DispatchFunction.from_callback(c2, positional=())
    f3 = enforcer.DispatchFunction.from_callback(c3, positional=())
    f4 = enforcer.DispatchFunction.from_callback(c4, positional=())
    f5 = enforcer.DispatchFunction.from_callback(c5, positional=())
    f6 = enforcer.DispatchFunction.from_callback(c6, positional=())
    f7 = enforcer.DispatchFunction.from_callback(c7, positional=())
    f8 = enforcer.DispatchFunction.from_callback(c8, positional=())
    f9 = enforcer.DispatchFunction.from_callback(c9, positional=())

    @attrs.frozen
    class _StubPattern1(test_helpers.scenarios.StubPattern):
        name: str = "p1"
        _dispatch_functions: Sequence[enforcer.DispatchFunction] = (f1, f2, f3)

        def exclude(self, *, auth_user_model: type) -> bool:
            return False

        def exclude_function(
            self, *, auth_user_model: type, function: enforcer.DispatchFunction
        ) -> bool:
            return function == f2

    @attrs.frozen
    class _StubPattern2(test_helpers.scenarios.StubPattern):
        name: str = "p2"
        _dispatch_functions: Sequence[enforcer.DispatchFunction] = (f4, f5)

        def exclude(self, *, auth_user_model: type) -> bool:
            return True

        def exclude_function(
            self, *, auth_user_model: type, function: enforcer.DispatchFunction
        ) -> bool:
            raise AssertionError("Should never reach here")

    @attrs.frozen
    class _StubPattern3(test_helpers.scenarios.StubPattern):
        name: str = "p3"
        _dispatch_functions: Sequence[enforcer.DispatchFunction] = (f6, f7, f8, f9)

        def exclude(self, *, auth_user_model: type) -> bool:
            return False

        def exclude_function(
            self, *, auth_user_model: type, function: enforcer.DispatchFunction
        ) -> bool:
            return function in (f7, f8)

    p1 = _StubPattern1()
    p2 = _StubPattern2()
    p3 = _StubPattern3()

    test_runner = enforcer.TestRunner(patterns=(p1, p2, p3))

    called: list[object] = []

    scenario1 = test_helpers.scenarios.StubPatternScenario(name="s1", on_run=called.append)
    scenario2 = test_helpers.scenarios.StubFunctionScenario(name="s2", on_run=called.append)
    scenario3 = test_helpers.scenarios.StubFunctionScenario(name="s3", on_run=called.append)

    test_runner.run_scenarios(
        auth_user_model=object,
        pattern_scenarios=(scenario1,),
        function_scenarios=(scenario2, scenario3),
    )

    assert called == [
        (scenario1, p1),
        # (scenario1, p2),
        (scenario1, p3),
        ####################
        (scenario2, p1, f1),
        # (scenario2, p1, f2),
        (scenario2, p1, f3),
        # (scenario2, p2, f4),
        # (scenario2, p2, f5),
        (scenario2, p3, f6),
        # (scenario2, p3, f7),
        # (scenario2, p3, f8),
        (scenario2, p3, f9),
        ####################
        (scenario3, p1, f1),
        # (scenario3, p1, f2),
        (scenario3, p1, f3),
        # (scenario3, p2, f4),
        # (scenario3, p2, f5),
        (scenario3, p3, f6),
        # (scenario3, p3, f7),
        # (scenario3, p3, f8),
        (scenario3, p3, f9),
    ]
