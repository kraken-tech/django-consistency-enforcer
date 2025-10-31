import types
from typing import Self

import attrs
from django.urls import resolvers


@attrs.frozen
class Where:
    """
    Used to say where an error with a url pattern can be found
    """

    name: str
    regex: str
    module: str
    namespace: str

    @classmethod
    def empty(cls) -> Self:
        """
        Used to construct an instance where all the values are empty.

        Useful in tests especially to create an instance of this class where we
        don't need to worry about the details it's actually representing.
        """
        return cls(name="", regex="", module="", namespace="")

    @classmethod
    def from_resolver(
        cls,
        resolver: resolvers.URLResolver,
        *,
        regex: str,
        name: str | None = None,
        namespace: str | None = None,
    ) -> Self:
        """
        Used to construct an instance taking into account the type of the
        urlconf_module on a url resolver.
        """
        if isinstance(resolver.urlconf_module, types.ModuleType):
            return cls(
                module=resolver.urlconf_module.__file__ or "",
                name=name or "",
                namespace=namespace or "",
                regex=regex,
            )
        else:
            return cls(module="", name=name or "", namespace=namespace or "", regex=regex)

    def display(self, *, indent: str = "  ", display_regex: bool = True) -> str:
        """
        Return a string representing this location.

        Essentially a string with each property on it's own line indented the
        amount as specified.
        """
        parts: list[str] = []
        if self.module:
            parts.append(f"{indent}module = {self.module}")
        if self.name:
            parts.append(f"{indent}name = {self.name}")
        if self.namespace:
            parts.append(f"{indent}namespace = {self.namespace}")
        if self.regex and display_regex:
            parts.append(f"{indent}regex = {self.regex}")
        return "\n".join(parts)
