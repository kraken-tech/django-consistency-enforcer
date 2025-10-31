:tocdepth: 3

.. _test_runner:

The test runner Mechanism
=========================

To create a full test requires bringing together the discovery of all the views
and url patterns in the django project, with the scenarios that perform the
checks.

Discovery
---------

To perform discovery requires looking at the django url resolver and turning each
found pattern into a subclass of :class:`django_consistency_enforcer.urls.Pattern`
to be passed into an instance of the test runner.

There are a few pieces used to make this a reasonably easy process:

.. code-block:: python

    from django_consistency_enforcer import urls as enforcer
    from django_consistency_enforcer import errors as enforcer_errors

    from django.urls import resolvers


    def from_raw_pattern(raw_pattern: enforcer.RawPattern, /) -> enforcer.ViewPattern:
        # Not all django views are classes, this helper will extract the class
        # from the view pattern and raise an error if the class is not a subclass
        # of django.views.generic.View
        view_class = enforcer.ensure_raw_pattern_is_generic_view(raw_pattern=raw_pattern)

        # This represents a pattern for a view that is either a plain function
        # Or the function from calling generic.View::as_view
        return enforcer.ViewPattern(
            view_class=view_class,
            raw_pattern=raw_pattern,
            parts=raw_pattern.parts,
            callback=raw_pattern.callback,
            where=raw_pattern.where,
        )

    def raw_pattern_excluder(*, raw_pattern: url_helpers.RawPattern) -> bool:
        # Return True if we want to exlude this pattern
        return False

    try:
        test_runner = url_helpers.TestRunner.from_raw_patterns(
            raw_patterns=url_helpers.all_django_patterns(resolver=resolvers.get_resolver()),
            raw_pattern_excluder=raw_pattern_excluder,
            pattern_maker=from_raw_pattern,
        )
    except enforcer_errors.FoundInvalidPatterns as e:
        raise AssertionError(
            f"Found invalid patterns in ROOT_URLCONF under {configuration}\n\n"
            + "\n\n".join(e.errors.by_most_repeated)
        ) from e

There are a few pieces here::

    raw_patterns=url_helpers.all_django_patterns(resolver=resolvers.get_resolver()),

This uses the :func:`django_consistency_enforce.urls.all_django_patterns`
function with the default django url resolver to recursively find all the known
url patterns in the current django environment.

The excluder is used to out right exclude certain patterns from all checks::

    raw_pattern_excluder=raw_pattern_excluder,

And finally we provide a factory for creating the actual class that represents
each pattern::

    pattern_maker=from_raw_pattern,

The type of the test runner will then be generic to the return type of this
factory and means that we can return objects with extra functionality on them
that custom scenarios may be strongly typed to.

Running scenarios
-----------------

Once we have our test runner, we may then run all of our
:ref:`scenarios <scenarios>`:

.. code-block:: python

    from django.apps import apps
    from django.conf import settings
    from django_consistency_enforcer import errors as enforcer_errors

    auth_user_model = apps.get_model(settings.AUTH_USER_MODEL)

    # Using the test_runner created in the code example above

    try:
        test_runner.run_scenarios(
            auth_user_model=auth_user_model,
            pattern_scenarios=(
                # List here instances of ``PatternScenario`` classes
                ...
            ),
            function_scenarios=(
                # List here instances of ``FunctionScenario`` classes
                ...
            ),
        )
    except enforcer_errors.FoundInvalidPatterns as e:
        raise AssertionError(
            f"Found some django views with problems\n\n"
            + "\n\n".join(e.errors.by_most_repeated)
        ) from e

The test runner
---------------

.. autoclass:: django_consistency_enforcer.urls.TestRunner
    :members:
    :undoc-members:

Example
-------

.. code-block:: python

    from django_consistency_enforcer import urls as enforcer
    from django.contrib.syndication import views as syndication_views


    class CustomPattern(ViewPattern[T_ViewClass]):
        def exclude(self, *, auth_user_model: type) -> bool:
            if isinstance(self.callback, syndication_views.Feed):
                # This is based off a weird view in django.contrib that doesn't inherit from generic.View
                # We ignore it to simplify the rest of our checks
                return True

            return super().exclude(auth_user_model=auth_user_model)

        def exclude_function(self, *, auth_user_model: type, function: DispatchFunction) -> bool:
            if function.defined_on and function.defined_on.__module__.startswith("oauth2_provider."):
                # Ignore code that comes from oauth2_provider as it doesn't have explicit request arg
                return True

            return super().exclude_function(auth_user_model=auth_user_model, function=function)


    def from_raw_pattern(raw_pattern: enforcer.RawPattern, /) -> CustomPattern:
        view_class = enforcer.ensure_raw_pattern_is_generic_view(raw_pattern=raw_pattern)

        return CustomPattern(
            view_class=view_class,
            raw_pattern=raw_pattern,
            parts=raw_pattern.parts,
            callback=raw_pattern.callback,
            where=raw_pattern.where,
        )


    class CustomCheckViewClassRequestAnnotationScenario(
        enforcer.CheckViewClassRequestAnnotationScenario[CustomPattern]
    ):
        # The CheckViewClassRequestAnnotationScenario is an abc.ABC class
        # that requires some custom implementation which is not included here
        ...


    class CustomCheckViewClassRequestAnnotationScenario(
        enforcer.CheckViewClassRequestAnnotationScenario[CustomPattern]
    ):
        # The CustomCheckPositionalArgsAreCorrectFunctionScenario is an abc.ABC class
        # that requires some custom implementation which is not included here
        ...


    try:
        test_runner = url_helpers.TestRunner.from_raw_patterns(
            raw_patterns=url_helpers.all_django_patterns(resolver=resolvers.get_resolver()),
            pattern_maker=from_raw_pattern,
        )
    except enforcer_errors.FoundInvalidPatterns as e:
        ...

    test_runner.run_scenarios(
        auth_user_model=auth_user_model,
        pattern_scenarios=(
            #
            # Ensure the request annotation on the class is correct
            CustomCheckViewClassRequestAnnotationScenario(),
        ),
        function_scenarios=(
            #
            # Make sure kwargs has an annotation that makes sense
            enforcer.CheckKwargsMustBeAnnotatedFunctionScenario(
                # Exit before other checks in case it's a case of the kwargs
                # Trying to be an Unpack[SomeTypeDict] and forgetting the Unpack
                exit_early=True,
                allows_any=True,
                allows_object=True,
            ),
            #
            # Make sure the positional args are correct
            CustomCheckPositionalArgsAreCorrectFunctionScenario(),
            #
            # Make sure that if the view has a required arg, that this arg is provided by the
            # pattern
            enforcer.CheckRequiredArgsMatchUrlPatternFunctionScenario(),
            #
            # Make sure the view accepts every captured argument
            enforcer.CheckAcceptsArgsFunctionScenario(),
            #
            # Make sure the view has the correct annotations
            enforcer.CheckHasCorrectAnnotationsFunctionScenario(),
        ),
    )
