#! /usr/bin/env python

"""
This file defines an example site that makes use of
the `dasha.web.templates.dash_bootstrap_demo` template.
"""

extensions = [
    {
        'module': 'dasha.web.extensions.dasha',
        'config': {
            'template': 'dasha.web.templates.dash_bootstrap_demo',
            'title_text': 'DashA with Bootstrap',
            }
        },
    ]
