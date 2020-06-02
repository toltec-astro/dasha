#! /usr/bin/env python

from . import ComponentTemplate
from .shareddatastore import SharedDataStore
from .valueview import ValueView
import dash_core_components as dcc
import dash_bootstrap_components as dbc
from astropy.utils.console import human_file_size
from tollan.utils import mapsum
from dash.dependencies import Input  # , State, Output, ClientsideFunction
import psutil


class SysInfo(ComponentTemplate):
    """This template displays a set of system information."""
    _info_view_cls = ValueView
    _datastore_cls = SharedDataStore
    _component_cls = dbc.Container
    fluid = True

    def __init__(self, update_interval=1000, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._update_interval = update_interval
        self._psutil_proc = psutil.Process()

        bar_dict = {
                'max': 1.,
                'step': 0.02,
                'size': 100,
                }
        self._sources = [
                {
                    'label': 'CPU',
                    'text': {
                        'func': lambda d: f"{d['cpu_perc']:.0f}%",
                        },
                    'bar': dict({
                        'func': lambda d: d['cpu_perc'] * 0.01,
                        }, **bar_dict),
                    },
                {
                    'label': 'MEM',
                    'text': {
                        'func': lambda d: human_file_size(d['mem_size']),
                        },
                    'bar': dict({
                        'func': lambda d: d['mem_perc'] * 0.01,
                        }, **bar_dict),
                    },
                ]

    def setup_layout(self, app):

        row = self.child(dbc.Row)
        views = list(map(
                lambda src: row.child(dbc.Col, lg=12, md=4).child(
                        self._info_view_cls(**src)), self._sources))

        def update_info(n_intervals):
            p = self._psutil_proc
            with p.oneshot():
                data = {
                        'cpu_perc': p.cpu_percent(),
                        'mem_perc': p.memory_percent(),
                        'mem_size': p.memory_info().rss,
                        }
            result = mapsum(
                    lambda view: [
                        c.func(data) for c in view.output_components],
                    views
                    )
            return result

        timer = self.child(dcc.Interval, interval=self._update_interval)
        datastore = self.child(self._datastore_cls())

        datastore.register_callback(
                mapsum(
                    lambda view: view.outputs,
                    views
                    ),
                [Input(timer.id, 'n_intervals')],
                [],
                update_info
                )

        super().setup_layout(app)

    @property
    def layout(self):
        return super().layout
