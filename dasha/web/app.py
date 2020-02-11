#! /usr/bin/env python

"""Flask script entry point."""

if __package__:
    from . import create_app  # noqa: F401
else:
    # this is to work around the connexion api resolver problem
    from dasha.web import create_app  # noqa: F401


if __name__ == "__main__":
    app = create_app()
    app.run(port=8050)
