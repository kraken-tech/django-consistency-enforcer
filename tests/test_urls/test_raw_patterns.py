import types

import django_consistency_enforcer_test_driver as test_helpers
from django import http
from django import urls as django_urls
from django.urls import resolvers
from django.views import generic

from django_consistency_enforcer import urls as enforcer


def test_all_django_patterns() -> None:
    class MyView(generic.View):
        pass

    class_view = MyView.as_view()

    module = types.ModuleType("my_amazing_module.urls")
    module.__file__ = "my_amazing_module/urls.py"
    module.__dict__["urlpatterns"] = (
        django_urls.path("/trees/<int:tree>", test_helpers.views.my_view, name="four"),
    )

    urlpatterns = (
        django_urls.path("/one/<str:greeting>/two", test_helpers.views.my_view, name="one"),
        django_urls.re_path(r"/three/(?P<greeting>\w+)", class_view, name="two"),
        django_urls.path(
            "/forest/<str:branch>",
            # django accepts this tuple, but django-stubs is not typed as such
            (module, "module", "three_namespace"),  # type: ignore[arg-type]
            name="three",
        ),
        django_urls.re_path(
            r"/five", test_helpers.views.my_view2, {"greeting": "hi"}, name="five"
        ),
    )

    root_patterns = django_urls.URLResolver(
        pattern=resolvers.RegexPattern(r"^"), urlconf_name=urlpatterns
    )

    found = list(
        enforcer.all_django_patterns(
            root_patterns, captured_arg_maker=enforcer.CapturedArg.from_converter
        )
    )

    first_part = enforcer.RawPatternPart(
        groups=0,
        captured={},
        where=enforcer.Where(module="", name="", namespace="", regex="^"),
    )

    where1 = enforcer.Where(
        module="", name="one", namespace="", regex="^/one/(?P<greeting>[^/]+)/two\\Z"
    )
    where2 = enforcer.Where(module="", name="two", namespace="", regex="/three/(?P<greeting>\\w+)")
    where3 = enforcer.Where(
        module="my_amazing_module/urls.py",
        name="",
        namespace="three_namespace",
        regex="^/forest/(?P<branch>[^/]+)",
    )
    where4 = enforcer.Where(
        module="my_amazing_module/urls.py",
        name="four",
        namespace="",
        regex="^/trees/(?P<tree>[0-9]+)\\Z",
    )
    where5 = enforcer.Where(module="", name="five", namespace="", regex="/five")

    assert found == [
        enforcer.RawPattern.from_parts(
            [
                first_part,
                enforcer.RawPatternPart(
                    groups=1,
                    captured={"greeting": test_helpers.comparators.CapturedString()},
                    where=where1,
                ),
            ],
            where=where1,
            callback=test_helpers.views.my_view,
        ),
        enforcer.RawPattern.from_parts(
            [
                first_part,
                enforcer.RawPatternPart(
                    groups=1,
                    captured={"greeting": enforcer.CapturedArg(converter=None, annotation=str)},
                    where=where2,
                ),
            ],
            where=where2,
            callback=class_view,
        ),
        enforcer.RawPattern.from_parts(
            [
                first_part,
                enforcer.RawPatternPart(
                    groups=1,
                    captured={"branch": test_helpers.comparators.CapturedString()},
                    where=where3,
                ),
                enforcer.RawPatternPart(
                    groups=1,
                    captured={"tree": test_helpers.comparators.CapturedInt()},
                    where=where4,
                ),
            ],
            where=where4,
            callback=test_helpers.views.my_view,
        ),
        enforcer.RawPattern.from_parts(
            [
                first_part,
                enforcer.RawPatternPart(
                    groups=0,
                    captured={},
                    default_arg_names={"greeting"},
                    where=where5,
                ),
            ],
            where=where5,
            callback=test_helpers.views.my_view2,
        ),
    ]

    # Prove default_args works the way we think it does
    cb, ags, kws = tuple(root_patterns.resolve("/five"))
    assert cb(http.HttpRequest(), *ags, **kws).content == b"greeting"
