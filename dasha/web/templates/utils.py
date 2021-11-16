#! /usr/bin/env python

import json
import dash
from dash import html, Output, Input, State
from plotly.subplots import make_subplots as _make_subplots


def fa(className, **kwargs):
    """Return a font-awesome icon.

    """
    return html.I(className=className, **kwargs)


def to_dependency(type_, dep):
    """Convert a dependency object to another `type_`.

    Parameters
    ----------
    type_ : str
        The type to convert to, choosing from "state", "input", or "output".

    """
    dispatch = {
            'state': State,
            'input': Input,
            'output': Output
            }
    return dispatch[type_](dep.component_id, dep.component_property)


def parse_prop_id(prop_id):
    """Return a parsed `prop_id`."""
    d, v = prop_id.rsplit('.', 1)
    if d == '':
        return None
    if '{' in d:
        d = json.loads(d)
    return {'id': d, 'prop': v}


def parse_triggered_prop_ids():
    """Return a parsed triggered `prop_id`."""
    return [
            parse_prop_id(d['prop_id']) for d in
            dash.callback_context.triggered]


def make_subplots(nrows, ncols, fig_layout=None, **kwargs):
    """Return a sensible multi-panel figure with predefined layout."""
    _fig_layout = {
            'uirevision': True,
            'xaxis_autorange': True,
            'yaxis_autorange': True,
            'showlegend': True,
            }
    if fig_layout is not None:
        _fig_layout.update(fig_layout)
    fig = _make_subplots(nrows, ncols, **kwargs)
    fig.update_layout(**_fig_layout)
    return fig
