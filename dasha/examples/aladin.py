#! /usr/bin/env python

"""
This file defines an example site that combines dash with
external js API.
"""


from dasha.web.templates import ComponentTemplate
from dasha.web.templates.common import LabeledInput
from dasha.web.templates.aladinlite import AladinLiteView

import dash
from dash.dependencies import Output, Input, State
import dash_html_components as html
import dash_bootstrap_components as dbc
from astroquery.utils import parse_coordinates
import astropy.units as u
import functools


class SkyView(ComponentTemplate):

    _component_cls = dbc.Container

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def setup_layout(self, app):
        container = self

        header_container, body_container = container.grid(2, 1)

        header_container.child(html.H3(self.title_text))

        controls_container, view_container = body_container.grid(2, 1)

        controls_form = controls_container.child(
                html.Div, className='d-flex align-items-center')

        coords_input = controls_form.child(LabeledInput(
            label_text='Coordinate',
            input_props={
                'placeholder': "e.g.: M51, 180d 0d, 1h12m43.2s +1d12m43s",
                'value': 'M51',
                # 'debounce': True,
                # 'autoFocus': True,
                },
            className='mr-2',
            )).input

        coords_display = controls_form.child(html.Div)
        alv = view_container.child(AladinLiteView(
            config={
                'survey': 'P/2MASS/color',
                'fov': 1 / 3,  # deg
                'target': 'M51'
                },
            ))

        super().setup_layout(app)

        @functools.lru_cache(maxsize=8)
        def _parse_coords(c):
            return parse_coordinates(c)

        def _c2str(c):
            return (
                    f"{c.ra.to_string(u.hour)} "
                    f"{c.dec.to_string(u.deg, alwayssign=True)}")

        @app.callback(
                [
                    Output(coords_display.id, 'children'),
                    Output(coords_input.id, 'valid'),
                    Output(coords_input.id, 'invalid'),
                    ],
                [
                    Input(coords_input.id, 'value'),
                    ]
                )
        def validate_coords(coords_input_value):
            try:
                c = _parse_coords(coords_input_value)
            except Exception:
                return "", False, True
            return dbc.FormText(
                    f"Coords resolved: {_c2str(c)}"), True, False

        @app.callback(
                alv.output_target,
                [
                    Input(coords_input.id, 'n_submit'),
                    Input(coords_input.id, 'n_blur')
                    ],
                [
                    State(coords_input.id, 'value')
                    ],
                prevent_initail_call=True
                )
        def update_view(n_submit, n_blur, coords_input_value):
            try:
                _parse_coords(coords_input_value)
            except Exception:
                raise dash.exceptions.PreventUpdate
            return coords_input_value


extensions = [
    {
        'module': 'dasha.web.extensions.dasha',
        'config': {
            'template': SkyView,
            'title_text': 'Sky View',
            }
        },
    ]
