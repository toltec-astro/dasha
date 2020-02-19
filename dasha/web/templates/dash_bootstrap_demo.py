#! /usr/bin/env python

"""This is a minimal template."""

from . import ComponentTemplate
import dash_html_components as html
import dash_bootstrap_components as dbc


class DashBootstrapDemo(ComponentTemplate):

    _component_cls = dbc.Container

    def setup_layout(self, app):
        title = self.title_text

        header = self.child(dbc.Row).child(dbc.Col).child(dbc.Jumbotron)
        body = self.child(dbc.Row).child(dbc.Col)
        footer = self.child(dbc.Row).child(dbc.Col)

        header.children = [
                html.H1(f'Hello, {title}!'),
                html.P('This is a simple description.')
                ]
        footer.children = [
                html.Hr(),
                html.P('This is a simple footer.')
                ]

        for i in range(5):
            row = body.child(dbc.Row)
            row.children = tuple(
                    dbc.Col(dbc.Alert(f"Cell {i}, {j}")) for j in range(5))
