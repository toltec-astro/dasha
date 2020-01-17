#! /usr/bin/env python

"""A db extension."""

import flask
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
from . import ExtensionProxy
import sys


db = ExtensionProxy(SQLAlchemy, sys.modules[__name__])


config = {
        "SQLALCHEMY_TRACK_MODIFICATIONS", False
        }


def init(cls):
    return cls()


def init_app(server):

    server.config.update(config)
    db.init_app(server)

    @server.teardown_appcontext
    def shutdown_db_session(exception=None):
        db.session.remove()


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
