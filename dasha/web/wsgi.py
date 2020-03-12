from .app import create_app
import logging

"""WSGI entry point."""

application = create_app()


if __name__ != "__main__":
    # propagate to gunicorn logger
    gunicorn_logger = logging.getLogger('gunicorn.error')
    application.logger.handlers = gunicorn_logger.handlers
    application.logger.setLevel(gunicorn_logger.level)
