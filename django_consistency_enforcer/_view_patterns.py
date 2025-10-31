from __future__ import annotations

import abc
import inspect
import pathlib
from collections.abc import Callable, Iterator, Sequence
from typing import Generic

import attrs
import django
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
    """
    All our scenarios are in terms of this interface.
    """

    @property
    @abc.abstractmethod
    def parts(self) -> Sequence[_raw_patterns.RawPatternPart]:
        """
        The parts that make up the whole pattern.
        """

    @property
    @abc.abstractmethod
    def callback(self) -> Callable[..., object]:
        """
        The function Django calls when this pattern is matched.
        """

    @property
    @abc.abstractmethod
    def where(self) -> _display.Where:
        """
        Information about where the final part of the pattern is defined.
        """

    @abc.abstractmethod
    def exclude(self, *, auth_user_model: type) -> bool:
        """
        Used by the test runner to skip analysis of this pattern.
        """

    @abc.abstractmethod
    def exclude_function(
        self, *, auth_user_model: type, function: _functions.DispatchFunction
    ) -> bool:
        """
        Used by the test runner to skip analysis of this function.
        """

    @abc.abstractmethod
    def relevant_functions(self) -> Iterator[_functions.DispatchFunction]:
        """
        Return an iterator of the functions to run function scenarios over.
        """


@attrs.frozen
class ViewPattern(Generic[T_ViewClass], Pattern):  # noqa: UP046
    """
    A concrete implementation of the :protocol:`Pattern` interface that is
    specific to subclasses of `django.views.generic.View`
    """

    raw_pattern: _raw_patterns.RawPattern
    """The full raw pattern this represents"""

    parts: Sequence[_raw_patterns.RawPatternPart]
    """The parts that make up the full pattern"""

    callback: Callable[..., object]
    """The function Django calls if this pattern is matched"""

    view_class: type[T_ViewClass] | None
    """The subclass of django.views.generic.View if this is a method"""

    where: _display.Where
    """Information of where the final part of this pattern was defined"""

    def exclude(self, *, auth_user_model: type) -> bool:
        """
        By default no pattern is excluded.
        """
        return False

    def exclude_function(
        self, *, auth_user_model: type, function: _functions.DispatchFunction
    ) -> bool:
        """
        By default only functions defined by Django itself is excluded from analysis.
        """
        if function.defined_on and function.defined_on.__module__.startswith("django."):
            # Ignore code that comes from django itself
            # Nothing to be gained from complaining about code that is out of the user's control
            return True
        elif function.view_class is None and function.module.startswith(
            str(pathlib.Path(django.__file__).parent)
        ):
            # Ignore code that comes from django itself
            # Nothing to be gained from complaining about code that is out of the user's control
            return True

        return False

    def dispatch_function_request_type(self) -> object:
        """
        Return the annotation that should be given to `request` positional arguments
        to dispatch functions.
        """
        return http.HttpRequest

    def make_dispatch_function(
        self, callback: Callable[..., object], *, positional: Sequence[tuple[str, object]]
    ) -> _functions.DispatchFunction:
        """
        Used to return a subclass of :class:`django_consistency_enforce.urls.DispatchFunction`.

        Useful if subclasses want to add different implementation details to
        these objects.
        """
        return _functions.DispatchFunction.from_callback(
            callback, view_class=self.view_class, positional=positional
        )

    def relevant_functions(self) -> Iterator[_functions.DispatchFunction]:
        """
        Yield the dispatch functions that should be passed into function scenarios.

        By default, if the callback is not a method, that's returned and nothing
        else.

        Otherwise we yield methods found on the view class:
        - `setup`
        - `dispatch`
        - `make_dispatch_function` if we are a subclass of `generic.RedirectView`
        - Those yield by `relevant_dispatch_functions`
        """
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
        """
        Yield the extra functions that represent specific http method types.

        So `get`, `post`, `delete`, etc, as defined by `http_method_names` on
        the view class.

        As well as `http_method_not_allowed` method.
        """
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
        """
        Return an empty string if we aren't a method, otherwise return a string
        representing information about the view class.
        """
        if self.view_class is None:
            return ""

        parts: list[str] = []
        parts.append(
            f"module = {None if (mod := inspect.getmodule(self.view_class)) is None else mod.__file__}"
        )
        parts.append(f"class = {self.view_class.__name__}")
        return f"\n{indent}".join(parts)
