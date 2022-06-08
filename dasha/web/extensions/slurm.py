#! /usr/bin/env python

from wrapt import ObjectProxy
import requests
from urllib.parse import urljoin
import functools
import pandas as pd
from pathlib import Path
from io import StringIO
from fabric import Connection
import uuid

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
        self._chdir = chdir

    def create_connection(self, open=True):
        """Return a new connection to the remote."""
        conn = Connection(self._remote_host)
        if open:
            conn.open()
        return conn

    @functools.lru_cache(maxsize=None)
    def get_or_create_connection(self, key=None):
        """Return a connection to the remote, cached using `key`."""
        # the key is required to manage the connection cache
        # so that different functions are getting a unique connection
        # cached by the _conn_key argument
        # this is to work around the issue with calling the function in
        # multithread that makes the connection unhappy.
        return self.create_connection(open=True)

    @functools.lru_cache(maxsize=None)
    def _get_or_create_chdir(self, _conn_key='_get_or_create_chdir'):
        """Return a working directory for the jobs."""
        chdir = self._chdir
        if chdir is None:
            # this resolves to the home directory on the remote
            return '.'
        conn = self.get_or_create_connection(key=_conn_key)
        check_dir_exists = conn.run(f"test -d {chdir}", warn=True, hide=True)
        if check_dir_exists.ok:
            return chdir
        create_dir = conn.run(f"mkdir -p {chdir}", warn=True, hide=True)
        if create_dir.ok:
            return chdir
        raise ValueError(f'unable to locate chdir on the remote: {chdir}')

    def _find_chdir_files(
            self, pattern, _conn_key='find_job_output_files'):
        chdir = self._get_or_create_chdir(_conn_key=_conn_key)
        conn = self.get_or_create_connection(key=_conn_key)
        result = conn.run(
            f"find {chdir} -maxdepth 1 -name '{pattern}'",
            warn=True, hide=True)
        if not result.ok:
            raise ValueError(f"No sbatch output files found in chdir {chdir}")
        filepaths = result.stdout.strip('\n').split("\n")
        return filepaths

    def get_cluster_info(self, _conn_key='get_cluster_info'):
        """Return the cluster info table."""
        conn = self.get_or_create_connection(key=_conn_key)
        partition = self._partition
        cmd = 'sinfo -N -o %all'
        if partition is not None:
            cmd += f' -p {partition}'
        result = conn.run(cmd, hide=True)
        stdout = result.stdout
        # load the table as csv
        df = pd.read_csv(StringIO(stdout), sep='|')
        return df

    def get_queue_info(self, _conn_key='get_queue_info'):
        """Return the queue info table."""
        conn = self.get_or_create_connection(key=_conn_key)
        cmd = 'squeue --me -o %all'
        result = conn.run(cmd, hide=True)
        stdout = result.stdout
        # load the table as csv
        df = pd.read_csv(StringIO(stdout), sep='|')
        return df

    def get_job_info(self, job_id, show_steps=True, _conn_key='get_job_info'):
        """Return the job info table."""
        conn = self.get_or_create_connection(key=_conn_key)
        cmd = f'sacct --parsable -o %all -j {job_id}'
        if not show_steps:
            cmd += '-X'
        result = conn.run(cmd, hide=True)
        stdout = result.stdout
        # load the table as csv
        df = pd.read_csv(StringIO(stdout), sep='|')
        if show_steps:
            return df
        # return the record for the job as dict
        return next(iter(df.to_records()))

    def run_sbatch(self, script, job_name=None, _conn_key='run_sbatch'):
        """Run sbatch with `script`."""
        # the stdin may get stuck for some reason.
        # we invalidate the cache every time to alwasys create a new
        # connection
        chdir = self._get_or_create_chdir(_conn_key=_conn_key)
        stdin = StringIO(script)
        job_name = job_name or f'job_{uuid.uuid1()}'
        cmd = f'sbatch -J {job_name}'
        if chdir is not None:
            cmd += f' --chdir={chdir}'
        partition = self._partition
        if partition is not None:
            cmd += f' --partition={partition}'
        conn = self.get_or_create_connection(key=_conn_key)
        result = conn.run(cmd, in_stream=stdin, hide=True)
        job_id = int(result.stdout.strip('\n').strip())
        return job_id

    def get_sbatch_job_output(
            self, job_id, n_lines=10,
            _conn_key='get_sbatch_job_output'):
        """Return the output content of job created with `run_sbatch`."""
        conn = self.get_or_create_connection(key=_conn_key)
        job_output_files = self._find_chdir_files(
            f'{job_id}-*.out', _conn_key=_conn_key)
        if not job_output_files:
            raise ValueError(f'No output file found for job_id={job_id}')
        filepath = job_output_files[-1]
        result = conn.run(f"tail -n {n_lines} {filepath}", hide=True)
        return result.stdout

    def cancel_job(
            self, job_id, _conn_key='cancel_job'):
        """Cancel job of `job_id`."""
        conn = self.get_or_create_connection(key=_conn_key)
        result = conn.run(f"scancel {job_id}", hide=True)
        return result

    def get_sbatch_job_ids(
            self, _conn_key='get_sbatch_job_ids', job_name_pattern=None):
        """Return the list of job ids found in chdir."""
        if job_name_pattern is None:
            output_file_pattern = f'[1-9]*.out'
        else:
            if any(c in job_name_pattern for c in '/\|@~'): 
                raise ValueError("invalid job name pattern.")
            output_file_pattern = f'[1-9]*{job_name_pattern}*.out'
        job_output_files = self._find_chdir_files(
            output_file_pattern, _conn_key=_conn_key)
        job_ids = list()
        for f in job_output_files:
            try:
                job_id = int(Path(f).name.split('-', 1)[0])
            except ValueError:
                continue
            job_ids.append(job_id)
        job_ids = sorted(job_ids)
        return job_ids
    
    def get_sbatch_script(self, job_id, _conn_key='get_sbatch_script'):
        conn = self.get_or_create_connection(key=_conn_key)
        result = conn.run(f"scontrol write batch_script {job_id} -", hide=True)
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
