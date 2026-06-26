#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
import numpy as np
import pandas as pd


def _get_nearest_date(df, tol=7):
    return df.index.get_indexer(df.index.values, method='nearest', tolerance=tol)


def get_interval_time(dtimeindex, windows_size=0.5):
    # dt time index need to be sorted
    # get interval between pastp
    return round((- pd.Series(dtimeindex[::-1]).diff().dt.days).mean() * windows_size)


def dt_replace(series, year=None, month=None, day=None):
    return pd.to_datetime(
        {
            'year': series.dt.year if year is None else year,
            'month': series.dt.month if month is None else month,
            'day': series.dt.day if day is None else day
        }
    )


def dt_index_replace(df):
    df.index = [
         datetime(d.year, d.month, 1) for d in df.index
     ]
    return df


def resample_multiindex(df, level_date, freq='M', agg='mean'):
    level_values = df.index.get_level_values
    grouper = (
        [pd.Grouper(freq=freq, level=level_date)] +
        [x for x in level_values if x.name != level_date]
    )
    return df.groupby(grouper).agg(agg)


def count_days(df):
    # get count for metD
    df = df.copy() # avoid side effects

    # compute diff of reverse datetime index to get time lapse
    timedt = - pd.Series(df.index[::-1]).diff().dt.days
    # reverse again to get back to time order, and reindex with dates
    timedt = pd.Series(timedt[::-1].to_numpy(), index=df.index)
    # diff[0] == np.nan so compute manually
    # so, get max date of last tendays, add 1 (start of next 10d), compute diff in days
    timedt.iloc[-1] = (timedt.index[-1] + pd.DateOffset(day=31) - timedt.index[-1]).days +1

    # affect in new col
    # df['count'] = timedt

    return timedt


def create_marthe_io(ts, date_deb=None, date_fin=None, timestep='D', unit='mm/d'):
    """ Create time serie for marthe """
    ts = ts.copy()[date_deb:date_fin]
    cols = list(ts.columns)
    ts.reset_index(inplace=True)
    ts.columns = ['Date'] + cols
    ts['NumPas'] = ts.index + 1 # parce que l'on inclus pas le pas 0
    ts = ts[cols + ['NumPas', 'Date']] # reorder

    if timestep == '10D':
        delta = count_days(ts)[date_deb:date_fin].reset_index(drop=True)
        ts['date_fin'] = ts['Date'] + pd.to_timedelta(delta - 1, 'd')

    ts['unit: {0}'.format(unit)] = '' # create empty col with unit

    return ts


def resample_10D(ts, func='sum', labels=['1', '11', '21']):
    """
     input : ts, a pandas TimeSeries or DF with DatetimeIndex
     output : a df with multi index

     using pd.cut to create times intervals in month and agg in it

     """
    # inspired from : https://stackoverflow.com/questions/68015379/resample-10d-but-until-end-of-months

    df = ts.copy() # shallow copy to avoid side effects
    df['count'] = 1 # to see after group by how many obs in group

    grp = df.groupby([
        pd.cut(df.index.day, [0, 10, 20, 31], labels=labels),
        df.index.month,
        df.index.year
    ]).agg(func)

    # not working if only series... cols needed for what's to come
    grp = pd.DataFrame(grp)

    # extract data from MultiIndex
    grp['year']  = grp.index.get_level_values(2)
    grp['month'] = grp.index.get_level_values(1)
    grp['day']   = pd.to_numeric(grp.index.get_level_values(0))

    # Reset index with DateTime, clean and sort df
    grp.reset_index(drop=True, inplace=True)
    grp.set_index(pd.to_datetime(grp[['year', 'month', 'day']]), inplace=True)
    grp.drop(['year', 'month', 'day'], axis=1, inplace=True)
    grp.sort_index(inplace=True)

    # done !
    return grp


def build_df_obs_sim(dfobs, dfsim, tresh=None, mode='head'):
    """ Build Obs and Sim DataFrame

    Obs are merged on sim timesteps following different rules (according to Marthe
    management of these variables):
        - piezometric (mode=head) : closest available obs to timestep ;
        - river discharge (mode=flux): mean on timestep duration.

    Notes
    -----

    If multiple obs or multiple sim columns (e.g. for different observation sites),
    it is recommended to apply this function in a loop. Resutls are not consistent
    when multiple columns are provided with NaNs, because of pd.merge_asof behavior.

    Parameters
    ----------
    dfobs: pd.DataFrame
        observed values, with datetime index.

    dfsim: pd.Dataframe
        simulated values, with datetime index.

    tresh: pd.Timedelta, optionnal
        if provided, setup a time treshold to look for observation data on
        simulation datetime index (e.g. `tresh=pd.Timedelta('15 days')`.
        If no observation is found within this treshold, NaNs are added.
        If not provided (default), half of the simulation time step is used as
        treshold.

    mode: str, optional
        kind of data: `flux` for river discharge,
        `head` for piezometric data (default)

    Returns
    -------
    pd.DataFrame, Joined values of simulation and observation, at
        simulated timesteps
    """
    # mode: H = niveau piézo (date exacte ou la plus proche),
    #       Q = débit (moyenne sur le pas de temps simulé)
    # TODO: arg keep_all=True --> garder toute les données, juste ajouté un
    # champs sim 1/0 --> plot avec tout le monde mais couleur différente si
    # pas simulé dans les obs

    if tresh is None:
        # if tresh is None, its set with half timestep from dfsim
        dt  = round((- pd.Series(dfsim.index[::-1]).diff().dt.days).mean() / 2)
        tresh = pd.Timedelta('{} days'.format(dt))

    # make sure inputs are df
    dfsim = pd.DataFrame(dfsim, copy=True).sort_index().dropna(how='all')
    dfobs = pd.DataFrame(dfobs, copy=True).sort_index().dropna(how='all')

    # clean colnames and levels --> harmonize between obs and sim and avoid
    # warnings/erros on join from differents levels
    dfsim.columns = pd.MultiIndex.from_tuples(
        [('sim', x) for x in dfsim.columns.get_level_values(-1)]
    )
    dfobs.columns = pd.MultiIndex.from_tuples(
        [('obs', x) for x in dfobs.columns.get_level_values(-1)]
    )

    if mode.lower() in ['flux', 'q', 'deb', "riv", 'débit_rivi', 'debit_rivi']:
        # in Q mode (river discharge), get mean obs value from simulated timestep
        # need to resample dfobs on dfsim index with mean agg --> bins on dfsim.index
        dfobs = dfobs.groupby(
            pd.cut(dfobs.index, bins=dfsim.index),
            observed=False
        ).mean()
        # reset index with end interval, convert categorical index to interval
        # index and get right bound
        # mid, left, right, lenght : https://pandas.pydata.org/docs/reference/api/pandas.IntervalIndex.html
        dfobs.index = pd.IntervalIndex(dfobs.index).right

        dfobsim = dfsim.join(dfobs, how='left')
    else:
        # in H mode (piezometric levels), get obs value with nearest sim date
        dfobsim = pd.merge_asof(
            left=dfsim, right=dfobs, # all df must be sorted by key !
            right_index=True, left_index=True,
            direction='nearest',
            tolerance=tresh,
            allow_exact_matches=True,
        )

        # drop non simulated timesteps
        # dfobsim = dfobsim[~dfobsim['sim'].isna().any(1)]#('sim', slice(None))

    return dfobsim
