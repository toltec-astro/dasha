#! /usr/bin/env python

from dasha.web.extensions.dasha import CSS

"""
This file defines an example site that makes use of
the `dasha.web.templates.slapdash` template.
"""

DASHA_SITE = {
    'extensions': [
        {
            'module': 'dasha.web.extensions.dasha',
            'config': {
                'THEME': CSS.themes.LUMEN,
                'template': 'dasha.web.templates.slapdash',
                'title_text': 'MySite',
                'pages': [
                    {
                        'template': 'dasha.examples.nat:Nat',
                        'route_name': 'nat',
                        'title_text': 'Nat',
                        'title_icon': 'fas fa-table',
                        },
                    {
                        'template': 'dasha.web.templates.viewgrid:ViewGrid',
                        'route_name': 'nat_in_grid',
                        'title_text': 'Nat in Grid',
                        'title_icon': 'fas fa-table',
                        'views': [
                            {
                                'template': 'dasha.examples.nat:Nat',
                                'title_text': 'nat1'
                                },
                            {
                                'template': 'dasha.examples.nat:Nat',
                                'title_text': 'nat2'
                                }
                            ]
                        },
                    {
                        'title_text': 'Submenu',
                        'pages': [
                            {
                                'template': 'dasha.examples.nat:Nat',
                                'route_name': 'nat_sub',
                                'title_text': 'Nat sub',
                                'title_icon': 'fas fa-table',
                                },
                            {
                                'template':
                                'dasha.web.templates.viewgrid:ViewGrid',
                                'route_name': 'nat_sub_in_grid',
                                'title_text': 'Nat sub in Grid',
                                'title_icon': 'fas fa-table',
                                'views': [
                                    {
                                        'template': 'dasha.examples.nat:Nat',
                                        'title_text': 'nat1'
                                        },
                                    {
                                        'template': 'dasha.examples.nat:Nat',
                                        'title_text': 'nat2'
                                        }
                                    ]
                                }
                            ]
                        }
                    ] + [
                        {
                            'template': 'dasha.examples.nat:Nat',
                            'route_name': f'nat_x{i}',
                            'title_text': 'Nat' * 10,
                            'title_icon': 'fas fa-table',
                            }
                        for i in range(20)
                            ],
                }
            },
        ],
    }
