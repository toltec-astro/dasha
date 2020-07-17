#! /usr/bin/env python

from flask_celeryext import FlaskCeleryExt
from wrapt import ObjectProxy
from tollan.utils.registry import Registry
from tollan.utils import getobj
from celery_once import QueueOnce


__all__ = [
        'celery_app', 'register_tasks', 'get_celery_tasks',
        'schedule_task'
        ]


celery_app = ObjectProxy(None)
"""A proxy to the `~celery.Celery` instance."""


_celeryext = ObjectProxy(None)
"""A proxy to the `~flask_celeryext.FlaskCeleryExt` instance."""


def init_ext(config):
    ext = _celeryext.__wrapped__ = FlaskCeleryExt()
    return ext


_celery_task_registry = Registry.create()
"""This keeps a record of celery tasks."""


def register_tasks(obj):
    """Register celery tasks in the registry."""
    _celery_task_registry.register(obj, str(obj))


class Q(object):
    """The default queues."""
    default = 'default'
    high_priority = "high_priority"
    normal_priority = "normal_priority"
    low_priority = "low_priority"


def init_app(server, config):
    server.config.update(config)
    _celeryext.init_app(server)
    # update the proxy object
    celery_app.__wrapped__ = _celeryext.celery
    celery_app.conf.update(
        redbeat_redis_url=config['CELERY_BROKER_URL'],
        beat_scheduler='redbeat.RedBeatScheduler',
        beat_schedule=dict(),
        ONCE={
                'backend': 'celery_once.backends.Redis',
                'settings': {
                    'url': config['CELERY_BROKER_URL'],
                    'default_timeout': 60 * 60  # second
                }
            },
        # and route options
        broker_transport_options={
            'priority_steps': [0, 3, 6, 9],
            'queue_order_strategy': 'priority',
            },
        task_default_priority=6,
        task_default_queue=Q.default,
        task_default_delivery_mode='transient',
        worker_pool_restarts=True,
        )

    class ContextQueueOnce(QueueOnce):
        def __call__(self, *args, **kwargs):
            with server.app_context():
                return super().__call__(*args, **kwargs)

    celery_app.QueueOnce = ContextQueueOnce

    _celery_task_registry.clear()

    # TODO use tollan.utils.namespace
    tasks = config.get('tasks', list())
    for task in tasks:
        type_ = getobj(task["type"])
        register_tasks(
                type_(**{k: v for k, v in task.items() if k != 'type'}))

    post_init_app = config.get('post_init_app', None)
    if post_init_app is not None:
        post_init_app()


def get_celery_tasks():
    modules = list(_celery_task_registry.keys())
    if len(modules) == 1:
        return modules[0]
    return modules


def schedule_task(task, **kwargs):
    if not isinstance(task, str):
        task = task.name
    kwargs.setdefault('task', task)
    kwargs.setdefault('options', {'queue': Q.default})
    celery_app.conf.beat_schedule[f'schedule:{task}'] = kwargs
