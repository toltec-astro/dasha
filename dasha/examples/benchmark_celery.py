#! /usr/bin/env python

"""
This file defines an example site that uses the celery task queue
and the IPC data store.

A running redis db is required as the backend.

To run the task queue:

.. code:: bash

    $ dasha -s dasha.examples.benchmark_celery celery

To run the site:

.. code:: bash

    $ dasha -s dasha.examples.benchmark_celery

"""

from tollan.utils.env import env_registry
from dasha.web.templates import ComponentTemplate
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_core_components as dcc
from dash.dependencies import Output, Input
from dasha.web.extensions.celery import celery_app
from schema import Schema
from tollan.utils.log import get_logger, timeit
import celery
from dasha.web.extensions.ipc import ipc
from tollan.utils.fmt import pformat_yaml


@celery.shared_task
def sleep(t, index):
    import time
    time.sleep(t)


class CeleryBenchmark(ComponentTemplate):

    _component_cls = dbc.Container
    _component_schema = Schema({
        'title_text': str,
        })

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

        ticker_container = body.child(html.Div, className='d-flex')
        ticker_container.child(
                dbc.Label("n_intervals:", className='mr-2'))
        ticker = ticker_container.child(html.Div, 'N/A')

        task_container = body.child(html.Div, className='d-flex')
        task_container.child(
                dbc.Label("n_active_tasks:", className='mr-2'))
        task_n_tasks = task_container.child(html.Div, 'N/A')

        worker_container = body.child(html.Div, className='d-flex')
        worker_container.child(
                dbc.Label("active_workers:", className='mr-2'))
        worker_worker_names = worker_container.child(html.Div, 'N/A')

        _celery_inspector = celery_app.control.inspect()

        timer_container = body.child(html.Div)
        timer = timer_container.child(
                dcc.Interval, interval=1000, max_intervals=0)

        @app.callback(
                [
                    Output(ticker.id, 'children'),
                    Output(task_n_tasks.id, 'children'),
                    Output(worker_worker_names.id, 'children'),
                    Output(timer.id, 'max_intervals'),
                    Output(timer.id, 'interval')
                    ],
                [
                    Input(timer.id, 'n_intervals'),
                    ],
                )
        def update(n_intervals):
            logger = get_logger()
            with timeit(f'update {n_intervals}'):
                sleep.delay(5, index=n_intervals)
            with timeit(f'inspect celery'):
                active = _celery_inspector.active()
                if active is not None:
                    worker = list(active.keys())[0]
                    tasks = active[worker]
                else:
                    worker = []
                    tasks = []
            logger.debug(f"tasks: {tasks}")
            store = ipc.get_or_create('rejson', 'active_info')
            store.set(active)
            return n_intervals, len(tasks), str(worker), \
                (n_intervals or 0) + 1, 100

        timer_for_active_info = body.child(dcc.Interval, interval=1000)
        active_info = body.child(html.Pre)

        @app.callback(
                Output(active_info.id, 'children'),
                [
                    Input(timer_for_active_info.id, 'n_intervals'),
                    ]
                )
        def get_active_info(n_intervals):
            logger = get_logger()
            store = ipc.get_or_create('rejson', 'active_info')
            # get worker
            worker = store('objkeys', '.')[0]
            # obj = store.get(worker)
            # worker contains a dot, so we have to go like this to get
            # the content.
            # this should be fix by providing a special interface
            # on ipc data store.
            # or we should implement handling of this case on
            # json path object.
            worker_path = f'["_ipc_obj"]["{worker}"]'
            obj = store.connection.jsonget(store.redis_key, worker_path)
            logger.debug(f"active_info: {obj}")
            return pformat_yaml(obj)


env_registry.register(
        "DASHA_CELERY_BENCHMARK_REDIS_URL",
        "The url to a redis database.",
        "redis://localhost:6379")


dasha_celery_benchmark_redis_url = env_registry.get(
        "DASHA_CELERY_BENCHMARK_REDIS_URL")

extensions = [
    {
        'module': 'dasha.web.extensions.celery',
        'config': {
            "CELERY_RESULT_BACKEND": f"{dasha_celery_benchmark_redis_url}/1",
            "CELERY_RESULT_EXPIRES": 0,  # second
            "CELERY_BROKER_URL": f"{dasha_celery_benchmark_redis_url}/1",
            }
        },
    {
        'module': 'dasha.web.extensions.ipc',
        'config': {
            'backends': {
                'rejson': {
                    'url': f'{dasha_celery_benchmark_redis_url}/2'
                    }
                }
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
