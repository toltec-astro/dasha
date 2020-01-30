#! /usr/bin/env python

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_daq as daq
import dash_html_components as html
from dash.dependencies import Input, Output, State, ClientsideFunction
from ....utils.log import get_logger
from .. import get_current_dash_app
from plotly.subplots import make_subplots
from ..utils import tz_offset
from ..common import LiveTitleComponent
from . import SimplePageTemplate
from ....utils import deepmerge
from ....utils.fmt import pformat_dict
from .ncscope import NcScope
from .csvscope import CsvScope
import numpy as np
from copy import deepcopy


app = get_current_dash_app()
logger = get_logger()


class LiveNcFileView(SimplePageTemplate):

    _template_params = [
            'label',
            'title_text',
            'title_icon',
            'update_interval',
            'sources',
            ]

    _controls = {
            'toggle-collate': {
                'value': 'on',
                'kwarg_key': 'collate',
                'type': 'input',
                'output_key': 'figure',
                },
            'toggle-tz': {
                'value': 'on',
                'kwarg_key': 'use_local_tz',
                'type': 'input',
                'output_key': 'figure',
                },
            'toggle-ut': {
                'value': 'value',
                'kwarg_key': 'use_ut',
                'type': 'input',
                'output_key': 'figure',
                },
            'file-info': {
                'value': 'children',
                'output_key': 'file_info',
                'type': 'output',
                },
            }

    _fig_layout = dict(
            uirevision=True,
            xaxis={
                'autorange': True,
                },
            yaxis={
                'autorange': True,
                },
            )

    def __init__(self, **params):
        super().__init__(**params)
        for src in self.sources.values():
            self._init_source(src)

    def _init_source(self, src):
        # update source key so that they don't clash.
        src['label'] = f"{self.label}_{src['label']}"
        # setup layout factory and callbacks
        src['_title_view'] = LiveTitleComponent(src['label'])

        src_fig_laytout = src.pop('fig_layout', dict())
        deepmerge(src_fig_laytout, self._fig_layout)
        src['fig_layout'] = src_fig_laytout

        ctx = src['label']

        ctrls = src.get('controls', list())

        for ctrl in ctrls:
            if ctrl not in self._controls:
                raise RuntimeError(f"undefined control {ctrl}")

        cb_inputs = [
                Input(f'{ctx}-update-timer', 'n_intervals'),
                ]
        cb_outputs = [
                Output(src['_title_view'].is_loading, 'children'),
                Output(f'{ctx}', 'figure'),
                ]

        ctrl_inputs = []
        ctrl_outputs = []
        for ctrl in ctrls:
            ctrl_type = self._controls[ctrl]['type']
            if ctrl_type == 'input':
                ctrl_inputs.append(ctrl)
            elif ctrl_type == 'output':
                ctrl_outputs.append(ctrl)

        for ctrl in ctrl_inputs:
            cb_inputs.append(
                Input(
                    f'{ctx}-control-{ctrl}',
                    self._controls[ctrl]['value']),
                )
        for ctrl in ctrl_outputs:
            cb_outputs.append(
                Output(
                    f'{ctx}-control-{ctrl}',
                    self._controls[ctrl]['value']),
                )

        @app.callback(cb_outputs, cb_inputs, [])
        def entry_update(n_intervals, *args):
            ctrl_kwargs = {
                    self._controls[ctrl]['kwarg_key']: arg
                    for ctrl, arg in zip(ctrl_inputs, args)}
            output_kwargs = {
                    self._controls[ctrl]['output_key']: True
                    for ctrl in ctrl_outputs}
            logger.debug(
                    f"update graph at {n_intervals}"
                    f" with {ctrl_kwargs}")
            outputs = self._get_outputs(
                    src, **ctrl_kwargs, **output_kwargs)
            return ("", outputs['figure']) + tuple(
                    outputs[k] for k in output_kwargs)

        if 'file-info' in ctrls:
            ctrl = 'file-info'
            app.clientside_callback(
                ClientsideFunction(
                    namespace='ui',
                    function_name='toggleWithClick',
                ),
                Output(f"{ctx}-control-{ctrl}-collapse", 'is_open'),
                [Input(f"{ctx}-control-{ctrl}-toggle", "n_clicks")],
                [State(f"{ctx}-control-{ctrl}-collapse", 'is_open')],
            )

    def _get_traces(self, src):
        # make deep copy be
        if callable(src['traces']):
            return src['traces'](src)

        # generic nc file trace
        result = []
        synced = dict() 
        for i, trace in enumerate(src['traces']):
            # make a deepcopy because we will modify this dict
            trace = deepcopy(trace)
            trace.setdefault('name', f"trace {i}")

            # load ncfile
            runtime_link = trace.pop('runtime_link', src.get('runtime_link', None))
            if runtime_link.endswith('.nc'):
                ns_cls = NcScope
            elif runtime_link.endswith('.csv'):
                ns_cls = CsvScope
            else:
                ns_cls = NcScope
            ns = ns_cls.from_link()
            if ns not in synced:
                synced[ns] = ns.sync()
            # get slice
            x_slice = trace.pop('x_slice', None)
            y_slice = trace.pop('y_slice', None)

            # in case only x or y slice is specified
            if x_slice is None and y_slice is not None:
                x_slice = y_slice
            elif x_slice is not None and y_slice is None:
                y_slice = x_slice
            if x_slice is None:
                x_slice = slice(None)
            if y_slice is None:
                y_slice = slice(None)

            # read data
            y_name = trace.pop('y')
            y = ns.var(y_name)

            if 'x' in trace:
                x_name = trace.pop('x')
                x = ns.var(x_name)
            else:
                x_name = 'index'
                x = np.arange(y)

            # read data with slice
            x = x[x_slice]
            y = y[y_slice]

            # dtype
            x_tz = None
            if 'x_dtype' in trace:
                x_dtype = trace.pop('x_dtype')
                if x_dtype == 'posixtime':
                    x_dtype = 'datetime64[s]'
                    x_tz = 'UTC'
                else:
                    x_tz = trace.pop('x_tz', None)
                x = np.asarray(x, dtype=x_dtype)
            if 'y_dtype' in trace:
                y = np.asarray(x, dtype=trace['y_dtype'])

            # filter data
            if 'trans' in trace:
                x, y = trace.pop('trans')(x, y)

            x_label = trace.pop('x_label', x_name)
            y_label = trace.pop('y_label', y_name)

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
                '_is_timeseries': x_tz is not None,
                '_x_tz': x_tz
                }
            deepmerge(trace_out, trace)
            result.append(trace_out)
        return result, ns

    def _get_layout(self, src):
        ctx = src['label']
        ctrls = src.get('controls', list())
        controls_grid = []

        def make_controls_row(controls):
            if len(controls) > 0:
                controls_grid.append(dbc.Row(controls, className='px-2'))
                return list()
            return controls
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
        if 'toggle-tz' in ctrls:
            ctrl = 'toggle-tz'
            controls.extend([
                    daq.BooleanSwitch(
                        id=f'{ctx}-control-{ctrl}',
                        label={
                            'label': src['local_tz'],
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
        controls = make_controls_row(controls)
        controls = html.Div(controls_grid, className='my-2')

        # outputs
        output_kwargs = dict()
        if 'file-info' in ctrls:
            ctrl = 'file-info'
            output_kwargs[self._controls[ctrl]['output_key']] = True

        outputs = self._get_outputs(src, **ctrl_kwargs, **output_kwargs)

        output_rows = [
            dbc.Row([dbc.Col(
                src['_title_view'].components(src['title'])), ]),
            dbc.Row([dbc.Col(controls), ]),
            ]

        # optional outputs
        if 'file-info' in ctrls:
            ctrl = 'file-info'
            output_rows.append(dbc.Row([
                    dbc.Col(html.Div([
                        dbc.Button(
                                "File Info",
                                id=f"{ctx}-control-{ctrl}-toggle",
                                className="mb-2",
                                size='sm',
                                color='info',
                                ),
                        dbc.Collapse(
                            html.Div(
                                id=f"{ctx}-control-{ctrl}",
                                children=outputs[
                                    self._controls[ctrl]['output_key']],
                                ),
                            id=f"{ctx}-control-{ctrl}-collapse"
                            ),
                        ]),
                    )]))

        graph_view = html.Div([
            dcc.Interval(
                id=f'{ctx}-update-timer',
                interval=self.update_interval),
            dcc.Graph(
                id=f'{ctx}',
                figure=outputs['figure'],
                # animate=True,
                )
            ])
        output_rows.append(dbc.Row([dbc.Col(graph_view), ]))
        return html.Div(output_rows)

    def get_layout(self, **kwargs):

        components = []

        width = 12 // len(self.sources)
        if width < 3:
            width = 3
        for src in self.sources.values():
            components.append(dbc.Col(
                self._get_layout(src), md=12, lg=6, xl=width))

        return html.Div([dbc.Row(components)])

    def _get_outputs(
            self, src, collate=False, use_local_tz=True,
            file_info=False):
        traces_in, ns = self._get_traces(src)

        # handle local tz
        # this will update traces
        for i, t in enumerate(traces_in):
            is_timeseries = t.pop("_is_timeseries", False)
            x_tz = t.pop('_x_tz', None)
            if is_timeseries:
                if x_tz is not None:
                    if use_local_tz:
                        t['x'] = t['x'] + tz_offset(src['local_tz'], x_tz)
                        x_tz_suffix = f' ({src["local_tz"]})'
                    else:
                        x_tz_suffix = f' ({x_tz})'
                    x_name = t['subplot_layout']['xaxis']['title']
                    t['subplot_layout']['xaxis']['title'] = \
                        f'{x_name}{x_tz_suffix}'

        # expand traces for 2d data
        traces = []
        for t in traces_in:
            y = t['y']
            n_dims_y = y.ndim
            if n_dims_y == 1:
                traces.append(t)
            elif n_dims_y == 2:
                # expand last dim
                for i in range(y.shape[-1]):
                    t_ = {
                        k: v for k, v in t.items() if k != 'y'
                        }
                    t_['y'] = y[:, i]
                    name = t_['name']
                    t_['name'] = f'{name} [{i}]'
                    traces.append(t_)
            else:
                continue

        fig_layout = deepcopy(src['fig_layout'])
        if collate or len(traces) == 1:
            n_panels = 1
            fig_layout.setdefault('height', 900)
            fig_kwargs = dict()
        else:
            n_panels = len(traces)
            fig_layout.setdefault('height', 300)
            fig_layout['showlegend'] = False
            fig_layout['height'] *= n_panels
            fig_kwargs = dict(subplot_titles=[t['name'] for t in traces])

        fig = make_subplots(
                rows=n_panels, cols=1, **fig_kwargs)

        fig.update_layout(**fig_layout)
        for i, t in enumerate(traces):
            subplot_layout = t.pop('subplot_layout', {
                'xaxis': dict(),
                'yaxis': dict(),
                })

            if collate:
                row = 1
                trace_kwargs = dict()
            else:
                row = i + 1
                trace_kwargs = dict(visible=True)
            col = 1
            t.update(**trace_kwargs)
            fig.append_trace(t, row, col)
            fig.update_xaxes(row=row, col=col, **subplot_layout['xaxis'])
            fig.update_yaxes(row=row, col=col, **subplot_layout['yaxis'])

        outputs = dict(figure=fig)
        if file_info:
            file_info = dbc.Card([
                    dbc.CardBody([
                        html.H6(ns.filepath.name),
                        html.Pre(pformat_dict(ns.read_as_dict(
                            src['info_keys'])))
                        ])
                    ], style={
                        'min-width': '40rem'})
            outputs['file_info'] = file_info
        return outputs


template_cls = LiveNcFileView
