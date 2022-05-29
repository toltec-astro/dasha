#!/usr/bin/env python


"""
This file defines an example site to demonstrate submitting jobs to SLURM
through Celery.
"""

from dash_component_template import ComponentTemplate
from dash import html, dcc, Output, Input, State
from dash.dash_table import DataTable
import dash_bootstrap_components as dbc

from tollan.utils.log import timeit, get_logger
from tollan.utils.fmt import pformat_yaml

import os
import uuid

from dash.long_callback import DiskcacheLongCallbackManager
import diskcache

from dasha.web.templates.common import (
        LabeledDropdown, LabeledChecklist,
        LabeledInput,
        CollapseContent,
        LiveUpdateSection
    )
from dasha.web.extensions.slurm import slurm_api


class SlurmJobRunner(ComponentTemplate):

    class Meta:
        component_cls = dbc.Container

    _job_name_prefix = 'slurm_job_runner'

    @classmethod
    def _make_job_name(cls):
        prefix = cls._job_name_prefix
        return f'{prefix}_{uuid.uuid1()}'

    def __init__(self, title_component=None, **kwargs):
        super().__init__(**kwargs)
        self._title_component = title_component or html.H3("Slurm Job Runner")
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
        output_view_header_container, output_view_container = body.child(
            html.Div).grid(2, 1)
        output_view_header = output_view_header_container.child(
                LiveUpdateSection(
                    title_component=html.H5("Job Output"),
                    interval_options=[2000, 5000, 10000],
                    interval_option_value=2000
                    ))
        output_view_pre_init_text = '<sumbit job to see output ...>'
        output_view_pre = output_view_container.child(
            html.Pre,
            output_view_pre_init_text
            )

        super().setup_layout(app)
        
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
{cmd_input_value}
            '''
            try:
                job_id = slurm_api.run_sbatch(job_script)
                job_data = {
                    'job_id': job_id,
                    'job_name': job_name,
                    'job_script': job_script
                    }
                return make_output(
                    html.Div([
                        html.H5(f'Job {job_id} submitted'),
                        html.Pre(job_script)
                        ]),
                    job_data
                    )
            except Exception as e:
                return make_output(
                    html.P(f'Failed submitting job: {e}'),
                    None)

        @app.callback(
                Output(output_view_pre.id, 'children'),
                output_view_header.timer.inputs + [
                    State(submitted_job_store.id, 'data')
                    ]
                )
        def update_output_view(n_calls, job_data):
            if job_data is None:
                return output_view_pre_init_text
            job_id = job_data['job_id']
            job_name = job_data['job_name']
            try:
                output = slurm_api.get_sbatch_live_output(job_id, n_lines=20)
            except Exception as e:
                return f'Error getting output for job_id={job_id}: {e}'
            return f"Output for job_id={job_id} job_name={job_name}\n\n{output}"
 

class SlurmJobView(ComponentTemplate):

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
                button_text='All Jobs ...',
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
            info_df = slurm_api.get_info()
            job_list_df = slurm_api.get_job_list()
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
        body.child(SlurmJobView())
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


DASHA_SITE = {
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
