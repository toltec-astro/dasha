#!/usr/bin/env python

from dash_component_template import ComponentTemplate
# import dash
from dash import html, dcc, Output, Input, State, ClientsideFunction, MATCH
import dash_bootstrap_components as dbc
from tollan.utils.log import get_logger
from ..extensions.dasha import resolve_url
from .multipage import PageTree
from .utils import update_class_name, PatternMatchingId, fa


__all__ = ['SlapDash', ]


# consumed by resolve_template
_resolve_template = 'SlapDash'


class SlapDash(ComponentTemplate):

    class Meta:
        component_cls = dbc.Container

    logger = get_logger()
    # style = {
    #         'min-width': 320,
    #         }

    def __init__(
            self, title_text, pages, *args,
            title_icon='far fa-chart-bar', **kwargs):
        kwargs.setdefault('fluid', True)
        kwargs['className'] = update_class_name(
            kwargs.get('className', None),
            'slapdash-root')
        super().__init__(*args, **kwargs)
        self.title_text = title_text
        self.title_icon = title_icon
        self.page_tree = PageTree({'pages': pages, 'title_text': title_text})

    def _make_footer(self, container):
        # footer = container.child(html.Footer, className='sticky-footer')
        # for elem in ['play', ]:
        #     container.child(html.Span(elem))
        # container.child(SysInfo())
        # container.child(html.Div, "This is a footer")
        pass

    def _setup_sidebar(self, app, container, location, clientside_state):
        sidebar = container.child(
            html.Div,
            className=(
                'slapdash-sidebar slapdash-sidebar-section '
                'navbar navbar-dark bg-dark py-4'),
            )
        header_row = sidebar.child(
            dbc.Row, align='center', justify='between',
            className='flex-nowrap')
        # make title
        header_row.child(dbc.Col, width='auto').child(
            dcc.Link, href=resolve_url("/"),
            children=[
                fa(self.title_icon, className='pe-2 py-2'),
                self.title_text
                ],
            className='navbar-brand mx-0', style={'font-size': '1.75rem'})
        # toggles for sidebar and navbar
        toggles = header_row.child(dbc.Col, width='auto')
        navbar_toggle = toggles.child(  # noqa: F841
                html.Button,
                children=html.Span(className="navbar-toggler-icon"),
                className="navbar-toggler slapdash-navbar-toggler",
                )
        sidebar_toggle = toggles.child(  # noqa: F841
                html.Button,
                children=html.Span(className="navbar-toggler-icon"),
                className="navbar-toggler slapdash-sidebar-toggler",
                )

        app.clientside_callback(
                ClientsideFunction(
                    namespace='ui',
                    function_name='collapseWithClick',
                    ),
                output=Output(sidebar.id, 'className'),
                inputs=[
                    Input(sidebar_toggle.id, "n_clicks"),
                    State(sidebar.id, 'className'),
                    ],
                )

        nav_collapse = sidebar.child(
            dbc.Row,
            className='mt-4 overflow-auto slapdash-sidebar-scrollable').child(
            dbc.Col, className='px-0').child(
                dbc.Collapse,
                className=(
                    'slapdash-nav-collapse navbar-collapse'),
                )

        app.clientside_callback(
                ClientsideFunction(
                    namespace='ui',
                    function_name='toggleWithClick',
                    ),
                output=Output(nav_collapse.id, 'is_open'),
                inputs=[
                    Input(navbar_toggle.id, "n_clicks"),
                    State(nav_collapse.id, 'is_open'),
                    ],
                )

        # create the navlist
        # this makers are passed to the page tree nav tree maker which provides
        # the pattern matching id and pattern matching callback
        def make_navlist(container, id):
            return container.child(
                dbc.Nav, id=id, vertical=True, pills=True,
                className='navbar-nav px-2')

        # make a pmid for callbacks
        pmid = PatternMatchingId(container_id=self.id, type='')

        def make_sub_container(container, title_text, id):
            section = container.child(
                html.Div,
                id=id,
                className=(
                    'slapdash-sidebar-section navbar navbar-dark bg-dark py-0'
                    ),
                )
            # we use this index to match the callbacks
            index = pmid.make_id()
            section_header = section.child(dbc.Row).child(
                dbc.Col,
                className=(
                    'slapdash-sidebar-section-header d-grid '
                    )
                ).child(
                    dbc.Button,
                    id=pmid(type='section-toggle', index=index),
                    className=(
                        'navbar-brand '
                        'text-start px-2 py-1 mx-0 shadow-none'),
                    size='sm',
                    color='dark',
                    style={'font-size': '1.25rem'}
                    )
            section_header.children = [
                    title_text,
                    html.I(
                        className='fas fa-angle-right ps-2',
                        id=pmid(type='section-toggle-icon', index=index)
                        )]
            section_collapse = section.child(dbc.Row).child(dbc.Col).child(
                    dbc.Collapse,
                    id=pmid(type='section-collapse', index=index),
                    className='flex-grow-1 slapdash-sidebar-scrollable',
                    style={'overflow': 'auto'}
                    )
            return section_collapse

        self.page_tree.setup_nav_tree(
            app,
            container=nav_collapse,
            make_navlist=make_navlist,
            make_sub_container=make_sub_container,
            location=location,
            clientside_state=clientside_state
            )

        # sub section toggle
        app.clientside_callback(
                ClientsideFunction(
                    namespace='ui',
                    function_name='toggleCollapseWithButtonChevron',
                    ),
                output=[
                    Output(
                        pmid(type='section-collapse', index=MATCH), 'is_open'),
                    Output(
                        pmid(type='section-toggle-icon', index=MATCH),
                        'className'),
                    ],
                inputs=[
                    Input(
                        pmid(type='section-toggle', index=MATCH),
                        'n_clicks'),
                    State(
                        pmid(type='section-collapse', index=MATCH),
                        'is_open'),
                    ],
                prevent_initial_call=True,
                )
        # footer = sidebar.child(
        #         dbc.Container, fluid=True,
        #         className='text-light')
        # footer.child(html.Hr(className='bg-light'))
        # self._make_footer(footer)

    def setup_layout(self, app):
        container = self
        location = container.child(dcc.Location, refresh=False)
        clientside_state = container.child(dcc.Store, data=dict())

        self._setup_sidebar(app, container, location, clientside_state)

        content_container = container.child(
            html.Div, className='slapdash-content')
        self.page_tree.setup_page_layouts(app, location, content_container)
        super().setup_layout(app)
