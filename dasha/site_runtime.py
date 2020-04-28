#! /usr/bin/env python

import sys
import inspect
import importlib
from collections.abc import Mapping
from pathlib import Path
from tollan.utils.log import get_logger
from tollan.utils.fmt import pformat_yaml
from tollan.utils import dict_from_object, object_from_spec


__all__ = ['SiteRuntime', ]


class SiteRuntime(object):
    """This class manages context of a DashA site.

    Parameters
    ----------
    server: `flask.Flask` or callable
        The server instance or a callable that returns it.

    extensions: list of dicts
        A list of server extension definitions.

    **kwargs:
        Additional configs that is passed to the server config dict.

    """

    logger = get_logger()

    def __init__(
            self,
            server=None,
            extensions=None,
            **kwargs):

        if server is None:
            server = self.default_server
        if extensions is None:
            from .examples import welcome_dash_bootstrap
            extensions = welcome_dash_bootstrap.extensions
        self._config = dict(server=server, extensions=extensions, **kwargs)

        def pformat_config(config):
            return pformat_yaml(
                    {k: v for k, v in config.items()
                        if not inspect.ismodule(v)})
        self.logger.debug(
                f"site runtime:\n{pformat_config(self._config)}")

    @property
    def config(self):
        return self._config

    @staticmethod
    def _resolve_extension(ext):

        def _extension_from_dict(ext):
            module_key = 'module'
            if module_key not in ext:
                raise RuntimeError(
                        f"invalid extension, {module_key} not found.")
            module = importlib.import_module(ext[module_key])
            for k, v in ext.items():
                setattr(module, k, v)
            return module

        if isinstance(ext, Mapping):
            return _extension_from_dict(ext)
        return ext

    def get_extentions(self):
        return map(self._resolve_extension, self.config['extensions'])

    def get_server(self):
        _server = self.config['server']
        if isinstance(_server, str):
            _server = object_from_spec(_server)
        if callable(_server):
            return _server(self.config)
        return _server

    @classmethod
    def default_server(cls, config):
        """Return a flask server."""
        import flask
        server = flask.Flask(__package__)
        server.config.from_object(config)
        cls.logger.debug(f"create default server {server}")
        return server

    @classmethod
    def from_object(cls, obj, **kwargs):
        """Create `SiteRuntime` object from a module."""
        obj_d = dict_from_object(obj)
        if 'extensions' not in obj_d:
            raise RuntimeError(f"no extension list defined in {obj}.")
        return cls(**obj_d, **kwargs)

    @classmethod
    def from_path(cls, module_path):
        """Create site runtime from path.

        The value of `path` shall be an import path to a python module that
        defines necessary attributes to construct the site runtime instance. It
        can either be the qualified name of an installed python module, or the
        path to a directory contains ``__init__.py`` or a ``.py`` file.

        Parameters
        ----------
        module_path : str
            The site module import path or file path.

        Returns
        -------
        SiteRuntime
            A `SiteRuntime` instance.

        """

        logger = get_logger()

        try:
            return cls.from_object(importlib.import_module(module_path))
        except Exception:
            logger.debug(
                    f"not a valid import path {module_path}, try as file path")
            # try interpret as path
            path = Path(module_path).expanduser().resolve()
            sys.path.insert(0, path.parent.as_posix())
            logger.debug(f"import {path.stem} from {path.parent}")
            return cls.from_object(importlib.import_module(path.stem))
