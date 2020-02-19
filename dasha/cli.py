#!/usr/bin/env python

import os
from pathlib import Path
import argparse


def load_env_helper():
    """A helper utility to load env vars from systemd env files."""
    parser = argparse.ArgumentParser(
            description='Load systemd env file.')
    parser.add_argument(
            'env_files',
            metavar='ENV_FILE', nargs='+',
            help='Path to systemd env file.')
    args = parser.parse_args()
    envs = dict()
    for path in args.env_files:
        with open(path, 'r') as fo:
            for ln in fo.readlines():
                ln = ln.strip()
                if ln.strip().startswith("#"):
                    continue
                k, v = map(str.strip, ln.split('=', 1))
                envs[k] = v
    cmd = ' '.join(f'{k}="{v}"' for k, v in envs.items())
    print(cmd)


def run_demo():
    """A helper utility to run the demos."""

    all_demos = {
                p.stem: p
                for p in
                filter(
                    lambda p: not p.name.startswith('_'),
                    Path(__file__).parent.joinpath(
                        'examples').glob("*.py")
                    )
                }
    all_demo_names = list(all_demos.keys())
    all_ext_procs = ['flask', 'celery', 'beat', 'flower']
    parser = argparse.ArgumentParser(
            description='Run the DashA demos.')
    parser.add_argument(
            'name',
            metavar='NAME',
            choices=all_demo_names,
            help="The name of the demo to run."
                 " Available demos: {}".format(", ".join(all_demo_names))
            )
    parser.add_argument(
            'extension',
            metavar='EXT',
            choices=all_ext_procs,
            nargs='?',
            default='flask',
            help="The extension process to run"
                 " Available options: {}".format(", ".join(all_ext_procs))
            )

    args = parser.parse_args()

    site = all_demos[args.name].as_posix()
    os.environ['DASHA_SITE'] = site

    import celery.bin as celery_bin

    def run_celery_service(name):
        from .web.celery_app import celery
        dispatch_cls = {
                'worker': celery_bin.worker.worker,
                }
        dispatch_options = {
                'worker': {
                    'loglevel': 'DEBUG',
                    'traceback': True,
                    },
                }
        service = dispatch_cls['worker'](app=celery)
        service.run(**dispatch_options.get('worker', dict()))

    if args.extension == 'flask':
        from .web import create_app
        app = create_app()
        app.run(debug=True, port=8050)
    elif args.extension == 'celery':
        run_celery_service('worker')
    elif args.extension == 'flower':
        run_celery_service('flower')
    else:
        raise NotImplementedError
