#! /usr/bin/env python

import os
from pathlib import Path
import configparser
import importlib


def config_from_rc():
    rcfile = Path(os.environ.get(
            "DASHPAGESRC", "~/.dashpagesrc")).expanduser()

    if not rcfile.exists():

        raise RuntimeError(
                "Unable to locate dashpagesrc file."
                " Either specify via environment variable DASHPAGESRC or"
                " create the file ~/.dashpagesrc."
                )

    config = configparser.ConfigParser()
    config.read(rcfile)

    return config


def site_from_env():
    module = os.environ.get(
            "DASHPAGES_SITE", None)

    if module is None:
        raise RuntimeError(
                "Unable to import dashpages site module."
                " Specify via environment variable DASHPAGES_SITE with"
                " a valid import path"
                )

    return importlib.import_module(module)
