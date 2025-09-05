from __future__ import annotations

import abc
import typing
from collections.abc import Iterator, Sequence
from typing import Protocol, Self

import attrs

from . import _display, _functions, _raw_patterns


class _Display(Protocol):
    def __call__(self, *, indent: str = ...) -> str: ...


class InvalidPattern(Exception):
    pass


@attrs.frozen
class ErrorContainer:
    _by_error_str: dict[str, int] = attrs.field(init=False, factory=dict)
    _error_by_str: dict[str, InvalidPattern] = attrs.field(init=False, factory=dict)

    def add(self, error: InvalidPattern) -> None:
        error_str = str(error)
        if error_str not in self._error_by_str:
            self._error_by_str[error_str] = error

        if error_str not in self._by_error_str:
            self._by_error_str[error_str] = 0

        self._by_error_str[error_str] += 1

    def __iter__(self) -> Iterator[InvalidPattern]:
        yield from (self._error_by_str[error_str] for error_str in self._by_error_str)

    @property
    def errors(self) -> Iterator[InvalidPattern]:
        yield from self

    @property
    def by_most_repeated(self) -> Iterator[str]:
        yield from (
            error
            for error, _ in (
                sorted(
                    self._by_error_str.items(),
                    key=lambda pair: (-pair[1], pair[0].__class__.__name__),
                )
            )
        )


@attrs.frozen
class FoundInvalidPatterns(Exception):
    errors: ErrorContainer

    def __str__(self) -> str:
        return "Found invalid patterns"


@attrs.frozen(kw_only=True)
class NoPositionalArguments(InvalidPattern):
    pattern: _raw_patterns.RawPattern
    where: _display.Where

    def __str__(self) -> str:
        return f"[NoPositionalArguments]\n{self.where.display()}\n  :: Please ensure that captured groups in url patterns always have a name"


@attrs.frozen(kw_only=True)
class MustSubclassDjangoGenericView(InvalidPattern):
    pattern: _raw_patterns.RawPattern
    where: _display.Where

    def __str__(self) -> str:
        return f"[MustSubclassDjangoGenericView]\n{self.where.display(display_regex=False)}\n  :: Views must inherit from django.views.generic.View"


@attrs.frozen(kw_only=True)
class RequiredArgOnViewNotAlwaysRequiredByPattern(InvalidPattern):
    pattern_wheres: Sequence[_display.Where]
    function_where: _Display
    missing_args: set[str]

    def __str__(self) -> str:
        url_patterns = ["  url patterns >>"]
        for i, where in enumerate(self.pattern_wheres):
            url_patterns.append(f"    {i} >")
            url_patterns.extend(where.display(indent="      ").split("\n"))

        return "\n".join(
            [
                "[RequiredArgOnViewNotAlwaysRequiredByPattern]",
                f"  {self.function_where()}",
                f"  missing_from_urlpatterns = {sorted(self.missing_args)}",
                "\n".join(url_patterns),
                " :: Found arguments on the view that are not provided by any of the patterns that lead to that view",
                " :: You likely want to use Unpack on the kwargs with a NotRequired on these args",
                " :: Or give them default values if you have provided explicit keywords to the function",
            ]
        )


@attrs.frozen(kw_only=True)
class ViewDoesNotAcceptCapturedArg(InvalidPattern):
    where: _display.Where
    missing: Sequence[tuple[_display.Where, str]]
    function_where: _Display

    def __str__(self) -> str:
        missing: list[str] = []
        for where, name in self.missing:
            missing.append(f"  Missing captured arg: {name}\n{where.display(indent='    ')}")

        return "\n".join(
            [
                "[ViewDoesNotAcceptCapturedArg]",
                f"  Originating:\n{where.display(indent='    ')}",
                f"  {self.function_where()}",
                "\n".join(missing),
                " :: There are args in the pattern that the view is not aware of",
                " :: You likely want to add those extra arguments to the view!",
            ]
        )


@attrs.frozen(kw_only=True)
class InvalidRequestAnnotation(InvalidPattern, abc.ABC):
    where: _display.Where
    view_class: type
    request_annotation: object
    expected_user_type: type
    class_where: _Display
    acceptable_annotations: Sequence[object]
    acceptable_request_annotation_containers: Sequence[object]

    @property
    def error(self) -> str:
        """
        Create a specific error condition depending on what is wrong.

        * If the annotation is one of the containers, then it was supplied without using square brackets on it
        * Ensure if we have a generic, it's one of the containers
        * Otherwise we must have the wrong user model inside the square brackets
        """
        if self.request_annotation in self.acceptable_request_annotation_containers:
            return "The annotation is not specifying a user model"
        elif (
            self.request_annotation not in self.acceptable_annotations
            and typing.get_origin(self.request_annotation)
            not in self.acceptable_request_annotation_containers
        ):
            return f"The annotation is not using a valid type\n      ({self.request_annotation})"
        else:
            return "The annotation is specifying the wrong user model"

    @property
    @abc.abstractmethod
    def expect(self) -> str:
        """
        Return a simple string representing what the type should be
        """

    @property
    @abc.abstractmethod
    def expanded_note(self) -> Iterator[str]: ...

    def __str__(self) -> str:
        return "\n".join(
            [
                "[InvalidRequestAnnotation]",
                f"  Originating:\n{self.where.display(indent='    ')}",
                f"  {self.class_where()}",
                f"  error = {self.error}",
                f"  expect = {self.expect}",
                *self.expanded_note,
            ]
        )


@attrs.frozen
class MismatchedRequiredArgs(InvalidPattern):
    @attrs.frozen
    class Incorrect:
        reason: str
        add_auth_message: bool = False

        @classmethod
        def missing(cls, name: str) -> Self:
            return cls(reason=f"Missing required positional argument: {name}")

        @classmethod
        def misnamed(cls, *, index: int, got: str, want: str) -> Self:
            if index == 0:
                reason = f"The first argument should be named {want}, but got {got}"
            elif index == 1:
                reason = f"The second argument should be named {want}, but got {got}"
            else:
                reason = f"Require positional parameter {index} to be named {want}, but got {got}"
            return cls(reason=reason)

        @classmethod
        def mistyped(
            cls, *, name: str, got: object, want: str, add_auth_message: bool = False
        ) -> Self:
            return cls(
                reason=f"The '{name}' argument needs to be '{want}' but it's '{got}'",
                add_auth_message=add_auth_message,
            )

        @classmethod
        def no_var_args(cls, *, name: str) -> Self:
            return cls(
                reason=f"Please remove the var args '*{name}' from the function signature and ensure all arguments are explicit"
            )

        @classmethod
        def make_keyword_only(cls, *, name: str) -> Self:
            return cls(
                reason=f"Please ensure the '{name}' argument comes after a lone '*' so that it is defined as keyword only"
            )

    function: _functions.DispatchFunction
    incorrect: Sequence[Incorrect]

    def __str__(self) -> str:
        problems = "\n    * ".join(inc.reason for inc in self.incorrect)
        add_auth_message = any(inc.add_auth_message for inc in self.incorrect)
        msg = (
            f"[MismatchedRequiredArgs]\n  {self.function.display()}\n  Found some problems with the arguments to some functions:\n    * {problems}"
            "\n  :: We want to create consistency around the names and types of the positional"
            "\n  :: arguments to specific functions on the Django views"
        )
        if add_auth_message:
            msg = f"{msg}\n  :: For Django class views, instead annotate request on the class and refer to `self.request.user`"

        return msg


@attrs.frozen
class InvalidArgAnnotations(InvalidPattern):
    function_where: _Display
    where: _display.Where
    incorrect: list[tuple[str, object, object]]

    def __str__(self) -> str:
        incorrect = []
        for name, view_annotation, pattern_annotation in self.incorrect:
            incorrect.append(
                f"    * Expected '{name}' to be '{pattern_annotation}', found '{view_annotation}'"
            )

        return "\n".join(
            [
                "[InvalidArgAnnotations]",
                f"  Originating:\n{self.where.display(indent='    ')}",
                f"  {self.function_where()}",
                "  Found some args that have incorrect annotations:",
                "\n".join(incorrect),
                "  :: When we defined url patterns we end up using converters that can change what",
                "  :: type the view gets and we want to mirror this in our dispatch related signatures",
            ]
        )


@attrs.frozen
class KwargsMustBeAnnotated(InvalidPattern):
    function: _functions.DispatchFunction
    arg_name: str
    allows_object: bool
    allows_any: bool

    def __str__(self) -> str:
        msg = [
            f"Please ensure `**{self.arg_name}` has an annotation using typing.Unpack or specify keyword arguments explicitly"
        ]
        if self.allows_object:
            msg.append(f"or use `**{self.arg_name}: object`")
        if self.allows_any:
            msg.append(f"or use `**{self.arg_name}: Any` from the typing module")

        return f"[KwargsMustBeAnnotated]\n  {self.function.display()}\n  :: " + "\n  :: ".join(msg)
