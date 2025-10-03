from django_consistency_enforcer import urls as enforcer


def from_raw_pattern(raw_pattern: enforcer.RawPattern) -> enforcer.ViewPattern:
    """
    Used as a `pattern_maker` in TestRunner instances in the tests.
    """
    view_class = enforcer.ensure_raw_pattern_is_generic_view(raw_pattern=raw_pattern)

    return enforcer.ViewPattern(
        view_class=view_class,
        raw_pattern=raw_pattern,
        parts=raw_pattern.parts,
        callback=raw_pattern.callback,
        where=raw_pattern.where,
    )
