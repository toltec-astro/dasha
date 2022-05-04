#!/usr/bin/env python

from functools import lru_cache
from pydantic import BaseModel, Field, Extra
from pydantic.typing import Annotated

from pathlib import Path
from typing import List, Any, Literal, Union, Dict, Optional

import numpy as np

from dash_component_template import ComponentTemplate
from dash import html, Output, dcc
import dash_bootstrap_components as dbc

# these are some useful, pre-made templates that can be used
# as a widget.
from dasha.web.templates.common import (
        LiveUpdateSection
    )
from dasha.web.templates.utils import fa, make_subplots

from tollan.utils.nc import NcNodeMapper

"""
This example shows one way to build complex dashboard with templates to allow
re-using with the settings specified as a declarative config dict.

This application makes live plots for data streams stored in netcdf files,
which is updated by external program.

The page runs a timer and polls the file for the latest data, and display them
in a Plotly plot panel template.

The content of the plotting panel is defined by "data_items" specified in the
plot panel config dict, which is implemented as pydantic models.

The code is structured into four parts:

* The data file handler NcDataSource, a subclass of DataSource, implementing
  the interface to sync and load data from a given netcdf file
* The plot panel config model PlotPanelConfig, a pydantic model that defines
  what to include in the panel for the input data
* The dash compoment templates PlotPanel and PlotPanelUsageExample. These
  templates consumes the plot panel config and render the page when the Dash
  app is run.
* The "user code" that shows how we can define a web page plotting a netCDF file 
  with the machinery that we just setup.
"""

## The data file handling classes
# these classes provides a common interface to provide data.
# In this example we use tollan.utils.nc.NcNodeMapper as the "backend" to
# retrieve the data in the netCDF files.
# More data source classes could be defined to handle other type of files like csv.
# 
# The entry point method of the data source is get_or_create_from_path,
# which is called when the plot panel config is parsed. Depending on the filepath,
# it returns the matching subclass instance for the file data type.

class DataSource(object):
    """A base class for data source.
    
    """
    @staticmethod
    @lru_cache(maxsize=None)
    def get_or_create_from_path(filepath):
        if filepath.suffix == '.nc':
            data_source_cls = NcDataSource
        elif filepath.suffix == '.csv':
            # TODO implement CsvDataSource to handle csv files
            data_source_cls = NotImplemented
        else:
            raise ValueError("unsupported data source")
        return data_source_cls(filepath)

    def _resolve_data(self, data_in):
        """Subclass implement this to resolve data spec with data source."""
        return NotImplemented

    def resolve_obj(self, obj):
        """Resolve all data reference in obj."""
        self.sync()
        result = dict()
        if not isinstance(obj, dict):
            obj = obj.__dict__
        for field, data_in in obj.items():
            if field.startswith('_'):
                continue
            data = self._resolve_data(data_in)
            result[field] = data
        return result

    @classmethod
    def __get_validators__(cls):
        yield cls.get_or_create_from_path

    @classmethod
    def __modify_schema__(cls, field_schema):
        pass


class NcDataSource(NcNodeMapper, DataSource):
    
    def __init__(self, filepath):
        super().__init__(source=filepath)

    def _resolve_data(self, data_in):
        # This function get called to invoke the getter functions in
        # the plot panel config.
        if callable(data_in):
            return data_in(self)
        if isinstance(data_in, str) and self.hasname(data_in):
            data = self.getany(data_in)
            return data
        return data_in
 

## The config model classes
# We use pydantic models to manage the config dict, which allows specifying
# the synctax of the config dict explicitly. 
# Note the DataItemConfig is a Union type of the concrete item configs,
# and each type of item is mapped to the web page component using the
# make_* method. The component templates takes these data items and calls
# the make_* methods with the data_source to extract the data to display.

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
    x: Any
    y: Any   
    z: Any
    trace_kw: Dict[str, Any]

    def make_traces(self, data_source):
        d = data_source.resolve_obj(self)
        trace = d['trace_kw'].copy()
        for k in ['x', 'y', 'z']:
            if d[k] is not None:
                trace[k] = d[k]
        # TODO we can implement support to expand 2d arrays data to multiple
        # 1-d traces if needed, since the returned item is a list of traces
        return [trace]


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
        return html.Pre(text, className='my-0')

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

## The compnent templates
# the templates consumes the config and build the page.
# note the use of the timer in PlotPanel, we setup a
# callback function at each tick of the timer to re-render the data

class PlotPanel(ComponentTemplate):
    """A component template for a plot panel."""

    class Meta:
        component_cls = dbc.Col
        
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
                    interval_option_value=5000
                    ))
        literal_container, plot_container = body.grid(2, 1)
        graph = plot_container.child(dcc.Graph)

        super().setup_layout(app)

        @app.callback(
                [
                    Output(literal_container.id, 'children'),
                    Output(graph.id, 'figure'),
                ],
                header.timer.inputs)
        def update_plot(n_calls):
            # literal items
            literal_children = list()
            for literal_item in self._data_items_by_type['literal']:
                literal_children.append(
                    literal_item.make_component(data_source))

            traces = list()
            for trace_item in self._data_items_by_type['trace']:
                traces.extend(trace_item.make_traces(data_source))
            # create the figure and add trace
            n_rows = max(t.get('row', 1) for t in traces)
            n_cols = max(t.get('col', 1) for t in traces)
            fig = make_subplots(n_rows, n_cols)
            for trace in traces:
                row = trace.pop('row', 1)
                col = trace.pop('col', 1)
                fig.add_trace(trace, row=row, col=col)
            return [literal_children, fig]


class PlotPanelUsageExample(ComponentTemplate):
    """An example template that makes uses of the PlotPanel template."""

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

        
## The code below is the "user code" that makes use of the machinery that
# we just setup. We define the dict config that describes what we need
# to plot, and actually create the dasha app with the template we defined
# in the DASHA_SITE variable.
# All the data items are specified with respect to the _resolve_data method
# in the NcDataSource. In NcDatdaSource._resolve_data, we will check if the
# data in the plot panel config is a callable, if so, it gets called
# with the data_source, so we can implement arbitury data transform in this way.
# If the data is a string and matches one of the variable name in the netCDF
# file, it is retrieved as-is

def utctime_getter(key, data_slice=None):
    """Getter to extract utc time from tel.nc"""
    from astropy.time import Time
    if data_slice is None:
        data_slice = slice(None, None)
    def func(s):
        var = s.getvar(key)
        return Time(var[data_slice], format='unix').to_datetime()
    return func


def coord_getter(key, data_slice=None):
    """Getter to extract coords from tel.nc"""

    if data_slice is None:
        data_slice = slice(None, None)

    def func(s):
        var = s.getvar(key)
        return np.rad2deg(var[data_slice])
    return func


def get_source_coord(s):
    from astropy.coordinates import SkyCoord
    import astropy.units as u
    ra = s.getany('Header.Source.Ra')
    dec = s.getany('Header.Source.Dec')
    coord = SkyCoord(ra=ra[0], dec=dec[0], unit=(u.rad, u.rad), frame='icrs')
    return coord.to_string(style='hmsdms')


trace_kw_default = {
                    'type': 'scattergl',
                    'mode': 'lines+markers',
                    'showlegend': True,
                    'marker': {
                        'color': 'red',
                        'size': 8
                    }
                }


data_slice = slice(-10000, None, 100)
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
                'value': 'Header.File.Name'
            },
            {
                'type': 'literal',
                'label': 'Source Name',
                'value': 'Header.Source.SourceName'
            },
            {
                'type': 'literal',
                'label': 'Source Coordinate',
                'value': get_source_coord
            },
            {
                'type': 'trace',
                'x': utctime_getter('Data.TelescopeBackend.TelTime', data_slice),
                'y': coord_getter('Data.TelescopeBackend.TelAzAct', data_slice),
                'trace_kw': {**trace_kw_default, **{
                    'name': 'Az vs Time',
                    'row': 1,
                    'col': 1,
                    }}
            },
            {
                'type': 'trace',
                'label': 'El vs Time',
                'x': utctime_getter('Data.TelescopeBackend.TelTime', data_slice),
                'y': coord_getter('Data.TelescopeBackend.TelElAct', data_slice),
                'trace_kw': {**trace_kw_default, **{
                    'name': 'El vs Time',
                    'row': 1,
                    'col': 2,
                    }}
            },
            {
                'type': 'trace',
                'label': 'Trajectory',
                'x': coord_getter('Data.TelescopeBackend.TelAzAct', data_slice),
                'y': coord_getter('Data.TelescopeBackend.TelElAct', data_slice),
                'trace_kw': {**trace_kw_default, **{
                    'name': 'El vs Time',
                    'row': 1,
                    'col': 3,
                    }}
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
