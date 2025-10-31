from typing import Any

import django_consistency_enforcer_test_driver as test_helpers
from django import http
from django.views import generic

from django_consistency_enforcer import urls as enforcer


class TestSignaturesForStandaloneFunctions:
    def test_it_works_when_annotations_are_not_strings(self) -> None:
        where = enforcer.Where.empty()
        assert list(
            test_helpers.patterns.from_raw_pattern(
                enforcer.RawPattern.from_parts(
                    [], where=where, callback=test_helpers.views.notstrings_type_args_view
                )
            ).relevant_functions()
        ) == [
            enforcer.DispatchFunction(
                enforcer.Function(
                    name="notstrings_type_args_view",
                    module=test_helpers.views.__file__,
                    function_args=[
                        enforcer.FunctionArg(
                            name="request",
                            keyword_only=False,
                            required=True,
                            annotation=http.HttpRequest,
                        ),
                        enforcer.FunctionArg(
                            name="one", keyword_only=True, required=True, annotation=int
                        ),
                        enforcer.FunctionArg(
                            name="two", keyword_only=True, required=False, annotation=int | str
                        ),
                    ],
                    allows_arbitrary=False,
                ),
                positional=test_helpers.views.generic_view_positional,
            )
        ]

    def test_it_works_when_annotations_are_strings(self) -> None:
        where = enforcer.Where.empty()
        functions = list(
            test_helpers.patterns.from_raw_pattern(
                enforcer.RawPattern.from_parts(
                    [], where=where, callback=test_helpers.views.string_type_args_view
                )
            ).relevant_functions()
        )
        assert functions == [
            enforcer.DispatchFunction(
                enforcer.Function(
                    name="string_type_args_view",
                    module=test_helpers.views.__file__,
                    function_args=[
                        enforcer.FunctionArg(
                            name="request",
                            keyword_only=False,
                            required=True,
                            annotation=http.HttpRequest,
                        ),
                        enforcer.FunctionArg(
                            name="one",
                            keyword_only=True,
                            required=True,
                            annotation=int,
                        ),
                        enforcer.FunctionArg(
                            name="two",
                            keyword_only=True,
                            required=True,
                            annotation=int | str,
                        ),
                    ],
                    allows_arbitrary=False,
                ),
                positional=test_helpers.views.generic_view_positional,
            )
        ]

    def test_it_works_when_args_and_kwargs(self) -> None:
        where = enforcer.Where.empty()
        functions = list(
            test_helpers.patterns.from_raw_pattern(
                enforcer.RawPattern.from_parts(
                    [], where=where, callback=test_helpers.views.string_type_request_view
                )
            ).relevant_functions()
        )
        assert functions == [
            enforcer.DispatchFunction(
                enforcer.Function(
                    name="string_type_request_view",
                    module=test_helpers.views.__file__,
                    function_args=[
                        enforcer.FunctionArg(
                            name="request",
                            keyword_only=False,
                            required=True,
                            annotation=http.HttpRequest,
                        ),
                        enforcer.FunctionArg(
                            name="args",
                            keyword_only=False,
                            required=False,
                            annotation=object,
                            is_variable_positional=True,
                        ),
                        enforcer.FunctionArg(
                            name="kwargs",
                            keyword_only=True,
                            required=False,
                            annotation=object,
                            is_variable_keywords=True,
                        ),
                    ],
                    allows_arbitrary=True,
                ),
                positional=test_helpers.views.generic_view_positional,
            )
        ]


class TestSignaturesForClassView:
    def test_it_can_determine_string_annotations_defined_on_parent_with_parent_closures(
        self,
    ) -> None:
        where = enforcer.Where.empty()
        functions = list(
            test_helpers.patterns.from_raw_pattern(
                enforcer.RawPattern.from_parts(
                    [], where=where, callback=test_helpers.views.MyViewChild.as_view()
                ),
            ).relevant_functions()
        )
        assert functions == [
            enforcer.DispatchFunction(
                enforcer.Function(
                    name="setup",
                    module=test_helpers.views.__file__,
                    view_class=test_helpers.views.MyViewChild,
                    defined_on=test_helpers.views.MyViewChild,
                    function_args=[
                        enforcer.FunctionArg(
                            name="self",
                            keyword_only=False,
                            required=False,
                            annotation=test_helpers.views.MyViewChild,
                            is_self=True,
                        ),
                        enforcer.FunctionArg(
                            name="request",
                            keyword_only=False,
                            required=True,
                            annotation=http.HttpRequest,
                        ),
                        enforcer.FunctionArg(
                            name="args",
                            keyword_only=False,
                            required=False,
                            annotation=object,
                            is_variable_positional=True,
                        ),
                        enforcer.FunctionArg(
                            name="kwargs",
                            keyword_only=True,
                            required=False,
                            annotation=object,
                            is_variable_keywords=True,
                        ),
                    ],
                    allows_arbitrary=True,
                ),
                positional=test_helpers.views.generic_view_positional,
            ),
            enforcer.DispatchFunction(
                enforcer.Function(
                    name="dispatch",
                    module=test_helpers.views.__file__,
                    view_class=test_helpers.views.MyViewChild,
                    defined_on=test_helpers.views.MyViewParent,
                    function_args=[
                        enforcer.FunctionArg(
                            name="self",
                            keyword_only=False,
                            required=False,
                            annotation=test_helpers.views.MyViewChild,
                            is_self=True,
                        ),
                        enforcer.FunctionArg(
                            name="request",
                            keyword_only=False,
                            required=True,
                            annotation=http.HttpRequest,
                        ),
                        enforcer.FunctionArg(
                            name="one",
                            keyword_only=True,
                            required=False,
                            annotation=int,
                        ),
                        enforcer.FunctionArg(
                            name="two",
                            keyword_only=True,
                            required=True,
                            annotation=str,
                        ),
                        enforcer.FunctionArg(
                            name="three",
                            keyword_only=True,
                            required=False,
                            annotation=bool,
                        ),
                    ],
                    allows_arbitrary=False,
                ),
                positional=test_helpers.views.generic_view_positional,
            ),
            enforcer.DispatchFunction(
                enforcer.Function(
                    name="http_method_not_allowed",
                    module=generic.base.__file__,
                    view_class=test_helpers.views.MyViewChild,
                    defined_on=generic.View,
                    function_args=[
                        enforcer.FunctionArg(
                            name="self",
                            keyword_only=False,
                            required=False,
                            annotation=test_helpers.views.MyViewChild,
                            is_self=True,
                        ),
                        enforcer.FunctionArg(
                            name="request",
                            keyword_only=False,
                            required=True,
                            annotation=Any,
                        ),
                        enforcer.FunctionArg(
                            name="args",
                            keyword_only=False,
                            required=False,
                            annotation=Any,
                            is_variable_positional=True,
                        ),
                        enforcer.FunctionArg(
                            name="kwargs",
                            keyword_only=True,
                            required=False,
                            annotation=Any,
                            is_variable_keywords=True,
                        ),
                    ],
                    allows_arbitrary=True,
                ),
                positional=test_helpers.views.generic_view_positional,
            ),
            enforcer.DispatchFunction(
                enforcer.Function(
                    name="get",
                    module=test_helpers.views.__file__,
                    view_class=test_helpers.views.MyViewChild,
                    defined_on=test_helpers.views.MyViewChild,
                    function_args=[
                        enforcer.FunctionArg(
                            name="self",
                            keyword_only=False,
                            required=False,
                            annotation=test_helpers.views.MyViewChild,
                            is_self=True,
                        ),
                        enforcer.FunctionArg(
                            name="request",
                            keyword_only=False,
                            required=True,
                            annotation=http.HttpRequest,
                        ),
                        enforcer.FunctionArg(
                            name="one",
                            keyword_only=True,
                            required=False,
                            annotation=int,
                        ),
                        enforcer.FunctionArg(
                            name="two",
                            keyword_only=True,
                            required=True,
                            annotation=str,
                        ),
                    ],
                    allows_arbitrary=False,
                ),
                positional=test_helpers.views.generic_view_positional,
            ),
            enforcer.DispatchFunction(
                enforcer.Function(
                    name="put",
                    module=test_helpers.views.__file__,
                    view_class=test_helpers.views.MyViewChild,
                    defined_on=test_helpers.views.MyViewParent,
                    function_args=[
                        enforcer.FunctionArg(
                            name="self",
                            keyword_only=False,
                            required=False,
                            annotation=test_helpers.views.MyViewChild,
                            is_self=True,
                        ),
                        enforcer.FunctionArg(
                            name="request",
                            keyword_only=False,
                            required=True,
                            annotation=http.HttpRequest,
                        ),
                        enforcer.FunctionArg(
                            name="one",
                            keyword_only=True,
                            required=False,
                            annotation=int,
                        ),
                        enforcer.FunctionArg(
                            name="two",
                            keyword_only=True,
                            required=True,
                            annotation=str,
                        ),
                        enforcer.FunctionArg(
                            name="three",
                            keyword_only=True,
                            required=False,
                            annotation=bool,
                        ),
                    ],
                    allows_arbitrary=False,
                ),
                positional=test_helpers.views.generic_view_positional,
            ),
            enforcer.DispatchFunction(
                enforcer.Function(
                    name="delete",
                    module=test_helpers.views.__file__,
                    view_class=test_helpers.views.MyViewChild,
                    defined_on=test_helpers.views.MyViewChild,
                    function_args=[
                        enforcer.FunctionArg(
                            name="self",
                            keyword_only=False,
                            required=False,
                            annotation=test_helpers.views.MyViewChild,
                            is_self=True,
                        ),
                        enforcer.FunctionArg(
                            name="request",
                            keyword_only=False,
                            required=True,
                            annotation=http.HttpRequest,
                        ),
                        enforcer.FunctionArg(
                            name="args",
                            keyword_only=False,
                            required=False,
                            is_variable_positional=True,
                            annotation=object,
                        ),
                        enforcer.FunctionArg(
                            name="kwargs",
                            keyword_only=True,
                            required=False,
                            is_variable_keywords=True,
                            annotation=str,
                        ),
                    ],
                    allows_arbitrary=False,
                ),
                positional=test_helpers.views.generic_view_positional,
            ),
            enforcer.DispatchFunction(
                enforcer.Function(
                    name="options",
                    module=generic.base.__file__,
                    view_class=test_helpers.views.MyViewChild,
                    defined_on=generic.View,
                    function_args=[
                        enforcer.FunctionArg(
                            name="self",
                            keyword_only=False,
                            required=False,
                            annotation=test_helpers.views.MyViewChild,
                            is_self=True,
                        ),
                        enforcer.FunctionArg(
                            name="request",
                            keyword_only=False,
                            required=True,
                            annotation=Any,
                        ),
                        enforcer.FunctionArg(
                            name="args",
                            keyword_only=False,
                            required=False,
                            annotation=Any,
                            is_variable_positional=True,
                        ),
                        enforcer.FunctionArg(
                            name="kwargs",
                            keyword_only=True,
                            required=False,
                            annotation=Any,
                            is_variable_keywords=True,
                        ),
                    ],
                    allows_arbitrary=True,
                ),
                positional=test_helpers.views.generic_view_positional,
            ),
        ]

    def test_it_only_gets_functions_defined_on_class_relevant_to_dispatch(self) -> None:
        where = enforcer.Where.empty()
        functions1 = list(
            test_helpers.patterns.from_raw_pattern(
                enforcer.RawPattern.from_parts(
                    [],
                    where=where,
                    callback=test_helpers.views.MyViewChild.as_view(),
                ),
            ).relevant_functions()
        )
        functions2 = list(
            test_helpers.patterns.from_raw_pattern(
                enforcer.RawPattern.from_parts(
                    [], where=where, callback=test_helpers.views.MyViewChild2.as_view()
                ),
            ).relevant_functions()
        )

        assert [m.name for m in functions1] == [
            "setup",
            "dispatch",
            "http_method_not_allowed",
            "get",
            "put",
            "delete",
            "options",
        ]
        assert [m.name for m in functions2] == [
            "setup",
            "dispatch",
            "http_method_not_allowed",
            "put",
            "options",
            "trace",
        ]

    def test_it_understands_generic_view(self) -> None:
        where = enforcer.Where.empty()
        functions = list(
            test_helpers.patterns.from_raw_pattern(
                enforcer.RawPattern.from_parts(
                    [],
                    where=where,
                    callback=generic.View.as_view(),
                ),
            ).relevant_functions()
        )
        assert [(m.name, m.positional) for m in functions] == [
            ("setup", test_helpers.views.generic_view_positional),
            ("dispatch", test_helpers.views.generic_view_positional),
            ("http_method_not_allowed", test_helpers.views.generic_view_positional),
            ("options", test_helpers.views.generic_view_positional),
        ]

        class MyView(generic.View):
            def get(self, request: http.HttpRequest) -> http.HttpResponse:
                return http.HttpResponse("hi")

            def put(self, request: http.HttpRequest) -> http.HttpResponse:
                return http.HttpResponse("hi")

            def post(self, request: http.HttpRequest) -> http.HttpResponse:
                return http.HttpResponse("hi")

            def patch(self, request: http.HttpRequest) -> http.HttpResponse:
                return http.HttpResponse("hi")

            def delete(self, request: http.HttpRequest) -> http.HttpResponse:
                return http.HttpResponse("hi")

            def head(self, request: http.HttpRequest) -> http.HttpResponse:
                return http.HttpResponse("hi")

        where = enforcer.Where.empty()
        functions = list(
            test_helpers.patterns.from_raw_pattern(
                enforcer.RawPattern.from_parts([], where=where, callback=MyView.as_view()),
            ).relevant_functions()
        )
        assert [(m.name, m.positional) for m in functions] == [
            ("setup", test_helpers.views.generic_view_positional),
            ("dispatch", test_helpers.views.generic_view_positional),
            ("http_method_not_allowed", test_helpers.views.generic_view_positional),
            ("get", test_helpers.views.generic_view_positional),
            ("post", test_helpers.views.generic_view_positional),
            ("put", test_helpers.views.generic_view_positional),
            ("patch", test_helpers.views.generic_view_positional),
            ("delete", test_helpers.views.generic_view_positional),
            ("head", test_helpers.views.generic_view_positional),
            ("options", test_helpers.views.generic_view_positional),
        ]

    def test_it_understands_generic_redirect_view(self) -> None:
        where = enforcer.Where.empty()
        functions = list(
            test_helpers.patterns.from_raw_pattern(
                enforcer.RawPattern.from_parts(
                    [], where=where, callback=generic.RedirectView.as_view()
                ),
            ).relevant_functions()
        )
        assert [(m.name, m.positional) for m in functions] == [
            ("setup", test_helpers.views.generic_view_positional),
            ("dispatch", test_helpers.views.generic_view_positional),
            ("get_redirect_url", ()),
            ("http_method_not_allowed", test_helpers.views.generic_view_positional),
            ("get", test_helpers.views.generic_view_positional),
            ("post", test_helpers.views.generic_view_positional),
            ("put", test_helpers.views.generic_view_positional),
            ("patch", test_helpers.views.generic_view_positional),
            ("delete", test_helpers.views.generic_view_positional),
            ("head", test_helpers.views.generic_view_positional),
            ("options", test_helpers.views.generic_view_positional),
        ]
