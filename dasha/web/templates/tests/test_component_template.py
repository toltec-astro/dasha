#! /usr/bin/env python


from .. import ComponentTemplate
import dash_html_components as html


def test_make_template_cls():
    template_cls = ComponentTemplate.make_template_cls(html.Div)
    assert template_cls._idt_class_label == 'div'
    assert ComponentTemplate._template_registry['div'] == template_cls
