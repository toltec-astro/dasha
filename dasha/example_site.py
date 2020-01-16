#! /usr/bin/env python
"""This file defaults an example site that uses only the defaults."""
from .utils import patch
from .utils.log import get_logger

# import extensions
from .web.extensions import db  # noqa: E402
from .web.extensions import cache  # noqa: E402
from .web.extensions import dasha  # noqa: E402


logger = get_logger(__name__)


@patch(db, 'init')
def db_init(cls):
    logger.debug(f"init db using {cls} ...")
    return cls()


@patch(cache, 'init_app')
def cache_init_app(server):
    cache_config = {'CACHE_TYPE': 'simple'}
    logger.debug(f"init cache using {cache_config} ...")
    cache.cache.init_app(server, config=cache_config)


@patch(dasha, 'init')
def dasha_init(cls):
    config = {
            'TITLE': 'Example Site'
            }
    logger.debug(f"init dasha using {config} ...")
    return cls(config)


# required site runtime attrs
# from .defaults import create_server  # noqa: F401
extensions = [db, cache, dasha]

# additional config
TITLE = "Example Site"
