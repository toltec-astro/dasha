#! /usr/bin/env python

"""A cache extension."""

from flask_caching import Cache
import sys
from . import ExtensionProxy

cache = ExtensionProxy(Cache, sys.modules[__name__])


def init(cls):
    return cls()


init_app = cache.init_app
