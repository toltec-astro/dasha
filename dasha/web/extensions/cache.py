#! /usr/bin/env python

"""A cache extension."""

from flask_caching import Cache
import sys
from . import ExtensionProxy


cache = ExtensionProxy(Cache, sys.modules[__name__])


config = {}


def init(cls):
    return cls()


def init_app(server):
    ext = cache._extension
    return cache.init_app(server, config=ext.config)
