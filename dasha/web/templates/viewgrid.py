#! /usr/bin/env python

from dash_component_template import ComponentTemplate
from dash import html
import dash_bootstrap_components as dbc
from . import resolve_template


# consumed by resolve_template
_resolve_template = 'ViewGrid'


class ViewGrid(ComponentTemplate):
    """This is a simple wrapper around multiple views."""

    class Meta:
        component_cls = html.Div

    def __init__(self, views, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.views = views

    def setup_layout(self, app):
        row = self.child(dbc.Row)
        for view in self.views:
            view = resolve_template(view)
            if view.dash_component_info.type is dbc.Col:
                row.child(view)
            else:
                row.child(dbc.Col, lg=6).child(view)
        super().setup_layout(app)
