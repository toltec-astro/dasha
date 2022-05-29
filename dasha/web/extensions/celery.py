#! /usr/bin/env python

from flask_celeryext import FlaskCeleryExt
from wrapt import ObjectProxy
from celery_once import QueueOnce

from copy import deepcopy

from tollan.utils.log import get_logger
from tollan.utils.fmt import pformat_yaml


__all__ = [
        'celery_app',
        'Q',
        'schedule_task',
        ]


celery_app = ObjectProxy(None)
"""A proxy to the `~celery.Celery` instance."""


_flask_celery_ext = ObjectProxy(None)
"""A proxy to the `~flask_celeryext.FlaskCeleryExt` instance."""


def init_ext(config):
    ext = _flask_celery_ext.__wrapped__ = FlaskCeleryExt()
    return ext


class Q(object):
    """The predefined queue names."""
    default = 'default'
    high_priority = "high_priority"
    normal_priority = "normal_priority"
    low_priority = "low_priority"


def init_app(server, config):
    """Setup `~dasha.web.extensions.celery.celery_app` for `server`.
    
    """
    logger = get_logger()

    # extract all upper case entries and update with the new settings
    # make a copy because we will modify it.
    flask_config = {k: deepcopy(v) for k, v in config.items() if k.isupper()}
    logger.debug(f"update server config:\n{pformat_yaml(flask_config)}")
    server.config.update(flask_config)
    _flask_celery_ext.init_app(server)

    # update the proxy object
    celery_app.__wrapped__ = _flask_celery_ext.celery
    celery_app.conf.update(
        redbeat_redis_url=config['CELERY_BROKER_URL'],
        beat_scheduler='redbeat.RedBeatScheduler',
        beat_schedule=dict(),
        ONCE={
                'backend': 'celery_once.backends.Redis',
                'settings': {
                    'url': config['CELERY_BROKER_URL'],
                    'default_timeout': 10 * 60  # second
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

    post_init_app = config.get('post_init_app', None)
    if post_init_app is not None:
        with server.app_context():
            post_init_app()


def schedule_task(task, **kwargs):
    if not isinstance(task, str):
        task = task.name
    kwargs.setdefault('task', task)
    kwargs.setdefault('options', {'queue': Q.default})
    celery_app.conf.beat_schedule[f'schedule:{task}'] = kwargs