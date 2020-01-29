#! /usr/bin/env python

import sys
import flask
from . import ExtensionProxy
from ..templates import Template
from ..templates.dasha import DashA


def dasha_template(config):
    template_cls = Template._load_template_cls(config['template'])

    class DashATemplate(template_cls, DashA):
        """DashA entry point class."""
        pass

    return DashATemplate(**config)


dasha = ExtensionProxy(dasha_template, sys.modules[__name__])


def init(cls):
    return cls(dasha._extension.config)


def init_app(server):
    return dasha.init_app(server, dasha._extension.config)


def get_current_dash_app():
    return flask.current_app.dash_app
