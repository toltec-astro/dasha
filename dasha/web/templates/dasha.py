#! /usr/bin/env python

import inspect
from dash import Dash
from tollan.utils.log import timeit
from . import Template
import copy


class DashA(object):
    """This class provides dash app related functionalities.
    """

    _dash_config_default = {
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
                ],
            }

    def __init__(self, config):
        self._config = config
        # This is needed to perserve any pre-registered templates
        self._template_registry = copy.copy(Template._template_registry)

    @timeit
    def init_app(self, server):
        def get_dash_args(config):
            dash_args = set(inspect.getfullargspec(Dash.__init__).args[1:])
            result = dict()
            for name in dash_args:
                key = name.upper()
                if hasattr(config, key):
                    result[name] = getattr(config, key)
            return result

        config = dict(self._dash_config_default, **self._config)

        app = Dash(
            name=__package__,
            server=server,
            suppress_callback_exceptions=True,
            **get_dash_args(config)
            )

        serve_locally = config["SERVE_LOCALLY"]
        app.scripts.config.serve_locally = serve_locally
        app.css.config.serve_locally = serve_locally

        # dev tools
        # app.enable_dev_tools(debug=True),

        with server.app_context():
            server.dash_app = app
            Template._template_registry = copy.copy(self._template_registry)
            template = Template.from_spec(self._config)
            timeit(template.setup_layout)(app)
            self.serve_layout(template, app)
        return server

    @staticmethod
    @timeit
    def serve_layout(template, app):
        app.layout = template.layout
