#! /usr/bin/env python

import os
from .. import SiteRuntime
from ..utils.log import get_logger, timeit, logit


__all__ = ['site', 'create_app']


# enable logging for development env
if os.environ.get('FLASK_ENV', 'development'):
    from ..utils.click_log import init as init_log
    init_log('DEBUG')


site = SiteRuntime.from_env()


@timeit
def create_app():
    """The web entry point."""

    logger = get_logger()

    from ..defaults import config as config_default

    # create server
    server = site.create_server(config_default)

    # init extensions
    if callable(site.extensions):
        exts = site.extensions()
    else:
        exts = site.extensions

    for ext in exts:
        with logit(logger.debug, f"init {ext.__name__}"):
            ext.init_app(server)

    return server
