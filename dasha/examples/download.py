#! /usr/bin/env python

"""
This file defines an example site that show how download works.
"""


from dasha.web.templates import ComponentTemplate

import dash
import plotly.graph_objects as go
from dasha.web.templates.common import LabeledInput
from dash.dependencies import Output, Input, State
import dash_html_components as html
import dash_core_components as dcc
import dash_bootstrap_components as dbc
from dash_extensions import Download
from dash_extensions.snippets import send_bytes
from astroquery.utils import parse_coordinates
import functools
import numpy as np
import astropy.units as u


class SkyViewDownload(ComponentTemplate):

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

        graph = view_container.child(dcc.Loading).child(dcc.Graph)

        coords_display = controls_form.child(html.Div)

        download_btn = controls_form.child(dbc.Button, 'Download')
        download_output = controls_form.child(Download)

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
                Output(download_output.id, 'data'),
                [
                    Input(download_btn.id, 'n_clicks'),
                    ],
                [
                    State(coords_input.id, 'value')
                    ],
                prevent_initial_call=True
                )
        def on_download(n_clicks, coords_input_value):
            try:
                hdulists = get_2mass_image(coords_input_value)
            except Exception:
                raise dash.exceptions.PreventUpdate
            # just download the last hdulsit
            hdulist = hdulists[-1]
            return send_bytes(
                        hdulist.writeto,
                        f"skyviewdownload_{coords_input_value}.fits")

        @app.callback(
                Output(graph.id, 'figure'),
                [
                    Input(coords_input.id, 'n_submit'),
                    Input(coords_input.id, 'n_blur')
                    ],
                [
                    State(coords_input.id, 'value')
                    ],
                )
        def update_view(n_submit, n_blur, coords_input_value):
            fig = go.Figure()
            trace = make_2mass_image_trace(coords_input_value)
            fig.add_trace(trace)
            fig.update_xaxes(
                    scaleanchor='x',
                    scaleratio=1.,
                    constrain='range',
                    )
            fig.update_layout(height=800)
            return fig


@functools.lru_cache(maxsize=None)
def get_2mass_image(coord_obs_value):

    from astroquery.skyview import SkyView

    ref_coord = parse_coordinates(coord_obs_value)

    hdulists = SkyView.get_images(
            ref_coord,
            # survey=['WISE 12', 'WISE 4.6', 'WISE 3.4'],
            survey=['2MASS-K', '2MASS-H', '2MASS-J'],
            )
    return hdulists


def make_2mass_image_trace(coord_obs_value):

    from astropy.wcs import WCS
    # from astropy.visualization import ZScaleInterval, ImageNormalize
    from astropy.visualization import make_lupton_rgb
    from astropy.wcs.utils import proj_plane_pixel_scales

    ref_coord = parse_coordinates(coord_obs_value)
    hdulists = get_2mass_image(coord_obs_value)

    # scales = [0.3, 0.8, 1.0]
    scales = [1.5, 1.0, 1.0]  # white balance

    def _bkg_subtracted_data(hdu, scale=1.):
        ni, nj = hdu.data.shape
        mask = np.ones_like(hdu.data, dtype=bool)
        frac = 5
        mask[
                ni // frac:(frac - 1) * ni // 4,
                nj // frac:(frac - 1) * nj // 4] = False
        data_bkg = hdu.data[mask]
        bkg = 3 * np.nanmedian(data_bkg) - 2 * np.nanmean(data_bkg)
        return (hdu.data - bkg) * scale

    image = make_lupton_rgb(
            *(_bkg_subtracted_data(
                hl[0], scale=scale)
                for hl, scale in zip(hdulists, scales)),
            Q=10, stretch=50)
    w = WCS(hdulists[0][0].header)
    dx, dy = proj_plane_pixel_scales(w)
    x0, y0 = w.all_pix2world(image.shape[0], 0, 0)
    # cos_dec = np.cos(np.deg2rad(ref_coord.dec.degree))
    trace = {
            'type': 'image',
            'name': f"{ref_coord.to_string('hmsdms')}",
            'z': image,
            'x0': x0.item(),
            'y0': y0.item(),
            'dx': np.abs(dx),  # / cos_dec,
            'dy': np.abs(dy),
            }
    return trace


extensions = [
    {
        'module': 'dasha.web.extensions.dasha',
        'config': {
            'template': SkyViewDownload,
            'title_text': 'Sky View',
            }
        },
    ]
