#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

import numpy as np
import pandas as pd

from martpy.inputs._io_utils import _build_header, _fmt_nchar
from martpy.utils.helper import from_histo_varname, to_histo_varname


_HISTO_PARSER = (
    r'^\s*(?P<id_grid>\d*)/(?P<variable>\w+)\s*/HISTO/\s*=\s*'
    r'/(?P<mode>[A-Za-z]+):'
    r'(?P<coord_x>[A-Za-z]+)=\s*'
    r'(?P<x>[+-]?\d+(?:\.\d+)?(?:e[+-]\d+)?),*'  # float,int,pos-neg parsing,e+- allowed
    # https://stackoverflow.com/questions/2124010/grep-regex-to-match-non-ascii-characters
    r'(?P<coord_y>[A-Za-z]+[^\x00-\x7F]?)=\s*'  # Marthe f****** non ASCII char!
    r'(?P<y>[+-]?\d+(?:\.\d+)?(?:e[+-]\d+)?),*'
    r'(?:[P|L]=\s*(?P<layer>\d+);)?\s*'   # optional if tronc/afl, L in english
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
        row=None,
        layer=1,
        Name=None,
        obs=None,
    ):
        # nb check that field is a Marthe field
        raise NotImplementedError

    def remove_observation(
        self,
        name=None,
        mode=None,
        igrid=None,
        x=None,
        y=None,
        col=None,
        row=None,
        layer=None
    ):
        pass

    def write_file(
        self,
        file_name='file.histo',
        title='Marthe Time series',
        encoding='ISO-8859-1',
        lang='fr'
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
        lang: str, optional
            Language of the file, by default 'fr' (french) or 'en' for english
        """
        histo_lines = _build_header(title, lang)
        histo_lines.extend(_build_histo_from_dataframe(self, lang))
        with open(file_name, mode='w', encoding=encoding) as f:
            f.write('\n'.join(histo_lines))

    @staticmethod
    def _set_coords_from_grid(df, grid, mode='xy'):
        """ memo: grid is a marthe grid file, read with gm library
        and add_col_row=True
        """
        if mode.lower() == 'xy':
            # X-column, Y-column, Join-col1, Join-col2
            XCOL, YCOL, JCOL1, JCOL2 = 'x', 'y', 'col', 'row'
        elif mode.lower() == 'cell':
            XCOL, YCOL, JCOL1, JCOL2 = 'col', 'row', 'x', 'y'
        else:
            raise ValueError(f"mode must be 'xy' or 'cell', got {mode}")

        df_histo = df.copy()

        # treat only rows with missing coords - use pd.isna (not np.isnanà for Int64 NaN
        df_histo_cells = df_histo.loc[pd.isna(df_histo[XCOL]) | pd.isna(df_histo[YCOL]), :]
        # Get grid coords dataframe
        _grid_loc = grid.to_dataframe()[['col', 'row', 'x', 'y']]
        # Merge to get coords
        df_histo_cells = df_histo_cells.reset_index().merge(
            _grid_loc, how='left', on=[JCOL1, JCOL2], suffixes=('', '_grid')
        ).set_index('index')
        # replace columns
        df_histo_cells = df_histo_cells.drop(columns=['x', 'y']).rename(
            {f'{XCOL}_grid': XCOL, f'{YCOL}_grid': YCOL}, axis=1
        )
        # return updated dataframe
        df_histo.update(df_histo_cells)
        return df_histo

    @staticmethod
    def _search_col_row_from_xy(df, grid):
        # less efficient than set_coords_from_grid but allow to query xy inside cells
        df_histo = df.copy()
        df_histo_cells = df_histo.loc[
            pd.isna(df_histo['col']) | pd.isna(df_histo['row']), :
        ]
        for idx, row in df_histo_cells.to_dict('index').items():
            _grid_loc = grid.gm.search_zone(x=row['x'], y=row['y'])
            # get only first x,y; even if multilayer, it's the same coordinates
            df_histo.loc[idx, 'col'] = _grid_loc['col'].data[0]
            df_histo.loc[idx, 'row'] = _grid_loc['row'].data[0]
        return df_histo

    @staticmethod
    def _set_coords_from_river_cell(df, grid_river):
        # TODO
        raise NotImplementedError(
            'Setting coordinates from river cells is not yet available'
        )

    def fill_coordinates_from_grid(self, grid):
        """ Get missing coordinates (x,y or row,col) from grid

        Parameters
        ----------
        grid : xr.Dataset with gridmarthe accessor
            gridfile as read by gridmarthe wrappers.
            See :py:func:`martpy.grid.load_marthe_grid` ; grid need col/row
            variables, so `add_col_row=True` must be set in load_marthe_grid
            call.

        Returns
        -------
        MartHisto
            DataFrame with coordinates filled
        """
        df_histo = self.copy()
        df_histo = self._set_coords_from_grid(df_histo, grid, mode='xy')
        df_histo = self._set_coords_from_grid(df_histo, grid, mode='cell')
        if np.any(pd.isna(df_histo['col'])) or np.any(pd.isna(df_histo['row'])):
            df_histo = self._search_col_row_from_xy(df_histo, grid)
        return df_histo

    def to_geodataframe(
        self,
        epsg=27572,
        fill_coords=False,
        grid=None,
        export_file=None
    ):
        """ Export a MartHisto object to shapefile/geopackage

        Parameters
        ----------
        epsg : int, optional
            EPSG code to set CRS, by default 27572
        fill_coords : bool, optional
            fill coordinates from grid, by default False
        grid : xarray.Dataset, optional
            marthe grid dataset, with col/rows variables, by default None.
            Used if `fill_coords=True`
        export_file : str, optional
            If set, the function will directly write GeoDataFrame to disk.
            This is the name of the file to be written, by default None (no
            file written). The extension determine the type of file to be
            written (e.g. 'histo.shp' will write a shapefile, whereas 'histo.gpkg'
            will write a geopackage).
        """
        import geopandas as gpd  # noqa: ICN002
        df = self.copy()

        if fill_coords:
            assert grid is not None, (
                'Please provide a permh grid file, with columns and rows, '
                'grid to fill coordinates.'
            )
            df = self.fill_coordinates_from_grid(grid)

        gdf = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(df['x'].values, df['y'].values, crs=epsg)
        )

        if export_file is not None:
            gdf.to_file(export_file, driver='GPKG')

        return gdf

    @classmethod
    def from_histo_file(self, filename, encoding='ISO-8859-1', verbose=False):
        """ Read a .histo file from Marthe model
        """
        return read_histo_file(filename, encoding=encoding, verbose=verbose)

    @classmethod
    def from_shapefile(self, filename, epsg=27572):
        """ Read a .gpkg file from Marthe model
        to create a MartHisto object
        """
        import geopandas as gpd  # noqa: ICN002
        gdf = gpd.read_file(filename).set_crs(epsg)
        # TODO: check validity of values in columns ?
        expected_columns = [
            'id_grid', 'variable', 'mode', 'x', 'y',
            'col', 'row', 'layer', 'name',
            # 'interp', 'obs', 'river_cell', 'river_afluent'  # not mandatory
        ]
        assert np.isin(expected_columns, gdf.columns).all(), (
            'The geopackage file does not contain all expected columns '
            'to build a MartHisto object.'
            ' Expected columns are: {}'.format(expected_columns)
        )
        return gdf

    @classmethod
    def from_pd(cls, df=None):
        """ Create a MartHisto object from a pandas DataFrame

        Useful if you already have a DataFrame with the expected columns and dtypes,
        or want to convert after a manipulation of the DataFrame (e.g. pd.concat
        of several histo files and/or dataframes).

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame with columns:
            - id_grid: the grid index in which is located the observation in model domain
            - variable: the variable to extract from simulation
            - name: name of the observation
            - mode: mode of the observation (XCOO, GRID, etc.)
            - x, y or col, row: coordinates of the observation
            - layer: layer of the observation
            - interp: wether the simulation extracted at obs location is interpolated or not

        Returns
        -------
        MartHisto
            MartHisto object created from the input DataFrame

        Example
        -------
        >>> res = MartHisto.from_pd(pd.concat([df, previous_histo_df]))
        """
        if df is None or df.empty:
            df = pd.DataFrame(columns=[
                'id_grid', 'variable', 'mode', 'x', 'y',
                'col', 'row', 'layer', 'name', 'interp', 'obs',
                'river_cell', 'river_afluent'
            ])
        # df = _set_histo_df_dtype(df)  # FIXME add duplicate cols for x,y,col,row
        return cls(df)

    @property
    def _constructor(self):
        # should ensure that operations on MartHisto return a MartHisto
        # (e.g. df.copy(), df.loc[], etc.)
        return MartHisto


def read_histo_file(histo_file, encoding='ISO-8859-1', verbose=False,
                    normalize_headers=True, lang='fr'):
    """ Read a .histo file from Marthe model

    .. versionchanged:: next
        The ``variable`` column is now normalized to its canonical generic
        name (accent-free, lowercase, e.g. ``'charge'``, ``'debit_rivi'``)
        instead of the raw histo form (``'Charge'``, ``'Débit_Rivi'``).
        This aligns ``read_histo_file`` with
        :func:`martpy.outputs.read_output_time_series` and removes the need
        for callers to handle both naming schemes. The normalization is on
        by default but can be turned off with ``normalize_headers=False`` to
        keep the raw histo form. See issue #8.

    Parameters
    ----------
    histo_file : str
        Path to the .histo file
    encoding : str, optional
        File encoding, by default 'ISO-8859-1'
    verbose : bool, optional
        Raise on parsing failure if True, by default False
    normalize_headers : bool, optional
        If True, the ``variable`` column is converted to its canonical
        generic name (lowercase, no accents, e.g. ``'charge'``,
        ``'debit_rivi'``) using
        :func:`~martpy.utils.helper.from_histo_varname`. If False, the raw
        histo form is kept (``'Charge'``, ``'Débit_Rivi'``). By default True.
    lang : str, optional
        Language of the input histo file headers (``'fr'`` or ``'en'``),
        used to normalize the ``variable`` column. Default ``'fr'``.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns:
        - id_grid: the grid index in which is located the observation in model domain
        - variable: the variable to extract from simulation (canonical generic name)
        - name: name of the observation
        - mode: mode of the observation (XCOO, GRID, etc.)
        - x, y or col, row: coordinates of the observation
        - layer: layer of the observation
        - interp: wether the simulation extracted at obs location is interpolated or not
    """
    with open(histo_file, encoding=encoding) as f:
        lines = [line.rstrip() for line in f if '/HISTO/' in line]

    data = []
    for line in lines:
        _match = re.search(_HISTO_PARSER, line)
        if not _match and verbose:
            print("Error while parsing histo line")
            raise ValueError('debug')
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
    if normalize_headers:
        data['variable'] = data['variable'].apply(
            lambda v: from_histo_varname(v, lang=lang)
        )
    return MartHisto(data)


def _set_histo_df_dtype(data):
    data = data.copy()
    # assert cols are present, then set dtype
    for x in ['X', 'Y', 'C', 'L']:
        if x not in data.columns:
            data[x] = pd.NA
    # data = data.fillna(np.nan)  # assert no 'None'
    data = data.rename({
        'X': 'x',
        'Y': 'y',
        'C': 'col',
        'L': 'row',
        'Tronç': 'river_cell',
        'Afflu': 'river_afluent'
    }, axis=1)
    data = data.astype({
        'id_grid': int,
        'variable': str,
        'mode': str,
        'x': float,
        'y': float,
        'col': 'Int64',  # Int64 to allow nan in integer column
        'row': 'Int64',
        'layer': 'Int64',
        'interp': bool,
        'obs': 'Int64',
        'name': str,
    })
    if 'river_cell' in data.columns:
        data = data.astype({'river_cell': 'Int64'})
    if 'river_afluent' in data.columns:
        data = data.astype({'river_afluent': 'Int64'})
    data = data.replace('None', np.nan)
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
    river_cell=None,
    river_afluent=None,
):
    gig = str(id_grid)
    layer = int(layer) if layer is not None else ''
    if gig == '0':
        gig = ''

    line = "{0:>2s}/{1:<13s}/HISTO/   =   /{2:>4s}:".format(
        gig, variable, mode
    )
    if mode.upper() in ['MAIL', 'CELL']:
        line += "C={:7d}L={:7d}P={:7d};".format(
            col, row, layer
        )
    elif mode.upper() in ['XCOO', 'COOR']:
        _x, _y = _fmt_nchar(x, nchar=7), _fmt_nchar(y, nchar=7)
        line += "X={}Y={}P={:7d};".format(
            _x, _y, layer
        )
    elif mode.upper() in ['AFFL', 'TRONC']:
        line += "Afflu={:7d},Tronç={:7d}".format(river_afluent, river_cell)
    elif mode.upper() in ['LAKE', 'LAC']:
        line += "N_Lac={},"
        # Aval = ; Globa=
        raise NotImplementedError('Lake in histo file are not yet supported.')
    else:
        raise ValueError(
            'Unknown `mode` for marthe time serie writer (*.histo). '
            'Valid modes are: MAIL or CELL (cell), XCOO (coordinates with interpolation)'
            'or COOR (xy without interpolation). AFFL for river.'
        )

    if obs is not None and not pd.isna(obs):
        line += ' Col_Obs={};'.format(obs)

    if name is not None and not pd.isna(name):
        line += ' Name={}'.format(name)

    return line


def _build_histo_from_dataframe(df, lang='fr'):
    """ Build histo file string content from martpy dataframe convention

    The ``variable`` column is converted from the canonical generic name
    (e.g. ``'charge'``, ``'debit_rivi'``) to the histo file form expected
    by Marthe (``'Charge'``, ``'Débit_Rivi'``) using
    :func:`~martpy.utils.helper.to_histo_varname`. Names that already match
    a histo form pass through unchanged.

    Parameters
    ----------
    df : pd.DataFrame
        Histo dataframe.
    lang : str, optional
        Target language of the histo file (``'fr'`` or ``'en'``).

    Returns
    -------
    list of str
        Histo file lines.
    """
    df_write = df.copy()
    df_write['variable'] = df_write['variable'].apply(
        lambda v: to_histo_varname(v, lang=lang)
    )
    lines = [_build_histo_line(**row) for row in df_write.to_dict('records')]
    if lang.lower() == 'fr':
        lines.append(' *** Fin du fichier des \'Mailles à Historique\'       ***')
    else:
        lines.append(' *** End of file: \'Cells with Time Series\'           ***')
    return lines
