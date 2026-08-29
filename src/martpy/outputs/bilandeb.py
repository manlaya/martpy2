# -*- coding: utf-8 -*-

import re
import io
import pandas as pd
import xarray as xr


def extract_layer_transfers(
    marthe_file: str, netcdf_file: str = None
) -> xr.Dataset | None:
    """Extract layer transfers from MARTHE "bilandeb.txt" file.

    Parameters
    ----------
    marthe_file : str
        Path (including file name) to the MARTHE file containing the
        layer transfers (typically named "bilandeb.txt").
    netcdf_file : str, optional
        Path (including file name with extension *.nc) to the netCDF
        file in which to store the layer transfers. If not provided,
        the layer transfers are returned as a `xarray.Dataset`.

    Returns
    -------
    xarray.Dataset or None
        The dataset containing the layer transfers. If ``netcdf_file``
        parameter is provided, `None` is returned and a netCDF file
        containing the layer transfers is written instead.

    """
    with open(marthe_file, 'r', encoding='cp1252') as f:
        txt = f.read()

    # find all dates
    dates = []

    dates.extend(
        re.compile('Date calendaire : ([0-9]{2}/[0-9]{2}/[0-9]{4})').findall(txt)
    )
    dates.extend(
        re.compile('Fin du pas : ([0-9]{2}/[0-9]{2}/[0-9]{4})').findall(txt)
    )

    dates = pd.to_datetime(dates, format='%d/%m/%Y')

    # find all blocks containing layer transfer tables
    re_blocks = (
        "Débits échangés entre les [0-9]* couches"
        "\n\n((?s:.)*?)\n                Somme totale"
    )

    blocks = re.compile(re_blocks).findall(txt)

    re_parts = (
        r" Num \| Contribution des couches \( > 0 si la couche "
        r"exporte ; < 0 si elle reçoit\)" + "\n" + "((?s:.)*?)" + "\n\n"
    )

    dfs = []

    for t, block in enumerate(blocks):
        # find all parts of the layer transfer table
        parts = re.compile(re_parts).findall(block)

        # process and clean layer transfer table
        df = None

        for part in parts:
            # use regex string match and read it with pandas
            df_ = pd.read_csv(io.StringIO(part), sep='|', dtype=str)

            # get rid of white spaces
            df_.columns = df_.columns.str.strip()
            df_ = df_.apply(lambda x: x.str.strip())

            # get rid of empty lines
            df_ = df_[pd.to_numeric(df_['Couc'], errors='coerce').notnull()]
            df_ = df_.set_index('Couc')

            # # only keep columns corresponding to layers + recharge
            df_ = pd.concat(
                [
                    df_.loc[:, pd.to_numeric(df_.columns, errors='coerce').notnull()],
                    df_.loc[:, 'Recharg']
                ],
                axis=1
            )

            # rename given columns
            df_ = df_.rename(columns={'Recharg': 'recharge'})

            # deal with scientific notation problem
            df_ = df_.replace('-', 'e-', regex=True)
            df_ = df_.replace(r'^e', '', regex=True)

            # deal with empty diagonal
            df_ = df_.replace('*', 'NAN')

            # convert strings to floating points
            df_ = df_.astype(float)

            # append to potential other blocks
            df = pd.concat([df, df_], axis=1)

        # drop duplicated columns (i.e. 'Recharge')
        df = df.T.drop_duplicates(keep='last').T

        dfs.append(df)

    # merge all blocks
    if len(dates) == len(dfs):
        dfs = pd.concat(dfs, keys=dates)
    else:
        # if the number of dates found is different from the number
        # of transfer blocks, do not use dates and use range instead
        dfs = pd.concat(dfs, keys=range(len(dfs)))

    # rename axes
    dfs.index.names = ['time', 'layer']
    dfs.columns.names = ['destination']

    # turn column index into categorical to make sure order will be
    # preserved in dimension of xarray dataset
    dfs.index = dfs.index.set_levels(
        pd.Categorical(
            dfs.index.levels[1], categories=dfs.index.levels[1], ordered=True
        ),
        level=1
    )

    dfs.columns = pd.Index(
        pd.Categorical(dfs.columns, categories=dfs.columns, ordered=True),
        name=dfs.columns.name
    )

    # split into two dataframes for layer transfers and for recharge
    dfs_lyr = dfs.iloc[:, :-1]
    dfs_rch = dfs.iloc[:, -1]

    # add destination as a third level to multi-index
    dfs_lyr = pd.melt(dfs_lyr, value_name='transfer', ignore_index=False)
    dfs_lyr = dfs_lyr.set_index('destination', append=True)

    # convert to xarray
    ds = xr.merge(
        [dfs_lyr.to_xarray(), dfs_rch.to_xarray()]
    )

    if netcdf_file is not None:
        ds.to_netcdf(netcdf_file)
    else:
        return ds
