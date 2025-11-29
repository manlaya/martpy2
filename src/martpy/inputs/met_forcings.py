#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import numpy as np
import pandas as pd

from martpy.utils.config import _get_resource_file


# TODO: copy SafranGrid dataclass from aquida here, and add methods to
# get met zones from lat/lon or x/y or shapefile, subset tabular data, write new
# files, set in TimeSteps actions, etc.

def read_zone_safran():
    """ Read X, Y center of cells and num safran """
    dfxy = pd.read_csv(
        _get_resource_file('_coordonnees_france_safran_9892.txt'),
        sep=r'\s+',
        header=None,
        skiprows=2,
        names=['zone', 'lat', 'lon', 'xc', 'yc', 'zc'],
        dtype={
            'zone' : np.int32,
            'lat'  : np.float64,
            'lon'  : np.float64,
            'xc'   : np.int32,
            'yc'   : np.int32,
            'zc'   : np.float32
        },
    )
    return dfxy


def write_met_forcings(df, fname):
    """ Write a DataFrame to Marthe sequential forcing file
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with date as index, grid cell/met zone as columns
    fname : str or Path-like
        output file name
    """
    date_col = df.index.name  # get date name
    cols = df.columns  # save met zone for reorder
    df = df.copy().reset_index()
    df = df[list(cols) + [date_col]]  # reorder cols to make date the last one, ignored by marthe
    # write with a '#' at the begining of file, for marthe
    with open(fname, mode="w", newline='') as f:
        f.write("# ")
        df.to_csv(
            f,
            date_format="%Y-%m-%d",
            sep="\t",
            float_format='%.2f',
            index=False,
        )
    return


def read_nzcli(file_nzcli, encoding='ISO-8859-1'):
    with open(file_nzcli, 'r', encoding=encoding) as f:
        nzcli = f.readlines()
    nzcli = '\n'.join([x for x  in nzcli if re.match(r'(\d+\s*)+', x)])  # skip header(s)
    forcing_cells = [int(x) for x in re.split(r'\s+', nzcli.strip())]
    return forcing_cells


def write_nzcli(clim_zone: list, file_nzcli):
    """ Write a climatic zone file (`*.nzcli`)

    Parameters
    ----------
    clim_zone : list if int
       List of climatic zones to use, it links zone grid to data
       (ie some kind of header for climatic tabular data),
       see Marthe general documentation for more informations.
    file_nzcli : str or Path-like.
        file to be written
    """
    with open(file_nzcli, mode='w', encoding='ISO-8859-1') as f:
        f.write('Numéro des {} Zones Météo des fichiers\n'.format(len(clim_zone)))
        f.write('    '.join(clim_zone))
        f.write('\n')
    return
