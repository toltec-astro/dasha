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
    # Print the env vars so that it can be captured by the shell
    print(cmd)


def _add_ext_arg(parser):
    _all_ext_procs = ['flask', 'celery', 'beat', 'flower']
    parser.add_argument(
            'extension',
            metavar='EXT',
            choices=_all_ext_procs,
            nargs='?',
            default='flask',
            help="The extension process to run"
                 " Available options: {}".format(", ".join(_all_ext_procs))
            )

    def handle_ext_args(args):
        if args.extension == 'flask':
            from .web import create_app
            app = create_app()
            app.run(debug=True, port=8050)
        elif args.extension in ['celery', 'beat', 'flower']:
            e = args.extension
            dispatch_cmd = {
                    'celery': 'worker',
                    }
            _run_celery_cmd(dispatch_cmd.get(e, e))
        else:
            raise NotImplementedError
    return parser, handle_ext_args


def _run_celery_cmd(name):
    import celery.bin.worker as celery_worker
    import celery.bin.beat as celery_beat
    from .web.celery_app import celery
    from flower.command import FlowerCommand

    class _flower(FlowerCommand):
        def run(self, *args, **kwargs):
            return self.run_from_argv('flower', (), **kwargs)

    dispatch_cmd = {
            'worker': celery_worker.worker,
            'beat': celery_beat.beat,
            'flower': _flower
            }
    dispatch_options = {
            'worker': {
                'loglevel': 'DEBUG',
                'traceback': True,
                },
            }
    cmd = dispatch_cmd[name](app=celery)
    cmd(**dispatch_options.get('worker', dict()))


def run():
    """A helper utility to run dasha site."""

    parser = argparse.ArgumentParser(
            description='Run DashA site.')
    parser.add_argument(
            'site',
            metavar='NAME',
            help="The module name or path to the site. "
                 "Examples: ~/mysite.py, mypackage.mysite")
    parser, handle_ext_args = _add_ext_arg(parser)
    args = parser.parse_args()
    os.environ['DASHA_SITE'] = args.site
    handle_ext_args(args)


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
    parser = argparse.ArgumentParser(
            description='Run the DashA demos.')
    parser.add_argument(
            'name',
            metavar='NAME',
            choices=all_demo_names,
            help="The name of the demo to run."
                 " Available demos: {}".format(", ".join(all_demo_names))
            )
    parser, handle_ext_args = _add_ext_arg(parser)
    args = parser.parse_args()
    site = all_demos[args.name].as_posix()
    os.environ['DASHA_SITE'] = site
    handle_ext_args(args)
