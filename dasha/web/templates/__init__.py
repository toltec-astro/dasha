#!/usr/bin/env python


from tollan.utils import getobj
from dash_component_template.template import Template
import collections.abc
import copy


__all__ = ['resolve_template']


def resolve_template(arg):
    """Return a `~dash_component_template.Template` instance from `arg`."""

    if isinstance(arg, Template):
        return arg
    if isinstance(arg, collections.abc.Mapping):
        arg = copy.copy(arg)
        component_cls = arg.pop('template')
        if isinstance(component_cls, str):
            component_cls = getobj(component_cls)
        return component_cls(**arg)
    raise ValueError(f"cannot resolve template from {arg}")
