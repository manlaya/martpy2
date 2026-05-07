#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# TODO, revoir postproc avec fich congif TOML,
# +mettre un entry point

import os

from common import (
    init_parser,
    read_toml
)


def main():
    parser = init_parser(
        'mart-postproc',
        descr='Generic Postprocessing of MARTHE outputs'
    )

    # config = read_toml()
    raise NotImplementedError
