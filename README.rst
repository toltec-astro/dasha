A multi-page Dash app framework.
--------------------------------

.. image:: http://img.shields.io/badge/powered%20by-AstroPy-orange.svg?style=flat
    :target: http://www.astropy.org
    :alt: Powered by Astropy Badge

DashA is a multi-page Dash app framework that supports seamless integration
with a variety of common backend services/extensions including:

* Co-existence with other Flask endpoints
* Flask-SQLAlchemy
* Cache
* Cache/IPC with Redis
* Celery
* Authentication with Flask-Dance

Installation and Usage
----------------------

.. Note:: Tollan is a utility library used by dasha but is not listed in the
    ``setup.cfg`` file yet. Therefore it has to be installed manually
    for now.

To install::

   $ pip install git+https://github.com/toltec-astro/tollan.git
   $ pip install git+https://github.com/toltec-astro/dasha.git

See ``dasha -h`` for usage.

Dasha comes with a set of examples that can be found in ``dasha/examples/``.
See ``dasha_demo -h`` for a list of the examples. For example, to run the
example named ``dasha_intro``::

   $ dasha_demo dasha_intro

The same examples can also be run via the full ``dasha`` command::

   $ dasha -s dasha.examples.dasha_intro

The command above will run the flask server in development mode,
and you'll see the page in live with your favorite browser::

    http://localhost:8050


License
-------

This project is Copyright (c) Zhiyuan Ma and licensed under
the terms of the BSD 3-Clause license. This package is based upon
the `Astropy package template <https://github.com/astropy/package-template>`_
which is licensed under the BSD 3-clause licence. See the licenses folder for
more information.
