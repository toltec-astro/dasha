#! /usr/bin/env python

"""A cache extension."""

from flask_caching import Cache
import sys
from tollan.utils.registry import Registry
from . import ExtensionProxy


__all__ = ['cache', 'get_cached_data', 'CachedData']


cache = ExtensionProxy(Cache, sys.modules[__name__])


config = {}


def init(cls):
    return cls()


def init_app(server):
    ext = cache._extension
    cache.init_app(server, config=ext.config)
    _cached_data_registry.clear()


_cached_data_registry = Registry.create()


def get_cached_data(label):
    return _cached_data_registry[label].get()


class CachedData(object):
    _cache = cache

    def __init__(self, label):
        _cached_data_registry.register(label, self)
        self._label = label
        # self.set(None)

    def set(self, value):
        self._cache.set(self._label, value)

    def get(self):
        return self._cache.get(self._label)
