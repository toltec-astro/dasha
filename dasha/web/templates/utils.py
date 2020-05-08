#! /usr/bin/env python
import dash_html_components as html
from dash.dependencies import Output, Input, State


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
