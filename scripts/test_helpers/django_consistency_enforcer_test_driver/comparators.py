import attrs
from django.urls import converters

from django_consistency_enforcer import urls as enforcer


@attrs.mutable
class IsConverter:
    expect: type
    got: object = attrs.field(init=False)

    def __eq__(self, o: object) -> bool:
        self.got = o
        return isinstance(o, self.expect)

    def __repr__(self) -> str:
        if hasattr(self, "got"):
            return repr(self.got)
        else:
            return super().__repr__()


def CapturedInt() -> enforcer.CapturedArg:
    return enforcer.CapturedArg(
        converter=IsConverter(
            converters.IntConverter  # type: ignore[arg-type]
        ),
        annotation=int,
    )


def CapturedString() -> enforcer.CapturedArg:
    return enforcer.CapturedArg(
        converter=IsConverter(
            converters.StringConverter  # type: ignore[arg-type]
        ),
        annotation=str,
    )
