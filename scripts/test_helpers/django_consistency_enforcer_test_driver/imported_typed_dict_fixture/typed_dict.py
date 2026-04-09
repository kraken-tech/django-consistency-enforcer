from __future__ import annotations

from typing import NotRequired, TypedDict


class UrlArgs(TypedDict):
    one: NotRequired[str]
    two: int
