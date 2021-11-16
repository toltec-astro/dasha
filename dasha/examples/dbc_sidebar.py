#!/usr/bin/env python

from dash import html, dcc
from dash_component_template import ComponentTemplate
import dash_bootstrap_components as dbc

from tollan.utils.log import get_logger
from dasha.web.templates.multipage import PageTree


class DBCSidebar(ComponentTemplate):

    class Meta:
        component_cls = dbc.Container

    # the style arguments for the sidebar. We use position:fixed and a fixed
    # width
    _sidebar_style = {
        "position": "fixed",
        "top": 0,
        "left": 0,
        "bottom": 0,
        "width": "16rem",
        "padding": "2rem 1rem",
        "background-color": "#f8f9fa",
        }

    # the styles for the main content position it to the right of the sidebar
    # and add some padding.
    _content_style = {
        "margin-left": "18rem",
        "margin-right": "2rem",
        "padding": "2rem 1rem",
        }

    logger = get_logger()

    def __init__(self, title_text, pages, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title_text = title_text
        # repackage the args and create the page tree
        self.page_tree = PageTree({'pages': pages, 'title_text': title_text})

    def _setup_sidebar(self, app, container, location, clientside_state):
        sidebar = container.child(html.Div, style=self._sidebar_style)
        # title
        sidebar.child(
            html.H2, self.title_text, className='display-4'
            )
        sidebar.child(html.Hr())

        # create the navlist
        # this makers are passed to the page tree nav tree maker which provides
        # the pattern matching id and pattern matching callback
        def make_navlist(container, id):
            return container.child(
                dbc.Nav, id=id, vertical=True, pills=True)

        def make_sub_container(container, title_text, id):
            sub_container = container.child(html.Div, id=id)
            sub_container.child(html.Div(title_text, className='mt-2'))
            return sub_container

        self.page_tree.setup_nav_tree(
            app,
            container=sidebar,
            make_navlist=make_navlist,
            make_sub_container=make_sub_container,
            location=location,
            clientside_state=clientside_state
            )

    def setup_layout(self, app):
        container = self

        location = self.child(dcc.Location, refresh=False)
        clientside_state = self.child(dcc.Store, data=dict())

        self._setup_sidebar(app, container, location, clientside_state)

        content_container = self.child(html.Div, style=self._content_style)

        self.page_tree.setup_page_layouts(app, location, content_container)

        super().setup_layout(app)


class SimplePage(ComponentTemplate):
    class Meta:
        component_cls = dbc.Container

    def __init__(self, title_text, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title_text = title_text

    def setup_layout(self, app):
        container = self
        container.child(html.H1, f"This is {self.title_text}")
        container.child(html.Hr())
        super().setup_layout(app)


DASHA_SITE = {
    'extensions': [
        {
            'module': 'dasha.web.extensions.dasha',
            'config': {
                'DEBUG': True,
                'THEME': dbc.themes.SKETCHY,
                'template': DBCSidebar,
                'title_text': 'Sidebar Example',
                'pages': [
                    {
                        'template': SimplePage,
                        'title_text': 'Page 1',
                        'route_name': 'page1',
                        },
                    {
                        'template': SimplePage,
                        'title_text': 'Page 2',
                        'route_name': 'page2',
                        },
                    {
                        'template': SimplePage,
                        'title_text': 'Page 3',
                        'route_name': 'page3',
                        },
                    {
                        'title_text': 'Nested 1',
                        'pages': [
                            {
                                'template': SimplePage,
                                'title_text': 'Page 4',
                                'route_name': 'page4',
                                },
                            {
                                'template': SimplePage,
                                'title_text': 'Page 5',
                                'route_name': 'page5',
                                },
                            {
                                'title_text': 'Nested Nested',
                                'pages': [
                                    {
                                        'template': SimplePage,
                                        'title_text': 'Page 6',
                                        'route_name': 'page6',
                                        },
                                    {
                                        'template': SimplePage,
                                        'title_text': 'Page 7',
                                        'route_name': 'page7',
                                        },

                                    ]
                                }

                            ]
                        }
                    ]
                }
            },
        ]
    }
