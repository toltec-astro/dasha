#! /usr/bin/env python


from dasha.web.templates import ComponentTemplate
import dash_html_components as html
import dash_core_components as dcc
from dasha.web.templates.timer import IntervalTimer
from schema import Schema
from copy import copy


class LiveUpdateSection(ComponentTemplate):
    _component_cls = html.Div
    _component_schema = Schema({
        'title_component': object,
        'interval_options': [int],
        'interval_option_value': int,
        })

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        container, banner_container = self.grid(2, 1)
        container.className = 'd-flex align-items-bottom'
        title = copy(self.title_component)
        title.className = 'mr-2 my-0'
        container.child(title)
        self._timer = container.child(
                IntervalTimer(
                    interval_options=self.interval_options,
                    interval_option_value=self.interval_option_value,
                    ))
        self._loading = container.child(
                dcc.Loading,
                parent_className='ml-4')
        banner_container.className = 'd-flex'
        self._banner = banner_container

    def setup_layout(self, app):
        super().setup_layout(app)

    @property
    def timer(self):
        return self._timer

    @property
    def loading(self):
        return self._loading

    @property
    def banner(self):
        return self._banner
