#! /usr/bin/env python

from . import ComponentTemplate
from .utils import to_dependency
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import ClientsideFunction, Output, Input, State


class SyncedList(ComponentTemplate):

    _component_cls = html.Div

    def __init__(
            self, primary_key, output,
            *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pk = primary_key
        self._output = output
        self._input = Input(output.component_id, output.component_property)

    def setup_layout(self, app):
        self.meta = self.child(dcc.Store, data={
            'pk': self._pk,
            'size': None,
            'pk_latest': None,
            })
        self.datastore = self.child(dcc.Store)
        super().setup_layout(app)

        cb_namespace = 'syncedlist'

        # this callback is to collect information of the current
        # client side data store.
        app.clientside_callback(
                ClientsideFunction(
                    namespace=cb_namespace,
                    function_name='updateMeta'
                ),
                Output(self.meta.id, 'data'),
                [to_dependency('input', self._output)],
                [State(self.meta.id, 'data')],
            )

        # this callback is to put the entry in data into the output data.
        # the update will be done with pk
        app.clientside_callback(
                ClientsideFunction(
                    namespace=cb_namespace,
                    function_name='update',
                ),
                self._output,
                [
                    Input(self.datastore.id, 'data'),
                    ],
                [
                    to_dependency('state', self._output),
                    State(self.meta.id, 'data')
                    ]
            )

    @property
    def layout(self):
        return super().layout
