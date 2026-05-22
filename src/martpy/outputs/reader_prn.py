#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from io import StringIO
from itertools import islice

import pandas as pd

from martpy.utils.constant import RENAME_HISTOBIL_HEAD_ZONE
from martpy.utils.helper import from_histo_varname
from martpy.utils.misc import _canonicalize_name


def read_output_time_series(ts_file, normalize_headers=False, lang='fr'):
    """ Read a time series output file (historiq.prn)

    Parameters
    ----------
    ts_file : str, Path
        path to historiq.prn file

    normalize_headers : bool, optional
        if True, the variable level of the column MultiIndex is converted
        to its canonical generic name (lowercase, no accents,
        e.g. ``'charge'``, ``'debit_rivi'``) using
        :func:`~martpy.utils.helper.from_histo_varname`. By default False.
    lang : str, optional
        Language of the .prn file headers (``'fr'`` or ``'en'``). Only used
        when ``normalize_headers=True``. Default ``'fr'``.

    Returns
    -------
    pd.DataFrame
        DataFrame with index=Date and multiheader
        If the marthe model is nested, the header will be 4 levels:
        (variable, grid, coords, name) else 3 levels (variable, coords, name)
        River variable also add a level for the river id (riv_afluent).
    """
    # read first 5 lines to guess nested
    with open(ts_file, encoding='cp1252', mode='r') as f:
        # read max 6 line of headers if nested grids + river_afluent
        head = list(islice(f, 6))

    if len(head) == 0:
        # no data to read, return empty df
        return pd.DataFrame()

    nested = bool(re.match(r".*(Main_Grid|Gigogne).*", "\n".join(head), re.DOTALL|re.I))
    has_riv_afl = bool(re.match(r".*(AF\d+_TR\d+).*", "\n".join(head), re.DOTALL|re.I))

    levels_name = ['variable', 'coords', 'name']
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
    if normalize_headers:
        _vars = df.columns.get_level_values(0)
        df.columns = pd.MultiIndex.from_tuples([
            (from_histo_varname(_vars[i], lang=lang), *cols[1:])
            for i, cols in enumerate(df.columns)
        ], names=levels_name)
    return df


def _clean_prn_header(col):
    """Normalize a water-balance .prn header (no histo mapping, only cleaning).

    Used for histobil/histoclim/histomas headers (e.g. ``'Pluie moyenne'``,
    ``'ETP'``), which are free-form labels and not histo variable names.
    For histo variable normalization, see
    :func:`~martpy.utils.helper.from_histo_varname`.
    """
    return _canonicalize_name(col)


def read_output_water_balance(
    balance_file,
    add_multiindex=True,
    normalize_headers=False,
    encoding='ISO-8859-1'
):
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

    normalize_headers : bool, optional
        if True normalize headers (lowercase, replace spaces/special characters
        by underscores). By default False.

    encoding : str, optional
       encoding of the file, by default 'ISO-8859-1'

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

            if 'riv_dra_lac' in str(balance_file):
                vol = re.search(r'Volumes\s+de\s+Rivi.*res\s+cumul.*s', header, re.I)
                if vol is not None:
                    zone = 'volume'

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
            # df = df.loc[:, [x for x in df.columns if not re.match('Date.*', x)]]
            df = df.drop(list(df.filter(regex='Date.*', axis=1)), axis=1)
            if normalize_headers:
                df.columns = [_clean_prn_header(x) for x in df.columns]
                # df.columns = df.columns.map(_clean_prn_header)  # avoid loop ?
            df.index.name = 'date'
            df = df.assign(zone=zone)
            df = df.set_index('zone', append=True)
            df = df.reorder_levels(['zone', 'date'])
            df = df.apply(pd.to_numeric, errors='coerce', axis=1)  # force numeric types
            df = df.dropna(how='all', axis=0).dropna(how='all', axis=1)  # coerce: non-num --> NaNs, drop here
            df_list.append(df)

    df = pd.concat(df_list, axis=0, ignore_index=False)
    if not add_multiindex:
        df = df.droplevel(0)  # drop zone level, keep only global zone

    return df


def read_prn(prn_file, **kwargs):
    """ Generic function to read a marthe output prn file

    It dispatches to specialized readers based on filename:
    - historiq.prn -> :py:func:`read_output_time_series`
    - histo(bil|mas|clim)*.prn -> :py:func:`read_output_water_balance`

    Parameters
    ----------
    prn_file : str
        Path to the prn file
    **kwargs
        Any addition keyword argument for :py:func:`read_output_water_balance`
        or :py:func:`read_output_time_series`

    Returns
    -------
    pd.DataFrame
        Dataframe with the content of the prn file
    """
    import os
    basename = os.path.basename(prn_file).lower()

    if 'historiq' in basename:
        return read_output_time_series(prn_file, **kwargs)
    elif re.match(r'histo(?:bil|clim|mas)', basename):
        return read_output_water_balance(prn_file, **kwargs)
    else:
        raise ValueError(
            'File is neither a historiq (time series) or histo(bil,clim,mas) (water/mass balance)'
        )
