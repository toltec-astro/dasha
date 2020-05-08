#! /usr/bin/env python


from wrapt import ObjectProxy
from tollan.utils.fmt import pformat_yaml
from tollan.utils.log import get_logger
from copy import deepcopy
from tollan.utils import rupdate


__all__ = ['IPC', 'ipc']


ipc = ObjectProxy(None)
"""A proxy to the `~dasha.web.extensions.ipc.IPC` instance."""


class IPC(object):
    """A class that manages various interprocess communication resources."""

    _default_config = {
            'backends': {
                'rejson': {
                    'url': "redis://localhost:6379/1"
                    },
                },
            }
    _supported_backends = ['rejson', ]
    _backends = None

    logger = get_logger()

    @classmethod
    def _ensure_config(cls, config):
        if config is None:
            config = dict()
        result = deepcopy(cls._default_config)
        rupdate(result, config)
        return result

    def _init_backend(self, name, config):
        self._backends[name] = getattr(
                self, f'_get_{name}_backend')(config)
        self.logger.debug(f"init backend {name}={self._backends[name]}")

    def _get_file_backend(self, config):
        return NotImplemented

    def _get_rejson_backend(self, config):
        from .ipc_backends.rejson import RejsonIPC
        RejsonIPC.init_ipc(**config)
        return RejsonIPC

    def init_app(self, server, config=None):
        config = self._ensure_config(config)
        self.logger.debug(f"IPC config: {pformat_yaml(config)}")

        self._backends = dict()
        for name, backend_config in config['backends'].items():
            if name not in self._supported_backends:
                self.logger.warning(f"ignore unknown backend {name}")
                continue
            self._init_backend(name, backend_config)

    def get_or_create(self, backend, *args, **kwargs):
        """Return an IPC instance for shared data access.

        `ValueError` is raised if `backend` is not configured.

        Parameters
        ----------
        backend : str
            The backend to use.
        *args, **kwargs
            The keyword arguments passed to the IPC instance constructor.

        """
        if self._backends is None or backend not in self._backends:
            raise ValueError(f"backend {backend} is not available")
        return self._backends[backend](*args, **kwargs)


def init_ext(config):
    ext = ipc.__wrapped__ = IPC()
    return ext


def init_app(server, config):
    ipc.init_app(server, config=config)
