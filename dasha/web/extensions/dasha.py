#! /usr/bin/env python

from wrapt import ObjectProxy
import inspect
from dash import Dash
from tollan.utils.log import timeit, get_logger
from tollan.utils.fmt import pformat_yaml
from ..templates import Template
from tollan.utils import rupdate, ensure_prefix
import copy


__all__ = ['DashA', 'dasha', 'dash_app', 'resolve_url', 'get_url_stem']


dash_app = ObjectProxy(None)
"""A proxy to the `~dash.Dash` instance."""


dasha = ObjectProxy(None)
"""A proxy to the `~dasha.web.extensions.dasha.DashA` instance."""


class DashA(object):
    """This class sets up a Dash app to serve a `~dasha.web.templates.Template`
    instance.

    Parameters
    ----------
    config : dict
        The Dash configurations and template configurations to use.
        Dash configurations shall be specified as ALL CAPS.
        This object is passed to `~dasha.web.templates.Template.from_dict`
        to create the template instance when `init_app` is called.
    """

    logger = get_logger()

    _dash_config_default = {
            "SERVE_LOCALLY": True,
            "ASSETS_FOLDER": '../templates/assets',
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
            # default app title
            'TITLE': None
            }

    def __init__(self, config):
        self.config = copy.copy(self._dash_config_default)
        rupdate(self.config, config)
        # This is needed to preserve any pre-registered templates
        self._template_registry = copy.copy(Template._template_registry)
        self.dash_app = None

    def init_app(self, server):

        def extract_dash_args(config):
            dash_args = set(inspect.getfullargspec(Dash.__init__).args[1:])
            result = dict()
            for name in dash_args:
                key = name.upper()
                if key in config:
                    result[name] = config.pop(key)
            return result, config

        dash_config, config = extract_dash_args(copy.deepcopy(self.config))

        self.logger.debug(f"Dash config:\n{pformat_yaml(dash_config)}")
        self.logger.debug(f"DashA config:\n{pformat_yaml(config)}")

        app = dash_app.__wrapped__ = Dash(
            name=__package__,
            server=server,
            suppress_callback_exceptions=True,
            **dash_config
            )

        serve_locally = dash_config["serve_locally"]
        app.scripts.config.serve_locally = serve_locally
        app.css.config.serve_locally = serve_locally

        # dev tools
        # app.enable_dev_tools(debug=True),

        with server.app_context():
            Template._template_registry = copy.copy(self._template_registry)
            template = Template.from_dict(config)
            with timeit("setup layout"):
                template.setup_layout(app)
                # try infer a title if title is not set
                if app.title is None:
                    app.title = getattr(template, 'title_text', None)
            with timeit('serve layout'):
                app.layout = template.layout
        return server


def init_ext(config):
    ext = dasha.__wrapped__ = DashA(config)
    return ext


def init_app(server, config):
    return dasha.init_app(server)


def resolve_url(path):
    """Expands an internal URL to include prefix the app is mounted at."""
    routes_prefix = dash_app.config.routes_pathname_prefix or ''
    return f"{routes_prefix}{path}".replace('//', '/')


def get_url_stem(path):
    """The inverse of `resolve_url`."""
    routes_prefix = dash_app.config.routes_pathname_prefix or ''
    if routes_prefix == '':
        return path
    routes_prefix = ensure_prefix(routes_prefix.strip('/'), '/')
    path = ensure_prefix(path, '/')
    if path.startswith(routes_prefix):
        path = path.replace(routes_prefix, "", 1)
    return ensure_prefix(path, '/')
