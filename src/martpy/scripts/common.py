#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import textwrap
from argparse import ArgumentParser, RawDescriptionHelpFormatter

from ..version import _copyleft


def init_parser(prog_name, descr):
    return ArgumentParser(
        prog=prog_name,
        formatter_class=RawDescriptionHelpFormatter,
        description=descr,
        epilog=textwrap.dedent(_copyleft)
    )


def read_toml(ftoml: str, encoding='utf-8'):
    from sys import version_info
    if version_info.minor >= 11:
        import tomllib  # in stdlib
        with open(ftoml, 'rb', encoding=encoding) as f:
            params = tomllib.load(f)
    else:
        import toml  # external dependancy
        with open(ftoml, 'r', encoding='utf-8') as f:
            params = toml.load(f)
    return params
