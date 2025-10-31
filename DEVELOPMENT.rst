Development
===========

This project uses `uv` to manage a ``virtualenv``.

All the commands will only install things locally to this repository.

To run mypy against this code::

  > ./types

To clear the cache first::

  > CLEAR_MYPY_CACHE=1 ./types 

To run tests::

  > ./test.sh

To run tests such that breakpoints work::

  > ./test.sh --mypy-same-process -s

To activate the ``virtualenv`` in your current shell::

  > source dev activate

To build the docs locally::

  > ./dev docs view

Releasing a version
-------------------

For maintainers, releasing a new version is a case of these two steps:

1. Update the changelog in the docs folder, and the version number in
   ``django_consistency_enforce/version.py`` and merge those changes into the
   ``main`` branch

2. Run the `Release Packages <https://github.com/kraken-tech/django-consistency-enforcer/actions/workflows/release.yml>`
   Github action.
