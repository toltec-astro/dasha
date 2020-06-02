#! /usr/bin/env python

import flask
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
from wrapt import ObjectProxy
from tollan.utils.log import get_logger
from tollan.utils.fmt import pformat_yaml
from copy import deepcopy
from sqlalchemy import MetaData


__all__ = ['db', 'get_db_engine', 'create_db_session', 'dataframe_from_db', ]


db = ObjectProxy(None)
"""A proxy to the `~flask_sqlalchemy.SQLAlchemy` instance."""


def init_ext(config):
    ext = db.__wrapped__ = SQLAlchemy()
    return ext


def init_app(server, config):
    """Setup `~dasha.webe.xtensions.db.db` for `server`.

    A default bind named "default" is enforced in the config.

    `ValueError` is raised if "default" is defined in ``SQLALCHEMY_BINDS``
    and ``SQLALCHEMY_DATABASE_URL`` is defined differently.

    """
    logger = get_logger()
    server.config.update(
        SQLALCHEMY_TRACK_MODIFICATIONS=False)

    # extract all upper case entries and update with the new settings
    # make a copy because we will modify it.
    flask_config = {k: deepcopy(v) for k, v in config.items() if k.isupper()}

    db_url = flask_config.get('SQLALCHEMY_DATABASE_URL', None)
    db_binds = flask_config.get('SQLALCHEMY_BINDS', dict())
    if db_url is None and len(db_binds) == 0:
        raise ValueError('no database is defined.')
    if 'default' not in db_binds:
        if db_url is None:
            k, v = next(iter(db_binds.items()))
            logger.warning(
                f"no default defined in SQLALCHEMY_BINDS,"
                f" use {k} as default.")
            db_binds['default'] = v
        else:
            # bind default as the db_url
            db_binds['default'] = db_url

    if db_url is None:
        # use default bind
        db_url = db_binds['default']
    flask_config['SQLALCHEMY_DATABASE_URL'] = db_url
    flask_config['SQLALCHEMY_BINDS'] = db_binds
    logger.debug(f"update server config:\n{pformat_yaml(flask_config)}")
    server.config.update(flask_config)
    db.init_app(server)

    @server.teardown_appcontext
    def shutdown_db_session(exception=None):
        db.session.remove()

    post_init_app = config.get('post_init_app', None)
    if post_init_app is not None:
        with server.app_context():
            post_init_app()


def get_db_engine(bind, server=None):
    """Return the database engine for `bind`."""
    if server is None:
        server = flask.current_app
    return db.get_engine(server, bind)


def get_db_metadata(bind, server=None):
    """Return the database metadata for `bind`."""
    metadata = MetaData()
    metadata.reflect(bind=get_db_engine(bind, server))
    return metadata


def create_db_session(bind, server=None):
    """Return a database session for `bind`."""
    if server is None:
        server = flask.current_app
    return db.create_scoped_session(
        options={'bind': db.get_engine(server, bind)})


def dataframe_from_db(query, bind=None, session=None, **kwargs):
    """Return dataframe from database query.

    One and only one of `bind` or `session` should be present.

    Parameters
    ----------
    bind : str
        The database bind.
    session : `~sqlalchemy.orm.scoping.scoped_session`
        The database session.

    Returns
    -------
    `~pandas.DataFrame`
        The query result.
    """
    if bind is None and session is None:
        raise ValueError('one of bind or session should be set.')
    if bind is not None and session is not None:
        raise ValueError("only one of bind or session should be set.")
    if bind is not None:
        session = create_db_session(bind)
    # session is not None

    parse_dates = [
            'Date', 'created_at', 'updated_at'
            ] + kwargs.pop('parse_dates', list())
    return pd.read_sql_query(
            query,
            con=session.bind,
            parse_dates=parse_dates,
            **kwargs
            )
