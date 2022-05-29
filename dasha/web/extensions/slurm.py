#! /usr/bin/env python

from wrapt import ObjectProxy
import requests
from urllib.parse import urljoin
import functools
import pandas as pd
from pathlib import Path
from io import StringIO
from fabric import Connection

__all__ = [
        'slurm_api',
        ]


slurm_api = ObjectProxy(None)
"""A proxy to the `SlurmAPI` instance."""


class SlurmAPI(object):
    """A base class that defines a common interface for SLURM integration."""
    
    pass


class SlurmRestAPI(SlurmAPI):
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
        return NotImplemented


class SlurmOnSSH(object):
    """A class to interact with SLURM using SSH"""

    def __init__(self, remote_host, partition=None, chdir=None):
        self._remote_host = remote_host
        self._partition = partition
        self._chdir = Path(chdir) if chdir is not None else None
    
    @functools.lru_cache(maxsize=10)
    def get_or_create_connection(self, key=None):
        conn = Connection(self._remote_host)
        return conn
    
    def get_hostname(self):
        conn = self.get_or_create_connection()
        return conn.run('hostname')
    
    def get_info(self):
        conn = self.get_or_create_connection()       
        partition = self._partition
        cmd = 'sinfo -N -o %all'
        if partition is not None:
            cmd += f' -p {partition}'
        result = conn.run(cmd)
        stdout = result.stdout
        # load the table as csv
        df = pd.read_csv(StringIO(stdout), sep='|')
        return df

    def get_job_list(self):
        conn = self.get_or_create_connection()       
        username = conn.user
        cmd = f'squeue -u {username} -o %all'
        result = conn.run(cmd)
        stdout = result.stdout
        # load the table as csv
        df = pd.read_csv(StringIO(stdout), sep='|')
        return df

    def get_job_info(self, job_id):
        conn = self.get_or_create_connection()       
        cmd = f'sacct --parsable -o %all -j {job_id}'
        result = conn.run(cmd)
        stdout = result.stdout
        # load the table as csv
        df = pd.read_csv(StringIO(stdout), sep='|')
        return df

    def run_sbatch(self, script, conn_key='sbatch'):
        conn = self.get_or_create_connection(key=conn_key)       
        stdin = StringIO(script)
        chdir = self._chdir
        cmd = f'sbatch'
        if chdir is not None:
            cmd += f' --chdir={chdir}'
        partition = self._partition
        if partition is not None:
            cmd += f' --parition={partition}'
        result = conn.run(cmd, in_stream=stdin)
        job_id = result.stdout.strip('\n').strip()
        return job_id
        
    def get_sbatch_live_output(
            self, job_id, n_lines=10, conn_key='sbatch_live_output'):
        chdir = self._chdir or '.'
        conn = self.get_or_create_connection(key=conn_key)              
        try:
            result = conn.run(
                f"find {chdir} -maxdepth 1 -name '{job_id}-*.out'")
        except Exception as e:
            raise ValueError(f"unable to find output for job_id={job_id}: {e}")
        if not result.ok:
            raise ValueError("No sbatch output file found for job_id={job_id}")
        # TODO revisit this assumption
        filepath = result.stdout.strip('\n').split("\n")[-1]
        result = conn.run(f"tail -n {n_lines} {filepath}")
        return result.stdout


def _get_api_cls(api_type):
    d = {
        'rest': SlurmRestAPI,
        'ssh': SlurmOnSSH,
        }
    if api_type in d:
        return d.get(api_type)
    raise ValueError(f"unsupported api type: {api_type}")


def init_ext(config):
    config = config.copy()
    api_type = config.pop('api_type')
    api_cls = _get_api_cls(api_type)
    ext = slurm_api.__wrapped__ = api_cls(**config)
    return ext


def init_app(server, config):
    """Setup `~dasha.web.extensions.slurm.slurm_api` for `server`.
    
    """
    pass