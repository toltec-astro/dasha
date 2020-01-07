#! /usr/bin/env python

"""Flask entry point."""

if __package__:
    from . import create_app  # noqa: F401
else:
    # this is to work around the connexion api resolver problem
    from dashpages.web import create_app  # noqa: F401
