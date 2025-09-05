import contextlib
import textwrap
from collections.abc import Iterator

from django_consistency_enforcer import errors as enforcer_errors


@contextlib.contextmanager
def expect_zero_or_one_errors() -> Iterator[enforcer_errors.ErrorContainer]:
    errors = enforcer_errors.ErrorContainer()
    try:
        yield errors
    finally:
        found = list(errors)
        if found:
            assert len(found) == 1
            raise found[0]


def expect_invalid_django_pattern_error(
    exc: enforcer_errors.InvalidPattern, message: str, /
) -> None:
    assert str(exc) == textwrap.dedent(message).strip()
