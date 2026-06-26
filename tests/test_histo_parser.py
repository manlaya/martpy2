#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import io
from unittest.mock import patch

import numpy as np
import pandas as pd

from martpy.inputs.mart_histo import (
    _HISTO_PATTERNS,
    _HISTO_PARSER,
    MartHisto,
    read_histo_file
)
from martpy.inputs._io_utils import _fmt_nchar


HISTO_FILE_READ = './tests/data/histo/hallue_with_afluent.histo'
HISTO_FILE = './tests/data/mart_hallue/hallue.histo'
# histo_file = './tests/data/mart_72/Craie_NPC.histo'
# histo_file = './tests/data/mart_74/craie_npc_with_obs_messy.histo'


def debug_regex():
    import re

    xfile = 'tests/data/mart_hallue/hallue.histo'
    # xfile = 'tests/data/mart_uk/mart_uk_files.histo'

    # copy from src/martpy/inputs/mart_histo.py
    # keep it here for dev purpose
    _HISTO_PATTERNS = (
        r'^\s*(?P<id_grid>\d*)/(?P<variable>\w+)\s*/HISTO/\s*=\s*',
        r'/(?P<mode>[A-Za-z]+):',
        r'(?P<coord_x>[A-Za-z]+)=\s*',
        r'(?P<x>[+-]?\d+(?:\.\d+)?(?:e[+-]\d+)?),*',  # float,int,pos-neg parsing,e+- allowed
        # https://stackoverflow.com/questions/2124010/grep-regex-to-match-non-ascii-characters
        r'(?P<coord_y>[A-Za-z]+[^\x00-\x7F]?)=\s*',   # Marthe f****** non ASCII char!
        r'(?P<y>[+-]?\d+(?:\.\d+)?(?:e[+-]\d+)?),*',
        r'(?:[P|L]=\s*(?P<layer>\d+);)?\s*',          # optional if tronc/afl, L in english
        r'(?:Col_Obs=(?P<obs>[^ ]+)\s*;)?\s*',
        r'(?:Name=(?P<name>[^;\n]+))?',
        r'(?P<name_old>[^;\n]+)?',                    # get name, even if "Name=" is not here (marthe<v7.8)
    )  # one hell of a regex
    _HISTO_PARSER = ''.join(_HISTO_PATTERNS)  # re.compile?
    regx = []
    for i, r in enumerate(_HISTO_PATTERNS):
        regx.append(''.join(_HISTO_PATTERNS[0:i+1]))

    with open(xfile, mode='r', encoding='ISO-8859-1') as f:
        histo = [line.rstrip() for line in f if '/HISTO/' in line]

    for line in histo:
        m = re.search(_HISTO_PARSER, line)
        if m:
            res = m.groupdict()
        else:
            raise ValueError('No match found in histo file')

        # for the debugger (go line by line here)
        for reg in regx:
            print(re.search(reg, line).groupdict())


def test_fmt_xchar():
    number = [
       152.1622,
       2.56e6,
       615375.11,
       12.365,
       2.542369,
       2.547e8,
    ]
    for n in number:
        x = _fmt_nchar(n)
        assert len(x) == 7, 'fmt 7 char for histo is wrong'
        assert x[-1] not in ['e', '+', '-'], 'fmt 7 char for histo is wrong'


def test_reader():
    histo = read_histo_file(HISTO_FILE_READ)

    assert isinstance(histo, MartHisto), 'Error while reading histo file'
    assert len(histo) == 6, 'Error while reading histo file'

    for x in ['id_grid', 'variable', 'mode','x', 'y', 'col', 'row', 'layer', 'name']:
        assert x in histo.columns, f'Error, missing column {x} in histo file'

    assert histo['name'].iloc[0] == '00464X0013/H1', 'Error while reading histo file, wrong name'
    assert histo['x'].iloc[0] == 611.62, 'Error while reading histo file, wrong x'
    assert histo['y'].iloc[0] == 2560.0, 'Error while reading histo file, wrong y'

    assert histo['col'].iloc[-2] == 22, 'Error while reading histo file, wrong col'
    assert histo['row'].iloc[-2] == 40, 'Error while reading histo file, wrong row'
    assert histo['name'].iloc[-3] == 'E6397010', 'Error while reading histo file, wrong name'

    assert histo['mode'].iloc[-1] == 'AFFL', 'Error while reading histo file, wrong mode'
    assert histo['river_cell'].iloc[-1] == 1, 'Error while reading histo file, wrong mode'

    assert histo['obs'][0] == 1
    assert pd.isna(histo['obs'][1])

    assert np.all(np.isin(['charge', 'debit_rivi'] , np.unique(histo['variable'])))
    assert np.all(np.isin(['XCOO', 'COOR', 'MAIL', 'AFFL'] , np.unique(histo['mode'])))


def test_name_fmt():
    test_str_histo = """Modélisation du bassin de la Somme en régime transitoire
    #<V7.8.4># --- Fin du texte libre --- ; Ne pas modifier/retirer cette ligne
    /Charge       /HISTO/   =   /XCOO:X= 617.43Y= 2558.7P=      1; Name=00471X0010/H1
    /Charge       /HISTO/   =   /XCOO:X= 617.43Y= 2558.7P=      1; 00471X0010/H1
    /Charge       /HISTO/   =   /XCOO:X= 617.43Y= 2558.7P=      1; Name=00471X0010 H1
    *** Fin du fichier des 'Mailles à Historique'       ***
    """
    expected_name = '00471X0010/H1'
    with patch('builtins.open', return_value=io.StringIO(test_str_histo)):
        result = read_histo_file('dummy.histo')  # fake path with mock.patch
        assert result['name'][0] == expected_name
        assert result['name'][1] == expected_name
        assert result['name'][2] == expected_name.replace('/', ' ')


def test_writer():
    histo = read_histo_file(HISTO_FILE)
    histo_file_out = './tests/data/tmp_outputs/histo_written.histo'
    histo.write_file(histo_file_out)
    # re read and compare file
    histo2 = read_histo_file(histo_file_out)
    assert len(histo2) == len(histo), 'Error while writing histo file'
    assert histo2.equals(histo), 'Error reread histo does not match'


def test_convert_geodataframe():
    from martpy import grid as mgrid
    from geopandas import GeoDataFrame
    histo = read_histo_file(HISTO_FILE)
    grid = mgrid.load_marthe_grid('./tests/data/mart_hallue/hallue.permh', add_col_row=True)

    gdf = histo.to_geodataframe(epsg=27572, fill_coords=True, grid=grid)
    assert isinstance(gdf, GeoDataFrame)
    assert hasattr(gdf, 'geometry')
    assert not np.any(gdf['geometry'].isna())


def test_write_longer_coords():
    FACTOR = 1000
    histo = read_histo_file(HISTO_FILE)
    histo.x = histo.x * FACTOR
    histo.y = histo.y * FACTOR
    histo_file_out = './tests/data/tmp_outputs/histo_written_longer_coords.histo'
    histo.write_file(histo_file_out)

    # re read and compare file
    histo2 = read_histo_file(histo_file_out)
    assert len(histo2) == len(histo), 'Error while writing histo file with longer coords'
    assert np.allclose(histo2.x.dropna(), histo.x.dropna()), \
        'Error while writing histo file with longer coords - X does not match'
    assert np.allclose(histo2.y.dropna(), histo.y.dropna()), \
        'Error while writing histo file with longer coords - Y does not match'
    assert histo2.name.dropna().equals(histo.name.dropna()), \
        'Error while writing histo file with longer coords - Name does not match'


def test_precision_lost():
    histo = read_histo_file('./tests/data/histo/MOD82_Safran_BV_Ext.histo')
    histo_file_out = './tests/data/tmp_outputs/histo_written_precision.histo'
    histo.write_file(histo_file_out)

    # re read and compare file
    histo2 = read_histo_file(histo_file_out)
    assert len(histo2) == len(histo), 'Error while writing histo file with precision lost'
    assert np.allclose(histo2.x.dropna(), histo.x.dropna()), 'Error while writing histo file with precision lost - X does not match'
    assert np.allclose(histo2.y.dropna().values, histo.y.dropna().values), 'Error while writing histo file with precision lost - Y does not match'
    assert np.all(histo2.y.dropna().values - histo.y.dropna().values == 0)  # bug with allclose?


def test_get_xy_from_grid():
    from martpy import grid as mgrid

    histo = read_histo_file(HISTO_FILE)
    grid = mgrid.load_marthe_grid('./tests/data/mart_hallue/hallue.permh', add_col_row=True)
    histo2 = histo.fill_coordinates_from_grid(grid)
    assert not np.any(np.isnan(histo2.x)), 'Error while getting x from grid'
    assert not np.any(np.isnan(histo2.y)), 'Error while getting y from grid'
    assert not np.any(pd.isna(histo2.col)), 'Error while getting col from grid'
    assert not np.any(pd.isna(histo2.row)), 'Error while getting row from grid'


def test_reader_normalizes_variable_column():
    """Issue #8: variable column is normalized to lowercase generic names."""
    histo = read_histo_file(HISTO_FILE)
    variables = set(histo['variable'].unique())
    # Histo file holds 'Charge' and 'Débit_Rivi' -> canonical generic forms
    assert variables == {'charge', 'debit_rivi'}, (
        f"variable column should be canonical generic names, got {variables}"
    )
    # And no raw histo form leaked through
    assert 'Charge' not in variables
    assert 'Débit_Rivi' not in variables


def test_writer_accepts_generic_varnames():
    """write_file() must convert generic names (e.g. CHARGE, charge) to histo names."""
    histo = read_histo_file(HISTO_FILE)
    # Replace canonical 'charge' with its uppercase alias from marthe_variables.csv
    histo_alias = histo.copy()
    histo_alias.loc[histo['variable'] == 'charge', 'variable'] = 'CHARGE'

    histo_file_out = './tests/data/tmp_outputs/histo_generic_varnames.histo'
    histo_alias.write_file(histo_file_out)

    # The file on disk must hold the native histo name, even when written from CHARGE
    with open(histo_file_out, encoding='ISO-8859-1') as f:
        content = f.read()
    assert '/Charge' in content, 'Histo file must contain native histo name "Charge"'
    assert '/CHARGE' not in content, 'Generic uppercase CHARGE must not leak into histo file'


def test_writer_roundtrip_preserves_variable():
    """read -> write -> read returns the same canonical variable values."""
    histo = read_histo_file(HISTO_FILE)
    out = './tests/data/tmp_outputs/histo_roundtrip.histo'
    histo.write_file(out)
    histo2 = read_histo_file(out)
    assert list(histo2['variable']) == list(histo['variable']), \
        'variable column must survive read->write->read unchanged'


def test_read_grid_only_histo():
    """Issue #32: a .histo with only grid-mode observations (col/row, no X/Y)
    must read without raising.

    The absent x/y columns must stay numpy float64 with NaN (not pd.NA / Float64),
    because np.isnan and fill_coordinates_from_grid rely on numpy floats.
    """
    histo = read_histo_file('./tests/data/histo/grid_only.histo')

    assert len(histo) == 2, 'Error while reading grid-only histo file'
    # grid coordinates are parsed correctly
    assert histo['col'].tolist() == [12, 5], 'wrong col in grid-only histo'
    assert histo['row'].tolist() == [34, 6], 'wrong row in grid-only histo'
    assert histo['layer'].tolist() == [1, 2], 'wrong layer in grid-only histo'

    # x/y are absent -> NaN, and must stay numpy float64 (Option A)
    assert histo['x'].dtype == np.float64, 'x must be numpy float64'
    assert histo['y'].dtype == np.float64, 'y must be numpy float64'
    assert np.all(np.isnan(histo['x'])), 'x must be NaN for grid-only histo'
    assert np.all(np.isnan(histo['y'])), 'y must be NaN for grid-only histo'

    # col/row stay nullable Int64
    assert isinstance(histo['col'].dtype, pd.Int64Dtype), 'col must be Int64'
    assert isinstance(histo['row'].dtype, pd.Int64Dtype), 'row must be Int64'


def test_read_histo_uk():
    histo = read_histo_file('./tests/data/mart_uk/mart_uk_files.histo')
    assert len(histo) == 3, 'Error while reading histo file'
    assert histo['name'].iloc[0] == 'TOTO', 'Error while reading histo file, wrong name'
    assert histo['name'].iloc[1] == 'tata', 'Error while reading histo file, wrong name'
    assert histo['mode'].iloc[0] == 'CELL', 'Error while reading histo file, wrong mode'
    assert histo['mode'].iloc[1] == 'XCOO', 'Error while reading histo file, wrong mode'
    assert histo['mode'].iloc[2] == 'COOR', 'Error while reading histo file, wrong mode'
    assert 'col' in histo.columns
    assert 'row' in histo.columns
    assert 'x' in histo.columns
    assert 'y' in histo.columns
    assert 'layer' in histo.columns
    # TODO: debug english row columns (without breaking french...)
    # assert 'R' not in histo.columns


def main():
    print('Testing histo parser')
    test_reader()
    test_writer()
    test_get_xy_from_grid()
    test_write_longer_coords()
    print('All tests passed')


if __name__ == '__main__':
    main()
