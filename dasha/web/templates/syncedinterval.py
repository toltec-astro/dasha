#! /usr/bin/env python


import dash_html_components as html
import dash_core_components as dcc
from . import ComponentTemplate


class SyncedInterval(ComponentTemplate):

    _component_cls = html.Div

    def setup_layout(self, app):

        self._timer = self.child(dcc.Interval, interval=self.resolution)

        super().setup_layout()

    def register_callback(interval, outputs, inputs, states, callback):
        """This will set up the exec of the :"""
        pass

    @property
    def layout(self):
        return super().layout
