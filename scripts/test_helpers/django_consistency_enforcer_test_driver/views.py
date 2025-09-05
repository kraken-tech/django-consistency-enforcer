from typing import NotRequired, TypedDict, Unpack

from django import http
from django.views import generic

generic_view_positional = (("request", http.HttpRequest),)


def my_view(request: http.HttpRequest, *args: object, **kwargs: object) -> http.HttpResponse:
    return http.HttpResponse("stuff")


def my_view2(request: http.HttpRequest, *, greeting: str) -> http.HttpResponse:
    return http.HttpResponse("greeting")


def string_type_args_view(
    request: "http.HttpRequest", *, one: "int", two: "int | str"
) -> http.HttpResponse:
    return http.HttpResponse("stuff")


def string_type_request_view(
    request: "http.HttpRequest", *args: object, **kwargs: object
) -> http.HttpResponse:
    return http.HttpResponse("stuff")


def notstrings_type_args_view(
    request: http.HttpRequest, *, one: int, two: int | str = 1
) -> http.HttpResponse:
    return http.HttpResponse("stuff")


class MyViewParent(generic.View):
    def setup(self, request: http.HttpRequest, *args: object, **kwargs: object) -> None:
        pass

    class _UrlArgs(TypedDict):
        one: NotRequired[int]
        two: str
        three: "NotRequired[bool]"

    def dispatch(
        self, request: http.HttpRequest, **kwargs: Unpack["_UrlArgs"]
    ) -> http.HttpResponseBase:
        return http.HttpResponse("asdf")

    def put(self, request: http.HttpRequest, **kwargs: "Unpack[_UrlArgs]") -> http.HttpResponse:
        return http.HttpResponse("asdf")


class MyViewChild(MyViewParent):
    def setup(self, request: "http.HttpRequest", *args: object, **kwargs: object) -> None:
        pass

    def get(self, request: http.HttpRequest, *, one: int = 1, two: str) -> "http.HttpResponse":
        return http.HttpResponse("got")

    def delete(
        self, request: http.HttpRequest, *args: object, **kwargs: str
    ) -> "http.HttpResponse":
        return http.HttpResponse("got")


class MyViewChild2(MyViewParent):
    def setup(self, request: "http.HttpRequest", *args: object, **kwargs: object) -> None:
        pass

    def trace(self, request: http.HttpRequest, *, one: int = 1, two: str) -> "http.HttpResponse":
        return http.HttpResponse("got")
