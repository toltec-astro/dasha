
from . import SimplePageTemplate
import dash_html_components as html
import dash_core_components as dcc
from  .. import get_current_dash_app
from dash.dependencies import Input, State, Output


class MySimplePageTemplate(SimplePageTemplate):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # all components need to be prefixed by this in order to
        # allow multiple of these instances co-exists.
        # otherwise the component names will clash.
        ctx = self.label

        app = get_current_dash_app()

        i = 0
        last_n_intervals = None  # use this to prevent triggering server counter from reset button
        n_last_ui_reset = 0

        @app.callback(
            Output(f'{ctx}-n-last-ui-reset', 'data'),
            [Input(f'{ctx}-reset', 'n_clicks')],
            [State(f'{ctx}-timer', 'n_intervals')])
        def click(n_clicks, n_intervals):
            return n_intervals 

        @app.callback(
            [Output(f'{ctx}-server-counter', 'children'),
             Output(f'{ctx}-client-counter', 'children'),
             Output(f'{ctx}-ui-counter', 'children'),
             ],
            [Input(f'{ctx}-timer', 'n_intervals'),
             Input(f'{ctx}-n-last-ui-reset', 'data')
             ],
                )
        def update(n_intervals, n_last_ui_reset):
            nonlocal i
            nonlocal last_n_intervals
            if n_intervals != last_n_intervals:
                i += 1
                last_n_intervals = n_intervals
            j = n_intervals
            print(n_intervals, n_last_ui_reset)
            k = n_intervals - (n_last_ui_reset or 0)
            return (
                    f"Server counter (resets on server restart): {i}",
                    f"Client counter (resets on page refresh): {j}",
                    f"Client+UI counter (resets on page refresh or reset button click): {k}",
                    )

    def get_layout(self):
        ctx = self.label
        return html.Div([
            "Hello",
            dcc.Interval(id=f'{ctx}-timer', interval=1000, n_intervals=0),
            html.Div("", id=f'{ctx}-server-counter'),
            html.Div("", id=f'{ctx}-client-counter'),
            html.Div("", id=f'{ctx}-ui-counter'),
            html.Button("Reset", id=f'{ctx}-reset'),
            dcc.Store(data=0, id=f"{ctx}-n-last-ui-reset"),
            ])


template_cls = MySimplePageTemplate
