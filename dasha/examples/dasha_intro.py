#! /usr/bin/env python


"""
This is the default DashA site returned by

.. code-block:: bash

    $ dasha

"""

# The server can be ignored which is to use the default flask server.
# server is expected to be a callable, and it may optionally accept
# a namespace object containing ALLCAPS attributes defined in this module
# as the sole argument.
# ALLCAP keys go in to default server config
ENV = 'development'

extensions = [
        {
            'module': 'dasha.web.extensions.dasha',
            'config': {
                'template': 'dasha.web.templates.dasha_intro',
                'title_text': 'DashA Intro',
                # ALLCAPS keys go into the Dash app config
                'TITLE': 'DashA Site'
                }
            }
        ]
