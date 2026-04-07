from __future__ import annotations

from typing import Unpack

from django import http

from .typed_dict import UrlArgs


def my_view(request: http.HttpRequest, **kwargs: Unpack[UrlArgs]) -> http.HttpResponseBase:
    return http.HttpResponse("asdf")
