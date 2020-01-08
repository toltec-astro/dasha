#! /usr/bin/env python

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_daq as daq
import dash_html_components as html
from dash.dependencies import Input, Output
from tolteca.utils.log import get_logger
from .. import get_current_dash_app
from plotly.subplots import make_subplots
from ..utils import tz_off_from_ut
from ..common import LiveTitleComponent
from . import SimplePageTemplate
from ....utils import deepmerge
from .ncscope import NcScope
import numpy as np


app = get_current_dash_app()
logger = get_logger()


class LiveNcFileView(SimplePageTemplate):

    _template_params = [
            'label',
            'title_text',
            'title_icon',
            'update_interval',
            'fig_layout',
            'source',
            ]

    _controls = {
            'toggle-collate': {
                'value': 'on',
                'kwarg_key': 'collate',
                },
            'toggle-ut': {
                'value': 'value',
                'kwarg_key': 'use_ut',
                }
            }

    def __init__(self, **params):
        super().__init__(**params)

        # some more default settings
        fig_layout = dict(
            uirevision=True,
            xaxis={
                'title': 'UT'
                },
            )
        deepmerge(fig_layout, self.fig_layout)
        self.fig_layout = fig_layout

        src = self.source
        # update source key so that they don't clash.
        src['label'] = f"{self.label}_{src['label']}"
        # setup layout factory and callbacks
        src['_title_view'] = LiveTitleComponent(src['label'])
        src['_utc_to_local_tz'] = tz_off_from_ut(src['local_tz'])

        ctx = src['label']

        ctrls = src.get('controls', list())

        for ctrl in ctrls:
            if ctrl not in self._controls:
                raise RuntimeError(f"undefined control {ctrl}")

        cb_inputs = [
                Input(f'{ctx}-update-timer', 'n_intervals'),
                ]

        for ctrl in ctrls:
            cb_inputs.append(
                Input(f'{ctx}-control-{ctrl}', self._controls[ctrl]['value']),
                    )

        @app.callback([
                Output(f'{ctx}', 'figure'),
                Output(src['_title_view'].is_loading, 'children')
                ], cb_inputs, [
                ])
        def entry_update(n_intervals, *args):
            ctrl_kwargs = {
                    self._controls[ctrl]['kwarg_key']: arg
                    for ctrl, arg in zip(ctrls, args)}
            logger.debug(
                    f"update graph at {n_intervals}"
                    f" with {ctrl_kwargs}")
            return self.get_figure(**ctrl_kwargs), ""

    def get_traces(self):
        src = self.source
        if callable(src['traces']):
            return src['traces'](src)

        # generic nc file trace
        ns = NcScope.from_link(src['runtime_link'])
        ns.sync()
        result = []
        for i, trace in enumerate(src['traces']):
            trace.setdefault('name', f"trace {i}")

            # get slice
            slice_ = trace.pop('slice', slice())

            # read data
            y_name = trace.pop('y')
            y = ns.var(y_name)[slice_]

            if 'x' in trace:
                x_name = trace.pop('x')
                x = ns.var(x_name)[slice_]
            else:
                x_name = 'index'
                x = np.arange(y)

            # dtype
            if 'x_dtype' in trace:
                x = np.asarray(x, dtype=trace['x_dtype'])
            if 'y_dtype' in trace:
                y = np.asarray(x, dtype=trace['y_dtype'])

            # filter data
            if 'trans' in trace:
                x, y = trace.pop('trans')(x, y)

            x_label = trace.pop('x_label', x_name)
            y_label = trace.pop('x_label', y_name)

            trace_out = {
                'x': x,
                'y': y,
                'subplot_layout': {
                    'xaxis': {
                        'title': x_label
                        },
                    'yaxis': {
                        'title': y_label
                        }
                    },
                }
            deepmerge(trace_out, trace)
            result.append(trace_out)
        return result

    def get_layout(self, **kwargs):
        src = self.source
        ctx = src['label']
        ctrls = src['controls']
        controls = []
        ctrl_kwargs = dict()
        if 'toggle-collate' in ctrls:
            ctrl = 'toggle-collate'
            controls.extend([
                    daq.BooleanSwitch(
                        id=f'{ctx}-control-{ctrl}',
                        label={
                            'label': 'Collate',
                            'style': {
                                'margin': '0px 5px',
                                },
                            },
                        labelPosition='left',
                        on=True,
                        style={
                            'margin': '0px 5px',
                            }
                        ),
                    html.Div(className='mx-4'),
                    ])
            ctrl_kwargs[self._controls[ctrl]['kwarg_key']] = True
        if 'toggle-ut' in ctrls:
            ctrl = 'toggle-ut'
            controls.extend([
                    html.Div([
                            html.Label(src['local_tz'], style={
                                'font-size': '14px',
                                'display': 'block',
                                'margin': '0px 5px',
                                }),
                            daq.ToggleSwitch(
                                id=f'{ctx}-control-{ctrl}',
                                value=False,
                                style={
                                    'margin': '0px 5px',
                                    }
                                ),
                            html.Label("UT", style={
                                'font-size': '14px',
                                'display': 'block',
                                'margin': '0px 5px',
                                }),
                            ], className='d-flex align-items-center'),
                    ])
            ctrl_kwargs[self._controls[ctrl]['kwarg_key']] = False

        controls = html.Div([
                dbc.Row(controls, className='px-2')])

        graph_view = html.Div([
            dcc.Interval(
                id=f'{ctx}-update-timer',
                interval=self.update_interval),
            dcc.Graph(
                id=f'{ctx}',
                figure=self.get_figure(**ctrl_kwargs),
                # animate=True,
                )
            ])
        return html.Div([
            dbc.Row([dbc.Col(
                src['_title_view'].components(self.title_text)), ]),
            dbc.Row([dbc.Col(controls), ]),
            dbc.Row([dbc.Col(graph_view), ]),
            ])

    def get_figure(self, collate=False, use_ut=False):
        src = self.source
        traces = self.get_traces()
        if collate:
            n_panels = 1
            fig_height = 900
            fig_kwargs = dict()
        else:
            n_panels = len(traces)
            fig_height = 300 * n_panels
            fig_kwargs = dict(subplot_titles=[t['name'] for t in traces])

        fig = make_subplots(
                rows=n_panels, cols=1, **fig_kwargs)

        fig.update_layout(
                height=fig_height,
                **self.fig_layout)
        if not use_ut:
            fig['layout']['xaxis']['title'] = src['local_tz']

        for i, t in enumerate(traces):
            subplot_layout = t.pop('subplot_layout', {
                'xaxis': dict(),
                'yaxis': dict(),
                })
            if collate:
                row = 1
            else:
                row = i + 1
            col = 1
            if not use_ut:
                t['x'] = t['x'] + src['_utc_to_local_tz']
            fig.append_trace(t, row, col)
            fig.update_xaxes(row=row, col=col, **subplot_layout['xaxis'])
            fig.update_yaxes(row=row, col=col, **subplot_layout['yaxis'])

        return fig


template_cls = LiveNcFileView
