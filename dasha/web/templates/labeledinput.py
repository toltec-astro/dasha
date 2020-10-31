#! /usr/bin/env python

from . import ComponentTemplate
import dash_bootstrap_components as dbc
from schema import Schema, Optional


__all__ = ['LabeledInput', ]


class LabeledInput(ComponentTemplate):
    """A labeled input widget.

    """

    _component_cls = dbc.InputGroup
    _component_schema = Schema({
        'label_text': str,
        Optional('input_props', default=dict): dict,
        })

    def __init__(self, *args, **kwargs):
        size = kwargs.pop('size', 'md')
        super().__init__(*args, **kwargs)
        container = self.child(dbc.InputGroup, size=size)
        container.child(
                dbc.InputGroupAddon(self.label_text, addon_type='prepend'))
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
