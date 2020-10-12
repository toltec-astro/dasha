#! /usr/bin/env python

from dasha.web.templates import ComponentTemplate
from dasha.web.extensions.dasha import resolve_url

from tollan.utils import rupdate

import dash_defer_js_import as dji
from dash.dependencies import Output
import dash_html_components as html
from jinja2 import Template
from schema import Schema, Optional


class AladinLiteView(ComponentTemplate):
    _component_cls = html.Div
    _component_schema = Schema({
        Optional('view_props', default=dict): dict,
        Optional('config', default=dict): dict,
        })

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        view_props = {
                'className': 'mx-2 my-2',
                'style': {
                    'height': 800
                    },
                }
        rupdate(view_props, self.view_props)

        self._view_div = self.child(
                html.Div, **view_props)
        self._view_div.set_wildcard_prop('data-init', self.config)

    def setup_layout(self, app):
        view_div = self._view_div
        container = self
        container.child(html.Div([
            html.Link(
                rel='stylesheet',
                href='https://aladin.u-strasbg.fr/AladinLite/api/v2/latest/aladin.min.css'  # noqa: E501
            )]))
        jquery_url = 'https://code.jquery.com/jquery-1.12.1.min.js'
        al_url = 'https://aladin.u-strasbg.fr/AladinLite/api/v2/latest/aladin.min.js'  # noqa: E501
        alview_url = resolve_url(f'/js/alview_{view_div.id}.js')
        container.child(dji.Import, src=jquery_url)
        container.child(dji.Import, src=al_url)
        container.child(dji.Import, src=alview_url)

        @app.server.route(alview_url, endpoint=view_div.id)
        def alview_js():
            return self.make_aladin_lite_js(view_div.id)

    @property
    def output_fov(self):
        return Output(self._view_div.id, 'data-fov')

    @property
    def output_survey(self):
        return Output(self._view_div.id, 'data-survey')

    @property
    def output_target(self):
        return Output(self._view_div.id, 'data-target')

    @property
    def outputs(self):
        return [getattr(self, k) for k in ['fov', 'survey', 'target']]

    @staticmethod
    def make_aladin_lite_js(component_id):
        """Return Aladin Lite javascript snippet for `component_id`."""
        template = Template("""
    // the DOM element that holds the aladin lite app.
    const dal = document.getElementById('{{id}}');

    // init props
    function dal_get_init() {
        default_init = {
            showControl: false,
            cooFrame: "J2000",
            showFullscreenControl: false,
            showFrame: false,
            showGotoControl: false,
            fov: 0.5,
            survey: 'P/DSS2/color',
            target: 'M1',
        };
        var init = JSON.parse(dal.getAttribute('data-init'));
        if (init) {
            return {...default_init, ...init};
        };
        return default_init;
    };

    function dal_get_fov() {
        return parseFloat(dal.getAttribute('data-fov'));
    };

    function dal_get_survey() {
        return dal.getAttribute('data-survey');
    };

    function dal_get_target() {
        return dal.getAttribute('data-target');
    };

    var dal_init = dal_get_init();
    console.log('dal_init: ', dal_init);
    var aladin = A.aladin('#{{id}}', dal_init);


    function update_aladin() {
        var fov = dal_get_fov();
        if (fov) {
            aladin.setFov(fov);
        };

        var survey = dal_get_survey();
        if (survey) {
            aladin.setImageSurvey(survey);
        };

        var target = dal_get_target();
        if (target) {
            aladin.gotoObject(target);
        };
    };

    // setup watcher to update aladin
    const observer = new MutationObserver(function(mutationsList, observer) {
        for(const mutation of mutationsList) {
            if (mutation.type === 'attributes') {
                if (
                    (mutation.attributeName === 'data-fov') ||
                    (mutation.attributeName === 'data-survey') ||
                    (mutation.attributeName === 'data-target')
                    ) {
                    update_aladin();
                };
            };
        };
    });

    // Start observing the target node for configured mutations
    observer.observe(dal, {attributes: true, });
    """)
        return template.render(id=component_id, )
