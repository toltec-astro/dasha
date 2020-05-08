#! /usr/bin/env python

"""Celery entry point."""

from dasha.web import create_site
from tollan.utils.log import timeit, get_logger
from dasha.web.extensions.celery import celery_app
from tollan.utils.fmt import pformat_yaml


# celery is special as the workers has to run on the server context.
# we purposefully avoid define tasks with the dasha context
# so that we can skip init the dasha extension.
@timeit
def create_celery():
    logger = get_logger()

    site = create_site()
    site.extensions = list(filter(
            lambda ext: not ext.module.__name__.endswith('dasha'),
            site.extensions
            ))

    logger.info(f"init celery site:\n{pformat_yaml(site.to_dict())}")

    site.init_app()

    return celery_app


create_celery()
