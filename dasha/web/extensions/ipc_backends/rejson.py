#! /usr/bin/env python

import redis
from rejson import Client
from rejson import Path as _JsonPath
from tollan.utils.log import get_logger


__all__ = ['JsonPath', 'RejsonIPC', ]


class JsonPath(_JsonPath):
    """This extends `~rejson.Path` with various helpers."""

    root = _JsonPath.rootPath()
    sep = '.'

    def __init__(self, path=_JsonPath.rootPath()):
        if isinstance(path, _JsonPath):
            path = path.strPath
        elif isinstance(path, str):
            pass
        else:
            raise ValueError("invalid input path type.")
        if path != self.root and path.endswith(self.sep):
            raise ValueError("path cannot be ends with '{self.sep}'")
        super().__init__(path)

    def is_absolute(self):
        return self.strPath.startswith(self.root)

    def is_root(self):
        return self.strPath == self.root

    def is_empty(self):
        return self.strPath == ''

    def joinpath(self, other):
        """Join this path with `other`.

        `ValueError` is raised if `other` is absolute.

        """
        if isinstance(other, str):
            other = self.__class__(other)
        if other.is_absolute():
            raise ValueError("Only can join relative path.")
        if self.is_root():
            return JsonPath(self.strPath + other.strPath)

        if other.is_empty():
            return JsonPath(self.strPath)
        return JsonPath(f'{self.strPath}{self.sep}{other.strPath}')

    @property
    def parent(self):
        if self.is_root() or self.is_empty():
            return None
        return self.strPath.rsplit(self.sep, 1)[0]

    @property
    def name(self):
        if self.is_root() or self.is_empty():
            return self.strPath
        return self.strPath.rsplit(self.sep, 1)[1]

    def relative_to(self, other):
        """Compute a version of this path relative to `other`."""
        if isinstance(other, str):
            other = self.__class__(other)
        if (self.is_absolute() and not other.is_absolute()) or (
                not self.is_absolute() and other.is_absolute()
                ):
            raise ValueError("both paths should be relative or absolute.")
        if self == other:
            return JsonPath('')
        prefix = other.strPath + ('' if other.is_root() else self.sep)
        if self.strPath.startswith(prefix):
            return JsonPath(self.strPath[len(prefix):])
        raise ValueError('unable to compute relative path.')

    def __eq__(self, other):
        if isinstance(other, str):
            other = self.__class__(other)
        return self.strPath.__eq__(other.strPath)

    def __repr__(self):
        return f'{self.__class__.__name__}({self.strPath})'

    def __str__(self):
        return self.strPath


class RejsonIPC(object):

    """This class manages a JSON object in redis.

    The actual object stored in the redis db under "redis_key" looks like:

    .. code::

        {
            '_ipc_rev': 0,
            '_ipc_obj': {'a': 'b'},
            '_ipc_key': 'redis_key'
            }

    Parameters
    ----------
    label : str
        The label of this IPC channel.

    """

    _connection = None
    """The actual redis client.

    This will be replaced after `init_ipc` is called.
    """

    _pipeline = None
    """A redis pipeline instance.

    This will be replaced after the `pipeline` context is entered.
    """

    _revkey = '_ipc_rev'
    """The key name to store the revision number."""

    _objkey = '_ipc_obj'
    """The key name to store the json object."""

    _keykey = '_ipc_key'
    """The key name to store the redis root key name."""

    _revpath = JsonPath().joinpath(_revkey)
    _objpath = JsonPath().joinpath(_objkey)
    _keypath = JsonPath().joinpath(_keykey)

    @staticmethod
    def _make_redis_key(label):
        """Create a unique key to use in the redis db."""
        return f'_ipc_{label}'

    def __init__(self, label):
        self._label = label
        self._rev = None

    @property
    def label(self):
        return self._label

    @property
    def redis_key(self):
        return self._make_redis_key(self._label)

    @staticmethod
    def _ensure_entry(obj, key, defval):
        """Modify `obj` such that `key` is present in `obj` with default
        value `defval`.
        """
        obj.setdefault(key, defval)
        return obj

    def _ensure_metadata(self, obj):
        """Modify `obj` such that revkey, objkey, and keykey are present."""
        redis_key = self.redis_key
        for key, defval in [
                (self._revkey, 0),
                (self._objkey, None),
                (self._keykey, redis_key),
                ]:
            obj.setdefault(key, defval)
        # check if redis_key matches.
        if redis_key != obj[self._keykey]:
            raise ValueError(f"inconsistent obj key {redis_key}")
        return obj

    @classmethod
    def init_ipc(cls, url):
        cls._connection = Client.from_url(url, decode_responses=True)

    @property
    def connection(self):
        if self._pipeline is not None:
            return self._pipeline
        return self._connection

    @property
    def pipeline(self):
        """A context manager that puts the connection in pipeline mode."""
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

    def get(self, path=JsonPath.root):
        """Return object at `path`.

        `None` is returned if unable to get object.
        """
        try:
            return self('get', path)
        except redis.exceptions.ResponseError:
            return None

    def set(self, obj, path=JsonPath.root):
        """Set `obj` to path."""
        return self('set', path, obj)

    def _get_rejson_path(self, path):
        """Returns the actual json object path in the redis db."""
        path = JsonPath(path)
        if path.is_absolute():
            path = path.relative_to(JsonPath.root)
        return self._objpath.joinpath(path)

    def __call__(self, op, path, *args, **kwargs):
        """Operate at `path`.

        Note that `path` is specified with respect to `_objpath`.
        """
        logger = get_logger('rejson_call')

        path = JsonPath(path)
        rejson_path = self._get_rejson_path(path)
        redis_key = self.redis_key

        logger.debug(
                f"op={op} redis_key={redis_key} rejson_path={rejson_path} "
                f"path={path} args={args} kwargs={kwargs}")
        _op = getattr(self.connection, f'json{op}')
        if op == 'set' and path.is_root():
            # this is to set the object
            # check the key exist in the client
            obj, = args
            logger.debug(
                    f"set root object to {obj} at key={redis_key}")
            if not self.connection.exists(redis_key):
                # create the object
                _obj = self._ensure_metadata({
                    self._objkey: obj
                    })
                logger.debug(
                        f"create object at key={redis_key} "
                        f"rejson_path={JsonPath.root} {_obj}")
                self.connection.jsonset(redis_key, JsonPath.root, _obj)
                return
        if op == 'set':
            if not self.connection.exists(redis_key):
                # make sure root object exists
                self.set(dict(), path=JsonPath.root)
            else:
                pass
        with self.pipeline:
            if op not in ['get', 'type']:
                # thees ops will update the object.
                self.connection.jsonnumincrby(
                        redis_key, self._revpath, 1)
            result = _op(redis_key, rejson_path, *args, **kwargs)
        return result

    def get_if_updated(self, obj=None):
        """Returns new obj if it is updated.

        """
        redis_key = self.redis_key
        if obj is not None and (
                redis_key not in obj or self._revkey not in obj or
                obj[redis_key] != redis_key):
            raise RuntimeError('invalid object for checking update.')
        rev = self.connection.jsonget(redis_key, self._revpath)
        if obj is not None and obj[self._revkey] == rev:
            return obj
        # get object and attach the rev and key to it
        obj = self.get()
        self._ensure_entry(obj, self._revkey, rev)
        self._ensure_entry(obj, redis_key, redis_key)
        return obj