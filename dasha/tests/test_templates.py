#!/usr/bin/env python

from dasha.web.templates import resolve_template
from dash_component_template import NullComponent, ComponentTemplate
from dash import html


class MyTemplate(ComponentTemplate):

    class Meta:
        component_cls = html.Div

    def __init__(self, a, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.a = a


_resolve_template = MyTemplate


def test_resolve_template():

    n = NullComponent(id='1')
    assert resolve_template(n) is n

    t = resolve_template({
        'template': MyTemplate,
        'a': 1
        })
    assert t.a == 1
    assert isinstance(t, MyTemplate)

    t = resolve_template({
        'template': 'dasha.tests.test_templates:MyTemplate',
        'a': 1
        })
    assert t.a == 1
    assert isinstance(t, MyTemplate)

    t = resolve_template({
        'template': 'dasha.tests.test_templates',
        'a': 1
        })
    assert t.a == 1
    assert isinstance(t, MyTemplate)
