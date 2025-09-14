.. _representations:

Representing views and patterns
===============================

A big part of this library is extracting information about the Django project
for the checks that are performed to make sure that details about how to get
this information does not affect what checks are made.

Every time a request comes into a Django server, that request is routed to
a ``view`` via the ``urlpatterns`` defined by the project, such that the ``view``
gets given that request object and any information that is extracted from the
request by that ``urlpattern``.

So we need objects that represent:
* What patterns exist
* What view they call out to
* What information gets extracted from the url pattern
* What information the view accepts and requires

These objects can be split into two groups, objects representing the views,
and objects representing the patterns.

Django views
------------

.. autoclass:: django_consistency_enforcer.urls.FunctionArg
    :members:
    :undoc-members:

.. autoclass:: django_consistency_enforcer.urls.Function
    :members:
    :undoc-members:

.. autoclass:: django_consistency_enforcer.urls.DispatchFunction
    :members:
    :undoc-members:

.. autoclass:: django_consistency_enforcer.urls.Where
    :members:
    :undoc-members:

Django patterns
---------------

.. autoclass:: django_consistency_enforcer.urls.CapturedArg
    :members:
    :undoc-members:

.. autoprotocol:: django_consistency_enforcer.urls.CapturedArgMaker

.. autoclass:: django_consistency_enforcer.urls.RawPatternPart
    :members:
    :undoc-members:

.. autoclass:: django_consistency_enforcer.urls.RawPattern
    :members:
    :undoc-members:

.. autoclass:: django_consistency_enforcer.urls.Pattern
    :members:
    :undoc-members:

.. autoclass:: django_consistency_enforcer.urls.ViewPattern
    :members:
    :undoc-members:

.. autofunction:: django_consistency_enforcer.urls.all_django_patterns

.. autofunction:: django_consistency_enforcer.urls.ensure_raw_pattern_is_generic_view
