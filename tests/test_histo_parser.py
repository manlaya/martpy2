#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd

from martpy.inputs.mart_histo import (
    MartHisto,
    read_histo_file
)
from martpy.inputs.io_utils import _fmt_nchar


HISTO_FILE_READ = './tests/data/mart_hallue/hallue_with_afluent.histo'
HISTO_FILE = './tests/data/mart_hallue/hallue.histo'
# histo_file = './tests/data/mart_72/Craie_NPC.histo'
# histo_file = './tests/data/mart_74/craie_npc_with_obs_messy.histo'


def debug_regex():
    import re
    
    xfile = 'tests/data/mart_hallue/hallue.histo'
    # xfile = 'tests/data/mart_uk/mart_uk_files.histo'

    # copy from src/martpy/inputs/mart_histo.py
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
    
    with open(xfile, mode='r', encoding='ISO-8859-1') as f:
        histo = [line.rstrip() for line in f if '/HISTO/' in line]
    
    for line in histo:
        m = re.search(_HISTO_PARSER, line)
        if m:
            res = m.groupdict()
        else:
            # for the debugger (go line by line here)
            reg1 = r'^\s*(?P<id_grid>\d*)/(?P<variable>\w+)\s*/HISTO/\s*=\s*'
            reg2 = reg1 + r'/(?P<mode>[A-Za-z]+):'
            reg3 = reg2 + r'(?P<coord_x>[A-Za-z]+)=\s*'
            reg4 = reg3 + r'(?P<x>[+-]?\d+(?:\.\d+)?(?:e[+-]\d+)?),*'
            reg5 = reg4 + r'(?P<coord_y>[A-Za-z]+[^\x00-\x7F]?)=\s*'
            reg6 = reg5 + r'(?P<y>[+-]?\d+(?:\.\d+)?(?:e[+-]\d+)?),*'
            reg7 = reg6 + r'(?:[P|L]=\s*(?P<layer>\d+);)?\s*'
            reg8 = reg7 + r'(?:Col_Obs=(?P<obs>[^ ]+)\s*;)?\s*'
            reg9 = reg8 + r'(?:Name=(?P<name>[^ ]+))?'
            reg10 = reg9+ r'(?P<name_old>[^\s;]+)?'
            re.search(reg1, line).groupdict()
            re.search(reg2, line).groupdict()
            re.search(reg3, line).groupdict()
            re.search(reg4, line).groupdict()
            re.search(reg5, line).groupdict()
            re.search(reg6, line).groupdict()
            re.search(reg7, line).groupdict()
            re.search(reg8, line).groupdict()
            re.search(reg9, line).groupdict()
            re.search(reg10, line).groupdict()
            raise ValueError('No match found in histo file')


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
    assert histo['mode'].iloc[-1] == 'AFFL', 'Error while reading histo file, wrong mode'
    assert histo['river_cell'].iloc[-1] == 1, 'Error while reading histo file, wrong mode'


def test_writer():
    histo = read_histo_file(HISTO_FILE)
    histo_file_out = './tests/data/tmp_outputs/histo_written.histo'
    histo.write_file(histo_file_out)
    # re read and compare file
    histo2 = read_histo_file(histo_file_out)
    assert len(histo2) == len(histo), 'Error while writing histo file'
    assert histo2.equals(histo), 'Error reread histo does not match'


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
