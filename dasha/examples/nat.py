#! /usr/bin/env python


"""
This file defines an example site that plays around with different Dash
components.
"""

from dasha.web.templates import ComponentTemplate
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_core_components as dcc
from dash.dependencies import Output, Input


class nat(ComponentTemplate):

    _component_cls = dbc.Container
    fluid = True

    def setup_layout(self, app):
        title = self.title_text
        header = self.child(dbc.Row).child(dbc.Col).child(dbc.Jumbotron)
        body = self.child(dbc.Row).child(dbc.Col)

        header.children = [
                html.H1(f'{title}'),
                html.P(
                    'This page is a test'
                    )
                ]

        timer = body.child(dcc.Interval, interval=1000)
        ticker_container = body.child(html.Div, className='d-flex')
        ticker_container.child(
                dbc.Label("n_intervals:", className='mr-2'))
        ticker = ticker_container.child(html.Div, 'N/A')

        factor = body.child(
                dcc.Input,
                placeholder="Enter a factor: ",
                type='number',
                value=1)

        @app.callback(
                Output(ticker.id, 'children'),
                [
                    Input(timer.id, 'n_intervals'),
                    Input(factor.id, 'value')
                    ]
                )
        def update(n_intervals, value):
            return str(n_intervals * value) + ' s'


extensions = [
    {
        'module': 'dasha.web.extensions.dasha',
        'config': {
            'template': nat,
            'title_text': 'Nat Test',
            }
        },
    ]
