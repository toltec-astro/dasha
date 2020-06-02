from .app import create_app
import logging
from dozer import Dozer

"""WSGI entry point."""

application = Dozer(create_app())


if __name__ != "__main__":
    pass
    # propagate to gunicorn logger
    # gunicorn_logger = logging.getLogger('gunicorn.error')
    # application.logger.handlers = gunicorn_logger.handlers
    # application.logger.setLevel(gunicorn_logger.level)
