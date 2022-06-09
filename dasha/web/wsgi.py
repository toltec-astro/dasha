from .app import create_app
import logging
from werkzeug.middleware.proxy_fix import ProxyFix

"""WSGI entry point."""

application = create_app()
application.wsgi_app = ProxyFix(application.wsgi_app, x_proto=1, x_host=1)


if __name__ != "__main__":
    # propagate to gunicorn logger
    gunicorn_logger = logging.getLogger('gunicorn.error')
    application.logger.handlers = gunicorn_logger.handlers
    application.logger.setLevel(gunicorn_logger.level)
