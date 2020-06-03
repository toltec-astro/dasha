#! /usr/bin/env python

"""
This file defines an example site that makes use of
the `dasha.web.templates.slapdash` template.
"""

extensions = [
    {
        'module': 'dasha.web.extensions.dasha',
        'config': {
            'template': 'dasha.web.templates.slapdash',
            'title_text': 'MySite',
            'pages': [
                {
                    'template': 'dasha.examples.nat',
                    'route_name': 'nat',
                    'title_text': 'Nat',
                    'title_icon': 'fas fa-table',
                    },
                {
                    'template': 'dasha.web.templates.viewgrid',
                    'route_name': 'nat_in_grid',
                    'title_text': 'Nat in Grid',
                    'title_icon': 'fas fa-table',
                    'views': [
                        {
                            'template': 'dasha.examples.nat',
                            'title_text': 'nat1'
                            },
                        {
                            'template': 'dasha.examples.nat',
                            'title_text': 'nat2'
                            }
                        ]
                    }
                ],
            }
        },
    ]