import django_consistency_enforcer_test_driver as test_helpers
import pytest
from django import http

from django_consistency_enforcer import errors as enforcer_errors
from django_consistency_enforcer import urls as enforcer


class TestViewPattern:
    def test_it_complains_if_view_class_is_not_a_generic_view(self) -> None:
        class View:
            pass

        def my_view(request: http.HttpRequest) -> http.HttpResponse:
            return http.HttpResponse("hi")

        my_view.view_class = View  # type: ignore[attr-defined]

        with pytest.raises(enforcer_errors.MustSubclassDjangoGenericView) as e:
            test_helpers.patterns.from_raw_pattern(
                enforcer.RawPattern.from_parts(
                    [],
                    where=enforcer.Where(
                        module="my.module", name="stuff", namespace="", regex=r"/"
                    ),
                    callback=my_view,
                )
            )

        test_helpers.checkers.expect_invalid_django_pattern_error(
            e.value,
            """
            [MustSubclassDjangoGenericView]
              module = my.module
              name = stuff
              :: Views must inherit from django.views.generic.View
            """,
        )

    def test_it_complains_if_captured_groups_with_no_named_captured_groups(self) -> None:
        with pytest.raises(enforcer_errors.NoPositionalArguments) as e:
            test_helpers.patterns.from_raw_pattern(
                enforcer.RawPattern.from_parts(
                    [
                        enforcer.RawPatternPart(
                            groups=1,
                            captured={},
                            where=enforcer.Where(
                                module="my.module", name="blah", namespace="", regex=r"/(\d+)"
                            ),
                        )
                    ],
                    where=enforcer.Where(
                        module="my.module", name="blah", namespace="", regex=r"/(\d+)"
                    ),
                    callback=test_helpers.views.my_view,
                )
            )

        test_helpers.checkers.expect_invalid_django_pattern_error(
            e.value,
            """
            [NoPositionalArguments]
              module = my.module
              name = blah
              regex = /(\\d+)
              :: Please ensure that captured groups in url patterns always have a name
            """,
        )
