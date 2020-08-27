#! /usr/bin/env python


"""This is a template that mimics slapdash style."""

from . import ComponentTemplate, Template
import dash_html_components as html
import dash_core_components as dcc
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from tollan.utils import ensure_prefix
from tollan.utils.log import get_logger
from tollan.utils.registry import Registry
from .utils import fa
from ..extensions.dasha import resolve_url
from .sysinfo import SysInfo
from dash.dependencies import (
        Input, State, Output, ClientsideFunction, MATCH)
from schema import Schema, Optional
# from .utils import parse_triggered_prop_ids
import dash


__all__ = ['SlapDash', ]


def _get_404_layout(route, reason):
    return dbc.Jumbotron([
                    html.H1(
                        "404: Not found",
                        className="text-danger"),
                    html.Hr(),
                    html.P(
                        f"Failed load {route}, "
                        f"reason: {reason}."
                        ),
                ])


class _SlapDashPageWrapper(ComponentTemplate):
    """This is a wrapper around any actual page template."""

    _component_cls = html.Div
    # this is only used for validate pages in SlapDash
    # this class should not be created using from_dict
    _component_schema = Schema({
        Optional('route_name'): str,
        Optional('title_text'): str,
        Optional('title_icon'): str,
        })

    @classmethod
    def from_dict():
        return NotImplemented

    def __init__(self, template, **kwargs):
        self._component_cls = template._component_cls
        self._template = template

    @property
    def _route_name(self):
        """This is the stem of the page url."""
        return resolve_url(ensure_prefix(getattr(
                self._template, 'route_name',
                self._template.idbase), '/'))

    @property
    def _title_text(self):
        return getattr(self._template, 'title_text', self._route_name)

    @property
    def _title_icon(self):
        return getattr(self._template, 'title_icon', 'fas fa-ellipsis-v')

    def _make_navlink(self, container):
        """This is the used as the navlist child"""
        title = [fa(self._title_icon), self._title_text]
        return container.child(
                dbc.NavLink,
                children=title,
                active=False,
                href=self._route_name,
                className='pr-2',
                style={
                  'white-space': 'nowrap',
                  'overflow': 'hidden',
                  'text-overflow': 'ellipsis'
                    }
                )

    def setup_layout(self, app):
        self._template.setup_layout(app)

    @property
    def layout(self):
        logger = get_logger()
        try:
            return self._template.layout
        except Exception as e:
            logger.error(
                    f"unable to load page {self._route_name}",
                    exc_info=True)
            reason = str(e)
            return _get_404_layout(self._route_name, reason)


class SlapDash(ComponentTemplate):

    _component_cls = dbc.Container
    _component_schema = Schema({
        'title_text': str,
        Optional('title_icon', default='far fa-chart-bar'): str,
        'pages': [_SlapDashPageWrapper._namespace_from_dict_schema, ]
        })
    fluid = True
    className = 'px-0'
    id = 'slapdash'
    style = {
            'min-width': 320,
            }

    def __init__(self, pages, **kwargs):
        super().__init__(**kwargs)
        self._pages = pages
        self._page_registry = Registry.create()

    def _make_title(self, container, component_cls, **kwargs):
        return container.child(component_cls, children=[
                fa(self.title_icon, style={
                    'padding': '0.5rem 0rem'
                    }),
                self.title_text
            ], **kwargs)

    def _make_footer(self, container):
        # footer = container.child(html.Footer, className='sticky-footer')
        # for elem in ['play', ]:
        #     container.child(html.Span(elem))
        container.child(SysInfo())

    def _make_page(self, d):
        page = _SlapDashPageWrapper(template=Template.from_dict(d))
        self._page_registry.register(page._route_name, page)
        return page

    def _make_sidebar(self, container):
        sidebar = container.child(
                html.Div,
                className=(
                    'navbar-dark bg-dark d-flex flex-column'),
                id='sidebar')
        header_row = sidebar.child(dbc.Row)
        self._make_title(
                header_row.child(dbc.Col).child(
                    html.Header, className="brand").child(
                        dcc.Link, href=resolve_url("/"),
                        ), html.H3)
        toggles = header_row.child(dbc.Col, width='auto', align='center')
        navbar_toggle = toggles.child(  # noqa: F841
                html.Button,
                children=html.Span(className="navbar-toggler-icon"),
                className="navbar-toggler",
                style={
                    "color": "rgba(0,0,0,.5)",
                    "border-color": "rgba(0,0,0,.1)",
                    'outline': 'none',
                    # 'background-color': 'blue',
                    },
                id='navbar-toggle',
                )
        sidebar_toggle = toggles.child(  # noqa: F841
                html.Button,
                children=html.Span(className="navbar-toggler-icon"),
                className="navbar-toggler",
                # the navbar-toggler classes don't set color
                style={
                    "color": "rgba(0,0,0,.5)",
                    "border-color": "rgba(0,0,0,.1)",
                    'outline': 'none',
                    # 'background-color': 'blue',
                    },
                id='sidebar-toggle',
            )

        sidebar_collapse = sidebar.child(
                dbc.Collapse, id='nav-collapse',
                className='flex-grow-1 sidebar-scrollable',
                style={
                    'overflow': 'auto',
                    })

        self.navlist = sidebar_collapse.child(
                dbc.Nav, vertical=True, pills=True, className='mt-1')

        submenu_id = 0

        for page in self._pages:
            # this is a top level page
            if 'template' in page.keys():
                page['_view'] = self._make_page(page)
                page['_view']._make_navlink(self.navlist)
            else:
                for key in page.keys():
                    section = self.navlist.child(
                        html.Div,
                        className='navbar-dark d-flex flex-column',
                        style={
                            'background-color': '#444a50',
                            'outline': 'none',
                            }
                        )
                    section_header = section.child(dbc.Row).child(
                            dbc.Col,
                            className='sidebar-section-header').child(
                                dbc.Button,
                                id={
                                    'type': 'section-toggle',
                                    'index': submenu_id
                                    },
                                className=(
                                    'btn-block text-left px-0 bg-dark'),
                                size='sm',
                                ).child(
                                        html.H5,
                                        className='pt-2 pl-3')
                    section_header.children = [
                            key,
                            html.I(
                                className='fas fa-angle-right pl-2',
                                id={
                                    'type': 'section-toggle-icon',
                                    'index': submenu_id
                                    }
                                )]
                    section_collapse = section.child(
                            dbc.Collapse,
                            id={
                                'type': 'section-collapse',
                                'index': submenu_id
                                },
                            className='flex-grow-1 sidebar-scrollable',
                            style={'overflow': 'auto'}
                            )
                    section_navlist = section_collapse.child(
                            dbc.Nav,
                            id={
                                'type': 'section-navlist',
                                'index': submenu_id
                                },
                            className='my-0',
                            vertical=True,
                            pills=True)
                    submenu_id += 1

                for subpages in page.values():
                    for subpage in subpages:
                        subpage['_view'] = self._make_page(subpage)
                        subpage['_view']._make_navlink(section_navlist)

        self.clientside_state.data['navlink_default'] = \
            self._pages[0]['_view']._route_name
        self.location = self.child(dcc.Location, refresh=False)

        footer = sidebar.child(
                dbc.Container, fluid=True,
                className='text-light')
        footer.child(html.Hr(className='bg-light'))
        self._make_footer(footer)

    def _get_content_layout(self, pathname):
        logger = get_logger()
        route_name = pathname
        if route_name not in self._page_registry:
            if route_name.rstrip('/') == resolve_url('').rstrip('/'):
                route_name = next(iter(self._page_registry))
                logger.debug(f"use default page {route_name}")
        if route_name in self._page_registry:
            logger.debug(
                    f"get layout for {route_name} from "
                    f"{self._page_registry.keys()}")
            return self._page_registry[route_name].layout
        return _get_404_layout(route_name, 'Invalid route')

    def setup_layout(self, app):
        self.clientside_state = self.child(dcc.Store, data=dict())
        self._make_sidebar(self)
        content_container = self.child(html.Div, id='page-content')

        # sidebar callbacks
        app.clientside_callback(
                ClientsideFunction(
                    namespace='ui',
                    function_name='activateNavlink',
                    ),
                Output(self.navlist.id, 'children'),
                [Input(self.location.id, 'pathname')],
                [State(self.navlist.id, 'children'),
                 State(self.clientside_state.id, 'data'),
                 ]
                )

        # sidebar callbacks
        app.clientside_callback(
                ClientsideFunction(
                    namespace='ui',
                    function_name='activateNavlink',
                    ),
                Output(
                    {'type': 'section-navlist', 'index': MATCH}, 'children'),
                [Input(self.location.id, 'pathname')],
                [State(
                    {'type': 'section-navlist', 'index': MATCH}, 'children'),
                 State(self.clientside_state.id, 'data'),
                 ]
                )

        app.clientside_callback(
                ClientsideFunction(
                    namespace='ui',
                    function_name='collapseWithClick',
                    ),
                Output("sidebar", 'className'),
                [Input("sidebar-toggle", "n_clicks")],
                [State("sidebar", 'className')],
                )
        app.clientside_callback(
                ClientsideFunction(
                    namespace='ui',
                    function_name='toggleWithClick',
                    ),
                Output("nav-collapse", 'is_open'),
                [Input("navbar-toggle", "n_clicks")],
                [State("nav-collapse", 'is_open')],
                )

        @app.callback(
            [
                Output(
                    {'type': 'section-collapse', 'index': MATCH}, 'is_open'),
                Output(
                    {'type': 'section-toggle-icon', 'index': MATCH},
                    'className'),
                ],
            [
                Input({'type': 'section-toggle', 'index': MATCH}, 'n_clicks')
                ],
            [
                State({'type': 'section-collapse', 'index': MATCH}, 'is_open')
                ],
            prevent_initial_call=True,
            )
        def toggle_submenu(n_clicks, is_open):
            print(f'toggle_submenu n = {n_clicks} o = {is_open}')
            if n_clicks is None:
                raise dash.exceptions.PreventUpdate
            if is_open is None:
                is_open = True
            else:
                is_open = not is_open
            if is_open:
                class_name = 'fas fa-angle-down pl-2'
            else:
                class_name = 'fas fa-angle-right pl-2'
            return is_open, class_name

        @app.callback(
                Output(content_container.id, "children"),
                [
                    Input(self.location.id, "pathname"),
                    Input(self.location.id, "search"),
                ])
        def render_page_content(pathname, search):
            if pathname is None:
                raise PreventUpdate(
                    "the first Location.pathname callback shall be ignored")
            return self._get_content_layout(pathname.rstrip('/'))

        super().setup_layout(app)

        # setup page layout, as pages are not in the object tree.
        for page in self._pages:
            if 'template' in page.keys():
                page['_view'].setup_layout(app)
            else:
                for subpages in page.values():
                    for subpage in subpages:
                        subpage['_view'].setup_layout(app)

    @property
    def layout(self):
        return super().layout


# this set the default template cls returned by the module resolver
_resolve_template_cls = SlapDash
