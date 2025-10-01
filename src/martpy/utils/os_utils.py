#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, shutil
from datetime import datetime

from .config import MART_OUTPUTS


def mk_run_dir(resdir=None):
    if resdir is None:
        resdir = '_run_{}'.format(
            datetime.strftime(datetime.now(),format='%Y%m%d_%H%M%S')
        )
    os.makedirs(resdir, exist_ok=True)
    return resdir


def mv_res(dst='./run'):
    os.makedirs(dst, exist_ok=True)
    for foutput in MART_OUTPUTS:
        if os.path.exists(foutput):
            shutil.move(foutput, dst)
    return 0

