#! /usr/bin/env python

import os
from .. import SiteRuntime
from ..utils.env import EnvRegistry
from ..utils.log import get_logger, timeit, logit
from ..utils.fmt import pformat_dict


__all__ = ['site', 'env_registry', 'create_app']


logger = get_logger()


# enable logging for development env
if os.environ.get('FLASK_ENV', 'development'):
    from ..utils.click_log import init as init_log
    init_log('DEBUG')


env_registry = EnvRegistry.create()
"""Used to hold all recognized environment variables."""

site = SiteRuntime.from_env(env_registry=env_registry)


@timeit
def create_app():
    server = site.create_server()
    for ext in site.extentions:
        with logit(logger.debug, f"init {ext.__name__}"):
            ext.init_app(server)
    logger.debug(f"registered envs:{pformat_dict(env_registry)}")
    return server
