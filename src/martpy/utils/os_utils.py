#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, shutil
from datetime import datetime

from .config import MART_OUTPUTS


def mk_run_dir(resdir=None):
    """ Create a directory to store the results of a simulation

    Parameters
    ----------
    resdir : str or Path-like, optional
        path to the directory to create, by default None.
        If None a directory named '_run_<date>' is created,
        with date format YYYY-MM-DD_HHMMSS

    Returns
    -------
    str or Path-like
        correspond to resdir. If resdir is None, return the path to the created
        directory with date fmt.
    """
    if resdir is None:
        resdir = '_run_{}'.format(
            datetime.strftime(datetime.now(),format='%Y%m%d_%H%M%S')
        )
    os.makedirs(resdir, exist_ok=True)
    return resdir


def mv_res(dst='./run'):
    """ Move results of a Marthe simulation

    Parameters
    ----------
    dst : str, optional
        destination folder, by default './run'
        if dst does not exist, it is created.

    Returns
    -------
    int:
        status, 0 if success
    """
    os.makedirs(dst, exist_ok=True)
    for foutput in MART_OUTPUTS:
        if os.path.exists(foutput):
            shutil.move(foutput, dst)
    return 0

