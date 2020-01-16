#! /usr/bin/env python
import copy


class Template(object):

    """A class that encapsulate a functional group of dash
    components.

    The child component ids are automatically namespace-d to
    allow re-use of the same template in multiple parts of
    a single page application.
    """

    _dash_config_default = {
            "REQUESTS_PATHNAME_PREFIX": None,
            "ROUTES_PATHNAME_PREFIX": None,
            "EXTERNAL_STYLESHEETS": list(),
            "EXTERNAL_SCRIPTS": list()
            }

    def __init__(self, config):
        self.dash_config = copy.copy(self._dash_config_default)
        self.dash_config.update(config)

    @property
    def layout(self):
        import dash_html_components as html
        return html.Div("Hello")
