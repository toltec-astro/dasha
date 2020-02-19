#! /usr/bin/env python

import sys
import flask
from . import ExtensionProxy
from ..templates.dasha import DashA


dasha = ExtensionProxy(DashA, sys.modules[__name__])


config = {}


def init(cls):
    return cls(dasha._extension.config)


def init_app(server):
    return dasha.init_app(server)


def get_current_dash_app():
    return flask.current_app.dash_app
