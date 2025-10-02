#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from matplotlib import pyplot as plt


def plot_clim_water_balance(
    dfbil,
    freq='Y',
    cols_to_keep=['Flux_Pluie', 'Flux_ETP', 'Flux_ETR', 'Infiltration', 'Ruissellement'],
    label_s=[],
    width=.9,
    dt_start=None,
    dt_end=None,
    xlab='Date',
    ylab='mm/year',
    title='Hydroclimatic water balance',
    save=True,
    file_out='bilan_hydroclim_year.png',
    **kwargs
):
    """ BarPlot of climatic water balance in mm/FREQ
    
    Parameters
    ----------
    dfbil : pd.DataFrame
        DataFrame as returned by `martpy.outputs.read_output_balance` with only
        date as index (if zone balance, use .xs to select zone)
    
    freq : str
        Resampling frequency (pandas offset alias) for the plot (default 'Y' for year)
    
    cols_to_keep : list of str
        List of columns to keep and plot (default
        ['Flux_Pluie', 'Flux_ETP', 'Flux_ETR', 'Infiltration', 'Ruissellement'])
    
    label_s : list of str
        List of labels for the legend (default [])
        If the length of label_s is less than cols_to_keep, cols_to_keep is used
    
    width : float
        Width of the bars (default 0.9)
    
    dt_start : str or pd.Timestamp, optional
        Start date to subset the DataFrame (default None)
    
    dt_end : str or pd.Timestamp, optional
        End date to subset the DataFrame (default None)
    
    xlab : str
        Label for x axis (default 'Date')
    
    ylab : str
        Label for y axis (default 'mm/year')
    
    title : str
        Title of the plot (default 'Bilan hydroclimatique')
    
    save : bool
        If True, save the figure (default True)
    
    file_out : str
        Path to save the figure (default 'bilan_hydroclim_year.png')
    
    **kwargs : keyword arguments
        Additional keyword arguments passed to `DataFrame.plot`

    Returns
    -------
    fig, ax : matplotlib Figure and Axes
        The figure and axes objects of the plot
    """

    # 'Pluie','ETP', 'Pluie Efficace','Recharge'
    # Si les colonne et labels n'ont pas la même longueur, erreur
    if len(label_s) < len(cols_to_keep):
        label_s = cols_to_keep
        print('Label < variables to plot --> Colname used !')
    
    # resample by freq
    dfbily = dfbil[cols_to_keep].resample(freq).sum()
    
    # subset df
    if dt_start is not None:
        dfbily = dfbily.loc[dt_start:]
    if dt_end is not None:
        dfbily = dfbily.loc[:dt_end]
    
    # Plot
    fig, ax = plt.subplots(figsize=(12,3))
    dfbily.plot(kind='bar', ax=ax, width=width, **kwargs)

    ax.set_xticklabels([x.strftime("%Y") for x in dfbily.index], rotation=90)
    
    plt.title(label=title, fontweight="bold")
    plt.xlabel(xlab) #, fontweight='bold')
    plt.ylabel(ylab) #, fontweight='bold')
    ax.set_axisbelow(True)
    plt.grid(True)

    plt.legend(labels=label_s, ncol=len(dfbily.columns))
    
    if save:
        plt.savefig(file_out, dpi=150, bbox_inches='tight')
    
    return fig, ax


def plot_aquifer_water_balance(df_bil, level='global', factor=(3600*24*30*1e-6)):
    """ Plot the water balance of the aquifer
    """
    df_bil = df_bil.copy() * factor
    gr_par = dict(linewidth=0.8)

    fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(10,8), sharex='all')
    axes = axes.ravel()

    # Inflow/outflow
    axes[0].set_title("Bilan hydraulique simulé")

    # 1st plot: bil
    df_bil['Recharge_Maill'].plot(ax=axes[0], color='b', label='Recharge', **gr_par)
    (df_bil['Sort_Pompag_fix']+df_bil['Réduct_Pompage']).plot(ax=axes[0], color='r', label='Prélèvements', **gr_par)
    df_bil['Débord/Suintem'].plot(ax=axes[0], color='green', label='Débordement', **gr_par)
    
    col_nr = 'Glob_Riv_Nappe' if level == 'global' else 'Glob_Riv-Nappe'
    df_bil[col_nr].plot(ax=axes[0], color='orange', label='Echanges avec le\nréseau hydrographique', **gr_par)
    
    col_lim = 'Glob_Limites' if level == 'global' else ['Glob_Limit_Zon', 'Glob_Lim_Z_Hau', 'Glob_Lim_Z_Bas']
    df_bil[col_lim].plot(ax=axes[0], color='purple', label='Limites', **gr_par)
    
    # 2nd plot storage variation
    col_stock = 'Glob_Stock' if level == 'global' else 'Stockage'
    df_bil[col_stock].plot(ax=axes[1], color='r', label='Stockage/déstockage', **gr_par)
    
    # 3rd plot, cumulative
    (df_bil[col_stock]).cumsum().plot(ax=axes[2], color='r', label='Cumul', **gr_par) # par mois
    
    for ax in axes:
        ax.hlines(
            0, xmin=df_bil.index.min(), xmax=df_bil.index.max(),
            color='k', linestyle='dashed', alpha=0.7, **gr_par
        )
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

    return fig, axes


def plot_aquifer_water_balance_by_year():
    raise NotImplementedError("Function not implemented yet") # TODO: func Quentin / Amorse


def plot_river_water_balance(df_bil, **kwargs):
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
        'Exutoires',
        # 'Stockage', 'DéStockage',
        # 'Entr_Limit_Zone', 'Sort_Limit_Zone', 
        # 'Écart_Bilan'
    ]

    fig, ax = plt.subplots(figsize=(10,5))
    df_bil[cols].droplevel(0).plot(ax=ax, **kwargs)
    plt.grid()
    plt.legend(loc='lower left')
    plt.xticks(rotation='horizontal', ha='center')
    ax.set_ylabel("Débit ($m^{3}.s^{-1}$)", fontsize=8)
    plt.tight_layout()
    return fig, ax


def plot_layer_transfer():
    raise NotImplementedError("Function not implemented yet")
