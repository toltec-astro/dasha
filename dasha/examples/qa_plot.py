#!/usr/bin/env python


from dasha.web.templates import ComponentTemplate
from dasha.web.templates.common import LabeledDropdown

import plotly.graph_objects as go
from dash.dependencies import Output, Input

import dash_html_components as html
import dash_core_components as dcc
import dash_bootstrap_components as dbc
from tollan.utils.fmt import pformat_yaml

import numpy as np


class QAExample(ComponentTemplate):
    _component_cls = dbc.Container

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def setup_layout(self, app):
        container = self

        header_container, body_container = container.grid(2, 1)

        header_container.child(html.H3(self.title_text))

        # input container to hold the figure for QA
        # output container to hold the QA report
        input_container, output_container = body_container.grid(1, 2)

        controls_container, view_container = input_container.grid(2, 1)

        controls_form = controls_container.child(
                html.Div, className='d-flex align-items-center')

        # this is to mimic the selection of data
        data_select = controls_form.child(
                LabeledDropdown(
                    label_text='Select Data',
                    className='mt-3 w-auto mr-3',
                    size='sm',
                    )).dropdown
        data_select.options = [
                {
                    'label': f'Dataset {i}',
                    'value': i
                    }
                for i in range(3)
                ]
        data_select.value = 1

        # the graph to hold the plot
        graph = view_container.child(dcc.Loading).child(dcc.Graph)

        super().setup_layout(app)

        # The callback to update graph based on selection
        @app.callback(
                Output(graph.id, 'figure'),
                [
                    Input(data_select.id, 'value'),
                    ],
                )
        def update_view(data_select_value):
            # make some fake waterfall data
            # y is time, x is channel
            n_y = 2000
            n_x = 100
            dy = 0.1  # time step in s
            dx = 1  # channel id step
            y0 = 0  # t0
            x0 = 0  # first channel id
            yy, xx = np.meshgrid(
                    np.arange(y0, y0 + n_y * dy, dy),
                    np.arange(x0, x0 + n_x * dx, dx),
                    )

            data = np.random.rand(n_y, n_x)
            fig = go.Figure()

            trace = {
                    'type': 'heatmap',
                    'name': f"Dataset {data_select_value}",
                    'z': data,
                    'x0': x0,
                    'y0': y0,
                    'dx': dx,
                    'dy': dy,
                    }
            # because plotly does not support lasso on the heatmap,
            # we need to plot a scatter layer to do the selection.
            # see this issue: https://github.com/plotly/plotly.js/issues/170
            sel_trace = {
                    'type': 'scattergl',
                    'mode': 'markers',
                    'x': xx.ravel(),
                    'y': yy.ravel(),
                    'marker_size': 5,
                    'marker_color': data.T.ravel(),
                    }

            fig.add_trace(trace)
            fig.add_trace(sel_trace)
            fig.update_xaxes(
                    scaleanchor='x',
                    scaleratio=n_y / n_x,
                    constrain='range',
                    title='Channel'
                    )
            fig.update_yaxes(
                    title='Time (s)'
                    )
            fig.update_layout(
                    height=1000,
                    uirevision=True,
                    coloraxis=dict(
                        colorscale='Viridis',
                        colorbar=dict(
                            title={
                                'text': 'Value',
                                'side': 'right',
                                },
                            )
                        ),
                    # showlegend=False,
                    # margin=dict(t=60),
                    clickmode='event+select'
                    )
            return fig

        @app.callback(
            Output(output_container.id, 'children'),
            [
                Input(graph.id, 'hoverData'),
                Input(graph.id, 'clickData'),
                Input(graph.id, 'selectedData'),
                ])
        def report_interaction(hover_data, click_data, selected_data):
            report = pformat_yaml(locals())
            return html.Pre(report)


extensions = [
    {
        'module': 'dasha.web.extensions.dasha',
        'config': {
            'template': QAExample,
            'title_text': 'QA Example',
            }
        },
    ]
