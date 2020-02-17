#!/usr/bin/env python

import argparse


def load_env_helper():
    """A helper utility to load env vars from systemd env files."""
    parser = argparse.ArgumentParser(description='Run command with systemd env file.')
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
