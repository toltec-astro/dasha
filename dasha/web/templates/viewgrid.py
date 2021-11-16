#! /usr/bin/env python

import dash_bootstrap_components as dbc
from dash_component_template import ComponentTemplate
from . import resolve_template


class ViewGrid(ComponentTemplate):
    """This is a simple wrapper around multiple views."""

    class Meta:
        component_cls = dbc.Container

    def __init__(self, views, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.views = views

    def setup_layout(self, app):
        row = self.child(dbc.Row)
        for view in self.views:
            # has to use the class level from_dict because we
            # need to construct arbitrary templates
            view = resolve_template(view)
            if view.component_info.type is dbc.Col:
                row.child(view)
            else:
                row.child(dbc.Col, lg=6).child(view)
        super().setup_layout(app)
