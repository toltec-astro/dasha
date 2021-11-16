#!/usr/bin/env python


from wrapt import ObjectProxy
from flask_dance.contrib.github import make_github_blueprint, github
from schema import Schema, Optional
from flask import redirect, url_for, Blueprint


__all__ = ['auth', 'github_auth', 'github']


auth = ObjectProxy(Blueprint('auth', __name__, url_prefix='/auth'))
"""A parent blueprint for all auth views."""


github_auth = ObjectProxy(None)
"""The blueprint for GitHub auth."""


def get_github_login_url():
    """Return the GitHub login URL."""
    return url_for("auth.github.login")


def is_authorized():
    """Return True if authorized."""
    return github.authorized


def get_github_user_info():
    """Return GitHub user info."""
    resp = github.get("/user")
    if resp.ok:
        return resp.json()
    return None


@auth.route("/")
def login():
    if not is_authorized():
        return redirect(get_github_login_url())
    user_info = get_github_user_info()
    s = "You are @{login} on GitHub".format(login=user_info['login'])
    return s


@auth.route("/logout")
def logout():
    if is_authorized():
        del github_auth.token
    return redirect(url_for("/"))


def init_ext(config):
    config_schema = Schema({
        'client_id': str,
        Optional('client_secret', default='true'): str
        })
    config = config_schema.validate(config)
    bp = github_auth.__wrapped__ = make_github_blueprint(
        client_id=config['client_id'],
        client_secret=config['client_secret']
        )
    auth.register_blueprint(bp, url_prefix="/login")
    return auth


def init_app(server, config):
    """Setup `auth` for `server`."""
    server.register_blueprint(auth)
