#! /usr/bin/env python


"""This is a template that mimics slapdash style."""

from . import ComponentTemplate
import dash_html_components as html
import dash_bootstrap_components as dbc


class SlapDash(ComponentTemplate):

    _component_cls = dbc.Container

    @property
    def layout(self):
        title = self.TITLE

        header = self.child(dbc.Row)
        body = self.child(dbc.Row)
        footer = self.child(dbc.Row)

        header.child(html.H1, f'Hello, {title}!')
        footer.child(html.H2, f'some text goes here')

        body.children = tuple(html.H3(i) for i in range(100))

        return super().layout
