#! /usr/bin/env python

from .. import site_from_env
from ..utils.log import get_logger
from ..utils.fmt import pformat_dict


__all__ = ['site', 'create_app']


site = site_from_env()


def create_app():

    logger = get_logger()

    from . import config

    if hasattr(site, 'create_server'):
        server = site.create_server(config)
    else:
        import flask
        server = flask.Flask(__package__)
        server.config.from_object(config)
        server.config.from_object(site)
        from ..utils.click_log import init as init_log
        init_log(level='DEBUG' if server.debug else 'INFO')

    if hasattr(site, 'backend'):
        site.backend.init_app(server)
    else:
        from . import backend
        backend.init_app(server)

    if hasattr(site, 'frontend'):
        site.frontend.init_app(server)
    else:
        from . import frontend
        frontend.init_app(server)

    logger.debug(f"flask config:\n{pformat_dict(server.config)}")
    return server
