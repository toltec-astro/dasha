#!/usr/bin/env python

from dash_component_template import ComponentTemplate
from dash import html, Input, Output
import dash_bootstrap_components as dbc

# these are some useful, pre-made templates that can be used
# as a widget.
from dasha.web.templates.common import (
        LabeledDropdown, LabeledChecklist,
        LabeledInput,
        CollapseContent,
        LiveUpdateSection
    )

from tollan.utils.log import get_logger
from tollan.utils.fmt import pformat_yaml


class LiveUpdateExample(ComponentTemplate):

    class Meta:
        component_cls = html.Div

    logger = get_logger()

    def setup_layout(self, app):
        container = self

        # create 2 row x 1 col layout
        header_container, body = container.grid(2, 1)

        # add a title in the header
        # we use the live update section to create the title
        # which comes with a timer that one can use to
        # trigger a callback periodically
        header = header_container.child(
                LiveUpdateSection(
                    title_component=html.H3("An Example Page"),
                    # these intervals are in milli seconds.
                    interval_options=[2000, 5000, 10000],
                    interval_option_value=2000
                    ))

        # In the body we just create two rows, one for
        # controlling widgets and the other for view result
        controls_container, view_container = body.grid(2, 1)

        # add some input widgets, which is wrapped in
        # a form, for better formatting
        controls_form = controls_container.child(
                dbc.Form, inline=True, className='my-4')

        example_select = controls_form.child(
                LabeledDropdown(
                    label_text='A dropdown',
                    # these are bootstrap classes that
                    # specify the margin and width of the
                    # widget
                    className='w-auto mr-3',
                    size='sm',
                    )).dropdown
        # add the options and values
        example_select.options = [
                {
                    'label': f"item {i}",
                    'value': i,
                    }
                for i in range(4)]
        example_select.value = 0

        example_input = controls_form.child(
                LabeledInput(
                    label_text='A input',
                    className='w-auto mr-3',
                    size='sm',
                    input_props={
                        # these are the dbc.Input kwargs
                        'type': 'number',
                        'placeholder': 'some number',
                        'min': 0
                        }
                    )).input

        example_checklist = controls_form.child(
                LabeledChecklist(
                    label_text='A checklist',
                    className='w-auto',
                    # set to true to allow multiple check
                    multi=False
                    )).checklist
        example_checklist.options = [
                {
                    'label': f"check {i}",
                    'value': i,
                    }
                for i in range(4)]
        example_checklist.value = 3

        # create a two column display in the view_container
        view, view_details_container = view_container.grid(1, 2)

        # we populate the view details with a collapse container
        view_details = view_details_container.child(
                CollapseContent(button_text='Details ...')).content

        # this line is needed to "resolve" the components
        # that we defined above.
        super().setup_layout(app)

        # now we are ready to define callbacks

        # we populate the view with some info from the widges
        @app.callback(
                Output(view.id, 'children'),
                # timer itself is a component defined in
                # dasha.web.template.timer.
                # the timer.inputs gives the Input object
                # for the timer, which is n_calls
                header.timer.inputs + [
                    # additional inputs from the widgets
                    Input(example_select.id, 'value'),
                    Input(example_input.id, 'value'),
                    Input(example_checklist.id, 'value'),
                    ],
                )
        def update_view(n_calls, select_value, input_value, checklist_value):
            # we can add some logging message for debug purpose
            self.logger.debug(
                    f"n_calls={n_calls} select_value={select_value}"
                    f"input_value={input_value} "
                    f"checklist_value={checklist_value}")

            # we can compose a layout to return as the child of view
            # using pure dash.
            # No component template is allowed inside callback.

            # As an example, we do a simple calcuation using the inputs note
            # that it is often the case one need to check the value against
            # None, which is the default
            if input_value is not None:
                a = n_calls * input_value
            else:
                a = 'N/A'
            return html.Ul([
                    html.Li(f'n = {n_calls}'),
                    html.Li(f'select = {select_value}'),
                    html.Li(f'input = {input_value}'),
                    html.Li(f'checklist = {checklist_value}'),
                    html.Li(f'n x input = {a}'),
                    ])

        @app.callback(
                Output(view_details.id, 'children'),
                header.timer.inputs + [
                    # additional inputs from the widgets
                    Input(example_select.id, 'value'),
                    Input(example_input.id, 'value'),
                    Input(example_checklist.id, 'value'),
                    ],
                )
        def update_view_details(
                n_calls, select_value, input_value, checklist_value):
            return html.Pre(pformat_yaml(locals()))


DASHA_SITE = {
    'extensions': [
        {
            'module': 'dasha.web.extensions.dasha',
            'config': {
                'template': LiveUpdateExample,
                }
            }
        ]
    }
