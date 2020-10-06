#! /usr/bin/env python

from dash.dependencies import Output, Input, State, ALL
import dash_html_components as html
import dash_core_components as dcc
import dash_bootstrap_components as dbc
from schema import Schema
import dash

from . import ComponentTemplate
from .utils import parse_triggered_prop_ids
from .collapsecontent import CollapseContent
from .shareddatastore import SharedDataStore

from tollan.utils.fmt import pformat_yaml
from tollan.utils import to_typed


__all__ = ['ButtonListPager', ]


def _get_items_range(
        page_id, n_items_per_page, n_items):
    start = page_id * n_items_per_page
    stop = start + n_items_per_page
    if stop > n_items:
        stop = n_items
    return start, stop


def _get_n_pages(n_items_per_page, n_items):
    n_pages = n_items // n_items_per_page + (
            n_items % n_items_per_page > 0)
    return n_pages


class ButtonListPager(ComponentTemplate):

    _component_cls = html.Div
    _component_schema = Schema({
        'title_text': str,
        'n_items_per_page_options': [object, ]
        })

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        settings_container, btns_container = self.grid(2, 1)
        settings_container.child(dbc.Label(
            self.title_text))
        settings_container_form = settings_container.child(
                dbc.Form, inline=True)

        settings_container_fgrp = settings_container_form.child(
                dbc.FormGroup, className='d-flex')
        # settings_container_fgrp.child(dbc.Label(
        #     self.title_text, className='mr-2'))
        n_items_per_page_select_igrp = settings_container_fgrp.child(
                    dbc.InputGroup, size='sm', className='w-auto mr-2')
        n_items_per_page_drp = n_items_per_page_select_igrp.child(
                dbc.Select,
                options=[
                    {
                        'label': v,
                        'value': v
                        }
                    for i, v in enumerate(
                        self.n_items_per_page_options)
                    ],
                value=self.n_items_per_page_options[0],
                )
        n_items_per_page_select_igrp.child(
                dbc.InputGroupAddon(
                    "items per page", addon_type="append"))
        self._ctx = {
                'n_items_per_page_drp': n_items_per_page_drp,
                'settings_container': settings_container,
                'settings_container_form': settings_container_form,
                'btns_container': btns_container
                }
        self._settings = self.child(SharedDataStore())
        self._current_page_store = self.child(dcc.Store, data=None)

    def register_n_items_callback(self, inputs, callback):
        self._settings.register_callback(
                outputs='n_items',
                inputs=inputs,
                callback=callback
                )

    @property
    def page_data_inputs(self):
        return [Input(self._current_page_store.id, 'data'), ]

    def setup_layout(self, app):

        def _get_n_items_per_page(value):
            if isinstance(value, str):
                return to_typed(value)
            return value

        # this had to be done here because id is only accessible
        # after __init__
        self._settings.register_callback(
                outputs='n_items_per_page',
                inputs=Input(
                    self._ctx['n_items_per_page_drp'].id, 'value'),
                callback=_get_n_items_per_page
                )

        btns_container = self._ctx['btns_container']
        settings_container_form = self._ctx['settings_container_form']
        details_container = settings_container_form.child(
                    CollapseContent(button_text='Details ...')).content
        details_container.parent = settings_container_form.parent

        super().setup_layout(app)

        def get_page_btn_id(i):
            return {
                    'parent_id': btns_container.id,
                    'page_id': i
                    }

        def resolve_page_info(d):
            n_items = d['n_items']
            n_items_per_page = d['n_items_per_page']
            if (
                    isinstance(n_items_per_page, str)
                    and n_items_per_page.lower() == 'all'):
                n_items_per_page = n_items
            n_pages = _get_n_pages(n_items_per_page, n_items)
            return {
                    'n_items': n_items,
                    'n_items_per_page': n_items_per_page,
                    'n_pages': n_pages,
                    }

        @app.callback(
                [
                    Output(btns_container.id, 'children'),
                    Output(details_container.id, 'children')
                    ],
                [
                    Input(self._settings.id, 'data')
                    ]
                )
        def update_btns_container(d):
            if d is None:
                return dash.no_update, html.Pre('(empty)')
            d = resolve_page_info(d)
            n_items = d['n_items']
            n_items_per_page = d['n_items_per_page']
            n_pages = d['n_pages']

            def get_page_btn_text(i):
                if n_pages == 1:
                    return 'All items'
                start, _ = _get_items_range(
                        i, n_items_per_page, n_items)
                return f'{start}'

            btns = [
                    dbc.Button(
                        get_page_btn_text(i),
                        id=get_page_btn_id(i),
                        color='link',
                        className='mr-1', size='sm')
                    for i in range(n_pages)
                    ]
            return btns, html.Pre(pformat_yaml(d))

        @app.callback(
                Output(self._current_page_store.id, 'data'),
                [
                    Input(get_page_btn_id(ALL), 'n_clicks')
                    ],
                [
                    State(self._settings.id, 'data')
                    ]
                )
        def update_current_page(n_clicks_values, settings):
            print(f"settings: {settings}")
            if settings is None:
                raise dash.exceptions.PreventUpdate
            d = parse_triggered_prop_ids()[0]
            if d is None:
                page_id = 0
            else:
                page_id = d['id']['page_id']
            settings = resolve_page_info(settings)
            n_items = settings['n_items']
            n_items_per_page = settings['n_items_per_page']
            n_pages = settings['n_pages']

            start, stop = _get_items_range(page_id, n_items_per_page, n_items)
            result = dict(**settings)
            result.update({
                    'page_id': page_id,
                    'start': start,
                    'stop': stop,
                    'n_pages': n_pages
                    })
            return result
