#! /usr/bin/env python

"""
This file defines an example site that makes use of
the `dasha.web.templates.slapdash` template.
"""

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
            'template': 'simple',
            'TITLE': 'DashA',
            # 'template': 'slapdash',
            # 'pages': [
            #     {
            #         'template': 'dashaexample',
            #         'title_text': 'Example',
            #         }
            #     ],
            }
        },
    ]
