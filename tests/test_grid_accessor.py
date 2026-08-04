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

def test_from_float():
    ds = grid.load_marthe_grid(FGRID, drop_nan=True)
    time_coords = ds['time']
    zone_coords= ds['zone']

    result = ds.gm.from_float(zone_coords, 1.0, 'CHARGE')

    assert np.max(result['charge'].values) == 1.0
    assert np.min(result['charge'].values) == 1.0

def test_set_value():
    ds = grid.load_marthe_grid(FGRID, drop_nan=True)

    result = ds.gm.set_value(zone=255, value= 10000.0, varname='permeab')

    assert result

def test_merge():
    ds = grid.load_marthe_grid(FGRID, drop_nan=True)

    result = ds.gm.merge(ds, varname='permh')

    assert 'permeab' in result.data_vars
    assert 'time' not in result.coords

def main():
    test_load_marthe_grid()
    test_xr_accessor()
    test_assign_zone_value()


if __name__ == "__main__":
    main()