#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import textwrap
from argparse import ArgumentParser, RawDescriptionHelpFormatter


# The following should be included in every verbose output of CLI scripts.
# see scripts/common.py for example with argparse
_copyleft = """
    {program}  Copyright (C) {year}  {name_of_author_for_copyright}.
    This program comes with ABSOLUTELY NO WARRANTY.
    This is free software, see GNU General Public Lisence v3 for copying.
""".format(program='martpy', year=2025, name_of_author_for_copyright='BRGM')


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
