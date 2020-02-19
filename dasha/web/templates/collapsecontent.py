#! /usr/bin/env python

from dasha.web.templates import ComponentTemplate
from dash.dependencies import Output, Input, State, ClientsideFunction
import dash_html_components as html
import dash_bootstrap_components as dbc


class CollapseContent(ComponentTemplate):
    _component_cls = html.Div

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._button = self.child(
                dbc.Button, self.button_text,
                className='mr-2 my-0 px-0 btn btn-link'
                )
        self.content = self.child(dbc.Collapse)

    def setup_layout(self, app):

        super().setup_layout(app)

        app.clientside_callback(
                ClientsideFunction(
                    namespace='ui',
                    function_name='toggleWithClick',
                    ),
                Output(self.content.id, 'is_open'),
                [Input(self._button.id, "n_clicks")],
                [State(self.content.id, 'is_open')],
                )

    @property
    def layout(self):
        return super().layout