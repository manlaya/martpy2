#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import pandas as pd
from numpy import nan

from martpy.inputs.io_utils import _build_header


_HISTO_PARSER = (
    r'^\s*(?P<id_grid>\d*)/(?P<variable>\w+)\s*/HISTO/\s*=\s*'
    r'/(?P<mode>[A-Za-z]+):'
    r'(?P<coord_x>[A-Za-z])=\s*(?P<x>[-\d.]+)'
    r'(?P<coord_y>[A-Za-z])=\s*(?P<y>[-\d.]+)'
    r'P=\s*(?P<layer>\d+);\s*'
    r'(?:Col_Obs=(?P<obs>[^ ]+)\s*;)?\s*'
    r'(?:Name=(?P<name>[^ ]+))?'
    r'(?P<name_old>[^\s;]+)?'  # get name, even if "Name=" is not here (marthe<v7.8)
)  # one hell of a regex


class MartHisto(pd.DataFrame):

    def __init__(self, df):
        super().__init__(df)

    def add_observation(
        self,
        field,
        mode,
        igrid=0,
        x=None,
        y=None,
        col=None,
        lig=None,
        layer=1,
        Name=None,
        obs=None,
    ):
        # nb check that field is a Marthe field
        return
    
    def remove_observation(
        self,
        name=None,
        mode=None,
        igrid=None,
        x=None,
        y=None,
        col=None,
        lig=None,
        layer=None
    ):
        pass

    def write_file(
        self,
        file_name='file.histo',
        title='Marthe Time series',
        encoding='ISO-8859-1'
    ):
        """ Write a .histo file
        To extract simulation results at specific locations

        Parameters
        ----------
        file_name : str, optional
            name of the file to be written, by default 'file.histo'
        title : str, optional
            a custom header in file, by default 'Marthe Time series'
        encoding : str, optional
            encoding for the file, by default 'ISO-8859-1'
        """
        histo_lines = _build_header(title)
        histo_lines.extend(_build_histo_from_dataframe(self))
        with open(file_name, mode='w', encoding=encoding) as f:
            f.write('\n'.join(histo_lines))

    @staticmethod
    def _set_xy_from_grid(df, grid):
        """ memo: grid is a marthe grid file, read with gm library
        and add_col_row=True
        """
        df_histo = df.copy()
        df_histo_cells = df_histo.dropna(subset=['col', 'row'])
        for i, row in df_histo_cells.iterrows():
            _grid_loc = grid.gm.search_zone(i=row['col'], j=row['row'])
            # get only first x,y; even if multilayer, it's the same coordinates
            df_histo.loc[row.name, 'x'] = _grid_loc['x'].data[0]
            df_histo.loc[row.name, 'y'] = _grid_loc['y'].data[0]
        return df_histo
    
    @staticmethod
    def _set_col_row_from_grid(df, grid):
        """ memo: grid is a marthe grid file, read with gm library
        and add_col_row=True
        """
        df_histo = df.copy()
        df_histo_cells = df_histo.dropna(subset=['x', 'y'])
        for i, row in df_histo_cells.iterrows():
            _grid_loc = grid.gm.search_zone(x=row['x'], y=row['y'])
            # get only first x,y; even if multilayer, it's the same coordinates
            df_histo.loc[row.name, 'col'] = _grid_loc['col'].data[0]
            df_histo.loc[row.name, 'row'] = _grid_loc['lig'].data[0]
        return df_histo
    
    def fill_coordinates_from_grid(self, grid):
        """ Get missing coordinates (x,y or row,col) from grid

        Parameters
        ----------
        grid : xr.Dataset with gridmarthe accessor
            gridfile as read by gridmarthe wrappers. See 
            :py:func:`martpy.grid.load_marthe_grid`
            grid need col/row variables, so `add_col_row=True` must be set in
            load_marthe_grid call.

        Returns
        -------
        MartHisto
            DataFrame with coordinates filled
        """
        df_histo = self.copy()
        df_histo = self._set_col_row_from_grid(df_histo, grid)
        df_histo = self._set_xy_from_grid(df_histo, grid)
        return df_histo


def read_histo_file(histo_file, encoding='ISO-8859-1'):
    """ Read a .histo file from Marthe model

    Parameters
    ----------
    histo_file : str
        Path to the .histo file
    encoding : str, optional
        File encoding, by default 'ISO-8859-1'
    
    Returns
    -------
    pd.DataFrame
        DataFrame with columns:
        - id_grid: the grid index in which is located the observation in model domain
        - variable: the variable to extract from simulation
        - name: name of the observation
        - mode: mode of the observation (XCOO, GRID, etc.)
        - x, y or col, lig: coordinates of the observation
        - layer: layer of the observation
        - interp: wether the simulation extracted at obs location is interpolated or not
    """
    with open(histo_file, encoding=encoding) as f:
        lines = [line.rstrip() for line in f if '/HISTO/' in line]
    
    data = []
    for line in lines:
        _match = re.search(_HISTO_PARSER, line)
        # if not _match:
        #     break  # debug
        if _match:
            parsed_vals = _match.groupdict()

            # rename x,y either to col, lig or x,y
            coords_x, coords_y = parsed_vals.pop('coord_x'), parsed_vals.pop('coord_y')
            parsed_vals[coords_x] = parsed_vals.pop('x')
            parsed_vals[coords_y] = parsed_vals.pop('y')

            if parsed_vals['mode'] == 'XCOO':
                parsed_vals['interp'] = True
            else:
                parsed_vals['interp'] = False
            
            # case where Name= is not present but still value
            _name_old = parsed_vals.pop('name_old')
            if _name_old is not None:
                parsed_vals['name'] = _name_old

            # convert id_grid to '0' if empty
            if parsed_vals['id_grid'] == '':
                parsed_vals['id_grid'] = '0'
            
            data.append(pd.DataFrame(parsed_vals, index=[0]))
    
    data = pd.concat(data, ignore_index=True)
    data = _set_histo_df_dtype(data)
    return MartHisto(data)


def _set_histo_df_dtype(data):
    data = data.copy()
    # assert cols are present, then set dtype
    for x in ['X', 'Y', 'C', 'L']:
        if x not in data.columns:
            data[x] = pd.NA
    data = data.rename({
        'X': 'x',
        'Y': 'y',
        'C': 'col',
        'L': 'row',
    }, axis=1)
    data = data.astype({
        'id_grid': int,
        'variable': str,
        'mode': str,
        'x': float,
        'y': float,
        'col': 'Int64',
        'row': 'Int64',
        'layer': int,
        'interp': bool,
        'obs': 'Int64',
        'name': str,
    })
    data = data.replace('None', nan)
    return data


def _build_histo_line(
    id_grid,
    variable,
    mode,
    col=None,
    row=None,
    x=None,
    y=None,
    layer=1,
    name='',
    obs=None,
    interp=None,  # dummy here but in df columns
):
    gig = str(id_grid)
    layer = int(layer)
    if gig == '0':
        gig = ''
    
    line = "{0:>2s}/{1:<13s}/HISTO/   =   /{2:>4s}:".format(
        gig, variable, mode
    )
    if mode.upper() == 'MAIL':
        line += "C={:7d}L={:7d}P={:7d};".format(
            col, row, layer
        )
    elif mode.upper() in ['XCOO', 'COOR']:
        line += "X={:7g}Y={:7g}P={:7d};".format(
            x, y, layer
        )
    else:
        raise ValueError(
            'Unknown `mode` for marthe time serie (*.histo). '
            'Valid modes are: MAIL (cell), XCOO (coordinates with interpolation)'
            'or COOR (xy without interpolation)'
        )
    
    if obs is not None and not pd.isna(obs):
        line += ' Col_Obs={};'.format(obs)
    
    if name is not None and not pd.isna(name):
        line += ' Name={}'.format(name)
    
    return line


def _build_histo_from_dataframe(df):
    """ Build histo file string content from martpy dataframe convention
    
    Returns
    -------
    list:
        list of strings (lines).
    """
    lines = []
    for row in df.to_dict('records'):
        lines.append(_build_histo_line(**row))
    lines.append(' *** Fin du fichier des \'Mailles à Historique\'       ***')
    return lines
