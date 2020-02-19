#! /usr/bin/env python
from . import ComponentTemplate
import dash_html_components as html
import dash_bootstrap_components as dbc


class ViewGrid(ComponentTemplate):
    """This is a simple wrapper around multiple views."""

    _component_cls = html.Div

    def setup_layout(self, app):
        row = self.child(dbc.Row)
        for view in self.views:
            view = self.from_spec(view)
            if view._component_cls is dbc.Col:
                row.child(view)
            else:
                row.child(dbc.Col, lg=6).child(view)
        super().setup_layout(app)

    @property
    def layout(self):
        return super().layout