#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, shutil
from pathlib import Path
from glob import glob
from tqdm import tqdm
from datetime import datetime

import pandas as pd
import numpy as np
import geopandas as gpd

import martpy as mart
import gridmarthe as gm

from matplotlib import pyplot as plt
from matplotlib import ticker
from matplotlib.gridspec import GridSpec

from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib import (colors, cm)

#from pymarthe import marthe as mm # TODO virer la dépendance pymarthe, finalement peu utile...
#plt.rcdefaults() # cause pymarthe change it... in functions.. so why global ?
# font = {'size' : 12, 'sans-serif':'Arial' }
# mpl.rc('font', **font)

# DEFAULTS, please edit variable in MAIN section (bottom of this script)
PATH_OBS = "./obs"
PATH_RMA = "./run_master_98975"
PATH_SIM = PATH_RMA


def ppprint(msg):
    print("\r  ... {}".format(msg), end="", flush=True)


# from pygar
def mk_run_dir():
    resdir = '_run_{}'.format(
        datetime.strftime(datetime.now(),format='%Y%m%d_%H%M%S')
    )
    # resdir = os.path.join(os.getcwd(), resdir)
    os.makedirs(resdir, exist_ok=True)
    return resdir


def mv_res(dst='./run'):
    os.makedirs(dst, exist_ok=True)
    ext = ["prn", "txt", "out", "png"]
    for e in ext:
        files = glob('./*.{}'.format(e))
        for f in files:
            # shutil.move(f, os.path.join(dst, os.path.split(f)[-1]))
            shutil.move(f, dst)
    return 0


def _read_output(fname, func, **kwargs):
    if os.path.isfile(fname): #try is more pythonnic, but not allowed when calling fortran procedure
        try:
            res = func(fname, **kwargs)
        except: # not really good, should specify which type of error we will ignore
            pass
        else:
            return res
    else:
        return None


def load_obs(key='gwl', path=PATH_OBS):
    # gwl or qriv - check on hdf5 file with bash command
    # h5dump -H ../bd_histo.h5 | grep 'GROUP'
    if path is None:
        return pd.DataFrame()
    df = pd.read_hdf(
        os.path.join(path, 'bd_histo.h5'), key=key
    )
    df = df.pivot_table(columns='indice', index=df.index.get_level_values(0))
    df.columns = df.columns.get_level_values(-1)
    df.index.name = 'date'
    df.index = pd.to_datetime(df.index, format='ISO8601')
    return df.sort_index()


def load_sims(path='.'):
    # version pymarthe
    # df_sim     = mm.marthe_utils.read_prn('historiq.prn')
    # flow_df    = mm.marthe_utils.read_budget('histobil_debit.prn')
    # flow_df_zb = mm.marthe_utils.read_zonebudget('histobil_debit.prn')
    # bud_df     = mm.marthe_utils.read_budget('histobil_nap_cumu.prn')
    # riv_df     = mm.marthe_utils.read_budget('histobil_riv_dra_lac.prn')
    # riv_df_zb  = mm.marthe_utils.read_zonebudget('histobil_riv_dra_lac.prn')
    mario = {
        'historiq'            : _read_output(Path(path, 'historiq.prn'            ), mart.read_historiq           ),
        'histoclim'           : _read_output(Path(path, 'histoclim.prn'           ), mart.read_histobil, mode='df'),
        'histobil_deb'        : _read_output(Path(path, 'histobil_debit.prn'      ), mart.read_histobil, mode='df'),
        'histobil_nap_pastp'  : _read_output(Path(path, 'histobil_nap_pastp.prn'  ), mart.read_histobil, mode='df'),
        'histobil_nap_cumul'  : _read_output(Path(path, 'histobil_nap_cumu.prn'   ), mart.read_histobil, mode='df'),
        'histobil_riv_dra_lac': _read_output(Path(path, 'histobil_riv_dra_lac.prn'), mart.read_histobil, mode='df'),
        # 'rivsim'              : _read_output(Path(path, 'rivsim.prn'), mart.read_rivsim, mode='df'), # func not yet available
        # 'chasim'              : _read_output(Path(path, 'chasim.out'), gm.open_mgrid, fpastp=rma.mlfiles['pastp'], var_attrs={'units': 'm' if rma.units['head'] is None else rma.units['head']}),
        # 'debsim'              : _read_output(Path(path, 'debsim.out'), gm.open_mgrid, varname='DEBIT', fpastp=rma.mlfiles['pastp'], var_attrs={'units': 'm3/s' if rma.units['flow'] is None else rma.units['flow']}), 
    }
    return mario


def compute_metrics(dfobsim, level_id=-1):
    dfobsim = dfobsim.copy().sort_index() # avoid PerformanceWarning unsort index
    dfobsim = dfobsim.sort_index(axis=1)
    met = []
    # loop sur les indices de stations
    for ind in np.unique(dfobsim.loc[:, (slice(None), 'sim')].columns.get_level_values(level_id)):
        # break
        tmp = dfobsim.loc[:, (slice(None), slice(None), ind)].dropna(how='any')
        try:
            obs, sim = pd.DataFrame(tmp.loc[:, (slice(None), 'obs')]), pd.DataFrame(tmp.loc[:, (slice(None), 'sim')])
        except KeyError:
            print('No data : {}'.format(ind))
            continue
        
        if len(obs.columns) > 1:
            print('Warning, duplicate obs : {}'.format(ind))
            obs = obs.iloc[:, 0]
        if len(sim.columns) > 1: # TODO: do loop for each cols to get every metrics if duplicate sims
            print('Warning, duplicate sim : {}'.format(ind))
            sim = sim.iloc[:, 0]
        
        metrics = mart.stats.MartheMetrics(obs, sim)
        met.append(metrics.to_dataframe(index=[ind]))
    
    return pd.concat(met)


def get_short_indice(indice, vartype='charge'):
    if vartype.lower() == 'charge':
        idx_short = indice[:10] # indice and not code_bss or whatever after 10th character
    elif vartype.lower() == 'débit_rivi':
        idx_short = indice[:8] # code_site and not code_station
    else:
        idx_short = indice
    return idx_short


def get_interval_time(dtimeindex, windows_size=0.5):
    # dt time index need to be sorted
    return round((- pd.Series(dtimeindex[::-1]).diff().dt.days).mean() * windows_size) # get interval between pastp


def make_df_obs_sim(io, dates=None, windows_size=0.5, path_obs=PATH_OBS):
    # **** Create df sim-obs
    varhisto = np.unique(io['historiq'].columns.get_level_values(0))
    dfobsim = []
    df_obs = []
    for v in varhisto:
        # v = 'Charge'
        k = 'gwl' if v == 'Charge' else 'qriv'
        dfobs = load_obs(key=k, path=path_obs)
        dfsim = io['historiq'][v]
        if dates is not None:
            dfsim = dfsim.loc[dfsim.index.isin(dates),:]
        
        dt = get_interval_time(dfsim.index, windows_size)
        res = []
        
        # tmp = mart.build_df_obs_sim(dfobs, dfsim, mode=v, tresh=pd.Timedelta('{} days'.format(dt)))
        # finally can't do it on full df (with cols = indice), too much NA
        # merge asof does not work properly
        # needs to drop na on df2, so need to do it for every obs to keep all measurements
        for x in dfsim.columns:
            
            idx = x[-1] # last level
            idx_short = get_short_indice(idx, v)
            df1 = pd.DataFrame(dfsim.loc[:, dfsim.columns.get_level_values(-1) == idx])
            
            try:
                df2 = pd.DataFrame(dfobs.loc[:, idx]).dropna()  #idx_short
            except KeyError:
                # if no obs found, just return sim
                df1.columns = pd.MultiIndex.from_tuples([('sim', x) for x in df1.columns.get_level_values(-1)])
                res.append(df1)
                continue
            else:
                blbl = mart.build_df_obs_sim(df2, df1, mode=v, tresh=pd.Timedelta('{} days'.format(dt)))
                blbl = blbl.sort_index(axis=1, level=0, ascending=False) # make sure of order : sim, obs
                blbl.columns = pd.MultiIndex.from_tuples([('sim', idx), ('obs', idx)]) # reconstruct for x_sim != x_obs // exemple 00123X0001_testcouche2 dans histo
                res.append(blbl)
        
        tmp = pd.concat(res) # merge all res
        
        tmp.columns = pd.MultiIndex.from_tuples([tuple([v]+[i for i in x]) for x in tmp.columns]) # add level var in columns
        df_obs.append(dfobs)
        dfobsim.append(tmp)
    
    df_obs = pd.concat(df_obs)
    dfobsim = pd.concat(dfobsim)
    dfobsim = dfobsim.groupby(dfobsim.index).mean() # duplicate index to clean TODO

    dfobsim = dfobsim.replace(mart.NaN_VALUES, np.nan)
    os.makedirs('postproc', exist_ok=True)
    dfobsim.to_csv('./postproc/df_obs_sim.csv', sep=';')
    # old. keep for memory if need te reverse dev : keep only 10char of idx
    # dfobsim.columns.set_levels(dfobsim.columns.get_level_values(-1).str.slice(0,10),level=-1)#, inplace=True) 
    # dfobsim.columns = pd.MultiIndex.from_tuples([(x[0], x[1], x[2][:10]) for x in dfobsim.columns]) # mk indice from code_bss
    
    return dfobsim, df_obs


def hist_metric(df_metrics, ax=None, fout=None, xmax=None, xmin=None, bins='auto', ecdf=True, **kwargs):
    if ax is None:
        fig, ax = plt.subplots(figsize=(3, 4))
    # for bins methods, see https://numpy.org/doc/stable/reference/generated/numpy.histogram_bin_edges.html#numpy.histogram_bin_edges
    # and https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.hist.html
    # ax.hist(df_metrics, bins='auto', histtype='step', density=True, cumulative=-1, **kwargs)
    # ax.hist(df_metrics, bins=bins, histtype='step', density=True, cumulative=True, **kwargs)
    if df_metrics.empty:
        return ax
    if ecdf:
        ax.ecdf(df_metrics, label='ECDF', **kwargs)
    else:
        ax.hist(df_metrics, bins=bins, **kwargs)
    
    if xmin is None:
        xmin = df_metrics.min()
        # else:
            # xmin = max(xmin, df_metrics.min())  # force min value
    if xmax is None:
        xmax = df_metrics.max()
    ax.set_xlim(xmin, xmax) # pour éviter le trait vertical partant de 0
    
    if fout is not None:
        plt.tight_layout()
        plt.savefig(fout, dpi=250)
    else:
        return ax


def set_var_types(df, histo, mode='index'):
    # TODO: NO, remove this, just join histo!!
    if mode == 'index':
        df = df.join(histo.set_index(histo['Name'].str.slice(0,10))['field'])
    #     df['type'] = np.where(df.index.str.startswith('E'), 'rivi', 'head') # TODO improve if other kind of var
    # elif mode == 'columns':
    #     type = np.where(df.columns.str.startswith('E'), 'rivi', 'head') # TODO improve if other kind of var
    #     df.columns = [(x, c) for x, c in zip(type, df.columns)]
    return df


def plot_hist_metrics(df_metrics, histo, resdir):
    # thx Ebus for the inspiration
    # df_metrics = pd.read_table('./submod2_liais/_run/metrics.txt', sep='\t', index_col=0)
    df_metrics = set_var_types(df_metrics, histo)
    
    fig, axes = plt.subplots(ncols=3, figsize=(10, 4))
    hist_metric(df_metrics.loc[df_metrics['field'] == 'Charge', 'rmse'             ], axes[0], color='blue')
    hist_metric(df_metrics.loc[df_metrics['field'] == 'Charge', 'nse_bias_excluded'], axes[1], color='blue', xmax=1, xmin=-0.1, complementary=True) # compl to reverse ecdf / more adapted for NSE
    # hist_metric(df_metrics.loc[df_metrics['field'] == 'Charge', 'mae'              ], axes[2], color='blue')
    hist_metric(df_metrics.loc[df_metrics['field'] == 'Charge', 'bias'              ], axes[2], ecdf=False)
    axes[0].set_title('RMSE')
    axes[1].set_title('NSE (bias excluded)')
    # axes[2].set_title('Bias (abs)')
    axes[2].set_title('Bias')
    for ax in axes.flatten()[:-1]:  # not for bias
        ax.yaxis.set_major_formatter(ticker.PercentFormatter(1.0))
        ax.grid(True)
    plt.tight_layout()
    plt.savefig(Path(resdir, 'hist_metric_head.png'), dpi=250)
    plt.close()
    
    fig, axes = plt.subplots(ncols=3, figsize=(10, 4))
    hist_metric(df_metrics.loc[df_metrics['field'] == 'Débit_Rivi',   'nse'], axes[0], color='green', xmax=1, xmin=-0.1, complementary=True)
    hist_metric(df_metrics.loc[df_metrics['field'] == 'Débit_Rivi',   'kge'], axes[1], color='green', xmax=1, xmin=-0.1, complementary=True)
    hist_metric(df_metrics.loc[df_metrics['field'] == 'Débit_Rivi', 'ratio'], axes[2], color='green')
    axes[0].set_title('NSE')
    axes[1].set_title('KGE')
    axes[2].set_title('Ratio')
    for ax in axes.flatten():
        ax.yaxis.set_major_formatter(ticker.PercentFormatter(1.0))
        ax.grid(True)
    plt.tight_layout()
    plt.savefig(Path(resdir, 'hist_metric_flow.png'), dpi=250)
    plt.close()
    
    # plt.show()

    return None


def set_gdf_lims(gdf, ax, delta=.05):
    xmin, ymin, xmax, ymax = np.round(gdf.total_bounds)
    x_range = xmax - xmin
    y_range = ymax - ymin
    # and add 5% margin around bounds (2.5% on each side)
    ax.set_xlim([xmin - (delta * x_range)/2, xmax + (delta * x_range)/2])
    ax.set_ylim([ymin - (delta * y_range)/2, ymax + (delta * y_range)/2])
    return ax


def plot_map(gdf, rivi=None, other=None, xy=None, ax=None, color=['lightgrey', 'blue', 'k', 'k'], **kwargs):
    # colors order: gdf, rivi, xy, other(s).
    # TODO add cx
    # TODO: class map pour ajout méthode
    # other allow to draw one or several (if list) more gdf as bounds
    if ax is None:
        fig, ax = plt.subplots()
    gdf.plot(ax=ax, color=color[0], **kwargs)
    if rivi is not None:
        rivi.plot(ax=ax, color=color[1])
    if other is not None:
        if not isinstance(other, list):
            other = [other]
        for i, x in enumerate(other):
            try:
                c = color[i+3]
            except IndexError:
                c = color[-1]
            x.boundary.plot(ax=ax, color=c)
    if xy is not None:
        xy.plot(marker='.', ax=ax, color=color[2])
    set_gdf_lims(gdf, ax)
    return ax


def mk_plot(df, column, other_sim=None, resdir='./', fout='plot.png', hline=None):
    cols = [column]
    if other_sim is not None:
        if any(other_sim.keys()):
            for k, v in other_sim.items():
                tmp = pd.DataFrame(v['histobil_deb'][column])
                tmp.columns = [k]
                df = df.join(tmp)
                cols.append(k)
    
    fig, ax = mart.plot_ts(
        df.loc[("global", slice(None)), cols].droplevel('zone'), #.iloc[1:,],
        ylabl=column,
    )

    if hline is not None:
        ax.axhline(y=hline, color="red", linewidth=.8)
    # plt.show()
    plt.savefig(Path(resdir, fout), dpi = 250, bbox_inches='tight')
    # plt.close()


def reorder_legend(**kwargs):
    handles, labels = plt.gca().get_legend_handles_labels()
    idx = [labels.index(x) for x in sorted(labels)]
    plt.legend([handles[i] for i in idx], [labels[i] for i in idx], **kwargs)


def gen_plot_obs_sim(
    dfobsim,
    histo=None, dfobs=None, df_metrics=None,
    resdir='./', polygs=[], other_sim=None,
    sim_name=None, min_year='1990', dates=None,
    plot_only_if_obs=True
):
    """ Thx JCM for inspiration """
    # -- mk plots and metrics
    color = ['g', 'k', 'red','orange', 'purple', 'dodgerblue', 'lime', 'yellow']
    
    # dfobsim.loc[:, (slice(None),'sim')].columns.get_level_values(-1)
    # for sta in tqdm(histo['Name'].str.slice(0, 10).to_list(), desc='Plot history matching'):
    # si on voulait les couples 00123W0001_lay1 et _lay2 sur le même graphes:
    # grouper par str.slice(0,10) => récup les données avec re.match
    # une seule obs (donc modifier le obsim)
    # mais si plusieurs test (simul), ça devient le binz
    for sta in tqdm(histo['Name'], desc='Plot history matching'):
        # sta = '00197X0049'
        
        ihisto = histo.loc[histo["Name"] == sta]
        thetitle = '{}\nLayer: {}'.format(sta, ihisto['Lay'].values[0])
        
        if sta not in dfobsim.columns.get_level_values(-1):
            continue

        df = dfobsim.loc[:, (slice(None), slice(None), sta)].dropna(how='all')
        
        var = df.columns.get_level_values(0)[0]
        ylabl = 'River flow ($m^{3}.s^{-1}$)' if var == 'Débit_Rivi' else 'Groundwater head (m a.s.l)'
        
        sta_short = get_short_indice(sta, var)
        
        df.columns = df.columns.droplevel(0) #0 ?
        colnames = [sim_name] if sim_name is not None else ['sim']
        if len(df.columns) > 1:
            df = df[['sim', 'obs']] # re-order
            if sim_name is not None:
                colnames.append('obs')
        else:
            if plot_only_if_obs:
                continue
        df.columns = colnames
        
        if df[sim_name].dropna().empty:
            continue
        
        if (df_metrics is not None) and (not df_metrics.empty):
            try:
                stats = df_metrics.loc[df_metrics.index == sta]
                substat = ['rmse', 'bias', 'nse', 'nse_bias_excluded'] if var == 'Charge' else ['ratio', 'kge', 'nse']
                stats = stats[substat].T.to_dict()[sta]
            except KeyError:
                stats = {}
        
        fig, ax = plt.subplots(ncols=2, figsize=(16,3), gridspec_kw={'width_ratios': [1, 2.5]})
        
        # TODO make a gridspec, should be more efficient
        # fig2, ax5 = plt.subplots()
        # fig = plt.figure(layout="constrained", figsize=(15,5)) # ou subplot_mosaic() ?
        # gs = GridSpec(nrows=2, ncols=3, figure=fig)
        # ax0 = fig.add_subplot(gs[0, 0]) # identical to ax1 = plt.subplot(gs.new_subplotspec((0, 0), colspan=3))
        # ax1 = fig.add_subplot(gs[0, 1:])
        # ax2 = fig.add_subplot(gs[1, 1:])
        ax0, ax1 = ax[0], ax[1]
        # fig2, ax2 = plt.subplots()
        
        ax0 = plot_map(*polygs, histo[histo['field']==var], ax=ax0)
        ihisto.plot(ax=ax0, marker='.', color='red') # current sta in red
        
        # df.index
        # df.groupby(df.index.month).mean().plot(
        #     ax=ax5,
        #     color=c,
        # )
        
        if other_sim is not None or len(other_sim)>0:
            if isinstance(other_sim, (pd.DataFrame)):
                other_sim = dict(sim2={'historiq': other_sim})
            c2 = color[len(df.columns):]
            for i, (k, v) in enumerate(other_sim.items()):
                tmp = v['historiq'].loc[:, v['historiq'].columns.get_level_values(-1) == sta].replace(mart.NaN_VALUES, np.nan)
                if dates is not None: # suppose que toutes les sim avaient le même pastp... hmmmmh
                    tmp = tmp.loc[tmp.index.isin(dates), :]
                ax1.plot(tmp.index, tmp.values, marker='.', markersize=3, linestyle='-', color=c2[i], label=k)
                # tmp = tmp.groupby(tmp.index.month).mean() # monthly mean cycle
                # ax2.plot(tmp.index, tmp.values, marker='.', markersize=3, linestyle='-', color=c[i], label=k)
        
        if (dfobs is not None) and (not dfobs.empty):
            try:
                ax1.plot(dfobs.loc[min_year:, sta_short].index, dfobs.loc[min_year:, sta_short], marker='.', markersize=3, zorder=0.5, color='blue', label='obs_all')
                # tmp = dfobs.loc['1980':, sta].dropna()
                # tmp = tmp.groupby(tmp.index.month).mean() # monthly mean cycle
                # _ = ax2.plot(tmp.index, tmp, marker='.', markersize=3, zorder=0.5, color='blue', label='obs_all')
            except KeyError:
                pass
        
        c1 = color[ :len(df.columns)+1]
        ax1 = mart.plot_obs_sim_with_metrics(
            df,
            # metrics=stats,
            ax=ax1,
            ylabl=ylabl,
            marker='.',
            markersize=3,
            color=c1,
        ) # why before not working ? moving line here to show all (dfobsim, obs, other_sim)
        ax1.set_title(thetitle)

        # TODO
        # Zoom sur qq années ??
        # cycle saisonnier moyen, pour obs, sim, other_sim, bref tout le monde
        # plot_season_cycle(df, dfobs, other_sim) # mettre les mêmes couleurs
        
        reorder_legend(bbox_to_anchor=(1.05, 1), loc='upper left') # reorder and make it outside

        plt.tight_layout()
        plt.savefig(Path(resdir, "{}_{}_sim_obs.png".format(var, sta.replace('/','_'))), dpi=300)
        # fig2.savefig("test.png")
        # plt.show()
        plt.close()

        # ----------- monthly cycle
        fig2, ax5 = plt.subplots(figsize=(8,3))
        dfm = df.groupby(df.index.month).mean()
        dfm.columns = df.columns.get_level_values(0)
        dfm.plot(
            ax=ax5,
            color=c1,
            title=thetitle,
        )
        if other_sim is not None or len(other_sim)>0:
            for i, (k, v) in enumerate(other_sim.items()):
                tmp = v['historiq'].loc[:, v['historiq'].columns.get_level_values(-1) == sta].replace(mart.NaN_VALUES, np.nan)
                if dates is not None: # suppose que toutes les sim avaient le même pastp... hmmmmh
                    tmp = tmp.loc[tmp.index.isin(dates), :]
                tmp = tmp.groupby(tmp.index.month).mean() # monthly mean cycle
                ax5.plot(tmp.index, tmp.values, marker='.', markersize=3, linestyle='-', color=c2[i], label=k)
        
        if (dfobs is not None) and (not dfobs.empty):
            try:
                tmp = dfobs.loc[min_year:, sta_short].dropna()
                tmp = tmp.groupby(tmp.index.month).mean() # monthly mean cycle
                _ = ax5.plot(tmp.index, tmp, marker='.', markersize=3, zorder=0.5, color='blue', label='obs_all')
            except KeyError:
                pass
        # force ticks every month
        ax5.set_xticks(np.arange(1, 13)) #plt.xticks
        months = pd.date_range(start='1900-01-01', end='1901-01-01', freq='M')
        months = [x.strftime("%b") for x in months]# [:1] for 1st letter only ?
        ax5.set_xticklabels(months, rotation=90)
        ax5.set_ylabel(ylabl)
        ax5.grid(True)
        reorder_legend(bbox_to_anchor=(1.05, 1), loc='upper left') # reorder and make it outside
        fig2.tight_layout()
        fig2.savefig(Path(resdir, "{}_{}_sim_obs_monthly_cycle.png".format(var, sta.replace('/', '_'))), dpi=300)
        # plt.show()
        plt.close()

    return None


def plot_bil_hyd(df_bil, resdir, level='global', factor=(3600*24*30*1e-6), fout='bilan_hyd.png'): #(3600 * 24 * 365 * 1e-6)
    """ thx Ebus
    TODO version avec les IN/OUT pas GLOB !"""
    df_bil = df_bil.copy() * factor
    gr_par = dict(linewidth=0.8)

    fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(10,8), sharex='all')
    axes = axes.ravel()

    # Inflow/outflow
    axes[0].set_title("Bilan hydraulique simulé")

    # ebus version => ax.step(date, val, where='mid', ...)
    # 1st plot: bil
    df_bil['Recharge_Maill'].plot(ax=axes[0], color='b', label='Recharge', **gr_par)
    (df_bil['Sort_Pompag_fix']+df_bil['Réduct_Pompage']).plot(ax=axes[0], color='r', label='Prélèvements', **gr_par)
    df_bil['Débord/Suintem'].plot(ax=axes[0], color='green', label='Débordement', **gr_par)
    
    col_nr = 'Glob_Riv_Nappe' if level == 'global' else 'Glob_Riv-Nappe'
    df_bil[col_nr].plot(ax=axes[0], color='orange', label='Echanges avec le\nréseau hydrographique', **gr_par)
    
    col_lim = 'Glob_Limites' if level == 'global' else ['Glob_Limit_Zon', 'Glob_Lim_Z_Hau', 'Glob_Lim_Z_Bas']
    df_bil[col_lim].plot(ax=axes[0], color='purple', label='Limites', **gr_par)
    
    # verif:
    # bilglob = df_bil['Recharge_Maill'] + df_bil['Sort_Pompag_fix'] + df_bil['Réduct_Pompage'] + df_bil['Débord/Suintem'] + df_bil[col_nr] + df_bil[col_lim]
    
    # bilglob.plot(ax=axes[0], color='k', label='Bilan global', **gr_par)
    # (df_bil['Glob_Stock'] - bilglob).plot(ax=axes[0], color='grey', label='Bilan global_sans_stock', **gr_par)
    
    # 2nd plot storage variation
    col_stock = 'Glob_Stock' if level == 'global' else 'Stockage'
    # df_bil[col_stock].plot(ax=axes[0], color='r', label='Stockage/déstockage', **gr_par)
    df_bil[col_stock].plot(ax=axes[1], color='r', label='Stockage/déstockage', **gr_par)
    
    # 3rd plot, cumulative
    # (df_bil[col_stock]/365.25).cumsum().plot(ax=axes[2], color='r', label='Cumulative', **gr_par)
    (df_bil[col_stock]).cumsum().plot(ax=axes[2], color='r', label='Cumul', **gr_par) # par mois
    
    for ax in axes:
        ax.hlines(0, xmin=df_bil.index.min(), xmax=df_bil.index.max(), color='k', linestyle='dashed', alpha=0.7, **gr_par)
        ax.grid(True)
        ax.set_axisbelow(True)
        ax.legend()
    
    # unit = "$Mm^{3}.an^{-1}$"
    unit = "$Mm^{3}/mois$"
    axes[0].set_ylabel("Entrées-sorties ({})".format(unit), fontsize=8) #\u00b3 
    axes[1].set_ylabel("Variations de stockage ({})".format(unit), fontsize=8)
    axes[2].set_ylabel("Stockage/déstockage cumulatif ($Mm^{3}$)", fontsize=8)

    plt.xticks(rotation='horizontal', ha='center')
    plt.tight_layout()
    plt.savefig(Path(resdir, fout), dpi=250)
    plt.close()

    return fig, axes


def plot_bil_rivi(df_bil, resdir, fout='bil_rivi.png'):
    # df_bil = io['histobil_riv_dra_lac'].loc[(slice(None), 'global'),:]
    cols = [
        'Par_Sources', 'Ruissel_Sup',
        'Entr_Injection', 'Sort_Pompage',
        # 'Entr_Inject_fix', 'Sort_Pompag_fix',
        # 'Dérivat_Entrant', 'Dérivat_Sortant',
        # 'Entr_Niv_Impos', 'Sort_Niv_Impos',
        'Nappe->Rivières', 'Rivières->Nappe',
        #'Lacs->Rivières', 'Rivières->Lacs',
        # 'Débor_Riv->Lacs',
        'Débo_Nap_Rivi.',
        'Exutoires_Riv.',
        # 'Stockage', 'DéStockage',
        # 'Entr_Limit_Zone', 'Sort_Limit_Zone', 
        # 'Écart_Bilan'
    ]
 
    moy_err = np.mean(df_bil['Écart_Bilan'])
    std_err = np.std(df_bil['Écart_Bilan'])  
    
    fig, ax = plt.subplots(figsize=(10,5))
    df_bil[cols].droplevel(1).plot(ax=ax)
    plt.grid()
    plt.legend(loc='lower left')
    plt.xticks(rotation='horizontal', ha='center')
    ax.set_ylabel("Débit ($m^{3}.s^{-1}$)", fontsize=8)
    plt.tight_layout()
    plt.savefig(Path(resdir, fout), dpi=250)
    # plt.show()
    plt.close()
    return fig, ax


def plot_ratio_inf_prelv(df_bil, resdir, fout='bil_ratio_prelv_rech.png', factor=1, **kwargs):
    """ thx Ebus """
    df_bil = df_bil.copy() * factor
    fig, ax = plt.subplots(figsize=(10, 5))
    ratio = ((-1 * (df_bil['Sort_Pompag_fix'] + df_bil['Réduct_Pompage'] )) / df_bil['Recharge_Maill']) * 100
    ratio.plot(ax=ax, color='blue', **kwargs)
    ax.set_ylabel("ratio prélèvements/recharge")
    ax.yaxis.set_major_formatter(ticker.PercentFormatter())
    plt.xticks(rotation='horizontal', ha='center')
    plt.grid(True)
    plt.savefig(Path(resdir, fout), dpi=250)
    return fig, ax


# def get_sym_cmap_norm(lower=None, upper=None, cmap='bwr', n_shades=5, extend='neither'):
#     """ 
#     colors.CenteredNorm() provide contineous norm
#     So : https://gist.github.com/turbach/c3ddb3650f34354e531e060e97d35e7a
#     # number of shades in each half of the color map

#     """
#     # lower = -1.0 * np.max(np.abs(y))  # always negative
#     upper = -lower  # always positive

#     # if lower != -upper:
#     #     msg = "upper and lower bounds must be symmetric around zero"
#     #     raise ValueError(msg)

#     # n_colors always odd for a white band around zero
#     n_colors = (2 * n_shades) + 1 

#     if extend == 'both':
#         nbins = n_colors + 2
#     elif extend in ['min', 'max']:
#         nbins = n_colors + 1
#     else:
#         nbins = n_colors
#     cmap = cm.get_cmap(cmap, n_colors)
#     bounds = np.round(np.linspace(lower, upper, n_colors+1))
#     norm = colors.BoundaryNorm(bounds, n_colors, extend=extend)
    
#     return cmap, norm


def plot_map_metrics(gdfhisto, polygs, resdir="./"):
    # cmap1, norm1 = get_sym_cmap_norm(lower=-10, n_shades=5, extend='both')
    norm1 = colors.BoundaryNorm(np.arange(0, 1.1, 0.1), ncolors=256, extend='min')
    gr_par = {
        'nse' : {
            'norm': norm1,
            'cmap': 'rainbow_r',
        },
        'kge' : {
            'norm': norm1,
            'cmap': 'rainbow_r',
        },
        'nse_bias_excluded' : {
            'norm': norm1,
            'cmap': 'rainbow_r',
            # 'cmap': 'RdYlBu',
        },
        'bias': {
            # 'norm': colors.CenteredNorm(),
            # 'norm': norm1,
            # 'cmap': cmap1,
            'norm' : colors.BoundaryNorm(np.round(np.linspace(-10, 10, 12)), ncolors=256, extend='both'),
            'cmap': 'bwr',
        },
        'rmse':{
            'norm': colors.BoundaryNorm(
                np.arange(0, np.min([np.max(gdfhisto.loc[gdfhisto['field']=='Charge', 'rmse']), 11]), 1),
                ncolors=256,
                extend='max'
            ),
            'cmap': 'RdYlGn_r',
        },
        'ratio':{
            # 'norm': colors.CenteredNorm(),
            # 'norm': colors.BoundaryNorm(np.linspace(0, 2, 11), ncolors=256, extend='both'),
            'norm': colors.Normalize(vmin=0, vmax=2),
        #     'cmap': '',
        },
    }
    
    for var, gr_df in gdfhisto.groupby('field'):
        
        # break
        if var == 'Charge':
            crit = ['rmse', 'bias', 'nse_bias_excluded']
            fancy = {'rmse': 'RMSE', 'bias': 'Bias (m)', 'nse_bias_excluded': 'Nash-Shutcliff Efficiency (bias excluded)'}
        elif var == 'Débit_Rivi':
            crit = ['kge', 'ratio', 'nse']
            fancy = {'kge':'Kling Gupta Efficiency (KGE)', 'ratio':'Ratio', 'nse': 'Nash-Shutcliff Efficiency'}
        
        for c in crit:
            if gr_df[c].dropna().empty:
                continue
            
            ax = plot_map(*polygs, gdfhisto, color=['none', 'lightskyblue', 'none', 'grey'], edgecolor='k')
            # ax.get_lines()[0].set_edgecolor("black")

            # custom cbar to force discrete colors
            par = gr_par.get(c, {})
            norm = par.get('norm', None)# get specific par or None, if None, see below
            cmap = par.get('cmap', 'bwr')
            if norm is None:
                bounds = np.linspace(gr_df[c].quantile(0.01), gr_df[c].quantile(0.99), 7)
                if len(np.unique(bounds) < 2):
                    # when only one value, can't make cmap normed
                    bounds = np.linspace(gr_df[c].quantile(0.01)-1, gr_df[c].quantile(0.99)+1, 7)
                norm = colors.BoundaryNorm(bounds, ncolors=256, extend='both')  # set bins to custom values
            
            divider = make_axes_locatable(ax)
            cax = divider.append_axes("right", size="3%", pad=0.1)

            gr_df.plot(
                ax=ax,
                column=c,
                cax=cax,
                cmap=cmap,
                norm=norm,
                edgecolor='k',
                legend=True,
                legend_kwds={
                    'label': fancy[c],
                    'ticks': norm.boundaries if c != 'ratio' else None,
                    # 'extend':'both',
                },
                zorder=2
            )
            # ax.figure.axes[1].tick_params(labelsize=8)
            # plt.show()

            plt.tight_layout()
            plt.savefig(Path(resdir, 'map_{}_{}.png'.format(var, c)), dpi=300)
            plt.close()
    return None


def main(
    io, histo, dates=None,
    calibr_dates=['1995', None],
    resdir='./',
    other_sim=[], polygs=[],
    sim_name=None,
    path_obs=PATH_OBS,
    add_other_sim_bil=False
):
    """ Postproc marthe 
    """
    # io['histobil_deb'] = io['histobil_deb'].swaplevel() # new martpy has invert order of level... damn you manlaya ! :)
    if dates is not None:
        io['histobil_deb'] = io['histobil_deb'].loc[io['histobil_deb'].index.get_level_values(1).isin(dates),:] # todo tester pour des non zone !
        # if io['histoclim'] is not None:
            # io['histoclim'] = io['histoclim'].loc[io['histoclim'].index.get_level_values(0).isin(dates),:]
    
    ppprint("Numerical performance analyses.\n")
    # -- Plot conv
    if add_other_sim_bil:
        others_bis = other_sim
    else:
        others_bis = None

    mk_plot(io['histobil_deb'], '%_Non_Converg'  , others_bis, resdir=resdir, fout='non-converg_int_percent_with_perman.png', hline=1)
    mk_plot(io['histobil_deb'], '%_Non_CV_Gl_Pas', others_bis, resdir=resdir, fout='non-converg_glob_percent_with_perman.png')
    mk_plot(io['histobil_deb'].iloc[1:,:], '%_Non_Converg'  , others_bis, resdir=resdir, fout='non-converg_int_percent_transit.png', hline=1)
    mk_plot(io['histobil_deb'].iloc[1:,:], '%_Non_CV_Gl_Pas', others_bis, resdir=resdir, fout='non-converg_glob_percent_transit.png')
    mk_plot(io['histobil_deb'], 'Nbre_Réduc_Pomp', others_bis, resdir=resdir, fout='nb_reduc_pump.png')
    mk_plot(io['histobil_deb'], 'Nombre_Itérat'  , others_bis, resdir=resdir, fout='nb_iter.png')
    mk_plot(io['histobil_deb'], 'Nombre_Désatur' , others_bis, resdir=resdir, fout='nb_desatur.png')
    
    mk_plot(io['histobil_deb'].iloc[1:,:], 'd_BilanVol_Pas'  , resdir=resdir, fout='ecart_bil.png')
    io['histobil_deb']['%_non_prelv'] = (io['histobil_deb']['Réduct_Pompage'] / io['histobil_deb']['Sort_Pompag_fix']).abs() * 100
    mk_plot(io['histobil_deb'], '%_non_prelv'  , resdir=resdir, fout='par_non_prelv.png')
    
    # --- make df obs-sim
    dfobsim, dfobs = make_df_obs_sim(io, dates, path_obs=path_obs)
    
    if (dfobs is not None) and (not dfobs.empty):
        # --- compute metrics
        # dfobsim.columns = dfobsim.columns.droplevel(0)
        ppprint("Computing metrics\n")
        df_metrics = compute_metrics(dfobsim.loc[calibr_dates[0]:calibr_dates[1], :])
        
        df_metrics.to_csv(Path(resdir, 'metrics.txt'), sep='\t', float_format='%.3f')
        df_metrics.describe().to_csv(Path(resdir, 'metrics_synthesis.txt'), sep='\t', float_format='%.3f')
        # grp = df_metrics.groupby('')  # field is not in df_metrics :(
         
        df_metrics[df_metrics['nse_bias_excluded'] < -5] = np.nan
        df_metrics = df_metrics[~df_metrics.isin([np.nan, np.inf, -np.inf]).any(axis=1)]
        plot_hist_metrics(df_metrics, histo, resdir) # histogramm of metrics
        
        # map of metrics
        gdfhisto = histo.set_index(histo['Name'].str.slice(0,10)).join(df_metrics, rsuffix='_metrics')
        # for map, get max nse line if dups
        gdfhisto = gdfhisto.loc[ gdfhisto.fillna(0).groupby(gdfhisto.index.str.slice(0,10))['nse_bias_excluded'].idxmax()]
        gdfhisto = gdfhisto.dropna(subset=['nse', 'rmse'])
        if not gdfhisto.empty:
            plot_map_metrics(gdfhisto, polygs, resdir)
    else:
        print('No obs at all.')
        df_metrics = None
    
    # --- plot obs sim ***************
    ppprint("Plotting history matching:\n")
    os.makedirs(Path(resdir, 'timeseries'), exist_ok=True)
    gen_plot_obs_sim(dfobsim, histo, dfobs, df_metrics, Path(resdir, 'timeseries'), polygs, other_sim, sim_name, dates=dates)
    # -------------------------
    
    # Plot some bilhyd results
    bil_glo = io['histobil_deb'].loc[('global', slice(None)), :].droplevel(0)#.drop('Date', axis=1)
    plot_bil_hyd(bil_glo, resdir, level='global', fout='bilan_hyd_global.png')
    ppprint("Water balance analyses\n")
    for zone in np.unique(io['histobil_deb'].index.get_level_values(0)):
        tmp = io['histobil_deb'].loc[(zone, slice(None)), :].droplevel(0)#.drop('Date', axis=1)
        plot_bil_hyd(
            tmp,
            resdir,
            level=zone,
            fout='bilan_hyd_zone_{}.png'.format(zone)
        )
        plot_ratio_inf_prelv(tmp, resdir, fout='bil_ratio_prelv_inf_{}.png'.format(zone) )
        
        plot_bil_rivi(io['histobil_riv_dra_lac'].loc[(zone, slice(None)),:], resdir, fout=f'bil_rivi_{zone}.png')

    # Plot some histoclim results
    if 'histoclim' in io.keys():
        if io['histoclim'] is not None:
            for zone in np.unique(io['histoclim'].index.get_level_values(0)):
                mart.plot_bil_clim(
                    io['histoclim'].loc[(zone, slice(None)), :].droplevel(0),
                    file_out=Path(resdir, 'bilan_hydroclim_global.png')
                )
    # ---- finaly, mv res
    # mv_res(resdir)
    
    return 0


if __name__ == "__main__":
    
    import warnings
    warnings.filterwarnings("ignore")

    resdir = 'postproc/_plots_v117b'
    PATH_OBS = "./obs"
    PATH_RMA = "./mart_cabbalr_ztopo_v117"
    # PATH_SIM = f"{PATH_RMA}/sim_1991-2020"
    PATH_SIM = f"{PATH_RMA}"
    SIM_NAME = "sim"
    
    print('===============================================')
    print('MARTHE Hydrogeological modelling postprocessing')
    print('===============================================')
    print('main sim experiment: {}\n'.format(PATH_SIM))
    
    os.makedirs(resdir, exist_ok=True)
    
    print('Reading other simulations to compare...')
    # for now, only for historymatching ; TODO: conv/bil anomaly
    other_sim = {
        'v110': {'historiq': mart.read_historiq('./mart_cabbalr_ztopo_v110_k_capt/historiq.prn')},
        # 'previous': {'historiq': mart.read_historiq('./mart_cabbalr_ztopo_v115-v116_modif_zsol/historiq.prn')},
        # 'v114': {'historiq': mart.read_historiq('./mart_cabbalr_ztopo_v114_sep_fract_recal/historiq.prn')},
        'v118': {'historiq': mart.read_historiq('./mart_cabbalr_ztopo_v118/historiq.prn')},
    }
    
    print('Reading GIS files...')
    # --- get shapes for plot
    extent   = gpd.read_file('./sig/contour_mart_cabb.shp')
    shp_zone = gpd.read_file('./sig/area/mask_cabbalr.shp')
    # shp_zone = extent
    rivi  = gpd.read_file('./sig/river/new_rivi_modif.shp')
    # dfhisto = mart.read_histomesh("{}/craie_npc_for_metrics.histo".format(PATH_RMA))
    dfhisto = mart.read_histomesh("{}/mart_cabbalr_for_metrics.histo".format(PATH_RMA))
    histo = gpd.read_file('./obs/histo_for_metrics.gpkg')
    histo = histo[histo['Name'].isin(dfhisto['Name'].values)]
    missing = dfhisto[~dfhisto['Name'].isin(histo['Name'].values)]
    if not missing.empty:
        print('Missing obs stations in gpkg:')
        print(missing)

    print('Loading main experiment simulations...')
    io = load_sims(PATH_SIM)
    dates = io['historiq'].index[io['historiq'].index.is_month_end]
    dates = dates[dates.slice_indexer('1992-01-01')]
    
    print('Processing...')
    # TODO add NIC with sim2
    status = main(
        io,
        histo,
        dates=dates, #pastp['Date'],
        resdir=resdir,
        other_sim=other_sim,
        polygs=[extent, rivi, shp_zone],
        sim_name=SIM_NAME,
        path_obs=PATH_OBS,
        add_other_sim_bil=False,
    )
    
    print("\n\033[0;33m That's all folks !\033[0m")
    sys.exit(status)
