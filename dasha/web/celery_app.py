#! /usr/bin/env python

"""Celery entry point."""

from dasha.web import site
from tollan.utils.log import timeit, logit, get_logger
from dasha.web.extensions.celery import get_celery_app


# celery is special as the works will need to run on the server context.
@timeit
def create_celery():
    logger = get_logger()
    server = site.get_server()
    for ext in site.get_extentions():
        if ext.__name__.endswith('dasha'):
            continue
        with logit(logger.debug, f"init app extension {ext.__name__}"):
            ext.init_app(server)

    return get_celery_app()


celery = create_celery()
