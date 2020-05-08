#! /usr/bin/env python

from tollan.utils.namespace import Namespace, dict_from_object
from schema import Schema, Use, And, Optional, SchemaError
import flask
from tollan.utils.log import get_logger, timeit, logit
from tollan.utils import getobj
from pathlib import Path
import importlib.util
from collections.abc import Mapping
from tollan.utils.fmt import pformat_yaml
import functools


__all__ = ['Extension', 'Stack', 'Site']


class Extension(Namespace):
    """
    This class provides a unified interface to configure and initialize
    extensions using the flask factory pattern (flask extensions).

    It shall be constructed via the :meth:`from_dict` class method. Two items
    are expected:

    1. "module". This shall be a module that defines the following two methods:

        1. ``init_ext``. This shall be a function that takes a config dict
        and return a properly configured underlying flask extension object.

        2. ``init_app``. This shall be a function that takes the underlying
        flask extension object and a config dict. It is called to setup the
        flask extension with respect to the given app.

    2. "config". The config dict to be passed to ``init_ext`` and ``init_app``.

    Conventionally, an `~wrapt.ObjectProxy` object should be made available
    at the extension module level to allow convenient importing from other
    modules. The ``__wrapped__`` object should be set to the underlying
    flask extension object at the end of ``init_ext``.

    For an example of extension module, see `~dasha.web.extensions.db`
    """

    # this allow extension to be created for any dict.
    _namespace_type_key = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ext = self.module.init_ext(self.config)

    def __repr__(self):
        return f'{self.module.__name__}'

    class _resolve_ext(object):
        """Validatable that resolves str to a extension module."""

        @staticmethod
        def validate(arg):
            if isinstance(arg, str):
                return getobj(arg)
            return arg

    _namespace_from_dict_schema = Schema(
            {
                'module': _resolve_ext(),
                'config': dict
                },
            ignore_extra_keys=True
            )
    _namespace_to_dict_schema = Schema(
            {
                'module': object,
                'config': object
                },
            ignore_extra_keys=True
            )

    def init_app(self, server):
        """Setup the underlying extension for app.

        `RuntimeError` is raised if this function is called multiple times.

        """
        self.module.init_app(server, self.config)

    def __eq__(self, other):
        """Extensions are identified by its module."""
        return self.module.__eq__(other.module)

    def __hash__(self):
        """Extensions are identified by its module."""
        return self.module.__hash__()


class Stack(Namespace):
    """
    This class is a thin wrapper around a set of extensions.

    Parameters
    ----------
    extensions : A list of `~dasha.core.Extension` or dict
        A list of extensions. Items of dict type should be such that extension
        objects can be constructed using
        `~dasha.core.Extension.from_dict`.

    """

    logger = get_logger()

    class _remove_dumplicated_extensions(object):
        """Validatable that removes duplicates in the extension list.

        Duplicates are identified by their class.

        """

        @staticmethod
        def validate(exts):
            # check exts types
            ext_insts = set()
            validated = []
            for ext in exts:
                if ext in ext_insts:
                    raise SchemaError(
                            f'duplicated extension found in stack: {ext}.')
                ext_insts.add(ext)
                validated.append(ext)
            return validated

    _namespace_from_dict_schema = Schema(
            {
                'extensions': And(
                    [Use(Extension.from_dict), ],
                    _remove_dumplicated_extensions(),
                    ),
                },
            ignore_extra_keys=True
            )
    _namespace_to_dict_schema = Schema(
            {
                'extensions': [Use(Extension.to_dict), ],
                },
            ignore_extra_keys=True
            )


def _default_server(config_obj):
    """Return a basic flask server.

    Parameters
    ----------
    config_obj : object
        Object that may carry server configurations.

    """
    server = flask.Flask(__package__)
    server.config.from_object(config_obj)
    return server


class Site(Namespace):
    """
    This class manages the context of a DashA site, composed of a server and
    a set of extensions.

    It shall be constructed via the ``from_*`` class methods. Two objects
    are expected:

    1. "server". This shall be a function that returns the server instance.
        This function optionally may take the site instance as the only
        argument.

    2. "extensions". The shall be a list of items that an
        `~dasha.core.Extension` object could be created from.
    """

    logger = get_logger()

    @timeit
    def init_app(self):
        """Initialize server and the extensions.

        This will instantiates the extensions and call the ``init_app``
        methods of them.

        .. note::
            :attr:`server` will be replaced with the actual server
            instance after this call.

        """
        logger = get_logger()
        server = self.server
        with logit(logger.debug, f"init server"):
            server = server(self)
        for ext in self.extensions:
            with logit(
                    logger.debug, f"init extension {ext}"):
                ext.init_app(server)
        self.server = server
        return server

    class _resolve_server_factory(object):
        """Validatable that resolves str to a server factory function."""

        @staticmethod
        def validate(arg):
            if isinstance(arg, str):
                arg = getobj(arg)
            if callable(arg):
                return arg
            raise SchemaError(f"Callable expected, {type(arg)} found.")

    _namespace_from_dict_schema = Schema(
            {
                Optional(
                    'server',
                    # has to wrap this in a lambda to allow later call in
                    # init_app
                    default=functools.wraps(
                        _default_server)(lambda: (_default_server))
                        ): _resolve_server_factory(),
                'extensions': And(
                    # make stack and unpack to check for duplicates
                    Use(lambda exts: dict(extensions=exts)),
                    Use(Stack.from_dict),
                    Use(lambda s: s.extensions),
                    ),
                # allcap keys are server configs
                Optional(str.isupper): object
                },
            ignore_extra_keys=True
            )
    _namespace_to_dict_schema = Schema(
            {
                'server': object,
                'extensions': [Use(Extension.to_dict)],
                Optional(str.isupper): object
                },
            ignore_extra_keys=True
            )

    @classmethod
    def from_dict(cls, d, **kwargs):
        cls.logger.debug(f"create site from\n{pformat_yaml(d)}")
        return super().from_dict(d, **kwargs)

    @classmethod
    def from_filepath(cls, filepath):
        """Create a site from a python source file.

        Parameters
        ----------
        filepath : str or `~pathlib.Path`
            The path of the python source file to use.

        Returns
        -------
        `~dasha.core.Site`
            A `~dasha.core.Site` instance.
        """
        with timeit(f'import site module from {filepath}'):
            filepath = Path(filepath).expanduser().resolve()
            spec = importlib.util.spec_from_file_location(
                    f"dasha_site_{filepath.stem}", filepath.as_posix())
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        return cls.from_object(module)

    @classmethod
    def from_object(cls, arg):
        """Create a site from an object that contains the site configurations.

        Parameters
        ----------
        arg : object or str
            The object to use. If str, `~tollan.utils.getobj` is used to
            import the object.

        Returns
        -------
        `~dasha.core.Site`
            A `~dasha.core.Site` instance.
        """
        if isinstance(arg, str):
            with timeit(f'import site module from {arg}'):
                obj = getobj(arg)
        else:
            obj = arg
        return cls.from_dict(dict_from_object(obj))

    @classmethod
    def from_any(cls, arg):
        """Create a site from `arg`.

        It checks the value of `arg` and dispatches to the most probable
        ``from_*`` factory method.
        """

        if isinstance(arg, str):
            # this could be a filepath or module path
            p = Path(arg)
            if p.exists() and (not p.is_dir()) and (p.suffix == '.py'):
                return cls.from_filepath(p)
        if isinstance(arg, Mapping):
            return cls.from_dict(arg)
        return cls.from_object(arg)
