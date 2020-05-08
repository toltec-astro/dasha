#! /usr/bin/env python

from . import ComponentTemplate
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_core_components as dcc
from schema import Schema


class DashIntro(ComponentTemplate):

    _component_cls = dbc.Container

    _component_schema = Schema({
        'title_text': str,
        })

    def setup_layout(self, app):
        title = self.title_text

        header = self.child(dbc.Row).child(dbc.Col).child(dbc.Jumbotron)
        body = self.child(dbc.Row).child(dbc.Col)
        footer = self.child(dbc.Row).child(dbc.Col)

        header.children = [
                html.H1(f'Greetings from {title}!'),
                html.P('DashA makes reusable pages.')
                ]
        footer.children = [
                html.Hr(),
                dcc.Markdown(
                    'https://github.com/toltec-astro/dasha',
                    )
                ]

        for i in range(5):
            row = body.child(dbc.Row)
            row.children = tuple(
                    dbc.Col(dbc.Alert(f"Cell {i}, {j}")) for j in range(5))
