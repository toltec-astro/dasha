#! /usr/bin/env python

"""This module implements a default site."""


def create_server(config):
    """Return a flask server."""
    import flask

    server = flask.Flask(__package__)
    server.config.from_object(config)
    return server


def _extensions():
    """Return a list of extension modules."""
    import importlib

    _exts = ['cache', 'db', 'dash']
    return (
            importlib.import_module(
                f'..web.extensions.{e}', package=__package__)
            for e in _exts)


extensions = _extensions()
