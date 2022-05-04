#!/usr/bin/env python

from functools import cached_property, lru_cache
from pydantic import BaseModel, Field, Extra, validator
from pydantic.typing import Annotated

from pathlib import Path
from typing import List, Any, Literal, Union, Callable, Optional

import numpy as np
import numpy.typing as npt

from dash_component_template import ComponentTemplate
from dash import html, Input, Output, dcc
import dash_bootstrap_components as dbc

# these are some useful, pre-made templates that can be used
# as a widget.
from dasha.web.templates.common import (
        LabeledDropdown, LabeledChecklist,
        LabeledInput,
        CollapseContent,
        LiveUpdateSection
    )
from dasha.web.templates.utils import fa

from tollan.utils.log import get_logger
from tollan.utils.fmt import pformat_yaml


class DataSource(object):
    """A base class for data source.
    
    """
    
    def sync():
        """Subclass implement this to refresh the underlying data object."""
        return NotImplemented

    def make_info():
        """Subclass implement this to generate info layout."""
        return NotImplemented

    def make_traces():
        """Subclass implement this to generate figure traces."""
        return NotImplemented

    def make_figure(collate=False):
        return NotImplemented
    
    @staticmethod
    @lru_cache(maxsize=None)
    def get_or_create_from_path(filepath):
        if filepath.suffix == '.nc':
            data_source_cls = NcDataSource
        elif filepath.suffix == '.csv':
            data_source_cls = CsvDataSource
        else:
            raise ValueError("unsupported data source")
        return data_source_cls(filepath)


class NcDataSource(DataSource):
    
    def __init__(self, filepath):
        self._filepath = filepath

    def resolve_data(self, data_in):
        if callable(data_in):
            return data_in(self)
        if isinstance(data_in, str) and self.hasany(data_in):
            data = self.getany(data_in)
            return data
        return data_in
    
    def resolve_obj(self, obj):
        result = dict()
        for field, data_in in obj.__dict__.items():
            if field.startswith('_'):
                continue
            data = self.resolve_data(data_in)
            result[field] = data
        return result

    def hasany(self, key):
        return False
    
    def getany(self, key):
        return NotImplemented

    def getstr(self, key):
        return key


class CsvDataSource(DataSource):
    pass


class DataSourceConfig(BaseModel):
    filepath: Path

    @property
    def data_source(self):
        return DataSource.get_or_create_from_path(self.filepath)

    def resolve_obj(self, obj):
        return self.data_source.resolve_obj(obj)


class DataItemConfigBase(BaseModel):
    class Config:
        extra: Extra.allow

class TraceItemConfig(DataItemConfigBase):
    type: Literal['trace']


class LiteralItemConfig(DataItemConfigBase):
    type: Literal['literal']
    value: Any
    label: Optional[str] = None

    def make_component(self, data_source):
        d = data_source.resolve_obj(self)
        text = d['value']
        label = d['label']
        if label is not None:
            text = f'{label}: {text}'
        return html.Pre(text)

class TitleItemConfig(DataItemConfigBase):
    type: Literal['title']
    text: Any = 'Plot Panel'
    icon: Any = 'fa-solid fa-chart-line'

    def make_component(self, data_source):
        d = data_source.resolve_obj(self)
        return html.H3([
                fa(d['icon'], className='pe-2 py-2'),
                d['text']
                ])


DataItemConfig = Annotated[
    Union[
        TraceItemConfig, LiteralItemConfig, TitleItemConfig,
        ], Field(discriminator='type')]

    
class PlotPanelConfig(BaseModel):
    """A config class to define content of a plot panel.
    
    The plot panel component is a dbc.Col that includes a title, and
    sub-components for the data_items.
    """
    data_source: DataSourceConfig
    data_items: List[DataItemConfig]
    col_width: Optional[int] = 12
    
    
class PlotPanelConfigList(BaseModel):
    """A wrapper class to parse a list of plot panels"""
    __root__: List[PlotPanelConfig]

    def __iter__(self):
        return iter(self.__root__)

    def __getitem__(self, item):
        return self.__root__[item]


class PlotPanel(ComponentTemplate):
    """A component template for a plot panel."""

    class Meta:
        component_cls = dbc.Col
        
    class TimeAxisTzSwitch(ComponentTemplate):

        class Meta:
            component_cls = dbc.Switch
            
        def setup_layout(app):
            super().setup_layout(app)

    class TraceCollateSwitch(ComponentTemplate):

        class Meta:
            component_cls = dbc.Switch
            
        def setup_layout(app):
            super().setup_layout(app)

    class InfoBar(ComponentTemplate):

        class Meta:
            component_cls = html.Div
            
        def setup_layout(app):
            super().setup_layout(app)

    def __init__(
            self,
            config,
            **kwargs):
        kwargs.setdefault('fluid', True)
        kwargs.setdefault('width', config.col_width)
        super().__init__(**kwargs)
        self._data_source = config.data_source
        # dispatch the data items
        d = self._data_items_by_type = dict()
        for data_item in config.data_items:
            if data_item.type not in d:
                d[data_item.type] = list()
            d[data_item.type].append(data_item)

    def setup_layout(self, app):
        container = self
        header_container, body = container.grid(2, 1)

        data_source = self._data_source
        if self._data_items_by_type['title']:
            title_item = self._data_items_by_type['title'][0]
        else:
            title_item = TitleItemConfig()
        header = header_container.child(
                LiveUpdateSection(
                    title_component=title_item.make_component(data_source),
                    interval_options=[2000, 5000, 10000],
                    interval_option_value=2000
                    ))
        literal_container, plot_container = body.grid(2, 1)
        for literal_item in self._data_items_by_type['literal']:
            literal_container.child(literal_item.make_component(data_source))

        graph = plot_container.child(dcc.Graph)

        super().setup_layout(app)


class PlotPanelUsageExample(ComponentTemplate):
    """An example template that makes uses of the PlotPanel template.."""

    class Meta:
        component_cls = dbc.Container

    def __init__(
            self, plot_panels, title='Example Page with Plot Panel', **kwargs):
        kwargs.setdefault('fluid', True)
        super().__init__(**kwargs)
        self._plot_panels = plot_panels
        self._title = title

    def setup_layout(self, app):
        container = self

        header_container, body = container.grid(2, 1)
        header_container.child(html.H3(self._title))
        header_container.child(html.Hr())
        for plot_panel in self._plot_panels:
            body.child(plot_panel)
        super().setup_layout(app)


plot_panel_config_list = PlotPanelConfigList.parse_obj([
    {
        'data_source': {
            'filepath': 'tel.nc'
        },
        'data_items': [
            {
                'type': 'title',
                'text': 'Telescope Position',
            },
            {
                'type': 'literal',
                'label': 'File Path',
                'value': lambda s: s.getstr('Header.File.Source')
            },
            {
                'type': 'trace',
                'label': 'Az vs Time',
                'x': 'Data.Telescope.Time',
                'y': 'Data.Telescope.Az',
            },
            {
                'type': 'trace',
                'label': 'El vs Time',
                'x': 'Data.Telescope.Time',
                'y': 'Data.Telescope.El',
            },
            {
                'type': 'trace',
                'label': 'Trajectory',
                'x': 'Data.Telescope.Az',
                'y': 'Data.Telescope.El',
            }
        ]
    }
])
   
plot_panels = [PlotPanel(config=config) for config in plot_panel_config_list]

DASHA_SITE = {
    'extensions': [
        {
            'module': 'dasha.web.extensions.dasha',
            'config': {
                'template': PlotPanelUsageExample,
                'plot_panels': plot_panels,
                }
            }
        ]
    }
