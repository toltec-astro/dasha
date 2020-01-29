#! /usr/bin/env python

import inspect
from dash import Dash
from tollan.utils.log import timeit


class DashA(object):
    """This class provides dash app related functionalities."""

    _dash_config_default = {
            "TITLE": 'DashA',
            "SERVE_LOCALLY": True,
            "REQUESTS_PATHNAME_PREFIX": None,
            "ROUTES_PATHNAME_PREFIX": None,
            "EXTERNAL_STYLESHEETS": list(),
            "EXTERNAL_SCRIPTS": list(),
            "META_TAGS": [
                    {
                        "name": "viewport",
                        "content": "width=device-width, initial-scale=1,"
                                   " shrink-to-fit=no"
                    }
                ]
            }

    @timeit
    def init_app(self, server, config):
        def get_dash_args(config):
            dash_args = set(inspect.getfullargspec(Dash.__init__).args[1:])
            result = dict()
            for name in dash_args:
                key = name.upper()
                if hasattr(config, key):
                    result[name] = getattr(config, key)
            return result

        for k, v in self._dash_config_default.items():
            config.setdefault(k, v)

        app = Dash(
            name=__package__,
            server=server,
            suppress_callback_exceptions=True,
            **get_dash_args(config)
        )

        app.title = config["TITLE"]
        serve_locally = config["SERVE_LOCALLY"]
        app.scripts.config.serve_locally = serve_locally
        app.css.config.serve_locally = serve_locally

        with server.app_context():
            server.dash_app = app
            app.layout = self.layout

        return server
