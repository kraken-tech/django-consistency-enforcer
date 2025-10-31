.. toctree::
   :hidden:

   api/changelog
   api/representations
   api/scenarios
   api/test_runner

Django Consistency Enforcer
===========================

A set of tools for creating consistency checks for Django projects.

API
---

Currently this only provides functionality for checking that the signature
of methods on Django view functions/classes line up with the url patterns that
use those django views.

It has:

* :ref:`Functionality for representing views and patterns <representations>`
* :ref:`A number of different scenarios to check <scenarios>`
* :ref:`A test runner that brings everything together <test_runner>`

History
-------

This library came out of the desire in 2025 to create strongly typed Django views
in a large Django monolith (millions of lines of Python) without creating a mypy
plugin.

It is very useful for us to ensure that the annotations in our views actually
match up with what information would be sent into these views and we decided
it would be useful for the wider open source community.
