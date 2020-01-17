#! /usr/bin/env python
"""This file defines an example site that uses only the defaults."""
# from .utils import patch
from .utils.log import get_logger

logger = get_logger(__name__)


# import extensions
# from .web.extensions import db  # noqa: E402
# from .web.extensions import cache  # noqa: E402
# from .web.extensions import dasha  # noqa: E402


# @patch(db, 'init')
# def db_init(cls):
#     logger.debug(f"init db using {cls} ...")
#     return cls()


# @patch(cache, 'init_app')
# def cache_init_app(server):
#     cache_config = {'CACHE_TYPE': 'simple'}
#     logger.debug(f"init cache using {cache_config} ...")
#     cache.cache.init_app(server, config=cache_config)


# @patch(dasha, 'init')
# def dasha_init(cls):
#     config = {
#             'TITLE': 'Example Site'
#             }
#     logger.debug(f"init dasha using {config} ...")
#     return cls(config)


# extensions = [db, cache, dasha]


extensions = [
    {
        'module': 'dasha.web.extensions.db',
        'binds': {
            }
        },
    {
        'module': 'dasha.web.extensions.cache',
        'config': {

            }
        },
    {
        'module': 'dasha.web.extensions.dasha',
        'template': 'dasha.web.templates.slapdash',
        'pages': []
        },
    ]

# from .defaults import create_server  # noqa: F401
