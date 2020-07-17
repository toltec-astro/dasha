#! /usr/bin/env python

from flask_apscheduler import APScheduler
from wrapt import ObjectProxy


__all__ = ['apscheduler', ]


apscheduler = ObjectProxy(None)
"""A proxy to the `~flask_apscheduler.APScheduler` instance."""


def init_ext(config):
    ext = apscheduler.__wrapped__ = APScheduler()
    return ext


def init_app(server, config):
    server.config.update(config)
    apscheduler.init_app(server)
