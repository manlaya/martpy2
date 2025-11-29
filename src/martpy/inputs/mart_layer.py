#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import pandas as pd

# from pymarthe "marthe_utils.py:L140" / slightly modified
#def get_layers_infos(layfile, base = 1):
def read_layer(file_layer, encoding='ISO-8859-1', base=1):
    """ Read a `.layer` marthe file
    
    Extract layer informations from Marthe .layer file 

    Parameters
    ----------
    layfile : str
        Marthe .rma file path
    base : int, optional
        base for layer counting.
        Python is 0-based.
        Marthe is compiled in 1-based (Fortran)
        Default is 1.

    Returns
    -------
    layers_infos: pandas.DataFrame
        layer informations like layer numbers, thickness, ...
    geom_infos: dict
        dictionnary containing number of nested grids,
        radial grid boolean, cross section grid boolean.
    
    Notes
    -----

    Output format:

        layer  thickness  epon_sup   ke  anisotropy     name
    0       1       50.0         0  0.0         0.0  layer_0
    1       2      150.0         1  0.0         0.0  layer_1

    Example
    -------
    layfile = 'mymarthemodel.layer'
    layers_infos, geom_infos = get_layers_infos(layfile)
    """
    # ---- Get .layer content as text
    with open(file_layer, 'r', encoding=encoding) as f:
        content = f.read()
    
    # ---- set regular expressions
    regex = [
        r"Cou=\s*(\d+)", r"[Epais|Épais]=\s*([-+]?\d*\.?\d+|\d+)",
        r"[Epon|Épon] Sup =\s*(\d+)", r"Ke=\s*(\d+)", r"Anisot=\s*(\d+)"
    ]
    
    # ---- Build Dataframe of all layer informations
    df = pd.DataFrame(
        [re.findall(r, content) for r in regex],
        index =['layer', 'thickness', 'epon_sup', 'ke', 'anisotropy'],
        dtype=float
    ).T
    
    # ---- Manage dtypes of informations
    dtypes = [int, float, int, float, float]
    layers_infos = df.astype({col:dt for col, dt in zip(df.columns, dtypes)})
    
    # ---- Manage layer counting from base
    layers_infos['layer'] = layers_infos['layer'].add(base-1)

    # ---- Add layer name if exist
    re_lnmes = r";\s*Name=\s*(.+)\n"
    if re.search(re_lnmes, content) is None:
        layers_infos['name'] = 'layer_' + layers_infos['layer'].astype(str)
    else:
        layers_infos['name'] = re.findall(re_lnmes, content)

    # ---- Determine number of "gigogne" (a.k.a nested grids)
    # and parse other information: grid is radial or cross-section
    geom_infos = {
        'n_subgrid': int(
            re.search(r"(\d+)=Nombre(\s+\S+)*\s*Gigogne", content, re.IGNORECASE).group(1)
        ),
        'is_cross_sect': bool(int(
            re.search(r"(\d+)=Coupe Verticale", content, re.IGNORECASE).group(1)
        )),
        'radial_grid': bool(int(
            re.search(r"(\d+)=Maillage Radial", content, re.IGNORECASE).group(1)
        )),
    }

    return layers_infos, geom_infos


def _write_layer(layer_df, dict_geom, file_layer, title='marthe layer file'):
    """ Write a layer file (`*.layer`)
    """
    with open(file_layer, mode='w', encoding='ISO-8859-1') as f:
        f.write(f'{title}\n')
        f.write(' *** Description des couches aquifères               ***\n')
        for row in layer_df.to_dict('records'):
            f.write(
                'Cou={0:3d};Épais={1:6.0f};Épon Sup ={2:3d};//////////=     0;'
                'Uni Ke={3:7.2f};Anisot= {4:7.2f}\n'.format(
                    int(row['layer']), float(row['thickness']), int(row['epon_sup']),
                    float(row['ke']), float(row['anisotropy'])
                )
            )
        f.write(' *** Sous-maillages Gigognes, Coupe, Radial          ***\n')
        f.write('{:>10}=Nombre de sous-maillages Gigognes\n'.format(dict_geom.get('n_subgrid', 0)))
        f.write('{:>10}=Coupe Verticale à Substratums Irréguliers (0=Non ; 1 => Coupe verticale)\n'.format(
            dict_geom.get('is_cross_sect', 0))
        )
        f.write('{:>10}=Maillage Radial [Rayon , Angle] (0=Non ; 1 => Maillage radial)\n'.format(
            dict_geom.get('radial_grid', 0))
        )
        f.write(' *** Fin du fichier \'Description des couches\'        ***\n')
    return
