#! /usr/bin/env python

from . import ComponentTemplate
import dash_bootstrap_components as dbc
from schema import Schema, Optional


__all__ = ['LabeledDropdown', ]


class LabeledDropdown(ComponentTemplate):
    """A labeled drop widget.

    """

    _component_cls = dbc.InputGroup
    _component_schema = Schema({
        'label_text': str,
        Optional('dropdown_props', default=dict): dict,
        })

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.child(dbc.InputGroupAddon(self.label_text, addon_type='prepend'))
        self._dropdown = self.child(dbc.Select, **self.dropdown_props)

    @property
    def dropdown(self):
        """The dropdown component."""
        return self._dropdown
