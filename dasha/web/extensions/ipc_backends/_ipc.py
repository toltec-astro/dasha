#! /usr/bin/env python


"""A interprocess communication extension."""

from . import ExtensionProxy
import sys
import pickle
from copy import deepcopy
from tollan.utils import rupdate
from tollan.utils.log import get_logger
from tollan.utils.fmt import pformat_dict


__all__ = ['ipc', 'IPC', ]


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
    """A class that manages various interprocess communication resources."""

    _default_config = {
            'backends': {
                'file': {
                    'rootpath': "/tmp/flask_ipc_extension"
                    },
                },
            }
    _supported_backends = ['redis', 'rejson', 'file', 'mmap', 'cache']
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
                    'exists': ((0, ), None),
                    }

            def __init__(self, label=None):
                self._key_decor = RedisKeyDecorator(prefix=label)

            def __call__(self, func_name, *args, **kwargs):
                logger = get_logger()
                _key_pos, _key_return_pos = self._dispatch_key_positons[
                        func_name]
                if isinstance(_key_pos, slice):
                    _key_pos = range(*_key_pos.indices(len(args)))

                args = list(args)
                for i, a in enumerate(args):
                    if i in _key_pos:
                        args[i] = self._key_decor.decorate(a)[0]
                logger.debug(f"op={func_name}, args={args}, kwargs={kwargs}")
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

    def _init_rejson_backend(self, url):

        import redis
        from rejson import Client
        from rejson import Path as JsonPath

        assert '.' == JsonPath.rootPath()

        def _normalize_path(path):
            if path is None:
                return '.'
            if not isinstance(path, str):
                raise ValueError("path should be a string or None.")
            if not path.startswith('.'):
                path = f'.{path}'
                return path
            return path

        class RejsonIPC(object):

            """This class manages an json object in redis.
            """

            _connection = Client.from_url(url, decode_responses=True)

            _revkey = '_ipc_rev'
            """The key to store revision info."""

            _revpath = _normalize_path(_revkey)

            _objkey = '_ipc_obj'
            """The key to store the actual object"""

            _objpath = _normalize_path(_objkey)

            _keykey = '_ipc_key'
            _keypath = _normalize_path(_keykey)

            @property
            def _key(self):
                """The unique key of this object to use in the redis db."""
                return f'_ipc_{self.label}'

            def __init__(self, label):
                self._label = label
                self._pipeline = None
                self._rev = None

            @property
            def label(self):
                """The unique label of this object."""
                return self._label

            @staticmethod
            def _ensure_entry(obj, key, val):
                if key in obj:
                    return obj
                obj[key] = val
                return obj

            def _ensure_metadata(self, obj):
                for key, val in [
                        (self._revkey, 0),
                        (self._objkey, None),
                        (self._keykey, self._key),
                        ]:
                    self._ensure_entry(obj, key, val)
                return obj

            @property
            def connection(self):
                if self._pipeline is not None:
                    return self._pipeline
                return self._connection

            @property
            def pipeline(self):

                class RejsonIPCPipeline:

                    def __init__(self, ipc):
                        self._ipc = ipc

                    def __enter__(self):
                        self._ipc._pipeline = self._ipc._connection.pipeline()
                        return self._ipc._pipeline

                    def __exit__(self, *args):
                        self._ipc._pipeline.execute()
                        self._ipc._pipeline = None
                return RejsonIPCPipeline(self)

            def get(self, path=None):
                """Return the object with path."""
                try:
                    return self('get', path)
                except redis.exceptions.ResponseError:
                    return None

            def set(self, obj, path=None):
                """Set the object at path."""
                return self('set', path, obj)

            def _prefix_path(self, path):
                path = _normalize_path(path)
                return f'{self._objpath}{path}'.rstrip('.')

            def __call__(self, op, path, *args, **kwargs):
                """Operate on path."""
                logger = get_logger()

                path = self._prefix_path(path)
                logger.debug(
                        f"op={op} path={path} args={args} kwargs={kwargs}")
                _op = getattr(self.connection, f'json{op}')
                if op == 'set' and path == self._objpath:
                    # this is to set the object
                    # check the key exist in the client
                    obj, = args
                    logger.debug(
                            f"set root object to {obj} at key={self._key}")
                    if not self.connection.exists(self._key):
                        # create the object
                        _obj = self._ensure_metadata(dict())
                        _obj[self._objkey] = obj
                        logger.debug(
                                f"create object at key={self._key} {_obj}")
                        self.connection.jsonset(self._key, '.', _obj)
                        return
                if op == 'set':
                    if not self.connection.exists(self._key):
                        logger.debug(
                                f'set root object for '
                                f'key={self._key} path={path}')
                        self.set(dict())
                    else:
                        logger.debug(
                            f"set object key={self._key} "
                            f"obj={self.connection.jsonget(self._key, '.')}"
                            f" path={path} args={args} kwargs={kwargs}")
                with self.pipeline:
                    if op not in ['get', 'type']:
                        # thees ops will update the object.
                        self.connection.jsonnumincrby(
                                self._key, self._revpath, 1)
                    result = _op(self._key, path, *args, **kwargs)
                return result

            def get_if_updated(self, obj):
                if self._key not in obj or self._revkey not in obj or \
                        obj[self._key] != self._key:
                    raise RuntimeError('invalid object for checking update.')
                rev = self.connection.jsonget(self._key, self._revpath)
                if obj[self._revkey] == rev:
                    return obj
                # get object and attach the rev and key to it
                obj = self.get()
                self._ensure_entry(obj, self._revkey, rev)
                self._ensure_entry(obj, self._key, self._key)
                return obj
        return RejsonIPC

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
