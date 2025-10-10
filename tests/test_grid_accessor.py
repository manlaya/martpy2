#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import xarray as xr

from martpy import grid


def test_load_marthe_grid():
    fgrid = './tests/data/mart_hallue/hallue.permh'
    ds = grid.load_marthe_grid(fgrid, drop_nan=True)
    assert isinstance(ds, xr.Dataset), 'Error while loading grid file'
    assert 'permeab' in ds.keys(), 'Error while loading grid file variable'
    assert ds.gm.dropna()
    return ds


def test_xr_accessor(ds):
    ds = ds.gm.assign_coords()
    assert 'x' in ds.coords, 'Error while adding zone coordinates'
    ds = ds.gm.stack_coords()
    assert 'zone' in ds.coords, 'Error while stacking coordinates'
    return ds


def test():
    ds = test_load_marthe_grid()
    ds = test_xr_accessor(ds)
    return ds


if __name__ == "__main__":
    test()