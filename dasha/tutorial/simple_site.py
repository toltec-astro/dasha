#! /usr/bin/env python

"""

==============
DashA Tutorial
==============

This is a file that shows how to set up a dasha page.

While the code implements a example site, below I describe
the relavent concepts of the dasha framework, as well as the
instruction to run the code.

Concepts
========

Site
----

"Site" is a user-defined python module that contains all
information including from server config to actual dash pages.

The site module itself servers as a flask config object. Any flask
or dash configurations can be set here. For example:

.. code-block::

    # example_site.py
     
    # Note that Dash config are those kwargs that is defined in the
    # `dash.Dash` class constructor. They have to be ALL CAPS to be
    # picked up.
    TITLE = "Dash App"  # This will translate to `dash.Dash(title="Dash App")`

    SQLALCHEMY_DATABASE_URL = "sqlite:///memory" #  This will be updated to `flask.Flask.config`.
    #

Arbituary variables can be defined in the site module, but in order to
define the dash pages, one need to define at least one of the belows:

* `frontend`: This is of the lowest level customization
  entry point. A method `frontend.init_app(app)`  is expected. An
  minimum frontend module may look like:
  
  .. code-block::

      class frontend:
          @staticmethod
          def init_app(app):
              # `app` is the current dash app.
              # Do whatever to it to setup.
              app.layout = html.Div("Hello World!")

* `pages`: This is a higher level customization entry point. The value
  of this variable shall be a list of dictionaries that defines the
  pages of the dash app.
  
  
Page
----
  
The page definition dict has to have some special entries:

- "label": This is used to label (and namespace) each page.
If multiple pages are defined, the label has to be unique.

- "title_text": This is used as the text shown in the navigation
sidebar.

- "template": This can be a string or a python module. A string is
equivalent to specifying a python module that ships with dasha
in `dasha/web/frontend/template/` folder. The module is expect to
have an attribute `template_cls`, whose value is a subclass of
`dasha.web.frontend.templates.SimplePageTemplate`.


Template
--------

A valid template class (the value of `template_cls` of in the `template` specified
in the list of page dicts) shall be a subclass of `dasha.web.frontend.template.SimplePageTemplate`.

It should be set up to do two things:

1. Set up the dash app callbacks. For the life time of an instance, these can only be
   executed once. A good place to put the callback setups is the constructor.

2. Set up the dash app layout. For the lifetime of an template instance, the
   layout will be queried multiple times via the instance's method `get_layout`,
   so expensive calculation for persistence data shall be put *outside* of
   `get_layout` function.

As an example, please consult the source code in ``dash/web/frontend/templates/simple.py``.


How-to-run
==========

We use flask as the backend server.

The directory `dasha/web` contains an `app.py` file that serves as the entry point script.

The best way to run the development server is to cd into `dasha/web`, and do

.. code-block:: bash

    $ DASHA_SITE=<path to site module> flask run

There are two ways to specify the ``DASHA_SITE``:

* A valid import path. For example `DASHA_SITE=dasha.tutorial.simple_site flask run`

* A valid path to a python module. For example `DASHA_SITE=../tutorial/simple_site flask run`
  Note that here there is no `.py` suffix to the path.

The server is running by default on ``::8050``.

"""
      
TITLE = "Simple"

from dasha.web.frontend.templates.simple import MySimplePageTemplate
from dasha.web.frontend.templates import SimplePageTemplate
import dash_html_components as html


class my_simple_template(object):
    class YetAnotherSimplePageTemplate(MySimplePageTemplate):

        def get_layout(self):
            layout = super().get_layout()
            layout.children.append(html.Div("... World."))
            return layout

    # this is needed to make `my_simple_template` recognized as a template
    template_cls = YetAnotherSimplePageTemplate


class my_simple_template2(object):
    class MyTemplateFromScratch(SimplePageTemplate):
        def get_layout(self):
            return html.Div("My template from scratch, ho-ho-ho!")

    template_cls = MyTemplateFromScratch


pages = [
        {
            "label": "simple",
            "template": 'simple',
            "title_text": "Predefined template",
            },
        {
            "label": "my_simple",
            "template": my_simple_template,
            "title_text": "Extending a template",
            },
        {
            "label": "my_simple2",
            "template": my_simple_template2,
            "title_text": "Template from scratch",
            },
        ]

