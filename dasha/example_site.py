#! /usr/bin/env python

"""This file defines an example site."""

server = 'dasha.site_runtime::DefaultSite.server'
extensions = [
    {
        'module': 'dasha.web.extensions.db',
        'config': {
            'SQLALCHEMY_BINDS': {'default': 'sqlite:///memory'}
            },
        },
    {
        'module': 'dasha.web.extensions.cache',
        'config': {'CACHE_TYPE': 'simple'}
        },
    {
        'module': 'dasha.web.extensions.dasha',
        'config': {
            # 'template': 'simple',
            'template': 'slapdash',
            'TITLE': 'DashA',
            }
        },
    ]
