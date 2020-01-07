#! /usr/bin/env python

from . import cache_config
from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from flask_migrate import Migrate
import pandas as pd
import flask
# from .misc.jwt import setup_jwt

from .. import site


setup_db = getattr(site, 'setup_db', None)
Base = getattr(site, 'db_Base', None)


# extensions
if Base is None:
    db = SQLAlchemy()
else:
    db = SQLAlchemy(model_class=Base, metadata=Base.metadata)

migrate = Migrate()
cache = Cache()


def init_app(server):

    migrate.init_app(server, db)

    server.config.from_object(cache_config)
    cache.init_app(server, config=server.config)

    if setup_db is not None:
        setup_db(server, db)
    else:
        db.init_app(server)

    @server.teardown_appcontext
    def shutdown_db_session(exception=None):
        db.session.remove()

    @server.before_first_request
    def setup():
        pass
        # setup_jwt(server, db.session)

    return server


def create_db_session(bind, server=None):
    if server is None:
        server = flask.current_app
    return db.create_scoped_session(
        options={'bind': db.get_engine(server, bind)})


def dataframe_from_db(bind, query, **kwargs):
    """Return dataframe from database."""
    session = create_db_session(bind)

    return pd.read_sql_query(
            query,
            con=session.bind,
            parse_dates=['Date'],
            )
