A multi-page dash app framework.
--------------------------------

.. image:: http://img.shields.io/badge/powered%20by-AstroPy-orange.svg?style=flat
    :target: http://www.astropy.org
    :alt: Powered by Astropy Badge

DashA is a multi-page dash app framework that allows create complex and
reusable pages.


Installation and Usage
----------------------

.. note::
    Tollan is a utility library used by dasha but is not listed in the
    ``setup.cfg`` file yet. Therefore it has to be installed manually
    for now.

.. code::txt
   $ pip install git+https://github.com/toltec-astro/tollan.git
   $ pip install git+https://github.com/toltec-astro/dasha.git

See ``dasha -h`` for usage.

Dasha comes with a set of examples that can be found in ``dasha/examples/``.
See ``dasha_demo -h`` for a list of the examples. For example, to run the
example named ``dasha_intro``:

.. code::txt
   $ dasha_demo dasha_intro

The same examples can also be run via the full ``dasha`` command:

.. code::txt
   $ dasha -s dasha.examples.dasha_intro


License
-------

This project is Copyright (c) Zhiyuan Ma and licensed under
the terms of the BSD 3-Clause license. This package is based upon
the `Astropy package template <https://github.com/astropy/package-template>`_
which is licensed under the BSD 3-clause licence. See the licenses folder for
more information.


Contributing
------------

We love contributions! DashA is open source,
built on open source, and we'd love to have you hang out in our community.

**Imposter syndrome disclaimer**: We want your help. No, really.

There may be a little voice inside your head that is telling you that you're not
ready to be an open source contributor; that your skills aren't nearly good
enough to contribute. What could you possibly offer a project like this one?

We assure you - the little voice in your head is wrong. If you can write code at
all, you can contribute code to open source. Contributing to open source
projects is a fantastic way to advance one's coding skills. Writing perfect code
isn't the measure of a good developer (that would disqualify all of us!); it's
trying to create something, making mistakes, and learning from those
mistakes. That's how we all improve, and we are happy to help others learn.

Being an open source contributor doesn't just mean writing code, either. You can
help out by writing documentation, tests, or even giving feedback about the
project (and yes - that includes giving feedback about the contribution
process). Some of these contributions may be the most valuable to the project as
a whole, because you're coming to the project with fresh eyes, so you can see
the errors and assumptions that seasoned contributors have glossed over.

Note: This disclaimer was originally written by
`Adrienne Lowe <https://github.com/adriennefriend>`_ for a
`PyCon talk <https://www.youtube.com/watch?v=6Uj746j9Heo>`_, and was adapted by
DashA based on its use in the README file for the
`MetPy project <https://github.com/Unidata/MetPy>`_.
