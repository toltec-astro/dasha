#! /usr/bin/env python

from flask_caching import Cache
from tollan.utils.registry import Registry
from wrapt import ObjectProxy
from .utils import KeyDecorator


__all__ = ['cache', 'UserCache', 'user_cache']


cache = ObjectProxy(None)
"""A proxy to the `~flask_caching.Cache` instance."""


def init_ext(config):
    ext = cache.__wrapped__ = Cache()
    return ext


def init_app(server, config):
    cache.init_app(server, config=config)
    user_cache.invalidate()


class UserCache(object):
    """A class to manage user cache items in namespaces.

    Parameters
    ----------
    namespace : str
        The namespace under which the cache is stored.
    """

    def __init__(self, namespace):
        self._namespace = namespace
        self._cached_keys = Registry.create()

    def invalidate(self):
        """Invalidate the cached keys.

        .. note::
            This does not remove the cached data from the underlying cache
            object.

        """
        self._cached_keys.clear()

    @property
    def namespace(self):
        return self._namespace

    @property
    def _key_decorator(self):
        return KeyDecorator(prefix=f'{self._namespace}_')

    def _make_user_cache_key(self, key, ensure_unique=False):
        if ensure_unique and key in self._cached_keys:
            raise RuntimeError(f"key {key} exists in cache.")
        _key = self._cached_keys[key] = self._key_decorator.decorate(key)
        return _key

    def __repr__(self):
        return f"{self.__class__.__name__}(namespace={self.namespace})"

    def __call__(self, opname, *args, **kwargs):
        args = list(args)
        if opname in ('get', 'set'):
            key_indices = [0]
            ensure_unique = (opname == 'set')
            for i in key_indices:
                args[i] = self._make_user_cache_key(
                        args[i], ensure_unique=ensure_unique)
        else:
            raise NotImplementedError
        return getattr(cache, opname)(*args, **kwargs)

    def get(self, *args, **kwargs):
        return self('get', *args, **kwargs)

    def set(self, *args, **kwargs):
        return self('set', *args, **kwargs)


user_cache = UserCache('dasha_user_cache')
"""A global `~dasha.web.extensions.cache.UserCache` instance."""
