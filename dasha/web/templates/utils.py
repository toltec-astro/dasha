#! /usr/bin/env python
import dash_html_components as html
from dash.dependencies import Output, Input, State
import dash
import json


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


def partial_update_at(pos, elem):
    """Return a tuple that only update the output at `pos`.

    Parameters
    ----------
    pos : slice, int
        The position of element(s) to update.
    elem : object
        The object to be updated at `pos`.
    """
    outputs_list = dash.callback_context.outputs_list
    print(dash.callback_context.outputs_list)
    if isinstance(outputs_list, dict):
        n_outputs = 1
    else:
        n_outputs = len(outputs_list)
    results = [dash.no_update, ] * n_outputs
    results[pos] = elem
    if isinstance(outputs_list, dict):
        return results[0]
    return results


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
