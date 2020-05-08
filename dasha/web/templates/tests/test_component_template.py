#! /usr/bin/env python


from .. import _make_component_template_cls, Template
import dash_html_components as html


def test_make_component_template_cls():
    template_cls = _make_component_template_cls(html.Div)
    assert template_cls._idt_class_label == 'div'
    assert Template._template_registry[
            'dash_html_components.Div.Div'] == template_cls
