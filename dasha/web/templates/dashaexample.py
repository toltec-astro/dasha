#!/usr/bin/env python

from . import ComponentTemplate
import dash_html_components as html


class DashaExample(ComponentTemplate):
    _component_cls = html.Div

    @property
    def layout(self):
        return html.H1("Example")
