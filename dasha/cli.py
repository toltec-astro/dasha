#!/usr/bin/env python

import os
import sys
from pathlib import Path
import argparse
from tollan.utils.sys import parse_systemd_envfile
import click
from tollan.utils.fmt import pformat_yaml
from tollan.utils.log import init_log, get_logger


__all__ = ['load_env_helper', 'run_demo', 'run_site', 'run_flask']


def load_env_helper():
    """A helper utility to expand env vars defined in systemd environment
    files in shell.
    """
    parser = argparse.ArgumentParser(
            description='Load systemd env file.')
    parser.add_argument(
            'env_files',
            metavar='ENV_FILE', nargs='+',
            help='Path to systemd env file.')
    args = parser.parse_args()
    envs = dict()
    for path in args.env_files:
        envs.update(parse_systemd_envfile(path))
    cmd = ' '.join(f'{k}="{v}"' for k, v in envs.items())
    # Print the env vars so that it can be captured by the shell
    print(cmd)


def _add_site_env_arg(parser):
    # note that site overrides DASHA_SITE in envfiles.
    parser.add_argument(
            '--site', '-s',
            metavar='NAME',
            default=None,
            help="The module name or path to the site. "
                 "Examples: ~/mysite.py, mypackage.mysite")
    parser.add_argument(
            '--env_files', '-e',
            metavar='ENV_FILE', nargs='*',
            help='Path to systemd env file.')

    def handle_site_env_args(args):
        logger = get_logger()
        envs = dict()
        for path in args.env_files or tuple():
            envs.update(parse_systemd_envfile(path))
        if args.site is not None:
            envs['DASHA_SITE'] = args.site
        if len(envs) > 0:
            logger.info(f"loaded envs:\n{pformat_yaml(envs)}")
        for k, v in envs.items():
            os.environ[k] = v or ''
    return parser, handle_site_env_args


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

    def _run_celery_cmd(name):
        import celery.bin.worker as celery_worker
        import celery.bin.beat as celery_beat
        from .web.celery_app import celery_app
        from .web.extensions.celery import Q
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
                    'queues': [k for k in dir(Q) if not k.startswith('_')],
                    },
                }
        cmd = dispatch_cmd[name](app=celery_app)
        cmd(**dispatch_options.get('worker', dict()))

    def handle_ext_args(args):
        if args.extension == 'flask':
            from .web import create_app
            app = create_app()
            # get port
            port = os.environ.get("FLASK_RUN_PORT", None)
            try:
                port = int(port)
            except Exception:
                port = 8050
            app.run(debug=True, port=port)
        elif args.extension in ['celery', 'beat', 'flower']:
            e = args.extension
            dispatch_cmd = {
                    'celery': 'worker',
                    }
            _run_celery_cmd(dispatch_cmd.get(e, e))
        else:
            raise NotImplementedError
    return parser, handle_ext_args


def run_site():
    """A helper utility to run DashA site."""

    parser = argparse.ArgumentParser(
            description='Run DashA site.')
    parser, handle_site_env_args = _add_site_env_arg(parser)
    parser, handle_ext_args = _add_ext_arg(parser)
    args = parser.parse_args()
    handle_site_env_args(args)
    handle_ext_args(args)


def run_demo():
    """A helper utility to run the examples in `~dasha.examples`"""

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


@click.command(context_settings={"ignore_unknown_options": True})
@click.argument('args', nargs=-1)
@click.pass_context
def run_flask(ctx, args):
    """Run DashA site."""
    # this is just a wrapper to an argumentparser.

    if len(args) > 0:
        cmd_self = sys.argv[1:sys.argv.index(args[0])]
    else:
        cmd_self = sys.argv[1:]

    parser = argparse.ArgumentParser(
            description='Run DashA site.',
            prog='flask {}'.format(' '.join(cmd_self)))
    parser, handle_site_env_args = _add_site_env_arg(parser)

    init_log(level='INFO')

    args = parser.parse_args(args)
    handle_site_env_args(args)
    os.environ['FLASK_APP'] = 'dasha.web.app'

    # get port
    port = os.environ.get("FLASK_RUN_PORT", None)
    try:
        port = int(port)
    except Exception:
        port = 8050
    from flask.cli import run_command
    ctx.parent.invoke(run_command, reload=True, port=port)
