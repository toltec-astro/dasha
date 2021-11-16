#! /usr/bin/env python

from dash_component_template import ComponentTemplate
import dash_bootstrap_components as dbc


__all__ = ['LabeledInput', ]


class LabeledInput(ComponentTemplate):
    """A labeled input widget.

    """
    class Meta:
        component_cls = dbc.InputGroup

    def __init__(self, label_text, *args, input_props=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_text = label_text
        self.input_props = input_props or dict()

        container = self
        container.child(dbc.InputGroupText(self.label_text))
        self._input = container.child(dbc.Input, **self.input_props)
        self._feedback = self.child(dbc.FormFeedback)

    @property
    def input(self):
        """The input component."""
        return self._input

    @property
    def feedback(self):
        """The feedback component."""
        return self._feedback
