#!/usr/bin/env python


from dash_component_template import ComponentTemplate
from dash import html, dcc
import dash_bootstrap_components as dbc
from dasha.web.templates.jumbotron import Jumbotron


class DashIntro(ComponentTemplate):

    class Meta:
        component_cls = dbc.Container

    def __init__(self, title_text, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title_text = title_text

    def setup_layout(self, app):
        title = self.title_text

        self.child(dbc.Row).child(dbc.Col).child(Jumbotron(
            title_text=f'Greetings from {title}!',
            body_text='DashA makes reusable pages.'
            ))
        body = self.child(dbc.Row).child(dbc.Col)
        footer = self.child(dbc.Row).child(dbc.Col)

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
        super().setup_layout(app)


DASHA_SITE = {
    'extensions': [
        {
            'module': 'dasha.web.extensions.dasha',
            'config': {
                'template': DashIntro,
                'title_text': 'DashA Intro',
                }
            }
        ]
    }
