#! /usr/bin/env python

"""This module defines DashA web server globals."""

import os
from tollan.utils.log import get_logger, timeit, init_log, logit
from tollan.utils.fmt import pformat_yaml
from tollan.utils.env import env_registry
from wrapt import ObjectProxy
from contextlib import ExitStack
from .. import Site
# import signal
import atexit


__all__ = ['site', 'create_site', 'create_app']


# enable logging for the start up if flask development is set
if os.environ.get('FLASK_ENV', None) == 'development':
    init_log(level='DEBUG')
else:
    init_log(level='INFO')


site = ObjectProxy(None)
"""
A proxy to a global `~dasha.core.Site` instance, which is made available after
`~dasha.web.create_site` is called.
"""

exit_stack = ExitStack()
""""
An `~contextlib.ExitStack` instance that can be used to register clean up
functions.
"""


@timeit
def create_site():
    """DashA entry point.

    Call this function to make available the `~dasha.web.site`.

    Returns
    -------
    `~dasha.Site`
        The site instance.

    """
    logger = get_logger()

    env_registry.clear()
    env_registry.register(
            'SECRET_KEY', 'The secret key to use.',
            'true')
    env_registry.register(
            'DASHA_SITE', 'The site module or path.',
            'dasha.examples.dasha_intro')
    env_registry.register('DASHA_LOGFILE', 'The file for logging.', None)
    env_registry.register('DASHA_LOGLEVEL', 'The DashA log level.', 'Info')
    logger.info(f"registered env vars:\n{pformat_yaml(env_registry)}")

    site.__wrapped__ = Site.from_any(env_registry.get('DASHA_SITE'))
    site.server_config.update(SECRET_KEY=env_registry.get('SECRET_KEY'))
    return site


@timeit
def create_app():
    """Flask entry point.

    """
    logger = get_logger()

    site = create_site()

    logger.info(f"init dasha site:\n{pformat_yaml(site.__dict__)}")
    server = site.init_app()
    # logger.info(f"flask config:\n{pformat_yaml(server.config)}")
    # reconfigure the logger
    logfile = env_registry.get('DASHA_LOGFILE')
    loglevel = env_registry.get('DASHA_LOGLEVEL')
    logger.info(f"reset logger: loglevel={loglevel} logfile={logfile}")
    # python logging level is upper case.
    init_log(level=loglevel.upper(), file_=logfile)
    from werkzeug.middleware.proxy_fix import ProxyFix
    server.wsgi_app = ProxyFix(server.wsgi_app, x_proto=1, x_host=1)
    return server


def _exit():
    logger = get_logger()
    with logit(logger.info, 'dasha clean up'):
        exit_stack.close()


atexit.register(_exit)
# signal.signal(signal.SIGTERM, _exit)
# signal.signal(signal.SIGINT, _exit)
