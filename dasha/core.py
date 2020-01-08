#! /usr/bin/env python

import os
import importlib


def site_from_env():

    ENV_SITE = 'DASHA_SITE'

    module = os.environ.get(
            ENV_SITE, "dasha.example_site")

    if module is None:
        raise RuntimeError(
                f"Unable to import {ENV_SITE} site module."
                f" Specify via environment variable {ENV_SITE} with"
                f" a valid import path"
                )

    return importlib.import_module(module)
