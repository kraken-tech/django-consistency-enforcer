from __future__ import annotations

import typing
import uuid
from collections.abc import Callable, Iterator, Sequence
from typing import Protocol, Self

import attrs
from django.urls import converters, resolvers

from . import _display

type _PatternType = resolvers.RegexPattern | resolvers.RoutePattern


@attrs.frozen
class CapturedArg:
    """
    This represents a named captured group in a url pattern and the converter that django will use
    on this part of the url.

    The `from_converter` classmethod on this class will instantiate this class with the annotations
    that are match the shape of the object the converter will return.
    """

    annotation: object
    converter: type | None = None

    @classmethod
    def from_converter(cls, converter: type | None) -> Self:
        if converter is None:
            return cls(converter=None, annotation=str)

        if isinstance(converter, converters.StringConverter):
            return cls(converter=converter, annotation=str)
        elif isinstance(converter, converters.IntConverter):
            return cls(converter=converter, annotation=int)
        elif isinstance(converter, converters.UUIDConverter):
            return cls(converter=converter, annotation=uuid.UUID)
        else:
            to_python = getattr(converter, "to_python", None)
            if to_python is not None:
                ret = typing.get_type_hints(to_python).get("return")
                if ret is not None:
                    return cls(converter=converter, annotation=ret)

        raise AssertionError(
            f"Need to expand the test to understand different kind of converter: {converter}"
        )


class CapturedArgMaker(Protocol):
    def __call__(self, converter: type | None, /) -> CapturedArg: ...


@attrs.frozen
class RawPatternPart:
    groups: int
    captured: dict[str, CapturedArg]
    where: _display.Where
    default_arg_names: set[str] = attrs.field(factory=set)

    @classmethod
    def from_pattern(
        cls,
        pattern: _PatternType,
        default_args: dict[str, object],
        where: _display.Where,
        *,
        captured_arg_maker: CapturedArgMaker,
    ) -> Self:
        captured: dict[str, CapturedArg] = {}

        regex = pattern.regex

        for name in regex.groupindex:
            captured[name] = captured_arg_maker(pattern.converters.get(name))

        return cls(
            groups=regex.groups,
            captured=captured,
            default_arg_names=set(default_args),
            where=where,
        )


@attrs.frozen
class RawPattern:
    parts: Sequence[RawPatternPart]
    callback: Callable[..., object]
    view_class: type | None
    where: _display.Where

    @classmethod
    def from_parts(
        cls,
        parts: Sequence[RawPatternPart],
        *,
        callback: Callable[..., object],
        where: _display.Where,
    ) -> Self:
        view_class = getattr(callback, "view_class", None)
        if view_class is None:
            return cls(parts=parts, callback=callback, view_class=None, where=where)
        else:
            assert isinstance(view_class, type)
            return cls(parts=parts, callback=callback, view_class=view_class, where=where)


def all_django_patterns(
    resolver: resolvers.URLResolver,
    *,
    captured_arg_maker: CapturedArgMaker = CapturedArg.from_converter,
    _chain: list[tuple[_PatternType, dict[str, object], _display.Where]] | None = None,
) -> Iterator[RawPattern]:
    """
    This is used to get us every url pattern matched to the callback associated with that url

    We can use this to then check that the url patterns and the signatures of the functions on the
    view match up
    """
    if _chain is None:
        _chain = []

    assert isinstance(resolver.pattern, resolvers.RegexPattern | resolvers.RoutePattern)

    resolver_where = _display.Where.from_resolver(
        resolver,
        namespace=resolver.namespace,
        regex=resolver.pattern.regex.pattern,
    )
    for pattern in resolver.url_patterns:
        if not isinstance(pattern, resolvers.URLResolver):
            assert isinstance(pattern.pattern, resolvers.RegexPattern | resolvers.RoutePattern)
            pattern_where = _display.Where.from_resolver(
                resolver, name=pattern.name, regex=pattern.pattern.regex.pattern
            )
            yield RawPattern.from_parts(
                [
                    RawPatternPart.from_pattern(
                        patt, default_args, where=where, captured_arg_maker=captured_arg_maker
                    )
                    for patt, default_args, where in (
                        *_chain,
                        (resolver.pattern, resolver.default_kwargs, resolver_where),
                        (pattern.pattern, pattern.default_args, pattern_where),
                    )
                ],
                callback=pattern.callback,
                where=pattern_where,
            )
        else:
            yield from all_django_patterns(
                pattern,
                captured_arg_maker=captured_arg_maker,
                _chain=[*_chain, (resolver.pattern, resolver.default_kwargs, resolver_where)],
            )
