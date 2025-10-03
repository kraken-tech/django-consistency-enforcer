from django import http
from django.views import generic


def index(request: http.HttpRequest) -> http.HttpResponse:
    return http.HttpResponse("")


def with_extra_args(request: http.HttpRequest, *, not_in_url: int) -> http.HttpResponse:
    return http.HttpResponse("")


def missing_specific_args(request: http.HttpRequest, *, in_url: int) -> http.HttpResponse:
    return http.HttpResponse("")


def wrong_type(request: http.HttpRequest, *, should_be_int: str) -> http.HttpResponse:
    return http.HttpResponse("")


class IncorrectView(generic.View):
    def get(self, request: http.HttpRequest, *, should_be_int: str) -> http.HttpResponse:
        return http.HttpResponse("")

    def post(self, request: http.HttpRequest, *, not_in_url: int) -> http.HttpResponse:
        return http.HttpResponse("")


class CorrectView(generic.View):
    def get(self, request: http.HttpRequest, *, should_be_str: str) -> http.HttpResponse:
        return http.HttpResponse("")

    def post(self, request: http.HttpRequest, *, should_be_str: str) -> http.HttpResponse:
        return http.HttpResponse("")
