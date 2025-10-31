from __future__ import annotations

import inspect
import types
import typing
from collections.abc import Callable, Mapping, Sequence
from typing import Any, ForwardRef, NotRequired, Required, Self, TypedDict, Unpack

import attrs
from typing_extensions import get_annotations


@attrs.frozen
class FunctionArg:
    name: str
    required: bool
    keyword_only: bool
    annotation: object

    is_self: bool = False
    is_variable_keywords: bool = False
    is_variable_positional: bool = False

    def matches(self, annotation: object) -> bool:
        if self.annotation == Any or (self.is_variable_keywords and self.annotation == object):
            return True

        accepts: list[object] = []
        if typing.get_origin(self.annotation) in (types.UnionType, typing.Union):
            accepts.extend(typing.get_args(self.annotation))
        else:
            accepts.append(self.annotation)

        requires: list[object] = []
        if typing.get_origin(annotation) in (types.UnionType, typing.Union):
            requires.extend(typing.get_args(annotation))
        else:
            requires.append(annotation)

        return all(req in accepts for req in requires)


@attrs.frozen
class Function:
    name: str
    module: str

    function_args: Sequence[FunctionArg]
    allows_arbitrary: bool

    view_class: type | None = None
    defined_on: type | None = None

    @classmethod
    def from_callback(
        cls,
        callback: Callable[..., object],
        view_class: type | None = None,
    ) -> Self:
        callback_module = inspect.getmodule(callback)

        globalns: dict[str, object] | None = None
        if callback_module is not None:
            globalns = callback_module.__dict__
        localns: Mapping[str, object] | None = None

        defined_on: type | None = None
        if view_class is not None:
            for kls in reversed(inspect.getmro(view_class)):
                if callback.__name__ in kls.__dict__:
                    defined_on = kls

        if defined_on is not None:
            localns = defined_on.__dict__

        signature = inspect.signature(callback)
        annotations = typing.get_type_hints(callback, globalns=globalns, localns=localns)
        if not annotations and getattr(callback, "__no_type_check__", False):
            annotations = get_annotations(callback, eval_str=True)

        function_args: list[FunctionArg] = []
        allows_arbitary = False
        for i, param in enumerate(signature.parameters.values()):
            if view_class is not None and i == 0:
                assert param.kind in (
                    inspect.Parameter.POSITIONAL_ONLY,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                )
                function_args.append(
                    FunctionArg(
                        name=param.name,
                        required=False,
                        keyword_only=False,
                        annotation=view_class,
                        is_variable_keywords=False,
                        is_variable_positional=False,
                        is_self=True,
                    )
                )
                continue

            if param.kind == inspect.Parameter.VAR_POSITIONAL:
                function_args.append(
                    FunctionArg(
                        name=param.name,
                        required=False,
                        keyword_only=False,
                        annotation=annotations.get(param.name, Any),
                        is_variable_keywords=False,
                        is_variable_positional=True,
                        is_self=False,
                    )
                )
                continue

            if param.kind == inspect.Parameter.VAR_KEYWORD and (
                param.annotation is param.empty or annotations[param.name] in (object, Any)
            ):
                allows_arbitary = True

            annotation = annotations.get(param.name, Any)

            if typing.get_origin(annotation) == Unpack:
                typed_dict = typing.get_args(annotation)[0]
                for name, typ in inspect.get_annotations(typed_dict).items():
                    if isinstance(typ, ForwardRef):
                        typ = typ._evaluate(
                            globalns, localns, type_params=(), recursive_guard=frozenset()
                        )

                    required = True
                    origin = typing.get_origin(typ)
                    if origin == Required:  # type: ignore[comparison-overlap]
                        typ = typing.get_args(typ)[0]
                    elif origin == NotRequired:  # type: ignore[comparison-overlap]
                        required = False
                        typ = typing.get_args(typ)[0]

                    function_args.append(
                        FunctionArg(
                            name=name, required=required, keyword_only=True, annotation=typ
                        )
                    )
            else:
                function_args.append(
                    FunctionArg(
                        name=param.name,
                        required=(
                            param.default == param.empty
                            and param.kind
                            not in (
                                inspect.Parameter.VAR_POSITIONAL,
                                inspect.Parameter.VAR_KEYWORD,
                            )
                        ),
                        keyword_only=(
                            param.kind
                            in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
                        ),
                        annotation=annotation,
                        is_variable_keywords=param.kind == inspect.Parameter.VAR_KEYWORD,
                    )
                )

        return cls(
            name=callback.__name__,
            module=("" if callback_module is None else callback_module.__file__ or ""),
            view_class=view_class,
            defined_on=defined_on,
            function_args=function_args,
            allows_arbitrary=allows_arbitary,
        )

    def display(self, *, indent: str = "  ") -> str:
        parts: list[str] = []
        parts.append(f"module = {self.module}")

        if self.defined_on:
            parts.append(f"class = {self.defined_on.__name__}")
            parts.append(f"method = {self.name}")
        else:
            parts.append(f"function = {self.name}")
        return f"\n{indent}".join(parts)


@attrs.frozen
class DispatchFunction:
    _function: Function
    positional: Sequence[tuple[str, object]]

    @property
    def name(self) -> str:
        return self._function.name

    @property
    def module(self) -> str:
        return self._function.module

    @property
    def function_args(self) -> Sequence[FunctionArg]:
        return self._function.function_args

    @property
    def allows_arbitrary(self) -> bool:
        return self._function.allows_arbitrary

    @property
    def view_class(self) -> type | None:
        return self._function.view_class

    @property
    def defined_on(self) -> type | None:
        return self._function.defined_on

    class _DisplayArgs(TypedDict):
        indent: NotRequired[str]

    def display(self, **kwargs: Unpack[_DisplayArgs]) -> str:
        return self._function.display(**kwargs)

    @classmethod
    def from_callback(
        cls,
        callback: Callable[..., object],
        view_class: type | None = None,
        *,
        positional: Sequence[tuple[str, object]],
    ) -> Self:
        function = Function.from_callback(callback, view_class=view_class)
        return cls(function=function, positional=positional)
