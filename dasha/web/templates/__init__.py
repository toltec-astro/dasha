#!/usr/bin/env python


from tollan.utils import getobj
from dash_component_template.template import Template
import collections.abc
import inspect
import copy


__all__ = ['resolve_template']


def resolve_template(arg):
    """Return a `~dash_component_template.Template` instance from `arg`."""

    if isinstance(arg, Template):
        return arg
    if isinstance(arg, collections.abc.Mapping):
        arg = copy.copy(arg)
        cls = arg.pop('template')
        if isinstance(cls, str):
            cls = getobj(cls)
        # in case the cls is a module, check for
        # the _resolve_template field
        if inspect.ismodule(cls):
            temp_attr = getattr(cls, '_resolve_template', None)
            if temp_attr is None:
                raise ValueError(f"cannot resolve template in module {cls}")
            if isinstance(temp_attr, str):
                cls = getattr(cls, temp_attr)
            else:
                cls = temp_attr
        if issubclass(cls, Template):
            return cls(**arg)
        raise ValueError(f"invalid template class {cls}")
    raise ValueError(f"cannot resolve template from {arg}")
