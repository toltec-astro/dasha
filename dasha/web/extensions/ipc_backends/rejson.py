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


class _RejsonIPCPipeline(object):
    """A context manager that handles pipeline state of an
    `RejsonIPC` instance.

    In particular, the implementation ensures that
    nested context is ignored.
    """

    logger = get_logger()

    def __init__(self, ipc):
        self._ipc = ipc
        # this is used to ensure that only one nesting of
        # pipeline context.
        self._is_nested = self._ipc._pipeline is not None

    def __enter__(self):
        if not self._is_nested:
            self._ipc._pipeline = self._ipc._connection.pipeline()
        return self

    @property
    def _pipeline(self):
        return self._ipc._pipeline

    def __exit__(self, *args):
        if self._is_nested:
            return
        self._ipc._pipeline = None

    def execute(self, result_index=None):
        if self._is_nested:
            return None
        result = self._pipeline.execute()
        # unpack if requested
        if result_index is None:
            return result
        return result[result_index]

    def try_execute(self, *args, **kwargs):
        try:
            return self.execute(*args, **kwargs)
        except Exception as e:
            self.logger.error(
                    f"failed execute query: {e}", exc_info=True)
            return None


class _RejsonIPCPipelineN(object):
    """A context manager that handles pipeline state of an
    `RejsonIPC` instance.

    """

    logger = get_logger()

    def __init__(self, ipc):
        self._ipc = ipc

    def __enter__(self):
        self._pipeline = self._ipc._connection.pipeline()
        self._ipc._pipelines.append(self._pipeline)
        return self

    def __exit__(self, *args):
        assert self._ipc._pipelines[-1] is self._pipeline
        self._ipc._pipelines.pop(-1)
        self._pipeline = None

    def execute(self, result_index=None):
        result = self._pipeline.execute()
        # unpack the result if there is only one item
        if result_index is None:
            return result
        return result[result_index]

    def try_execute(self, *args, **kwargs):
        try:
            return self.execute(*args, **kwargs)
        except Exception as e:
            self.logger.error(
                    f"failed execute query: {e}", exc_info=True)
            return None


class RejsonIPC(object):

    """This class manages a JSON object in redis.

    The actual data stub stored in the redis db under ``redis_key`` looks like:

    .. code::

        {
            '_ipc_obj': {'a': 'b'},
            '_ipc_meta': {
                'key': 'redis_key'
                'rev': 0,
                'created_at': [xxxx, yyyy],
                'updated_at': [zzzz, wwww],
                }
            }

    Parameters
    ----------
    label : str
        The label of this IPC channel.

    """

    _connection = None
    """The redis client.

    This will be replaced after `init_ipc` is called.
    """

    _obj_key = '_ipc_obj'
    """The key name to store the actual JSON payload object."""

    _meta_key = '_ipc_meta'
    """The key name to store the metadata."""

    _obj_path = JsonPath().joinpath(_obj_key)

    _meta_path = JsonPath().joinpath(_meta_key)

    @staticmethod
    def _make_redis_key(label):
        """Create a unique key to use in the redis db."""
        return f'_ipc_{label}'

    def __init__(self, label):
        self._label = label
        self._pipeline = None

    @property
    def label(self):
        return self._label

    @property
    def redis_key(self):
        """The key of the redis db entry."""
        return self._make_redis_key(self._label)

    def _create_rejson_data(self, obj=None, time=None):
        """Build the data to store in the redis db.

        """
        redis_key = self.redis_key
        data = {
                self._meta_key: dict(),
                self._obj_key: obj
                }
        meta = data[self._meta_key]
        for key, default in [
                ('key', redis_key),
                ('rev', 0),
                ('created_at', time),
                ('updated_at', time),
                ]:
            meta.setdefault(key, default)
        return data

    @staticmethod
    def _resolve_path(path, parent_path):
        path = JsonPath(path)
        if path.is_absolute():
            path = path.relative_to(JsonPath.root)
        return parent_path.joinpath(path)

    def _resolve_obj_path(self, path):
        """Returns the JSON data path for given object path."""
        return self._resolve_path(path, self._obj_path)

    def _resolve_meta_path(self, path):
        """Returns the JSON data path for given metadata path."""
        return self._resolve_path(path, self._meta_path)

    @classmethod
    def init_ipc(cls, url):
        cls._connection = Client.from_url(url, decode_responses=True)

    @property
    def connection(self):
        # this hides the pipeline away
        if self._pipeline is not None:
            return self._pipeline
        return self._connection

    @property
    def pipeline(self):
        """A pipeline execution context."""

        return _RejsonIPCPipeline(self)

    def get_rejson_data(self):
        """Return the entire JSON data."""
        return self._query_rejson_data('get', JsonPath.root)

    def get_meta(self, key=None):
        """Return the metadata."""
        if key is None:
            key = ''
        return self._query_rejson_data('get', self._meta_path.joinpath(key))

    def ensure_obj(self, obj=None):
        """Setup the JSON data with `obj` if it does not exist yet.

        Returns
        -------
        bool
            False if new object is created.
        """
        logger = get_logger()
        redis_key = self.redis_key
        # by pass any pipeline to check key exists
        if not self._connection.exists(redis_key):
            data = self._create_rejson_data(
                    obj=obj, time=self.connection.time())
            logger.debug(
                    f"create data at key={redis_key} "
                    f"meta={data[self._meta_key]} "
                    f"obj_type={type(data[self._obj_key])}")
            self.connection.jsonset(redis_key, JsonPath.root, data)
            return False
        else:
            logger.debug(f"data at key={redis_key} exists.")
            return True

    def _query_rejson_data(
            self, op, rejson_path, *args, **kwargs):
        """Query JSON data at path `path`.

        This assumes that the data exists.
        """
        logger = get_logger('rejson query')
        redis_key = self.redis_key
        logger.debug(
                f"conn_type={self.connection.__class__.__name__} op={op}"
                f" redis_key={redis_key} "
                f"rejson_path={rejson_path}")

        if self._is_readonly_query_op(op):
            return getattr(self.connection, f'json{op}')(
                    redis_key, rejson_path, *args, **kwargs)
        # use a pipeline to update the data with meta
        with self.pipeline as p:
            self.connection.jsonnumincrby(
                    redis_key, self._meta_path.joinpath("rev"), 1)
            # need to get the time immediately so use self._connection
            self.connection.jsonset(
                    redis_key,
                    self._meta_path.joinpath("updated_at"),
                    self._connection.time())
            getattr(self.connection, f'json{op}')(
                    redis_key, rejson_path, *args, **kwargs)
            p.execute()
        return None

    _readonly_query_ops = [
            'get', 'mget', 'type',
            'strlen', 'arrindex', 'arrlen',
            'objkeys', 'objlen', 'resp'
            ]

    @classmethod
    def _is_readonly_query_op(cls, op):
        return op in cls._readonly_query_ops

    def query_obj(self, op, path, *args, **kwargs):
        """Query object at path `path` with `op`.

        This assumes that the data exists.
        """
        logger = get_logger()

        path = JsonPath(path)
        rejson_path = self._resolve_obj_path(path)

        logger.debug(f"resolve obj path {path} -> {rejson_path}")

        return self._query_rejson_data(op, rejson_path, *args, **kwargs)

    def is_initialized(self):
        return self._connection.exists(self.redis_key)

    def type(self, path=JsonPath.root):
        return self.query_obj('type', path)

    def is_null(self, path=JsonPath.root):
        type_ = self.query_obj('type', path)
        if type_ is None:
            return type_
        return self.query_obj('type', path) == 'null'

    def get(self, path=JsonPath.root):
        """Return value at `path`.

        `None` is returned if unable to get object.
        """
        logger = get_logger()
        try:
            return self.query_obj('get', path)
        except redis.exceptions.ResponseError as e:
            logger.debug(
                    f"unable to get obj from {self.redis_key}: {e}",
                    exc_info=True)
        return None

    def reset(self, obj):
        """Reset the object with `obj`."""
        self.connection.jsonset(
                self.redis_key, JsonPath.root,
                self._create_rejson_data(obj))

    def set(self, obj, path=JsonPath.root):
        """Set `obj` to path.

        If `path` is root, new object is created implicitly.
        """
        if path == JsonPath.root and not self.ensure_obj(obj=obj):
            # new object is created so return.
            return
        # set the object
        # this will trigger an update of the rev
        self.query_obj('set', path, obj)

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
        # def _ensure_metadata(self, obj, time=None):
        #     """Modify `obj` such that metadata are present."""
        #     pass
        # check if redis_key matches.
        # if redis_key != meta['key']:
        #     raise ValueError(f"inconsistent obj key {redis_key}")
