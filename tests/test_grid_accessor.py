#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import xarray as xr

from martpy import grid
from martpy.inputs._mart_parser import _parse_mart_file


FGRID = './tests/data/mart_hallue/hallue.permh'


def test_load_marthe_grid():
    ds = grid.load_marthe_grid(FGRID, drop_nan=True)
    assert isinstance(ds, xr.Dataset), 'Error while loading grid file'
    # assert isinstance(ds, grid.MartGrid), 'Error while loading grid file'
    assert 'permeab' in ds.keys(), 'Error while loading grid file variable'


def test_xr_accessor():
    ds = grid.load_marthe_grid(FGRID, drop_nan=True)
    ds = ds.gm.assign_coords()
    assert 'x' in ds.coords, 'Error while adding zone coordinates'
    ds = ds.gm.stack_coords()
    assert 'zone' in ds.coords, 'Error while stacking coordinates'


def test_assign_zone_value():
    par = _parse_mart_file('tests/data/mart_hallue/hallue.mart')
    ds = grid.load_marthe_grid(
        FGRID.replace('permh', 'zgeom'), drop_nan=True, nan_value=[9999., 0.]
    )
    ds2 = ds.gm.assign_zone_values('zgeom', par['init_parameters']['PERMEAB'])
    assert np.isin(np.unique(ds2['zgeom'].values), [0.001, 0.002]).all(), (
        'Error with assign value from zone'
    )


def main():
    test_load_marthe_grid()
    test_xr_accessor()
    test_assign_zone_value()


if __name__ == "__main__":
    main()