import contextlib
import textwrap
from collections.abc import Iterator

from django_consistency_enforcer import errors as enforcer_errors


@contextlib.contextmanager
def expect_zero_or_one_errors() -> Iterator[enforcer_errors.ErrorContainer]:
    """
    Helper used to make an error container and raise the one error found
    at the end of the context manager if any errors are found.

    Will complain if more than one error is found if there are any errors.
    """
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
    """
    Used to compare a multiline string to an error. Essentially a shortcut to
    textwrap.dedent.
    """
    assert str(exc) == textwrap.dedent(message).strip()
