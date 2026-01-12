#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd

from martpy.inputs.mart_histo import (
    MartHisto,
    read_histo_file
)

HISTO_FILE_READ = './tests/data/mart_hallue/hallue_with_afluent.histo'
HISTO_FILE = './tests/data/mart_hallue/hallue.histo'
# histo_file = './tests/data/mart_72/Craie_NPC.histo'
# histo_file = './tests/data/mart_74/craie_npc_with_obs_messy.histo'

def test_reader():
    histo = read_histo_file(HISTO_FILE_READ)
    assert isinstance(histo, MartHisto), 'Error while reading histo file'
    assert len(histo) == 6, 'Error while reading histo file'
    for x in ['id_grid', 'variable', 'mode','x', 'y', 'col', 'row', 'layer', 'name']:
        assert x in histo.columns, f'Error, missing column {x} in histo file'


def test_writer():
    histo = read_histo_file(HISTO_FILE)
    histo_file_out = HISTO_FILE.replace('.histo', '_out.histo')
    histo.write_file(histo_file_out)
    # re read and compare file
    histo2 = read_histo_file(histo_file_out)
    assert len(histo2) == len(histo), 'Error while writing histo file'


def test_get_xy_from_grid():
    from martpy import grid as mgrid

    histo = read_histo_file(HISTO_FILE)
    grid = mgrid.load_marthe_grid('./tests/data/mart_hallue/hallue.permh', add_col_row=True)
    histo2 = histo.fill_coordinates_from_grid(grid)
    assert not np.any(np.isnan(histo2.x)), 'Error while getting x from grid'
    assert not np.any(np.isnan(histo2.y)), 'Error while getting y from grid'
    assert not np.any(pd.isna(histo2.col)), 'Error while getting col from grid'
    assert not np.any(pd.isna(histo2.row)), 'Error while getting row from grid'


def main():
    print('Testing histo parser')
    test_reader()
    test_writer()
    test_get_xy_from_grid()
    print('All tests passed')


if __name__ == '__main__':
    main()