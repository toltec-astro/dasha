from .backend.db_config import *  # noqa: F401, F403

TITLE = "DashA"

# The value of this parameter will be propagated into both
# `app.scripts.config.serve_locally` and `app.css.config.serve_locally`
SERVE_LOCALLY = True

#
# Dash.__init__ keyword arguments
#

# URL prefix for client-side requests and client-side requests. If not None,
# must begin and end with a '/'.
REQUESTS_PATHNAME_PREFIX = None

# URL prefix for server-side routes. If not None, must begin and end with a
# '/'.
ROUTES_PATHNAME_PREFIX = None

# Externally hosted CSS files go in here. If you want to use Bootstrap from a
# CDN, Dash Bootstrap Components contains links to bootstrapcdn:
#
# import dash_bootstrap_components as dbc
# EXTERNAL_STYLESHEETS = [dbc.themes.BOOTSTRAP]
#
# or if you want to use a Bootswatch theme:
#
# import dash_bootstrap_components as dbc
# EXTERNAL_STYLESHEETS = [dbc.themes.CYBORG]
EXTERNAL_STYLESHEETS = []

# Externally hosted Javascript files go in here.
EXTERNAL_SCRIPTS = []

# Meta tags for viewport responsiveness
META_TAGS = [
        {
            "name": "viewport",
            "content": "width=device-width, initial-scale=1, shrink-to-fit=no"
        }
    ]
