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
from dash.dependencies import Input, State, Output, ClientsideFunction
from schema import Schema, Optional


__all__ = ['SlapDash', ]


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
                href=self._route_name)

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
            return dbc.Jumbotron([
                    html.H1(
                        "404: Not found",
                        className="text-danger"),
                    html.Hr(),
                    html.P(
                        f"Failed load {self._route_name}, "
                        f"reason: {reason}."
                        ),
                ])


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
                className='navbar-dark bg-dark d-flex flex-column',
                id='sidebar')
        header = sidebar.child(dbc.Row)
        self._make_title(
                header.child(dbc.Col).child(
                    html.Header, className="brand").child(
                        dcc.Link, href=resolve_url("/"),
                        ), html.H3)
        toggles = header.child(dbc.Col, width='auto', align='center')
        self.navbar_toggle = toggles.child(
                html.Button,
                children=html.Span(className="navbar-toggler-icon"),
                className="navbar-toggler",
                style={
                    "color": "rgba(0,0,0,.5)",
                    "border-color": "rgba(0,0,0,.1)",
                    'outline': 'none',
                },
                id='navbar-toggle',
            )
        self.sidebar_toggle = toggles.child(
                html.Button,
                children=html.Span(className="navbar-toggler-icon"),
                className="navbar-toggler",
                # the navbar-toggler classes don't set color
                style={
                    "color": "rgba(0,0,0,.5)",
                    "border-color": "rgba(0,0,0,.1)",
                    'outline': 'none',
                },
                id='sidebar-toggle',
            )

        self.sidebar_collapse = sidebar.child(
                dbc.Collapse, id='nav-collapse', className='flex-grow-1')
        self.navlist = self.sidebar_collapse.child(
                dbc.Nav, vertical=True, pills=True)
        for page in self._pages:
            page['_view'] = self._make_page(page)
            page['_view']._make_navlink(self.navlist)
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
        logger.debug(
                f"get layout for {route_name} from "
                f"{self._page_registry.keys()}")
        return self._page_registry[route_name].layout

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
            page['_view'].setup_layout(app)

    @property
    def layout(self):
        return super().layout


# this set the default template cls returned by the module resolver
_resolve_template_cls = SlapDash
