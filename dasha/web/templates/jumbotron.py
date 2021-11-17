#!/usr/bin/env python


from dash_component_template import ComponentTemplate
from dash import html
import dash_bootstrap_components as dbc


class Jumbotron(ComponentTemplate):

    class Meta:
        component_cls = html.Div

    def __init__(self,
                 *args,
                 title_text=None,
                 subtitle_text=None,
                 body_text=None,
                 button_text=None,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.title_text = title_text
        self.subtitle_text = subtitle_text
        self.body_text = body_text
        self.button_text = button_text
        self.className = 'jumbotron bg-light'

    def setup_layout(self, app):
        container = self
        if self.title_text is not None:
            container.child(html.H1(self.title_text, className='display-3'))
        if self.subtitle_text is not None:
            container.child(html.P(self.subtitle_text, className='lead'))
        if self.body_text is not None or self.button_text is not None:
            container.child(html.Hr(className='my-2'))
        if self.body_text is not None:
            container.child(html.P(self.body_text))
        if self.button_text is not None:
            button = container.child(html.P, className='lead').child(
                dbc.Button, self.button_text, color='primary')
        else:
            button = None
        self.button = button

        super().setup_layout(app)
