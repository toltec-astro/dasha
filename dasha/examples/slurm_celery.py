#!/usr/bin/env python


"""
This file defines an example site to demonstrate submitting jobs to SLURM
through Celery.
"""

from dash_component_template import ComponentTemplate
from dash import html, dcc, Output, Input
from dash.dash_table import DataTable
import dash_bootstrap_components as dbc

from tollan.utils.log import timeit, get_logger
from tollan.utils.fmt import pformat_yaml
from dasha.web.extensions.celery import celery_app
import celery

import os
import functools
import requests
from urllib.parse import urljoin

import yaml
from fabric import Connection
import pandas as pd

from dasha.web.templates.common import (
        LabeledDropdown, LabeledChecklist,
        LabeledInput,
        CollapseContent,
        LiveUpdateSection
    )


class SlurmRestAPI(object):
    """A class to interact with SLURM rest api"""

    def __init__(self, base_url, username, token):
        self._base_url = base_url
        self._username = username
        self._token = token
        
    def _make_auth_header(self):
        return {
            'X-SLURM-USER-NAME': self._username,
            'X-SLURM-USER-TOKEN': self._token
            }

    def _make_url(self, endpoint):
        return urljoin(self._base_url, endpoint)

    def get_request(self, endpoint, params=None):
        """Make a GET request.

        Parameters
        ----------
        endpoint : str
            API endpoint.
        params : dict
            Dictionary of parameters to be passed with the request.
            Defaults to `None`.

        Returns
        -------
        class:`requests.Response`
            Response object of requests library.
        """
        params = params or {}
        headers = self._make_auth_header()
        url = self._make_url(endpoint)
        try:
            resp = requests.get(url, params=params, headers=headers)
            if resp.status_code >= 300:
                if resp.text:
                    error_msg = resp.text
                    raise RuntimeError(
                        "ERROR: GET HTTP {0} - {1}. MSG: {2}".format(
                            resp.status_code, url, error_msg
                        )
                    )
            return resp
        except ConnectionError:
            raise ConnectionError(
                f"ERROR: GET - Could not establish connection to api {url}."
            )

    def post_request(self, endpoint, data=None, params=None, files=None):
        """Make a POST request.

        params will be added as key-value pairs to the URL.

        Parameters
        ----------
        endpoint : str
            API endpiont.
        data : str
            Metadata as a json-formatted string. Defaults to `None`.
        params : dict
            Dictionary of parameters to be passed with the request.
            Defaults to `None`.
        files: dict
            e. g. files = {'file': open('sample_file.txt','rb')}

        Returns
        -------
        requests.Response
            Response object of requests library.
        """
        params = params or {}
        headers = self._make_auth_header()
        url = self._make_url(endpoint)
        try:
            resp = requests.post(
                url, data=data, params=params, files=files, headers=headers)
            if resp.status_code >= 300:
                if resp.text:
                    error_msg = resp.text
                    raise RuntimeError(
                        "ERROR: POST HTTP {0} - {1}. MSG: {2}".format(
                            resp.status_code, url, error_msg
                        )
                    )
            return resp
        except ConnectionError:
            raise ConnectionError(
                f"ERROR: POST - Could not establish connection to API: {url}"
            )

    def get_job_list(self):
        df = pd.DataFrame()
        df['jobid'] = [1, 2]
        df['cmdline'] = ['hostname', 'whoami']
        return df

        
@functools.lru_cache(maxsize=1)
def get_slurm_rest_api():
    base_url = os.environ['SLURM_BASE_URL']
    username = os.environ['SLURM_USERNAME']
    token = os.environ['SLURM_TOKEN']
    return SlurmRestAPI(base_url=base_url, username=username, token=token)


@celery.shared_task
def slurm_job_runner(job_config):
    slurm_rest_api = get_slurm_rest_api()
    resp = slurm_rest_api.run_cmd(['hostname'], stdout='')
    print(resp)
    return


class SlurmOnSSH(object):
    def __init__(self, remote_host):
        self._remote_host = remote_host
    
    @functools.lru_cache(maxsize=1)
    def get_or_create_connection(self):
        conn = Connection(self._remote_host)
        return conn
    
    def get_hostname(self):
        conn = self.get_or_create_connection()
        return conn.run(['hostname'])
    
    def get_job_list(self):
        conn = self.get_or_create_connection()       
        return conn.run(['squeue' '-u' '${USERNAME}'])

    @classmethod
    def from_config_file(cls, config_file):
        with open(config_file) as fo:
            config = yaml.load(fo)
        kwargs = config.get("slurm_on_ssh")
        return cls(**kwargs)

    
@functools.lru_cache(maxsize=1)
def get_slurm_on_ssh():
    slurm_remote_host = os.environ['SLURM_REMOTE_HOST']
    return SlurmOnSSH(remote_host=slurm_remote_host)


class SlurmJobViewComponent(ComponentTemplate):

    class Meta:
        component_cls = dbc.Container

    def __init__(self, title_component=None, **kwargs):
        super().__init__(**kwargs)
        self._title_component = title_component or html.H3("Slurm Job View")
        
    def setup_layout(self, app):
        container = self
        header_container, body = container.grid(2, 1)

        header = header_container.child(
                LiveUpdateSection(
                    title_component=self._title_component,
                    interval_options=[2000, 5000, 10000],
                    interval_option_value=2000
                    ))

        view_container = body.child(html.Div)
        job_list_dt = view_container.child(
            DataTable,
            )
        
        super().setup_layout(app)
        
        @app.callback(
                [
                    Output(job_list_dt.id, 'data'),
                    Output(job_list_dt.id, 'columns'),
                    ],
                header.timer.inputs 
                )
        def update_view(n_calls):
            slurm_on_ssh = get_slurm_on_ssh()
            job_list_df = slurm_on_ssh.get_job_list()
            return [
                job_list_df.to_dict(orient="records"),
                [{'name': c, 'id': c} for c in job_list_df.columns]
                ]
 

def make_celery_ext_config():
    celery_redis_url = os.environ['CELERY_REDIS_URL']
    return {
        "CELERY_RESULT_BACKEND": f"{celery_redis_url}/1",
        "CELERY_RESULT_EXPIRES": 0,  # second
        "CELERY_BROKER_URL": f"{celery_redis_url}/1",
        }


DASHA_SITE = {
    'extensions': [
        {
            'module': 'dasha.web.extensions.celery',
            'config': make_celery_ext_config(),
            },
        {
            'module': 'dasha.web.extensions.dasha',
            'config': {
                'template': SlurmJobViewComponent,
                }
            },
        ],
    }
