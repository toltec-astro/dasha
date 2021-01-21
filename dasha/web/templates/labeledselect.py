#! /usr/bin/env python

from . import ComponentTemplate
import dash_bootstrap_components as dbc
from schema import Schema, Optional


__all__ = ['LabeledDropdown', 'LabeledChecklist']


class LabeledDropdown(ComponentTemplate):
    """A labeled dropdown widget.

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


class LabeledChecklist(ComponentTemplate):
    """A labeled checklist widget.

    """

    _component_cls = dbc.FormGroup
    check = True
    inline = True
    _component_schema = Schema({
        'label_text': str,
        Optional('checklist_props', default=dict): dict,
        Optional('multi', default=True): bool,
        })

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        label_text = self.label_text
        if not label_text.endswith(':'):
            label_text += ':'
        self.child(dbc.Label(
            label_text, className='mt-2',
            style={
                'color': '#495057',
                'font-size': '.875rem',
                'padding': '.25rem .5rem',
                }
            ))
        checklist_props = dict(
                labelClassName=(
                    'btn btn-sm btn-link form-check-label rounded-0'),
                labelCheckedClassName='active btn-outline-primary',
                custom=False,
                inputClassName='d-none',
                className='d-flex flex-wrap form-check-compact',
                )
        checklist_props.update(self.checklist_props)
        if self.multi:
            select_cls = dbc.Checklist
        else:
            select_cls = dbc.RadioItems
        self._checklist = self.child(select_cls, **checklist_props)

    @property
    def checklist(self):
        """The dropdown component."""
        return self._checklist
