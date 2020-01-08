import dash_bootstrap_components as dbc
import dash_html_components as html

from dash.dependencies import Input, State, Output
from ...backend import dataframe_from_db
from .. import get_current_dash_app
from ....utils.log import timeit, get_logger
from ..common import TableViewComponent, SyncedListComponent
from . import SimplePageTemplate


app = get_current_dash_app()
logger = get_logger()


class LiveDBView(SimplePageTemplate):

    _template_params = [
            'label',
            'title_text',
            'title_icon',
            'update_interval',
            'n_records',
            'sources',
            ]

    def __init__(self, **params):
        super().__init__(**params)

        # update source key so that they don't clash.
        for k in list(self.sources.keys()):
            nk = f"{self.label}_{k}"
            self.sources[nk] = self.sources.pop(k)
            self.sources[nk]['label'] = nk
        # setup layout factory and callbacks
        for src in self.sources.values():
            src['_synced_list'] = sln = SyncedListComponent(src['label'])
            src['_table_view'] = tbn = TableViewComponent(src['label'])

            sln.make_callbacks(
                    app,
                    data_component=(tbn.table, 'data'),
                    cb_namespace='tolteca',
                    cb_state='array_summary',
                    cb_commit='array_concat',
                    )

            @timeit
            @app.callback([
                    Output(sln.items, 'data'),
                    Output(tbn.is_loading, 'children')
                    ], [
                    Input(sln.timer, 'n_intervals')], [
                    State(sln.state, 'data')
                    ])
            def update(n_intervals, state):
                # it is critical to make sure the body does not refer to
                # mutable global states
                src = self.sources[state['label']]
                try:
                    nrows = state['size']
                    first_row_id = state['first']['id']
                    if nrows < self.n_records:
                        first_row_id -= self.n_records - nrows
                except Exception:
                    return list(), html.Div(dbc.Alert(
                            "Refresh Failed", color="danger"),
                            style={
                                'padding': '15px 0px 0px 0px',
                                })
                else:
                    df = dataframe_from_db(
                        src['bind'],
                        src['query_update'].format(
                            id_since=first_row_id + 1,
                            n_records=self.n_records, **src),
                        **src['query_params'])
                    return df.to_dict("records"), ""

    def _get_layout(self, src):
        try:
            df = dataframe_from_db(
                    src['bind'],
                    src['query_init'].format(
                        n_records=self.n_records, **src),
                    **src['query_params'])
        except Exception as e:
            logger.error(e, exc_info=True)
            return html.Div(dbc.Alert(
                        "Query Failed", color="danger"),
                        style={
                            'padding': '15px 0px 0px 0px',
                            })

        slc = src['_synced_list'].components(interval=self.update_interval)
        slc.append(html.Div(id='{}-dummy'.format(src['_table_view'].table)))

        components = src['_table_view'].components(
                src['title'],
                additional_components=slc,
                columns=[
                    {"name": i, "id": i} for i in df.columns],
                data=df.to_dict("records"),
                fixed_rows={'headers': True, 'data': 0},
                )
        return components

    def get_layout(self, **kwargs):
        '''Returns the layout that contains a table view to the source.'''

        components = []

        width = 12 / len(self.sources)
        for src in self.sources.values():
            components.append(dbc.Col(
                self._get_layout(src), width=12, lg=width))

        return html.Div([dbc.Row(components)])


template_cls = LiveDBView
