#!/usr/bin/env python

import os
from dash_component_template import ComponentTemplate
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output
from dasha.web.extensions.auth import (
    get_github_user_info,
    is_authorized,
    # github_auth
    )
from tollan.utils.fmt import pformat_yaml


class MyApp(ComponentTemplate):
    class Meta:
        component_cls = dbc.Container

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fluid = False

    def setup_layout(self, app):
        container = self
        header, body = container.grid(2, 1)
        header.child(html.H1("Hello, Dash!"))
        auth_btn = header.child(dbc.Button, color='link')
        auth_link = auth_btn.child(dcc.Link, href='', refresh=True)
        text = body.child(html.Pre, 'N/A')
        loc = body.child(dcc.Location, refresh=False)

        @app.callback(
            output=Output(text.id, 'children'),
            inputs=[Input(loc.id, 'pathname')])
        def show_auth(pathname):
            s = f'Page URL: {pathname}'
            if is_authorized():
                user_info = get_github_user_info()
                s += f'\n{pformat_yaml(user_info)}'
            else:
                s += '\nUnauthorized!'
            return s

        @app.callback(
            output=[
                Output(auth_link.id, 'href'),
                Output(auth_btn.id, 'color'),
                ],
            inputs=[Input(loc.id, 'pathname')])
        def update_btn_auth(pathname):
            if is_authorized():
                return ['/auth/logout', 'secondary']
            return ['/auth', 'link']

        # @app.callback(
        #     output=[
        #         Output(loc.id, 'pathname'),
        #         Output(loc.id, 'refresh'),
        #         ],
        #     inputs=[Input(btn_auth.id, 'n_clicks')],
        #     prevent_initial_call=True)
        # def do_auth(n_clicks):
        #     if is_authorized():
        #         return '/auth/logout', False
        #     return 'auth/', False


# https://stackoverflow.com/q/27785375
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

DASHA_SITE = {
    'extensions': [
        {
            'module': 'dasha.web.extensions.auth',
            'config': {
                'client_id': 'c19cb36f3e00597f99e1',
                'client_secret': 'bc41d0cb03df896c9b70a644fec34098fe95464f'
                }
            },
        {
            'module': 'dasha.web.extensions.dasha',
            'config': {
                'DEBUG': True,
                'THEME': dbc.themes.YETI,
                'template': MyApp,
                }
            },
        ]
    }
