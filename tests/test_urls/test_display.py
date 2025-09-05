import textwrap

import django_consistency_enforcer_test_driver as test_helpers

from django_consistency_enforcer import urls as enforcer


def test_can_display_for_a_function() -> None:
    function = enforcer.Function.from_callback(test_helpers.views.my_view)
    assert (
        function.display(indent="").strip()
        == textwrap.dedent(f"""
    module = {test_helpers.views.__file__}
    function = my_view
    """).strip()
    )


def test_can_display_for_a_class_view_function() -> None:
    function = enforcer.Function.from_callback(
        test_helpers.views.MyViewChild.get, view_class=test_helpers.views.MyViewChild
    )
    assert (
        function.display(indent="").strip()
        == textwrap.dedent(f"""
    module = {test_helpers.views.__file__}
    class = MyViewChild
    method = get
    """).strip()
    )
