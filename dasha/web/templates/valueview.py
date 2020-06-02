#! /usr/bin/env python

from . import ComponentGroup
import dash_html_components as html
import dash_daq as daq


__all__ = ['ValueView', ]


class ValueView(ComponentGroup):
    """This template provides a set of components to display values."""

    _component_cls = html.Div
    className = 'd-flex align-content-stretch flex-wrap'

    _component_group = [
        {
            'key': 'label_container',
            'type': 'static',
            'prop': None,
            'required': True,
            },
        {
            'key': 'label',
            'type': 'static',
            'prop': None,
            },
        {
            'key': 'text',
            'type': 'output',
            'prop': 'children',
            },
        {
            'key': 'bar',
            'type': 'output',
            'prop': 'value',
            },
        ]

    def __init__(self, **kwargs):
        if kwargs.get('text', None) is None and \
                kwargs.get('bar', None) is None:
            raise ValueError('text and bar cannot be both None.')
        self._source = kwargs
        super().__init__(**kwargs)

        @self._make_component_obj('label_container')
        def label_container(self, *args, **kwargs):
            kwargs.setdefault('className', 'd-flex flex-fill text-monospace')
            kwargs.setdefault('style', {
                    'min-width': '33%'
                    })
            return self.child(html.Div, *args, **kwargs)

        @self._make_component_obj('label')
        def label(self, *args, **kwargs):
            kwargs.setdefault('className', 'mr-auto pr-2')
            return self.label_container.child(html.Span, *args, **kwargs)

        @self._make_component_obj('text')
        def text(self, *args, **kwargs):
            kwargs.setdefault('children', 'N/A')
            return self.label_container.child(html.Span, *args, **kwargs)

        @self._make_component_obj('bar')
        def bar(self, *args, **kwargs):
            kwargs.setdefault('color', {
                    "ranges": {
                        "#92e0d3": [0, 0.3],
                        "#f4d44d ": [0.3, 0.7],
                        "#f45060": [0.7, 1],
                    }
                })
            kwargs.setdefault('showCurrentValue', False)
            return self.child(
                html.Div,
                className="pl-2 py-1 daq-graduatedbar").child(
                daq.GraduatedBar,
                *args,
                **kwargs
                )
