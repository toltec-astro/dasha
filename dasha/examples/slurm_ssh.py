#!/usr/bin/env python


"""
This file defines an example site to demonstrate submitting jobs to SLURM
through SSH.
"""

from dash_component_template import ComponentTemplate, NullComponent
import dash
from dash import html, dcc, Output, Input, State, ALL
from dash.dash_table import DataTable
import dash_bootstrap_components as dbc

from tollan.utils.log import get_logger
from tollan.utils import odict_from_list

import os
from io import StringIO
import pandas as pd
import uuid

from dash.long_callback import DiskcacheLongCallbackManager
import diskcache

from dasha.web.templates.common import (
        LabeledDropdown,
        LabeledInput,
        CollapseContent,
        LiveUpdateSection
    )
from dasha.web.extensions.slurm import slurm_api
from dasha.web.templates.utils import PatternMatchingId, fa


class SlurmJobRunner(ComponentTemplate):

    class Meta:
        component_cls = dbc.Container

    logger = get_logger()

    _job_name_prefix = 'slurm_job_runner'

    @classmethod
    def _make_job_name(cls):
        prefix = cls._job_name_prefix
        return f'{prefix}_{uuid.uuid1()}'

    def __init__(self, title_component=None, **kwargs):
        super().__init__(**kwargs)
        self._title_component = title_component or html.H3("Slurm Job Runner")
        # this can be replace to use redis + celery
        cache = diskcache.Cache("./slurm_job_runner_cache")
        self._long_callback_manager = DiskcacheLongCallbackManager(cache)

    def setup_layout(self, app):
        container = self
        header_container, body = container.grid(2, 1)
        header_container.child(self._title_component)

        # make a form to specify the job details
        job_form_container = body.child(dbc.Form).child(
                    dbc.Row, className='gx-2 gy-2')

        cmd_input = job_form_container.child(
            LabeledInput(
                label_text='Command', size='sm',
                input_props={
                    'value': 'uname -a'
                    })
            ).input
        submit_button_container = job_form_container.child(
            html.Div,
            className=(
                'd-flex justify-content-start mt-2'
                )
            )
        submit_button_text = 'Sumbit'
        submit_button_spinner = dbc.Spinner(
            spinner_style={"width": "1rem", "height": "1rem"}
            )
        submit_button = submit_button_container.child(
            dbc.Button, submit_button_text,
            color='primary', size='sm',
            )
        submit_result_modal = submit_button_container.child(
            dbc.Modal, is_open=False, centered=False)
        submitted_job_store = submit_button_container.child(dcc.Store)

        body.child(html.Hr(className='my-2'))
        job_view_header_container, job_view_container = body.child(
            html.Div).grid(2, 1)
        job_view_header = job_view_header_container.child(
                LiveUpdateSection(
                    title_component=html.H5("Job Output"),
                    interval_options=[2000, 5000, 10000],
                    interval_option_value=2000
                    ))
        job_list_container, job_details_container = (
            job_view_container.colgrid(1, 2))
        job_list_group = job_list_container.child(dbc.ListGroup)
        job_cancel_modal = job_list_container.child(
            dbc.Modal, is_open=False, centered=False)

        # pmid for contents in the job list group
        pmid = PatternMatchingId(container_id=job_list_group.id, type='')

        def make_job_list_entry(container, job_data):
            job_id = job_data['job_id']
            # job_name = job_data['job_name']
            state = job_data['state']

            content_container = container.child(
                dbc.ListGroupItem,
                className='d-flex align-items-center',
                )
            index = pmid.make_id()
            state_color = {
                'PENDING': 'warning',
                'RUNNING': 'success',
                'COMPLETED': 'info',
                }.get(state, 'danger')
            content_container.child(
                dbc.Label(
                    job_id, className='font-weight-bold my-0 me-2',
                    id=pmid(type='job_id_label', index=index),
                    ))
            content_container.child(
                dbc.Badge(state, color=state_color, className='me-2'))
            # content_container.child(dbc.Label(job_name))
            if state in ['RUNNING', ]:
                content_container.child(
                    dbc.Spinner,
                    color='secondary',
                    show_initially=False,
                    spinner_class_name='me-2',
                    spinner_style={"width": "1rem", "height": "1rem"},
                    id=pmid(type='job_running_spinner', index=index),
                    )
            if state in ['RUNNING', 'PENDING']:
                cancel_button = dbc.Button(
                    fa("fa-solid fa-ban fa-lg text-danger"),
                    size='sm',
                    color='light',
                    className='me-2',
                    id=pmid(type='job_cancel_button', index=index),
                    )
                content_container.child(
                        dcc.ConfirmDialogProvider,
                        cancel_button,
                        id=pmid(type='job_cancel_confirm', index=index),
                        message=f"Cancel job {job_id}?",
                        )
                content_container.child(
                    dbc.Tooltip(
                        "Click to cancel job.",
                        target=cancel_button.id)
                    )

            content_container.child(
                dbc.Button,
                fa('fa-solid fa-eye fa-lg text-secondary'),
                size='sm',
                color='light',
                id=pmid(type='job_view_button', index=index)
                )

        output_pre_init_text = '<sumbit job to see output ...>'
        output_pre = job_details_container.child(
            html.Pre,
            output_pre_init_text
            )
        output_view_job_store = job_details_container.child(
            dcc.Store)

        super().setup_layout(app)

        def make_job_data(cmd):
            job_name = self._make_job_name()
            job_script = f'''#!/bin/bash
#SBATCH -J {job_name}
#SBATCH -o %j-%x.out  # %j = job ID
#SBATCH -t 00:10:00  # Job time limit
#SBATCH --nodes=1  # Node count required for the job
#SBATCH --ntasks=1  # Number of tasks to be launched
#SBATCH --cpus-per-task=1  # Number of cores per task
#SBATCH --mem=1G  # Mem required per node
#SBATCH --parsable
{cmd}
            '''
            return {
                'job_script': job_script,
                'job_name': job_name,
                }

        @app.long_callback(
            [
                Output(submit_result_modal.id, 'children'),
                Output(submit_result_modal.id, 'is_open'),
                Output(submitted_job_store.id, 'data'),
                ],
            [
                Input(submit_button.id, 'n_clicks'),
                State(cmd_input.id, 'value'),
                ],
            running=[
                (
                    Output(submit_button.id, "disabled"), True, False
                    ),
                (
                    Output(submit_button.id, "children"),
                    submit_button_spinner, submit_button_text
                    ),
            ],
            prevent_initial_call=True,
            manager=self._long_callback_manager
            )
        def run_sbatch(n_clicks, cmd_input_value):
            def make_output(content, job_data):
                return [dbc.ModalBody(content), True, job_data]
            job_data = make_job_data(cmd_input_value)
            job_script = job_data['job_script']
            try:
                job_id = slurm_api.run_sbatch(job_script)
                job_data['job_id'] = job_id
                return make_output(
                    html.Div([
                        html.H5(f'Job {job_id} submitted'),
                        html.Pre(job_script)
                        ]),
                    job_data
                    )
            except Exception as e:
                self.logger.debug("Failed submitting job: {e}", exc_info=True)
                return make_output(
                    html.P(f'Failed submitting job: {e}'),
                    None)

        @app.callback(
                Output(job_list_group.id, 'children'),
                job_view_header.timer.inputs
                )
        def update_job_list_group(n_calls):
            job_ids = slurm_api.get_sbatch_job_ids()
            if not job_ids:
                return [dbc.ListGroupItem('No jobs found')]
            conn = slurm_api.get_or_create_connection(
                key='update_job_list_group')
            job_ids_str = ','.join(map(str, job_ids))
            result = conn.run(
                f"sacct --parsable -X -o %all -j {job_ids_str}", hide=True)
            df = pd.read_csv(StringIO(result.stdout), sep='|')
            df = df.sort_values(by=['JobID'], ascending=False)
            container = NullComponent(id=job_list_group.id)
            for entry in df.itertuples():
                job_data = {
                    'job_id': entry.JobID,
                    'job_name': entry.JobName,
                    'state': entry.State,
                    }
                make_job_list_entry(container, job_data)
            return container.layout

        @app.callback(
            [
                Output(job_cancel_modal.id, 'children'),
                Output(job_cancel_modal.id, 'is_open'),
                ],
            [
                Input(pmid(type='job_cancel_confirm', index=ALL),
                      'submit_n_clicks'),
                State(pmid(type='job_id_label', index=ALL), 'children')
                ],
            prevent_initial_call=True,
            )
        def on_job_cancel(*args):
            triggered_prop_ids = dash.callback_context.triggered_prop_ids
            if not triggered_prop_ids:
                return dash.no_update
            index = next(iter(
                dash.callback_context.triggered_prop_ids.values()))['index']
            n_clicks = odict_from_list(
                dash.callback_context.inputs_list[0],
                key=lambda d: d['id']['index'])[index].get('value', None)
            job_id = odict_from_list(
                dash.callback_context.states_list[0],
                key=lambda d: d['id']['index'])[index].get('value', None)
            if not n_clicks or not job_id:
                return dash.no_update

            def make_output(content):
                return [dbc.ModalBody(content), True]

            job_id = int(job_id)

            try:
                result = slurm_api.cancel_job(job_id)
                return make_output(
                    html.Div([
                        html.H5(f'Job {job_id} canceled'),
                        html.Pre(result.stdout)
                        ])
                    )
            except Exception as e:
                self.logger.debug("Failed cancelling job: {e}", exc_info=True)
                return make_output(
                    html.P(f'Failed cancelling job: {e}'),
                    None)

        @app.callback(
            Output(output_view_job_store.id, 'data'),
            [
                Input(submitted_job_store.id, 'data'),
                Input(pmid(type='job_view_button', index=ALL),
                      'n_clicks'),
                State(pmid(type='job_id_label', index=ALL), 'children')
                ],
            prevent_initial_call=True,
            )
        def on_job_details_view(submitted_job_data, *args):
            triggered_prop_ids = dash.callback_context.triggered_prop_ids
            if not triggered_prop_ids:
                return dash.no_update
            if next(iter(triggered_prop_ids.keys())).endswith('.data'):
                # new job submitted
                return submitted_job_data
            # viewing old jobs
            index = next(iter(
                triggered_prop_ids.values()))['index']
            n_clicks = odict_from_list(
                dash.callback_context.inputs_list[1],
                key=lambda d: d['id']['index'])[index].get('value', None)
            job_id = odict_from_list(
                dash.callback_context.states_list[0],
                key=lambda d: d['id']['index'])[index].get('value', None)
            if not n_clicks or not job_id:
                return dash.no_update

            job_id = int(job_id)
            job_info = slurm_api.get_job_info(job_id, show_steps=False)
            return {
                'job_id': job_info['JobID'],
                'job_name': job_info['JobName']
                }

        @app.callback(
                Output(output_pre.id, 'children'),
                job_view_header.timer.inputs + [
                    State(output_view_job_store.id, 'data')
                    ]
                )
        def update_output_view(n_calls, job_data):
            if job_data is None:
                return output_pre_init_text
            job_id = job_data['job_id']
            job_name = job_data['job_name']
            job_script = job_data.get('job_script', None)
            if job_script is not None:
                job_script_text = f'\n<<\n{job_script}\n<EOF>\n------'
            else:
                job_script_text = 'N/A\n------'
            try:
                output = slurm_api.get_sbatch_job_output(job_id, n_lines=20)
            except Exception as e:
                return f'Error getting output for job_id={job_id}: {e}'
            return (
                f"Output for:\n"
                f"  job_id: {job_id}\n"
                f"  job_name: {job_name}\n"
                f"  job_script: {job_script_text}\n"
                f"{output}")


class SlurmInfoView(ComponentTemplate):

    class Meta:
        component_cls = dbc.Container

    def __init__(self, title_component=None, **kwargs):
        super().__init__(**kwargs)
        self._title_component = title_component or html.H3("Slurm Info View")

    def setup_layout(self, app):
        container = self
        header_container, body = container.grid(2, 1)

        header = header_container.child(
                LiveUpdateSection(
                    title_component=self._title_component,
                    interval_options=[2000, 5000, 10000],
                    interval_option_value=2000
                    ))

        view_container = body.child(html.Div, className='mb-4')
        dt_kwargs = {
            # 'filter_action': 'native',
            'sort_action': 'native',
            'sort_mode': 'multi',
            # 'row_selectable': 'single',
            }
        info_dt = view_container.child(
            CollapseContent(
                button_text='Cluster Info ...',
                className='mb-2',
                )).content.child(
                DataTable,
                **dt_kwargs,
                )
        job_list_dt = view_container.child(
            CollapseContent(
                button_text='All Running Jobs ...',
                className='mb-2',
                )).content.child(
                DataTable,
                **dt_kwargs,
                )
        job_info_container = view_container.child(dbc.Form).child(
                    dbc.Row, className='gx-2 gy-2')
        job_id_select = job_info_container.child(
            LabeledDropdown(
                label_text='Select job id to view details',
                className='mb-2 w-auto',
                size='sm',
                )
            ).dropdown
        job_info_dt = job_info_container.child(
            DataTable,
            **dt_kwargs,
            )

        super().setup_layout(app)

        @app.callback(
                [
                    Output(info_dt.id, 'data'),
                    Output(info_dt.id, 'columns'),
                    Output(job_list_dt.id, 'data'),
                    Output(job_list_dt.id, 'columns'),
                    Output(job_id_select.id, 'options'),
                    ],
                header.timer.inputs
                )
        def update_view(n_calls):
            info_df = slurm_api.get_cluster_info()
            job_list_df = slurm_api.get_queue_info()
            return [
                info_df.to_dict(orient="records"),
                [{'name': c, 'id': c} for c in info_df.columns],
                job_list_df.to_dict(orient="records"),
                [{'name': c, 'id': c} for c in job_list_df.columns],
                [{'label': j, 'id': j} for j in job_list_df['JOBID']],
                ]

        @app.callback(
            [
                Output(job_info_dt.id, 'data'),
                Output(job_info_dt.id, 'columns'),
                ],
            [
                Input(job_id_select.id, 'value')
                ],
            )
        def update_job_info_dt(job_id):
            if job_id is None:
                return [None, None]
            job_info_df = slurm_api.get_job_info(job_id=job_id)
            return [
                job_info_df.to_dict(orient="records"),
                [{'name': c, 'id': c} for c in job_info_df.columns],
                ]


class SlurmOnSSHExample(ComponentTemplate):

    class Meta:
        component_cls = dbc.Container

    def __init__(self, title_component=None, **kwargs):
        super().__init__(**kwargs)
        self._title_component = (
            title_component or html.H3("Slurm On SSH Example"))

    def setup_layout(self, app):
        container = self
        header_container, body = container.grid(2, 1)

        header_container.child(self._title_component)
        body.child(SlurmJobRunner())
        body.child(html.Hr(className='my-2'))
        body.child(SlurmInfoView())
        super().setup_layout(app)


def get_slurm_config():
    slurm_remote_host = os.environ['SLURM_REMOTE_HOST']
    slurm_partition = os.environ.get('SLURM_PARTITION', None)
    slurm_chdir = os.environ.get('SLURM_CHDIR', None)
    return {
        'api_type': 'ssh',
        'remote_host': slurm_remote_host,
        'partition': slurm_partition,
        'chdir': slurm_chdir
        }


def DASHA_SITE():
    return {
    'extensions': [
        {
            'module': 'dasha.web.extensions.slurm',
            'config': get_slurm_config()
            },
        {
            'module': 'dasha.web.extensions.dasha',
            'config': {
                'template': SlurmOnSSHExample,
                }
            },
        ],
    }
