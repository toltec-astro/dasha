#! /usr/bin/env python

import os
import sys
import importlib
from collections.abc import Mapping
from pathlib import Path
from tollan.utils.log import get_logger
from tollan.utils.fmt import pformat_dict
from tollan.utils import dict_from_object, object_from_spec
from tollan.utils.env import env_registry


__all__ = ['SiteRuntime', ]


class DefaultSite(object):
    """Default implementation of a site."""

    logger = get_logger()

    @classmethod
    def server(cls, config):
        """Return a flask server."""
        import flask
        server = flask.Flask(__package__)
        server.config.from_object(config)
        cls.logger.debug(f"create default server {server}")
        return server

    extensions = (
            importlib.import_module(
                f'..web.extensions.{e}', package=__package__)
            for e in ('dasha', ))
    """A set of default extensions."""


class SiteRuntime(object):
    """This class manages context of a DashA site.

    The site runtime provides method tha

    Parameters
    ----------
    server: `flask.Flask` or callable
        The server instance or a callable that returns it.

    extensions: list of dicts
        A list of server extension definition dicts.

    **kwargs:
        Additional configs that is passed to the server config dict.

    """

    _default_runtime_env_name = 'DASHA_SITE'
    _default_dasha_site = 'dasha.example_site'

    logger = get_logger()

    def __init__(
            self,
            server=DefaultSite.server,
            extensions=DefaultSite.extensions,
            **kwargs):

        self._config = dict(server=server, extensions=extensions, **kwargs)
        self.logger.debug(
                f"site runtime: {pformat_dict(self._config)}")

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
    def from_object(cls, obj, **kwargs):
        """Create `SiteRuntime` object from a module."""
        return cls(**dict_from_object(obj), **kwargs)

    @classmethod
    def from_env(
            cls, name=_default_runtime_env_name,
            default=_default_dasha_site,
            ):
        """Create site runtime from environment variable.

        The value of environment variable `name` shall be an import path to a
        python module that defines necessary attributes to construct the site
        runtime instance. It can either be the qualified name of an installed
        python module, or the path to a directory contains ``__init__.py`` or a
        ``.py`` file.

        Parameters
        ----------
        name : str
            The name of environment variable to use.

        default: str
            A default value in case `name` is not found.

        Returns
        -------
        SiteRuntime
            A `SiteRuntime` instance.

        """

        logger = get_logger()

        env_registry.register(
            name,
            "The import path or file system path of the site module."
            )

        _error = "Unable to create site runtime: {reason}"
        module_path = os.environ.get(name, default)
        if module_path is None:
            raise RuntimeError(
                    _error.format(
                        reason=f'environment variable {name} is not set, '
                               f'and a default module path is not specified.'
                        )
                )
        if module_path == default:
            logger.warning(
                    f"environment variable {name} is not set,"
                    f" use default {module_path}")

        try:
            return cls.from_object(importlib.import_module(module_path))
        except Exception:
            # try interpret as path
            path = Path(module_path).expanduser().resolve()
            sys.path.insert(0, path.parent.as_posix())
            return cls.from_object(importlib.import_module(path.name))
