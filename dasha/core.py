#! /usr/bin/env python

import os
import sys
import importlib
from collections.abc import Mapping
from pathlib import Path
from .utils.log import get_logger
from .utils.fmt import pformat_dict
from .utils import dict_from_object
from . import defaults

__all__ = ['SiteRuntime', ]


class SiteRuntime(object):
    """This class encapsulates all the runtime config of a DashA site."""

    _default_runtime_env_name = 'DASHA_SITE'

    _default_config = {
            'create_server': defaults.create_server,
            'extensions': defaults.extensions
            }

    logger = get_logger()

    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)

    def __init__(self, config):
        """Initialize `SiteRuntime` object from runtime configuration `config`.

        Parameters
        ----------
        config: dict
            The runtime config to use.
        """
        super().__init__()
        for k, v in self._default_config.items():
            if k not in config:
                self.logger.debug(f"{k} not found in config, use default {v}")
            config.setdefault(k, v)
        # normalize extension
        self._config = config
        self.logger.debug(
                f"site runtime from config:{pformat_dict(config)}")

    @property
    def config(self):
        return self._config

    @staticmethod
    def _normalize_extension(ext):
        def _extension_from_dict(config):
            module_key = 'module'
            if module_key not in config:
                raise RuntimeError(
                        f"failed creating extension, {module_key} not found")
            module = importlib.import_module(config[module_key])
            for k, v in config.items():
                setattr(module, k, v)
            return module
        if isinstance(ext, Mapping):
            return _extension_from_dict(ext)
        return ext

    @property
    def extentions(self):
        return map(self._normalize_extension, self.config['extensions'])

    def create_server(self):
        return self.config['create_server'](self.config)

    @classmethod
    def from_object(cls, obj, **kwargs):
        """Create `SiteRuntime` object from a module."""
        return cls(dict_from_object(obj, **kwargs))

    @classmethod
    def from_env(
            cls, name=_default_runtime_env_name, default=None,
            env_registry=None
            ):
        """Create `SiteRuntime` object from environment variables.

        The value of environment variable `name` shall be an import
        path to a python module that defines necessary attributes
        of the to-be-created `SiteRuntime` object.
        It can either be a qualified name of a installed python module,
        or file system path to a python module
        (directory with ``__init__.py`` or a ``.py`` file).

        Parameters
        ----------
        name : str
            The name of environment variable to use.

        default: str
            A default value in case `name` is not found.

        env_registry: `dasha.utils.env.EnvRegistry`
            Register `name` to the specified registry.

        Returns
        -------
        SiteRuntime
            A `SiteRuntime` instance.
        """

        logger = get_logger()

        if env_registry is not None:
            env_registry.register(
                    name,
                    "The import path to a python module that defines the site."
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
            path = Path(module_path).expanduser().resolve()
            sys.path.insert(0, path.parent.as_posix())
            return cls.from_object(importlib.import_module(path.name))
