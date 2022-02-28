#! /usr/bin/env python

import flask
from pathlib import Path
import importlib.util
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Sequence
from schema import Use

from tollan.utils.fmt import pformat_yaml
from tollan.utils.log import get_logger, timeit, logit
from tollan.utils import getobj
from tollan.utils import rupdate
from tollan.utils.dataclass_schema import add_schema
from tollan.utils.schema import ObjectSchema


__all__ = ['Extension', 'Site']


DASHA_SITE_VAR_NAME = 'DASHA_SITE'


def _ensure_obj(arg):
    """Load python object if `arg` is string."""
    if isinstance(arg, str):
        return getobj(arg)
    return arg


@add_schema
@dataclass
class Extension(object):
    """
    A class to provide unified interface to configure and initialize
    extensions using the flask factory pattern (flask extensions).

    It shall be constructed via the :meth:`from_dict` class method. Two items
    are expected:

    1. ``module``. This shall be a module that defines the following two
    methods:

        1. ``init_ext``. This shall be a function that takes a config dict and
        return a properly configured underlying flask extension object.

        2. ``init_app``. This shall be a function that takes the underlying
        flask extension object and a config dict. It is called to setup the
        flask extension with respect to the given app.

    2. ``config``. The config dict to be passed to ``init_ext`` and
    ``init_app``.

    Conventionally, an `~wrapt.ObjectProxy` object should be made available
    at the extension module level to allow convenient importing from other
    modules. The ``__wrapped__`` object should be set to the underlying
    flask extension object at the end of ``init_ext``.

    The underlying extension object is also available as attribute :attr:`ext`.

    For an example of extension module, see `~dasha.web.extensions.db`
    """

    module: object = field(
        metadata={
            'description': 'The extension module.',
            'schema': ObjectSchema(
                attrs_required=('init_ext', 'init_app'),
                base_schema=Use(_ensure_obj))
            }
        )
    config: dict = field(
        default_factory=dict,
        metadata={
            'description': 'The extension config dict.',
            }
        )

    def __post_init__(self, *args, **kwargs):
        self._ext = self.module.init_ext(self.config)

    def init_app(self, server):
        """Set up the extension module for app.

        """
        self.module.init_app(server, self.config)

    @property
    def ext(self):
        return self._ext


def _resolve_ext(ext):
    """Load extension if `ext` is dict.
    """
    # first pass, create extension objects
    if isinstance(ext, Mapping):
        return Extension.from_dict(ext)
    return ext


def _make_ext_list(exts):
    """Load extension list from extension definitions.

    Dict will be resolved to `Extension` object, and duplicates
    will be merged.

    Parameters
    ----------
    exts : list of dict or `Extension`.
        The extension definitions.
    """
    exts = list(map(_resolve_ext, exts))
    ext_dict = dict()
    # check extension of same module and merge the config
    for ext in exts:
        if ext.module in ext_dict:
            rupdate(ext_dict[ext.module].config, ext.config)
        else:
            ext_dict[ext.module] = ext
    return list(ext_dict.values())


def _make_flask_server():
    """Return a basic flask server used as default when server is not specifed
    in `Site`.
    """
    return flask.Flask(__package__)


@timeit
def _resolve_server(arg):
    """Load server instance."""

    if isinstance(arg, str):
        arg = getobj(arg)
    if callable(arg):
        return arg()
    return arg


@add_schema
@dataclass
class Site(object):
    """
    A class to manage the context of a DashA site, composed of a Flask server,
    a server config dict, and a set of extensions:

    1. ``server``. Optional, this shall be a Flask server instance or a
    callable return a server instance. If str, it is resolved using
    `~tollan.utils.getobj`. When not specified, a basic Flask server is created
    and used.

    1. ``server_config``. Optional. This shall be a dict or object for
    configuring the Flask server. This is typically used to configure the
    default Flask server when ``server`` is not set.

    2. ``extensions``. The shall be a list of items that an
        `~dasha.core.Extension` object could be created from.

    Instance of this class is typically created via the ``from_*`` class
    methods.
    """
    server: object = field(
        default_factory=_make_flask_server,
        metadata={
            'description': 'The Flask server.',
            'schema': Use(_resolve_server)
            }
        )

    server_config: object = field(
        default_factory=dict,
        metadata={
            'description': 'The Flask server config.',
            }
        )

    extensions: Sequence[Extension] = field(
        default_factory=list,
        metadata={
            'description': 'The extension list.',
            'schema': Use(_make_ext_list)
            }
        )

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
        with logit(logger.debug, f"init server {server}"):
            config = self.server_config
            if isinstance(config, Mapping):
                server.config.update(config)
            else:
                server.config.from_object(config)
        for ext in self.extensions:
            with logit(
                    logger.debug, f"init extension {ext}"):
                ext.init_app(server)
        return server

    @classmethod
    def from_dict(cls, d):
        cls.logger.debug(f"create site from\n{pformat_yaml(d)}")
        # the add_schema creates from_dict_ because we have from_dict
        # already
        return cls.from_dict_(d)

    @classmethod
    def from_filepath(cls, filepath):
        """Create a site from a python source file.

        The module file has to have a dict named dasha_site
        which get passed to :meth:`from_dict`.

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
        if not hasattr(obj, DASHA_SITE_VAR_NAME):
            raise ValueError(
                f"Object {obj} does not define a DASHA_SITE variable")
        DASHA_SITE = obj.DASHA_SITE
        if callable(DASHA_SITE):
            DASHA_SITE = DASHA_SITE()
        return cls.from_dict(DASHA_SITE)

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
