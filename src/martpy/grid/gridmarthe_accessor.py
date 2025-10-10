#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from functools import wraps
from typing import Union

import xarray as xr

import gridmarthe as gm


# 1st version is from gridmarthe sources.
# this code is now developped here,
@xr.register_dataset_accessor('gm')
class MartheGrid(object):
    """ A Marthe grid attributes/methods accessor for xarray.Dataset objects
    
    Example
    --------
    >>> ds = gm.load_marthe_grid(**kwargs)
    >>> ds.mart.dropna('permeab', 0.)
    """
    def __init__(self, xr_obj: Union[xr.Dataset, None] = None):
        self.obj = xr_obj
    
    @wraps(gm.assign_coords)
    def assign_coords(self, add_lay=True):
        # self.assign_coords.__doc__ = gm.assign_coords.__doc__  # wraps should do it
        return gm.assign_coords(self.obj, add_lay)
    
    @wraps(gm.stack_coords)
    def stack_coords(self, coords=['z', 'y', 'x']):
        return gm.stack_coords(self.obj, coords)
    
    @wraps(gm.dropna)
    def dropna(self, varname='charge', nan_value=9999.):
        return gm.dropna(self.obj, varname, nan_value)
    
    @wraps(gm.search_zone)
    def search_zone(self, i=None, j=None, x=None, y=None, z=None):
        return gm.search_zone(self.obj, i=i, j=j, x=x, y=y, z=z)
    
    @wraps(gm.subset_with_coords)
    def subset_with_coords(
        self,
        dims=['x', 'y'],
        gdf=None,
        xmin=None,
        ymin=None,
        xmax=None,
        ymax=None
    ):
        return gm.subset_with_coords(self.obj, dims, gdf, xmin, ymin, xmax, ymax)
    
    @wraps(gm.clip_dataset)
    def clip_dataset(self, gdf, crs=27572, engine='gdf'):
        return gm.clip_dataset(self.obj, gdf, crs, engine)
    
    @wraps(gm.to_geodataframe)
    def to_geodataframe(self, epsg='EPSG:27572', fmt='long'):
        # from .mgrid_utils import to_geodataframe
        return gm.to_geodataframe(self.obj, epsg, fmt)
    
    def to_recarray(self):
        """ get grid as np.recarray for pymarthe (PEST-Marthe coupling) compatibility
        """
        df = self.obj.to_dataframe()
        return df.to_records()
    
    @wraps(gm.to_raster)
    def to_raster(
        self,
        varname=None,
        x_dim='x',
        y_dim='y',
        time=None,
        epsg=27572,
        filename_tpl='raster'
    ):
        gm.to_raster(self.obj, varname, x_dim, y_dim, time, epsg, filename_tpl)
        return None
    
    @wraps(gm.plot_nested_grid)
    def plot_nested_grid(self, ax=None, varname='charge', **kwargs):
        gm.plot_nested_grid(self.obj, ax, varname, **kwargs)

