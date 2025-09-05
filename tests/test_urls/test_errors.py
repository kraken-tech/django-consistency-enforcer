import attrs

from django_consistency_enforcer import errors as enforcer_errors


class TestErrorContainer:
    def test_it_stores_by_unique_counts_of_str_of_the_errors(self) -> None:
        errors = enforcer_errors.ErrorContainer()

        class ErrorOne(enforcer_errors.InvalidPattern):
            def __str__(self) -> str:
                return "error!"

        @attrs.frozen
        class ErrorTwo(enforcer_errors.InvalidPattern):
            value: str

            def __str__(self) -> str:
                return self.value

        e1 = ErrorOne()
        e2 = ErrorOne()
        errors.add(e1)
        assert list(errors) == [e1]
        assert list(errors.errors) == [e1]
        assert list(errors.by_most_repeated) == [str(e1)]

        errors.add(e2)
        assert list(errors) == [e1]
        assert list(errors.errors) == [e1]
        assert list(errors.by_most_repeated) == [str(e1)]

        e3 = ErrorTwo("error!")
        errors.add(e3)
        assert list(errors) == [e1]
        assert list(errors.errors) == [e1]
        assert list(errors.by_most_repeated) == [str(e1)]

        e4 = ErrorTwo("aa")
        errors.add(e4)
        assert list(errors) == [e1, e4]
        assert list(errors.errors) == [e1, e4]
        assert list(errors.by_most_repeated) == [str(e1), str(e4)]

        errors.add(ErrorTwo("aa"))
        errors.add(ErrorTwo("aa"))
        assert list(errors.by_most_repeated) == [str(e1), str(e4)]

        errors.add(ErrorTwo("aa"))
        errors.add(ErrorTwo("aa"))
        assert list(errors.by_most_repeated) == [str(e4), str(e1)]

        e5 = ErrorTwo("ab")
        errors.add(e5)
        assert list(errors) == [e1, e4, e5]
        assert list(errors.errors) == [e1, e4, e5]
        assert list(errors.by_most_repeated) == [str(e4), str(e1), str(e5)]
