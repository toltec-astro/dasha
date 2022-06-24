#! /usr/bin/env python

import flask
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
from wrapt import ObjectProxy
from tollan.utils.log import get_logger
from tollan.utils.fmt import pformat_yaml
from collections import UserDict
from copy import deepcopy
from sqlalchemy import MetaData
from tollan.utils.db import SqlaDB
from tollan.utils.registry import Registry, register_to
import cachetools.func


__all__ = [
        'db', 'get_db_engine', 'create_db_session', 'dataframe_from_db',
        'DatabaseRuntime']


db = ObjectProxy(None)
"""A proxy to the `~flask_sqlalchemy.SQLAlchemy` instance."""


def init_ext(config):
    ext = db.__wrapped__ = SQLAlchemy()
    return ext


def init_app(server, config):
    """Setup `~dasha.web.extensions.db.db` for `server`.

    A default bind named "default" is enforced in the config.

    `ValueError` is raised if "default" is defined in ``SQLALCHEMY_BINDS``
    and ``SQLALCHEMY_DATABASE_URI`` is defined differently.

    """
    logger = get_logger()
    server.config.update(
        SQLALCHEMY_TRACK_MODIFICATIONS=False)

    # extract all upper case entries and update with the new settings
    # make a copy because we will modify it.
    flask_config = {k: deepcopy(v) for k, v in config.items() if k.isupper()}

    db_url = flask_config.get('SQLALCHEMY_DATABASE_URI', None)
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
    flask_config['SQLALCHEMY_DATABASE_URI'] = db_url
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
            'Date', 'DateTime' 'created_at', 'updated_at'
            ] + kwargs.pop('parse_dates', list())
    return pd.read_sql_query(
            query,
            # con=session.get_bind(),
            con=session.bind,
            parse_dates=parse_dates,
            **kwargs
            )


_sqladb_setup_funcs = Registry.create()
"""A registry to hold pre-defined SQLA database setup functions.
"""


@register_to(_sqladb_setup_funcs, 'reflect_tables')
def _sqladb_setup_func_refect_tables(d):
    return d.reflect_tables()


class DatabaseRuntime(UserDict):
    """A helper class to manage databases.

    Parameters
    ----------
    binds : list, optional
        The list of binds to manage. If None, it will include all the
        binds specified in the ``SQLALCHEMY_BINDS`` environment variable.
    binds_required : list, optional
        The list of binds required. If any is missing, `RuntimeError`
        is raised. Default is to ignore.
    setup_funcs : list, optional
        The list of functions to finish the setup of each DB instance.
        If None, it will be ``reflect_tables`` for all the binds.
    """

    logger = get_logger()

    def __init__(self, binds=None, binds_required=None, setup_funcs=None):
        if binds is None:
            from flask import current_app
            binds = current_app.config['SQLALCHEMY_BINDS'].keys()
        if binds_required is None:
            binds_required = []
        # resolve the setup funcs
        if setup_funcs is None:
            setup_funcs = {b: 'reflect_tables' for b in binds}
        # check and resolve the strings in setup_funcs
        _setup_funcs = dict()
        for b, f in setup_funcs.items():
            if isinstance(f, str):
                if f in _sqladb_setup_funcs:
                    _setup_funcs[b] = _sqladb_setup_funcs[f]
                else:
                    raise ValueError(
                            f"unknown setup function {f} for bind={b}")
            elif callable(f):
                _setup_funcs[b] = f
            else:
                raise ValueError(
                    f"invalid setup function for bind={b}: "
                    f"callable or one of {list(_sqladb_setup_funcs.keys())} "
                    f"is expected.")

        self._binds = binds
        self._binds_required = binds_required
        self._setup_funcs = _setup_funcs

        # create the dbs
        sqladbs = dict()
        for bind in binds:
            sqladbs[bind] = self._get_sqladb(
                    bind,
                    raise_on_error=bind in binds_required
                    )
        super().__init__(sqladbs)

        # run the setup for all binds
        for b in self:
            self._setup_sqladb(b)

    def _setup_sqladb(self, bind):
        sqladb = self[bind]
        setup_func = self._setup_funcs.get(bind, None)
        if setup_func is not None:
            try:
                setup_func(sqladb)
            except Exception as e:
                self.logger.error(
                        f"unable to setup db {sqladb}: {e}",
                        exc_info=True)
                if bind in self._binds_required:
                    raise
        return sqladb

    @classmethod
    def _get_sqladb(cls, bind, raise_on_error=True):
        try:
            result = SqlaDB.from_flask_sqla(db, bind=bind)
        except Exception as e:
            cls.logger.error(
                    f"unable to connect to db bind={bind}: {e}",
                    exc_info=True)
            if raise_on_error:
                raise
            else:
                result = None
        return result

    @cachetools.func.ttl_cache(ttl=1)
    def ensure_connection(self, bind):
        try:
            with self[bind].session_context as session:
                session.execute('SELECT 1')
        except Exception as e:
            self.logger.debug(f"reconnect db {bind}: {e}")
            # this seems to be needed otherwise it will overflow the conn
            # pool of SQLA.
            # TODO revisit this
            session.close()
            self._setup_sqladb(bind)

    def __key(self):
        return tuple(self.keys())

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__key() == other.__key()
        return NotImplemented
