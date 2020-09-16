#! /usr/bin/env python
from . import ComponentTemplate
import dash_html_components as html
import dash_bootstrap_components as dbc
from schema import Schema


class ViewGrid(ComponentTemplate):
    """This is a simple wrapper around multiple views."""

    _component_cls = html.Div
    _component_schema = Schema({
            'views': [dict, ]
            })

    def setup_layout(self, app):
        row = self.child(dbc.Row)
        for view in self.views:
            # has to use the class level from_dict because we
            # need to construct arbitrary templates
            view = ComponentTemplate.from_dict(view)
            if view._component_cls is dbc.Col:
                row.child(view)
            else:
                row.child(dbc.Col, lg=6).child(view)
        super().setup_layout(app)
