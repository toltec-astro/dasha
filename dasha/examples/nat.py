#! /usr/bin/env python


"""
This file defines an example site that plays around with different Dash
components.
"""

from dash_component_template import ComponentTemplate
from dash import html, dcc, Output, Input
import dash_bootstrap_components as dbc
from dasha.web.templates.jumbotron import Jumbotron


class Nat(ComponentTemplate):

    class Meta:
        component_cls = dbc.Container

    def __init__(self, title_text, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title_text = title_text
        self.fluid = True

    def setup_layout(self, app):
        title = self.title_text
        self.child(dbc.Row).child(dbc.Col).child(
            Jumbotron(
                title_text=f'{title}',
                body_text='This page is a test',
                ))
        body = self.child(dbc.Row).child(
            dbc.Col, style={'margin-left': '2.5rem'})

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

        super().setup_layout(app)

        @app.callback(
                Output(ticker.id, 'children'),
                [
                    Input(timer.id, 'n_intervals'),
                    Input(factor.id, 'value')
                    ]
                )
        def update(n_intervals, value):
            return str((n_intervals or 0) * value) + ' s'


DASHA_SITE = {
    'extensions': [
        {
            'module': 'dasha.web.extensions.dasha',
            'config': {
                'template': Nat,
                'title_text': "Nat's Test",
                }
            },
        ]
    }
