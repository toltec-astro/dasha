#! /usr/bin/env python
import dash_html_components as html
from dash.dependencies import Output, Input, State


def resolve_url(path):
    """Expands an internal URL to include prefix the app is mounted at."""
    from flask import current_app as server
    return f"{server.config.get('ROUTES_PATHNAME_PREFIX', '')}{path}"


def fa(className):
    return html.I(className=className)


def to_dependency(type_, dep):
    dispatch = {
            'state': State,
            'input': Input,
            'output': Output
            }
    return dispatch[type_](dep.component_id, dep.component_property)
