#! /usr/bin/env python

import dash_daq as daq
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Output, Input
from . import ComponentTemplate
import numpy as np
from astropy.utils.console import human_time
from .collapsecontent import CollapseContent
from tollan.utils.fmt import pformat_yaml


class ReJsonIPCInfo(ComponentTemplate):

    _component_cls = html.Div

    def __init__(self, store_factory, timeout_thresh=3, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._store_factory = store_factory
        self._timeout_thresh = timeout_thresh

    def setup_layout(self, app):

        indicator_container = self.child(
                html.Div, className='align-items-center d-flex')
        indicator = indicator_container.child(
                daq.Indicator,
                label='',
                labelPosition='right',
                )

        check_interval = 1
        timer = indicator_container.child(
                dcc.Interval, interval=check_interval * 1000)

        # details_container = self.child(html.Div)
        collapse = CollapseContent(button_text='Details ...')
        collapse._button.size = 'sm'
        details = indicator_container.child(collapse).content
        # move the details container to self.
        details.parent = self
        super().setup_layout(app)

        @app.callback(
                [
                    Output(indicator.id, 'color'),
                    Output(indicator.id, 'label'),
                    Output(details.id, 'children')
                    ],
                [
                    Input(timer.id, 'n_intervals'),
                    ],
                prevent_initial_call=True)
        def update_info(n_intervals):
            store = self._store_factory()
            meta = store.get_meta()
            has_value = not store.is_null()

            # check time info
            current_time = store._connection.time()
            elapsed = np.array(current_time) - np.array(meta['updated_at'])
            elapsed = elapsed[0] + 1e-6 * elapsed[1]

            value_is_active = elapsed < self._timeout_thresh

            if not has_value:
                color = '#f45060'
            elif not value_is_active:
                color = '#f4d44d'
            else:
                color = '#92e0d3'
            if not has_value:
                label = 'Data source error'
            else:
                label = f'Last updated: {human_time(elapsed)} ago',
            return (
                    color,
                    {
                        'label': label,
                        'style': {
                            'margin-left': '0.5rem'
                            }
                        },
                    html.Pre(pformat_yaml(meta))
                    )
