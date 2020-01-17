#! /usr/bin/env python


"""This is a template that mimics slapdash style."""

from . import Template
import dash_html_components as html


class SlapDash(Template):

    _make_availabel_factories = [
            html.Div,
            html.P,
            ]

    def __init__(self, config, parent=None):
        super().__init__(parent=parent)
        self._config = config

    @property
    def layout(self):
        title = self._config['TITLE']

        container = self.make_component(html.Div)

        header = container.make_component(html.H1, f'Hello, {title}!')
        body = container.make_component(html.H2, f'some text goes here')

        container.children = [header, body]
        container.children.extend([html.H3(i) for i in range(100)])
        return container.layout

    @classmethod
    def from_dict(cls, config):
        return cls(config)
