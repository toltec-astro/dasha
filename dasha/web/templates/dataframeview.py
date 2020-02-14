#! /usr/bin/env python


from . import ComponentTemplate
from .syncedlist import SyncedList
import dash_table
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Output, Input, State, ClientsideFunction
import dash_bootstrap_components as dbc


default_dash_table_kwargs = dict(
    filter_action="native",
    sort_mode="multi",
    # sort_action="native",
    # column_selectable="single",
    # row_selectable="multi",
    # virtualization=True,
    # persistence=True,
    # persistence_type='session',
    page_action='none',
    style_data_conditional=[
        {
            'if': {'row_index': 'odd'},
            'backgroundColor': '#fafafa'
        }
    ],
    style_table={
        'border': 'thin lightgrey solid'
    },
    # style_data={
    #     'whiteSpace': 'normal',
    # },
    style_header={
        'backgroundColor': '#dddddd',
        'fontWeight': 'bold'
    },
    style_cell={
        'textAlign': 'left',
        'padding': '5px',
        'max-width': '500px',
        'min-width': '60px',
    },
    fixed_rows={'headers': True, 'data': 0},
    )


class DataFrameView(ComponentTemplate):
    """This provides view to a data frame, which can be partially updated."""

    _component_cls = html.Div
    collapsible = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        header = self.child(dbc.Row).child(
                dbc.Col, className='d-flex align-items-center')
        if self.collapsible:
            self._title = header.child(
                    html.Button,
                    self.title_text,
                    style={
                        'line-height': '20px'
                        },
                    className='mr-2 my-0 px-0 btn btn-link',
                    )
        else:
            self._title = header.child(html.H4, self.title_text, style={
                'line-height': '50px'
                }, className='my-0')
        self._loading = header.child(dcc.Loading)
        if self.collapsible:
            content = self.child(dbc.Row).child(dbc.Col).child(
                    dbc.Collapse, className='mt-2')
        else:
            content = self.child(dbc.Row).child(dbc.Col).child(
                    html.Div, className='viewport-height mt-2')
        self.content_container = content

    def setup_layout(self, app):

        timer = self.child(dcc.Interval, interval=self.update_interval)
        title = self._title
        loading = self._loading
        content = self.content_container

        tbl_kwargs = dict({}, **default_dash_table_kwargs)
        self._tbl = tbl = content.child(dash_table.DataTable, **tbl_kwargs)
        sl = content.child(SyncedList(
            self.primary_key,
            Output(tbl.id, 'data')))

        super().setup_layout(app)

        if self.collapsible:
            app.clientside_callback(
                ClientsideFunction(
                    namespace='ui',
                    function_name='toggleWithClick',
                    ),
                Output(content.id, 'is_open'),
                [Input(title.id, "n_clicks")],
                [State(content.id, 'is_open')],
                )

        @app.callback(
                [
                    Output(sl.datastore.id, 'data'),
                    Output(loading.id, 'children'),
                    ],
                [Input(timer.id, 'n_intervals')],
                [State(sl.meta.id, 'data')]
                )
        def update(n_intervals, meta):
            df = self.data()
            # only push the entries with larger pk
            pk = meta['pk']
            df = df[df[pk] > meta['pk_latest']]
            return df.to_dict("records"), html.Span("")

    @property
    def layout(self):
        df = self.data()
        if df is None:
            return html.Div(dbc.Alert(
                    "Failed to get data.", color="danger"),
                    style={
                        'padding': '15px 0px 0px 0px',
                        }
                    )
        self._tbl.data = df.to_dict('records')
        self._tbl.columns = [
                    {"name": i, "id": i} for i in df.columns]
        return super().layout
