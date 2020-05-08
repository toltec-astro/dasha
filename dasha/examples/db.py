#! /usr/bin/env python

"""
This file defines an example site that make uses of the db extension.
"""

from dasha.web.templates import ComponentTemplate
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_core_components as dcc
from dash.dependencies import Output, Input
from schema import Schema
from tollan.utils.log import timeit, get_logger
from tollan.utils.fmt import pformat_yaml
from dash_table import DataTable
from dasha.web.extensions.db import (
        dataframe_from_db, get_db_engine, create_db_session, db)
from sqlalchemy import Table, Column, Integer, String, select


def create_tables(db):
    logger = get_logger()

    tables = []

    from tollan.utils.db import convensions as c

    def qualified(name):
        return name

    def tbl(name, *args):
        return Table(qualified(name), db.metadata, *args)

    tables.extend([
        tbl(
                "my_table",
                c.pk(),
                Column('value', Integer),
                Column('info', String),
                c.created_at(),
                c.updated_at(),
                c.client_info(),
            ),
        c.tbl_client_info(db)
        ])
    engine = get_db_engine(bind='default')
    try:
        db.metadata.create_all(engine)
    except Exception as e:
        raise RuntimeError(f"unable to create tables: {e}")
    db.metadata.reflect(bind=engine)
    logger.debug(f"all tables: {pformat_yaml(db.metadata.tables)}")
    # insert some data
    ins_client_info = db.metadata.tables['client_info'].insert()
    client_pk = engine.execute(ins_client_info).inserted_primary_key[0]
    ins = db.metadata.tables['my_table'].insert().values(
            value=None, info=None, client_info_pk=client_pk)
    engine.execute(
            ins,
            [
                {
                    'value': i,
                    'info': f'[item {i}](https://github.com/toltec-astro)',
                    # 'client_info': client_pk
                    }
                for i in range(10)
                ]
            )


class DBExample(ComponentTemplate):

    _component_cls = dbc.Container
    _component_schema = Schema({
        'title_text': str,
        })

    def setup_layout(self, app):
        title = self.title_text

        header = self.child(dbc.Row).child(dbc.Col).child(dbc.Jumbotron)
        body = self.child(dbc.Row).child(dbc.Col)

        header.children = [
                html.H1(f'{title}'),
                html.P(
                    'This page views a in-memory database.')
                ]

        ticker_container = body.child(html.Div, className='d-flex')
        ticker_container.child(
                dbc.Label("n_intervals:", className='mr-2'))
        ticker = ticker_container.child(html.Div, 'N/A')

        timer = body.child(
                dcc.Interval, interval=1000)

        session = create_db_session(bind='default')

        # get column names
        colnames = [
            c.name
            for c in db.metadata.tables['my_table'].columns
            if c.name not in ['client_info_pk']
            ] + ['hostname', ]
        # build query
        my_table = db.metadata.tables['my_table']
        client_info = db.metadata.tables['client_info']
        j = my_table.join(
                select([client_info.c.pk, client_info.c.hostname]),
                my_table.c.client_info_pk == client_info.c.pk)

        def is_pk(c):
            return (c.name == 'pk') or (c.name.endswith('_pk'))
        stmt = select([col for col in j.columns if not is_pk(col)])

        extra_column_kwargs = {
                'info': {
                    'presentation': 'markdown'
                    }
                }

        tbl = body.child(
                DataTable,
                columns=[
                        dict(
                            {"name": c, "id": c},
                            **extra_column_kwargs.get(c, dict())
                            )
                        for c in colnames
                        ],
                style_cell={
                    'textAlign': 'left',
                    },
                css=[{
                    # this is needed to make the markdown <p> vertically
                    # centered.
                    'selector': '.cell-markdown p',
                    'rule': '''
                        margin: 0.5rem 0
                    '''
                    }],
                )

        @app.callback(
                [
                    Output(tbl.id, 'data'),
                    Output(ticker.id, 'children'),
                    ],
                [
                    Input(timer.id, 'n_intervals'),
                    ],
                prevent_initial_call=True,
                )
        def get_data(n_intervals):
            logger = get_logger()
            engine = get_db_engine(bind='default')
            logger.debug(f"all tables: {engine.table_names()}")
            with timeit(f'get from session {session}'):
                df = dataframe_from_db(stmt, session=session)
                logger.debug(f"data:\n{df}")
            return df.to_dict('record'), n_intervals or '0'


extensions = [
    {
        'module': 'dasha.web.extensions.db',
        'config': {
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "SQLALCHEMY_BINDS": {
                'default': f"sqlite:///:memory:",
                },
            'post_init_app': create_tables,
            }
        },
    {
        'module': 'dasha.web.extensions.dasha',
        'config': {
            'template': DBExample,
            'title_text': 'DB Example',
            }
        },
    ]
