#! /usr/bin/env python
import dash_html_components as html
from dash.dependencies import Output, Input, State
from ..extensions.dasha import get_current_dash_app
from tollan.utils import ensure_prefix


def resolve_url(path):
    """Expands an internal URL to include prefix the app is mounted at."""
    app = get_current_dash_app()
    routes_prefix = app.config.routes_pathname_prefix or ''
    return f"{routes_prefix}{path}".replace('//', '/')


def get_url_stem(path):
    """The inverse of `resolve_url`."""
    app = get_current_dash_app()
    routes_prefix = app.config.routes_pathname_prefix or ''
    if routes_prefix == '':
        return path
    routes_prefix = ensure_prefix(routes_prefix.strip('/'), '/')
    path = ensure_prefix(path, '/')
    if path.startswith(routes_prefix):
        path = path.replace(routes_prefix, "", 1)
    return ensure_prefix(path, '/')


def fa(className):
    return html.I(className=className)


def to_dependency(type_, dep):
    dispatch = {
            'state': State,
            'input': Input,
            'output': Output
            }
    return dispatch[type_](dep.component_id, dep.component_property)
