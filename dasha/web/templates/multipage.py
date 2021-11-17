#!/usr/bin/env python

from anytree import AnyNode, RenderTree
from tollan.utils import ensure_prefix
from tollan.utils.log import get_logger

import dash
from dash import html, Output, Input, State, ClientsideFunction, MATCH
import dash_bootstrap_components as dbc
from dash_component_template import ComponentTemplate

from ..extensions.dasha import resolve_url
from . import resolve_template
from .utils import fa


__all__ = ['Page', 'PageTree']


class Page(ComponentTemplate):
    """A wrapper template to serve page in an multiple component template.
    """

    class Meta:
        component_cls = html.Div

    _icon_style = {
        'padding': '0.5rem 1rem',
        'width': '50px',
        'text-align': 'center'
        }

    def __repr__(self):
        return f'{self.__class__.__name__}({self.title_text})'

    def __init__(
            self,
            template,
            route_name=None,
            title_text=None, title_icon=None,
            **kwargs):
        super().__init__(**kwargs)
        self._template = template
        if route_name is None:
            route_name = getattr(self._template, 'route_name', None)
        if route_name is None:
            route_name = self._template.idbase
        self._route_name = ensure_prefix(route_name, '/')
        if title_text is None:
            title_text = getattr(self._template, 'title_text', None)
        if title_text is None:
            title_text = self._route_name
        self.title_text = title_text
        if title_icon is None:
            title_icon = getattr(self._template, 'title_icon', None)
        if title_icon is None:
            title_icon = 'fas fa-ellipsis-v'
        self.title_icon = title_icon

    @property
    def route_name(self):
        return resolve_url(self._route_name)

    def make_navlink(self, navlist):
        """This is the used as the navlist child"""
        title = [fa(self.title_icon, style=self._icon_style), self.title_text]
        return navlist.child(
                dbc.NavLink,
                children=title,
                active=False,
                href=self.route_name,
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
            layout = self._template.layout
            return layout
        except Exception as e:
            logger.error(
                    f"unable to load page {self._route_name}",
                    exc_info=True)
            reason = str(e)
            return self._get_404_layout(self._route_name, reason)

    @staticmethod
    def _get_404_layout(route, reason):
        return html.Div([
                        html.H1(
                            "404: Not found",
                            className="text-danger"),
                        html.P(
                            f"Failed to load {route}. "
                            f"Reason: {reason}."
                            ),
                        ], className='jumbotron bg-light')


class PageTree(object):
    """A class to manage a set of pages in a tree structure.

    Parameters
    ----------
    pages : dict
        A nested dict that defines a tree of pages. The dict of a non-leaf
        node shall have keys ``title_text`` and ``pages`` while leaf node
        shall have key ``template``.
    """

    logger = get_logger()

    @staticmethod
    def _is_leaf(d):
        return 'template' in d and 'pages' not in d

    def __init__(self, pages):
        if self._is_leaf(pages):
            raise ValueError("input dict shall have a ``pages`` key.")

        # this page index hold the route names of pages as key
        # this also ensures no duplicated route name are in the pages
        page_index = dict()

        def _make_tree(d, parent):
            if self._is_leaf(d):
                p = Page(template=resolve_template(d))
                n = AnyNode(page=p, parent=parent)
                # use the unresolved route_name so we don't need the
                # app context
                route_name = p._route_name
                if route_name in page_index:
                    raise ValueError(
                        f'duplicated route name {route_name} found in pages.')
                page_index[route_name] = n
            else:
                parent = AnyNode(page=d['title_text'], parent=parent)
                for dd in d['pages']:
                    _make_tree(dd, parent=parent)

        root = AnyNode(page=pages['title_text'], parent=None)
        for d in pages['pages']:
            _make_tree(d, root)
        self.logger.info('page tree:\n{}'.format(RenderTree(root)))
        self._root = root
        self._page_index = page_index

    def setup_page_layouts(self, app, location, content_container):
        """Setup multi-page layout and the location callback for rendering.
        """
        for node in self._page_index.values():
            node.page.setup_layout(app)

        @app.callback(
            output=Output(content_container.id, 'children'),
            inputs=[
                Input(location.id, "pathname")
                ]
            )
        def render_page_content(pathname):
            if pathname is None:
                # the first Location.pathname callback shall be ignored
                return dash.no_update
            return self.get_page_layout(route_name=pathname)

    def get_page_layout(self, route_name):
        route_name = route_name.rstrip('/')
        if route_name not in self._page_index:
            if route_name == resolve_url('').rstrip('/'):
                # route to the default page
                route_name = next(iter(self._page_index.keys()))
        if route_name in self._page_index:
            return self._page_index[route_name].page.layout
        return Page._get_404_layout(
            route_name, f'Page {route_name} does not exist')

    def setup_nav_tree(
            self, app, container, make_navlist, make_sub_container,
            location, clientside_state):
        """Setup a tree of nav lists for the page tree."""
        # we use patten matching ids for all created navlist, which have
        _container_id = container.id

        def _iter_index():
            h = 0
            while True:
                yield h
                h += 1
        iter_index = _iter_index()

        def _make_id(type, match_index=False):
            return {
                'container_id': _container_id,
                'type': type,
                'index': MATCH if match_index else next(iter_index)}

        navlist = make_navlist(container=container, id=_make_id('navlist'))

        def _make_navlink_for_node(node, navlist):
            for node in node.children:
                if node.is_leaf:
                    page = node.page
                    page.make_navlink(navlist)
                else:
                    # create a subsection and navlist
                    sub_container = make_sub_container(
                        navlist,
                        title_text=node.page,
                        id=_make_id('sub_container'))
                    sub_navlist = make_navlist(
                        container=sub_container,
                        id=_make_id('navlist'))
                    _make_navlink_for_node(node, sub_navlist)
        _make_navlink_for_node(self._root, navlist)

        # make pattern matching ids
        navlist_id = _make_id('navlist', match_index=True)

        # update clientside_state for default navlink
        clientside_state.data['navlink_default'] = next(
            iter(self._page_index.keys()))

        # setup navlist callback
        app.clientside_callback(
                ClientsideFunction(
                    namespace='ui',
                    function_name='activateNavlink',
                    ),
                output=Output(navlist_id, 'children'),
                inputs=[
                    Input(location.id, 'pathname'),
                    State(navlist_id, 'children'),
                    State(clientside_state.id, 'data')
                    ],
                )
