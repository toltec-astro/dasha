#! /usr/bin/env python


"""A interprocess communication extension."""

from . import ExtensionProxy
import sys
import pickle
from copy import deepcopy
from tollan.utils import rupdate
from tollan.utils.log import get_logger
from tollan.utils.fmt import pformat_dict


class _KeyDecorator(object):
    def __init__(self, prefix=None, suffix=None):
        self._prefix = prefix or ''
        self._suffix = suffix or ''

    def _decorate(self, key):
        return f"{self._prefix}{key}{self._suffix}"

    def decorate(self, *keys):
        return tuple(map(self._decorate, keys))

    def _resolve(self, key):
        return key.lstrip(self._prefix).rstrip(self._suffix)

    def resolve(self, *keys):
        return tuple(map(self._resolve, keys))

    def __call__(self, *args):
        return self.decorate(*args)

    def r(self, *args):
        return self.resolve(*args)


class IPC(object):
    """A class that manages various ipc resources."""

    _default_config = {
            'backends': {
                'file': {
                    'rootpath': "/tmp/flask_ipc_extension"
                    },
                },
            }
    _supported_backends = ['redis', 'file', 'mmap', 'cache']
    _backends = None

    logger = get_logger()

    @classmethod
    def _ensure_config(cls, config):
        if config is None:
            config = dict()
        result = deepcopy(cls._default_config)
        rupdate(result, config)
        return result

    def _init_backend(self, name, **kwargs):
        self._backends[name] = getattr(
                self, f'_init_{name}_backend')(**kwargs)
        self.logger.debug(f"init backend {name}={self._backends[name]}")

    def _init_file_backend(self, rootpath):
        return NotImplemented

    def _init_cache_backend(self):
        from .cache import CachedData, _cached_data_registry

        def factory(label):
            logger = get_logger()
            if label in _cached_data_registry:
                logger.debug(f"get existing cache {label}")
                return _cached_data_registry[label]
            logger.debug(f"create cache {label}")
            return CachedData(label)

        return factory

    def _init_redis_backend(self, url):

        from redis.client import StrictRedis

        class RedisKeyDecorator(_KeyDecorator):
            pass

        class RedisIPC(object):
            connection = StrictRedis.from_url(url, decode_responses=True)

            _dispatch_key_positons = {
                    'get': ((0, ), None),
                    'set': ((0, ), None),
                    }

            def __init__(self, namespace=None):
                self._key_decor = RedisKeyDecorator(prefix=namespace)

            def __call__(self, func_name, *args, **kwargs):
                _key_pos, _key_return_pos = self._dispatch_key_positons[
                        func_name]
                if isinstance(_key_pos, slice):
                    _key_pos = range(*_key_pos.indices(len(args)))

                for i, a in enumerate(args):
                    if i in _key_pos:
                        args[i] = self._key_decor.decorate(a)
                result = getattr(
                        self.connection, func_name)(*args, **kwargs)
                return result

            def _dump_object(self, value):
                """Dumps an object into a string for redis.  By default it
                serializes integers as regular string and pickle dumps
                everything else.
                """
                t = type(value)
                if t == int:
                    return str(value).encode("ascii")
                return b"!" + pickle.dumps(value)

            def _load_object(self, value):
                """The reversal of :meth:`dump_object`.  This might be called
                with None.
                """
                if value is None:
                    return None
                if value.startswith(b"!"):
                    try:
                        return pickle.loads(value[1:])
                    except pickle.PickleError:
                        return None
                return int(value)

        return RedisIPC

    def init_app(self, server, config=None):
        config = self._ensure_config(config)
        self.logger.debug(f"IPC config: {pformat_dict(config)}")

        self._backends = dict()
        for name, kwargs in config['backends'].items():
            if name not in self._supported_backends:
                self.logger.warning(f"unknown backend {name}, ignore.")
                continue
            self._init_backend(name, **kwargs)

    def get_or_create(self, backend, **kwargs):
        """Return an instance for shared data access."""
        if self._backends is None:
            return None
        return self._backends[backend](**kwargs)


ipc = ExtensionProxy(IPC, sys.modules[__name__])


config = {}


def init(cls):
    return cls()


def init_app(server):
    ext = ipc._extension
    ipc.init_app(server, config=ext.config)
