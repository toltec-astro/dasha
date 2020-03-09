#! /usr/bin/env python

"""A celery extension."""

# import flask
from flask_celeryext import FlaskCeleryExt
import sys
from . import ExtensionProxy
from tollan.utils.registry import Registry
from tollan.utils import object_from_spec
from celery_once import QueueOnce


celeryext = ExtensionProxy(FlaskCeleryExt, sys.modules[__name__])

config = {}


def init(cls):
    return cls()


_celery_task_registry = Registry.create()


def register_tasks(obj):
    _celery_task_registry.register(obj, str(obj))


def init_app(server):
    ext = celeryext._extension
    server.config.update(ext.config)
    celeryext.init_app(server)

    celery = get_celery_app()
    celery.conf.update(
        redbeat_redis_url=ext.config['CELERY_BROKER_URL'],
        beat_scheduler='redbeat.RedBeatScheduler',
        beat_schedule=dict(),
        ONCE={
                'backend': 'celery_once.backends.Redis',
                'settings': {
                    'url': ext.config['CELERY_BROKER_URL'],
                    'default_timeout': 60 * 60  # second
                }
            }
        )

    class ContextQueueOnce(QueueOnce):
        def __call__(self, *args, **kwargs):
            with server.app_context():
                return super().__call__(*args, **kwargs)

    celery.QueueOnce = ContextQueueOnce

    _celery_task_registry.clear()

    tasks = ext.config.get('tasks', list())
    for task in tasks:
        type_ = object_from_spec(task["type"])
        register_tasks(
                type_(**{k: v for k, v in task.items() if k != 'type'}))

    post_init_app = ext.config.get('post_init_app', None)
    if post_init_app is not None:
        post_init_app()


def get_celery_app():
    return celeryext.celery


def get_celery_tasks():
    modules = list(_celery_task_registry.keys())
    if len(modules) == 1:
        return modules[0]
    return modules


def schedule_task(task, **kwargs):
    if not isinstance(task, str):
        task = task.name
    kwargs.setdefault('task', task)
    celery = get_celery_app()
    celery.conf.beat_schedule[f'update_{task}'] = kwargs
