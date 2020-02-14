#! /usr/bin/env python

from ..extensions.db import dataframe_from_db
from ..extensions.celery import get_celery_app
from celery.utils.log import get_task_logger


class SyncedDatabase(object):

    def __init__(
            self,
            label,
            update_interval,  # milliseconds
            bind,
            query_init,
            query_update,
            query_params,
            datastore,
            ):

        self._label = label
        self._period = update_interval * 1e-3
        self._datastore = datastore()

        logger = get_task_logger(self._label)
        logger.setLevel('INFO')
        celery = get_celery_app()

        class TaskBase(celery.QueueOnce):
            _datastore = self._datastore

        @celery.task(
                name=self._task_name,
                base=TaskBase,
                once={'graceful': True})
        def update():
            old = update._datastore.get()
            logger.debug(f'update {update._datastore._label}')
            assert self._label == update._datastore._label
            if old is None:
                new = dataframe_from_db(bind, query_init, **query_params)
                logger.debug(f"init table of {new.shape} query={query_init}")
            else:
                logger.debug(f"the latest entry in old is {old.iloc[0]}")
                query = query_update(old)
                new = dataframe_from_db(bind, query, **query_params)
                logger.debug(
                        f"update table of {old.shape} with "
                        f" query={query} got table of {new.shape}")
                new = new.append(old)
            update._datastore.set(new)

        celery.conf.beat_schedule.update(**{
            f'update_{self._task_name}': {
                'task': self._task_name,
                'schedule': self._period,
                'args': (),
                },
            })

    @property
    def _task_name(self):
        return f"{self.__class__.__name__.lower()}_{self._label}"

    def data(self):
        return self._datastore.get()
