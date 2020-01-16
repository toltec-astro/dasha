#! /usr/bin/env python

import inspect
from dash import Dash
import flask
import sys
from ...utils.log import timeit
from . import ExtensionProxy
from ..templates import Template


dasha = ExtensionProxy(Template, sys.modules[__name__])


def init(cls):
    return cls()


@timeit
def init_app(server):
    config = {
            "META_TAGS": [
                {
                    "name": "viewport",
                    "content": "width=device-width, initial-scale=1,"
                               " shrink-to-fit=no"
                }
            ]
        }

    config.update(dasha.dash_config)

    def get_dash_args(config):
        dash_args = set(inspect.getfullargspec(Dash.__init__).args[1:])
        result = dict()
        for name in dash_args:
            key = name.upper()
            if hasattr(config, key):
                result[name] = getattr(config, key)
        return result

    app = Dash(
        name=__package__,
        server=server,
        suppress_callback_exceptions=True,
        **get_dash_args(config)
    )

    app.title = config.get("TITLE", 'DashA')

    serve_locally = config.get("SERVE_LOCALLY", True)
    app.scripts.config.serve_locally = serve_locally
    app.css.config.serve_locally = serve_locally

    with server.app_context():
        server.dash_app = app
        app.layout = dasha.layout

    return server


def get_current_dash_app():
    return flask.current_app.dash_app
