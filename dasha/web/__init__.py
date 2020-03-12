#! /usr/bin/env python

"""This module defines DashA web server globals."""

import os
from tollan.utils.log import get_logger, timeit, logit, init_log
from tollan.utils.fmt import pformat_dict
from tollan.utils.env import env_registry
from .. import SiteRuntime


__all__ = ['site', 'create_app']


# enable logging for the start up if flask development is set
if os.environ.get('FLASK_ENV', 'development'):
    init_log(level='DEBUG')


env_registry.register('DASHA_LOGFILE', 'The file for logging.')
env_registry.register('DASHA_LOGLEVEL', 'The DashA log level.')


site = SiteRuntime.from_env()
"""Used to manage the site runtime configs."""


@timeit
def create_app():
    logger = get_logger()
    server = site.get_server()
    for ext in site.get_extentions():
        with logit(logger.debug, f"init app extension {ext.__name__}"):
            ext.init_app(server)
    logger.debug(f"registered env vars:{pformat_dict(env_registry)}")
    # reconfigure the logger
    logfile = env_registry.get('DASHA_LOGFILE', None)
    loglevel = env_registry.get('DASHA_LOGLEVEL', 'INFO')
    init_log(level=loglevel, file_=logfile)
    return server
