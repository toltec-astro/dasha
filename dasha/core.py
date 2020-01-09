#! /usr/bin/env python

import os
import sys
import importlib
from pathlib import Path


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

    try:
        return importlib.import_module(module)
    except Exception:
        path = Path(module).expanduser().resolve()
        sys.path.insert(0, path.parent.as_posix())
        return importlib.import_module(path.name)
