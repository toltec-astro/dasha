#! /usr/bin/env python


"""
This file defines an example site that benchmarks the celery task queue.
"""

from tollan.utils.env import env_registry
from dasha.web.templates import ComponentTemplate
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_core_components as dcc
from dash.dependencies import Output, Input
from dasha.web.extensions.celery import get_celery_app
import celery


@celery.shared_task
def sleep(t):
    import time
    time.sleep(t)


class CeleryBenchmark(ComponentTemplate):

    _component_cls = dbc.Container
    fluid = True

    def setup_layout(self, app):
        title = self.title_text
        header = self.child(dbc.Row).child(dbc.Col).child(dbc.Jumbotron)
        body = self.child(dbc.Row).child(dbc.Col)

        header.children = [
                html.H1(f'{title}'),
                html.P(
                    'This page runs some celery tasks and'
                    ' calculates the overall throughput.')
                ]

        timer = body.child(dcc.Interval, interval=1000)
        ticker_container = body.child(html.Div, className='d-flex')
        ticker_container.child(
                dbc.Label("n_intervals:", className='mr-2'))
        ticker = ticker_container.child(html.Div, 'N/A')

        task_container = body.child(html.Div, className='d-flex')

        _celery_inspector = get_celery_app().control.inspect()
        task_stats = task_container.child(html.Pre)

        @app.callback(
                [
                    Output(ticker.id, 'children'),
                    Output(task_stats.id, 'children'),
                    ],
                [
                    Input(timer.id, 'n_intervals')
                    ]
                )
        def update(n_intervals):
            sleep.delay(5)
            return n_intervals, _celery_inspector.active()


env_registry.register(
        "DASHA_EXAMPLE_REDIS_URL", "The url to a redis database.")


dasha_example_redis_url = env_registry.get(
        "DASHA_EXAMPLE_REDIS_URL", 'redis://localhost:6379')

extensions = [
    {
        'module': 'dasha.web.extensions.celery',
        'config': {
            "CELERY_RESULT_BACKEND": f"{dasha_example_redis_url}/1",
            "CELERY_RESULT_EXPIRES": 0,  # second
            "CELERY_BROKER_URL": f"{dasha_example_redis_url}/1",
            }
        },
    {
        'module': 'dasha.web.extensions.dasha',
        'config': {
            'template': CeleryBenchmark,
            'title_text': 'Celery Benchmark',
            }
        },
    ]
