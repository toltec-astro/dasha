#! /usr/bin/env python

"""This module defines DashA web server globals."""

import os
from tollan.utils.log import get_logger, timeit, logit, init_log
from tollan.utils.fmt import pformat_dict
from tollan.utils.env import env_registry
from .. import SiteRuntime


__all__ = ['site', 'create_app']


# enable logging if flask development is set
if os.environ.get('FLASK_ENV', 'development'):
    init_log(level='DEBUG')


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
    return server
