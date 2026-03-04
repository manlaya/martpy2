#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from io import StringIO

import pandas as pd

from martpy.utils.constant import RENAME_HISTOBIL_HEAD_ZONE


def read_output_time_series(ts_file):
    """ Read a time series output file (historiq.prn)

    Parameters
    ----------
    ts_file : str, Path
        path to historiq.prn file

    Returns
    -------
    pd.DataFrame
        DataFrame with index=Date and multiheader
        If the marthe model is nested, the header will be 4 levels:
        (field, grid, coords, name) else 3 levels (field, coords, name)
    """
    # read first 5 lines to guess nested
    with open(ts_file, encoding='cp1252', mode='r') as f:
        # max 6 line of headers if nested grids + river_afluent
        head = [next(f) for x in range(6)]

    nested = bool(re.match(r".*(Main_Grid|Gigogne).*", "\n".join(head), re.DOTALL|re.I))
    has_riv_afl = bool(re.match(r".*(AF\d+_TR\d+).*", "\n".join(head), re.DOTALL|re.I))

    levels_name = ['field', 'coords', 'name']
    if nested:
        levels_name.insert(2, 'grid')
    if has_riv_afl:
        levels_name.insert(levels_name.index('name'), 'riv_afluent')

    if not re.match('^#', head[len(levels_name)]):
        levels_name.pop(-1)  # if no name, drop last header / header start with #

    headers = [i+1 for i, _ in enumerate(levels_name)]

    df = pd.read_csv(
        ts_file, sep='\t', encoding='cp1252',
        header=headers, index_col=0,
        parse_dates=True, dayfirst=True, #infer_datetime_format=True
    )

    df = df.dropna(how='all', axis=1)  # drop empty col at the end
    #rename columns levels and index
    df.columns = df.columns.rename(levels_name, level=[i-1 for i in headers])
    df = df.rename_axis("date", axis=0)
    # remove int step col if present:
    df = df.loc[:,~df.columns.get_level_values(-1).str.match('.*<Date>')]
    return df


def read_output_water_balance(balance_file, add_multiindex=True, encoding='ISO-8859-1'):
    """ Read a water balance output file

    This function reads histobil_debit.prn/histoclim.prn or any balance *.prn file
    and return a pandas DataFrame with a multiindex columns: date, zone.

    If the balance file is zonal, zone level will take the zone number.
    Additionally, a 'global' zone will be created with the sum of all zones.

    If the balance file is not zonal, only a 'global' zone level will be created.

    Parameters
    ----------
    balance_file : str, Path
        path to bilan.prn file

    add_multiindex : bool, optional
        if True, add a multiindex to columns (date, zone), by default True
        if False, return a single index with date only (only 'global' zone is kept)

    Returns
    -------
    pd.DataFrame
        DataFrame with index=(date, zone)
    """
    with open(balance_file, encoding=encoding, mode='r') as f:
        content = f.read()

    # split by blank lines
    blocks = re.split(r'\n\s*\n', content)  # or ^\s*$, re.MULTILINE)

    # parse each block
    df_list = []
    for block in blocks:
        if re.match(r'.*^\s*Date\s+', block, re.MULTILINE|re.DOTALL|re.IGNORECASE):
            # if block contain Date header, it is a data block
            # get index of Date line (i.e remove any comment before)
            istart = re.search(r'^\s*Date\s+', block, re.M|re.I).start()

            # parse header to get zones
            header = block[:istart]
            # match Zone X or Zone = X (different version of Marthe)
            zone = re.search(r'zone\s+(?:=\s*)?(\d+)', header, re.IGNORECASE)
            zone = zone.group(1) if zone is not None else 'global'

            if not add_multiindex and zone != 'global':
                continue  # if not add_multiindex, only read global zone

            # then read block with pd.read_csv
            df = pd.read_csv(
                StringIO(block[istart:]), sep='\t', encoding=encoding,
                header=0 if zone == 'global' else [0, 1],
                index_col=0,
                parse_dates=True,
                dayfirst=True,  # infer_datetime_format is deprecated
            )
            df = df.dropna(axis=1, how='all')  # empty col at the end

            if zone != 'global':
                # remove unused level of columns
                df.columns = df.columns.droplevel(1)
                # rename columns, to match 'global' zone
                df = df.rename(RENAME_HISTOBIL_HEAD_ZONE, axis=1)

            # clean dataframe
            # drop int date col if present
            df = df.loc[:, [x for x in df.columns if not re.match('Date.*', x)]]
            df.index.name = 'date'
            df = df.assign(zone=zone)
            df = df.set_index('zone', append=True)
            df = df.reorder_levels(['zone', 'date'])

            df_list.append(df)
    df = pd.concat(df_list, axis=0, ignore_index=False)
    if not add_multiindex:
        df = df.droplevel(0)  # drop zone level, keep only global zone
    return df


def read_prn(prn_file):
    """ Generic function to read a marthe output prn file

    It dispatches to specialized readers based on filename:
    - historiq.prn -> read_output_time_series
    - histobil*.prn -> read_output_water_balance

    Parameters
    ----------
    prn_file : str
        Path to the prn file

    Returns
    -------
    pd.DataFrame
        Dataframe with the content of the prn file
    """
    import os
    basename = os.path.basename(prn_file).lower()

    if 'historiq' in basename:
        return read_output_time_series(prn_file)
    elif 'histobil' in basename or 'histoclim' in basename:
        return read_output_water_balance(prn_file)
    else:
        raise ValueError(
            'File is neither a historiq (time series) or histobil/histoclim (water balance)'
        )
