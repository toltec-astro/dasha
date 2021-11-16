#!/usr/bin/env python

from flask import Blueprint, Flask

bp = Blueprint('simple_flask_view_bp', __name__)


@bp.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


def server():
    app = Flask(__name__)
    app.register_blueprint(bp)
    return app


DASHA_SITE = {'server': server}
