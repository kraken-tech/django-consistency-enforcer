.. _scenarios:

Scenarios of behaviour to check
===============================

This library is built on the idea of splitting all of our checks into multiple
isolated ``scenarios`` where each scenario can focus on enforcing some specific
requirement. These are then strung together using the
:ref:`test runner <test_runner>`.

These scenarios are either a check on the view themself, or a check on the
pattern and must subclass one of these two base classes:

.. autoclass:: django_consistency_enforcer.urls.PatternScenario
    :members:
    :undoc-members:

.. autoclass:: django_consistency_enforcer.urls.FunctionScenario
    :members:
    :undoc-members:

Built in scenarios
------------------

.. autoclass:: django_consistency_enforcer.urls.CheckAcceptsArgsFunctionScenario
    :members:
    :undoc-members:

.. autoclass:: django_consistency_enforcer.urls.CheckHasCorrectAnnotationsFunctionScenario
    :members:
    :undoc-members:

.. autoclass:: django_consistency_enforcer.urls.CheckKwargsMustBeAnnotatedFunctionScenario
    :members:
    :undoc-members:

.. autoclass:: django_consistency_enforcer.urls.CheckPositionalArgsAreCorrectFunctionScenario
    :members:
    :undoc-members:

.. autoclass:: django_consistency_enforcer.urls.CheckRequiredArgsMatchUrlPatternFunctionScenario
    :members:
    :undoc-members:

.. autoclass:: django_consistency_enforcer.urls.CheckViewClassRequestAnnotationScenario
    :members:
    :undoc-members:
