#! /usr/bin/env python

import sys
import flask
from . import ExtensionProxy
from ..templates import Template
from ..templates.dasha import DashA
import copy


def dasha_template(config):

    def cls_func(template_cls):
        class DashATemplate(template_cls, DashA):
            """DashA entry point class."""
            pass
        return DashATemplate

    return load_template(config, cls_func=cls_func)


dasha = ExtensionProxy(dasha_template, sys.modules[__name__])


def init(cls):
    return cls(dasha._extension.config)


def init_app(server):
    return dasha.init_app(server, dasha._extension.config)


def get_current_dash_app():
    return flask.current_app.dash_app


def load_template(spec, cls_func=None):
    """Return a template instance from some given spec.

    The `spec` shall be specified as a dict that contains the key `template`,
    which shall be a spec string that is passed to
    `Template._load_template_cls` to get the template class. All other items
    are passed to the constructor of the template class.

    If `cls_func` is set, the template class will be passed to it as the
    sole parameter and the returned type will be used as the template class.
    """
    print(spec)
    spec = copy.copy(spec)
    template_cls = Template._load_template_cls(spec.pop('template'))

    if cls_func is None:
        return template_cls(**spec)
    return cls_func(template_cls)(**spec)
