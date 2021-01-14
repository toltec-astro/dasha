#! /usr/bin/env python


"""
This file defines an multi page site that uses the Burger component
from dash_extensions.
"""

from dasha.web.templates import ComponentTemplate
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash_extensions import Burger
# import dash_core_components as dcc
# from dash.dependencies import Output, Input


class BurgerApp(ComponentTemplate):

    _component_cls = dbc.Container
    fluid = True
    id = 'burger-app'

    def _make_sidebar(self, container):
        pages = [
                ('Page A', '/page_a', html.H5('Page A')),
                ('Page 1', '/page_1', html.Pre('Page 1')),
                ('Page 2', '/page_2', html.P('Page 2')),
                ]
        children = []
        for nav_text, href, content in pages:
            children.append(html.A(children=nav_text, href=href))
        container.child(
                Burger(
                    children=children,
                    effect="slide",
                    position="right",
                    pageWrapId="page-content",
                    outerContainerId="burger-page",
                    ))

    def setup_layout(self, app):
        self._make_sidebar(self)
        content_container = self.child(html.Div, id='page-content')
        content_container.child(html.P, 'content goes here')

        super().setup_layout(app)


extensions = [
    {
        'module': 'dasha.web.extensions.dasha',
        'config': {
            'template': BurgerApp,
            'title_text': 'Burger',
            }
        },
    ]
