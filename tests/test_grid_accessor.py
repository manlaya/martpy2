#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import xarray as xr

from martpy import grid


FGRID = './tests/data/mart_hallue/hallue.permh'


def test_load_marthe_grid():
    ds = grid.load_marthe_grid(FGRID, drop_nan=True)
    assert isinstance(ds, xr.Dataset), 'Error while loading grid file'
    # assert isinstance(ds, grid.MartheGrid), 'Error while loading grid file'
    assert 'permeab' in ds.keys(), 'Error while loading grid file variable'


def test_xr_accessor():
    ds = grid.load_marthe_grid(FGRID, drop_nan=True)
    ds = ds.gm.assign_coords()
    assert 'x' in ds.coords, 'Error while adding zone coordinates'
    ds = ds.gm.stack_coords()
    assert 'zone' in ds.coords, 'Error while stacking coordinates'


def main():
    test_load_marthe_grid()
    test_xr_accessor()


if __name__ == "__main__":
    main()