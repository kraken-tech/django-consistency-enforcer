from __future__ import annotations

import abc
import inspect
from collections.abc import Callable, Iterator, Sequence
from typing import Generic

import attrs
from django import http
from django.views import generic
from typing_extensions import TypeVar

from . import _display, _errors, _functions, _raw_patterns

T_ViewClass = TypeVar("T_ViewClass", bound=generic.View, default=generic.View)

T_Pattern = TypeVar("T_Pattern", bound="Pattern", default="Pattern")
T_ViewPattern = TypeVar("T_ViewPattern", bound="ViewPattern", default="ViewPattern")

T_CO_Pattern = TypeVar("T_CO_Pattern", bound="Pattern", default="Pattern", covariant=True)


def ensure_raw_pattern_is_generic_view(
    *, raw_pattern: _raw_patterns.RawPattern
) -> type[generic.View] | None:
    """
    A lot of the code here relies on the behaviour of django.views.generic.View and so this
    helper exists to look at the raw pattern and complain if the view class is not a generic.View
    subclass when a view_class is associated with the pattern.

    This function returns that view class typed such that mypy knows it's a generic.View subclass

    The implemented checks also rely on the behaviour of django.views.generic.View::as_view
    to guarantee that if there are any named capture groups in the url pattern, then there will be no positional
    arguments passed into setup/dispatch/get/post/etc

    And so it will also complain if there are no named capture groups if the pattern has any
    captured groups
    """
    if raw_pattern.view_class is not None:
        if not issubclass(raw_pattern.view_class, generic.View):
            raise _errors.MustSubclassDjangoGenericView(
                pattern=raw_pattern, where=raw_pattern.where
            )

    # Requiring named capture groups simplifies the checks that need to be made
    # The `pattern.groups` represents the number of captured groups including named and unnamed
    # groups
    # The `patterns.captured` represents the types associated with each named grouped in the
    # url pattern
    # So as long as there are more than zero captured groups if we have any group, then the
    # view will only get keyword arguments
    for part in raw_pattern.parts:
        if part.groups and len(part.captured) == 0:
            raise _errors.NoPositionalArguments(pattern=raw_pattern, where=part.where)

    return raw_pattern.view_class


class Pattern(abc.ABC):
    @property
    @abc.abstractmethod
    def parts(self) -> Sequence[_raw_patterns.RawPatternPart]: ...

    @property
    @abc.abstractmethod
    def callback(self) -> Callable[..., object]: ...

    @property
    @abc.abstractmethod
    def where(self) -> _display.Where: ...

    @abc.abstractmethod
    def exclude(self, *, auth_user_model: type) -> bool: ...

    @abc.abstractmethod
    def exclude_function(
        self, *, auth_user_model: type, function: _functions.DispatchFunction
    ) -> bool: ...

    @abc.abstractmethod
    def relevant_functions(self) -> Iterator[_functions.DispatchFunction]: ...


@attrs.frozen
class ViewPattern(Generic[T_ViewClass], Pattern):  # noqa: UP046
    raw_pattern: _raw_patterns.RawPattern

    parts: Sequence[_raw_patterns.RawPatternPart]
    callback: Callable[..., object]
    view_class: type[T_ViewClass] | None
    where: _display.Where

    def exclude(self, *, auth_user_model: type) -> bool:
        return False

    def exclude_function(
        self, *, auth_user_model: type, function: _functions.DispatchFunction
    ) -> bool:
        if function.defined_on and function.defined_on.__module__.startswith("django."):
            # Ignore code that comes from django itself
            # Nothing to be gained from complaining about code that is out of the user's control
            return True

        return False

    def dispatch_function_request_type(self) -> object:
        return http.HttpRequest

    def make_dispatch_function(
        self, callback: Callable[..., object], *, positional: Sequence[tuple[str, object]]
    ) -> _functions.DispatchFunction:
        return _functions.DispatchFunction.from_callback(
            callback, view_class=self.view_class, positional=positional
        )

    def relevant_functions(self) -> Iterator[_functions.DispatchFunction]:
        view_class = self.view_class
        if view_class is None:
            yield self.make_dispatch_function(
                self.callback,
                positional=(("request", http.HttpRequest),),
            )
        else:
            yield self.make_dispatch_function(
                view_class.setup,
                positional=(("request", http.HttpRequest),),
            )
            yield self.make_dispatch_function(
                view_class.dispatch,
                positional=(("request", http.HttpRequest),),
            )

            if issubclass(redirect_view_class := view_class, generic.RedirectView):
                yield self.make_dispatch_function(
                    redirect_view_class.get_redirect_url,
                    positional=(),
                )

            yield from self.relevant_dispatch_functions(
                request_type=self.dispatch_function_request_type(), view_class=view_class
            )

    def relevant_dispatch_functions(
        self, *, view_class: type[T_ViewClass], request_type: object
    ) -> Iterator[_functions.DispatchFunction]:
        yield self.make_dispatch_function(
            view_class.http_method_not_allowed,
            positional=(("request", request_type),),
        )

        for method_name in view_class.http_method_names:
            method = getattr(view_class, method_name, None)

            if method is not None:
                yield self.make_dispatch_function(
                    method,
                    positional=(("request", request_type),),
                )

    def display_view_class(self, *, indent: str = "  ") -> str:
        if self.view_class is None:
            return ""

        parts: list[str] = []
        parts.append(
            f"module = {None if (mod := inspect.getmodule(self.view_class)) is None else mod.__file__}"
        )
        parts.append(f"class = {self.view_class.__name__}")
        return f"\n{indent}".join(parts)
