#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from functools import wraps
from typing import Union

import xarray as xr

import gridmarthe as gm
import numpy as np


# 1st version is from gridmarthe sources.
# this code is now developped here,
@xr.register_dataset_accessor('gm')
class MartGrid(object):
    """ A Marthe grid attributes/methods accessor for xarray.Dataset objects

    Example
    --------
    >>> ds = gm.load_marthe_grid(**kwargs)
    >>> ds.mart.dropna('permeab', 0.)
    """
    def __init__(self, xr_obj: Union[xr.Dataset, None] = None):
        self.obj = xr_obj

    @staticmethod
    def from_float(zone, value, varname):
        """Load a variable
                
        Parameters
        ----------
        zone : xr.DataArray
            zone array
        value : float
            float number to set all values
        varname : str
            variable name
        
        Returns
        -------
        xarray.Dataset
            New dataset with assigned value
        """
        ds = xr.Dataset(
        {
            varname.lower(): (("time", "zone"), np.full((1, len(zone)), value))
            },
            coords={
            "time": [0],
            "zone": zone

        })
        return ds

    def merge(self, other_ds, varname=None):
        """Merge current dataset with an other
                
        Parameters
        ----------
        other_ds : xr.Dataset | None
            dataset to be merged

        varname : str
            varname used for replace the ext
        
        Returns
        -------
        xarray.Dataset
            New dataset with assigned value
        """
        try:
            if other_ds is None:
                return self.obj

            if varname is not None:
                varname_to_replace = list(self.obj.data_vars.keys())[0]
                self.obj = self.obj.rename({varname_to_replace : varname})

            ds = xr.merge([self.obj, other_ds], join='outer', compat='no_conflicts')
        
            return ds
        except Exception as e:
            print(f"{e}")
            return self.obj

    def set_value(self, zone, value, varname):
        """Set a value in the dataset
                        
        Parameters
        ----------
        zone : int | None
            zone number
        value : float | numpy.ndarray
            value to be set in the zone
        varname : str
            variable name
                
        Returns
        -------
        bool
            True if modified, otherwise False
        """
        try:
            if isinstance(value, float) and zone is not None:
                self.obj[varname].loc[{'zone': zone}] = value
            elif isinstance(value, np.ndarray):
                self.obj[varname].values = value
            else:
                return False
            return True
        except Exception as e:
            print(f"{e}")
            return False

    @wraps(gm.write_marthe_grid)
    def write_marthe_grid(self,
        fileout='grid.out',
        varname=None,
        file_permh: str|None = None,
        nan_value=9999.,
        title=None,
        dims=None,
        force_full_grid=False,
        debug=False
    ):
        return gm.write_marthe_grid(ds=self.obj,
                                    fileout=fileout,
                                    varname=varname,
                                    file_permh=file_permh,
                                    nan_value=nan_value,
                                    title=title,
                                    dims=dims,
                                    force_full_grid=force_full_grid,
                                    debug=debug)

    @wraps(gm.get_active_mask)
    def get_active_mask(
        self, varname: str='permeab',
        nanval: list=[-9999., 0.], as_array=False,
        only_mask=False, shp_file=None
    ):
        return gm.get_active_mask(self.obj,
                                  varname=varname,
                                  nanval=nanval,
                                  as_array=as_array,
                                  only_mask=only_mask,
                                  shp_file=shp_file)
    
    @wraps(gm.assign_coords)
    def assign_coords(self, add_lay=True):
        # self.assign_coords.__doc__ = gm.assign_coords.__doc__  # wraps should do it
        return gm.assign_coords(self.obj, add_lay)
    
    @wraps(gm.stack_coords)
    def stack_coords(self, coords=['z', 'y', 'x']):
        return gm.stack_coords(self.obj, coords)
    
    @wraps(gm.dropna)
    def dropna(self, varname='charge', nan_value=9999.):
        return gm.dropna(ds=self.obj, nanval=nan_value, varname=varname)
    
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

    # Additional methods can be added here
    def assign_zone_values(self, zone_field='zone_geom', list_values_dict=[]):
        """ Assign values to grid cells based on zone information

        Parameters
        ----------
        zone_field : str, optional
            Name of the field in the grid that contains zone information,
            by default 'zone_geom'
        list_values_dict : list
            Dictionary with zone as keys and values to assign as values.
            Example: [{'mode': 'ZONE_GEO', 'zone': 3, 'value': 0.001}, ... ]

        Returns
        -------
        xarray.Dataset
            New dataset with assigned values
        """
        par = {x['zone']: x['value'] for x in list_values_dict}
        zgeom_par = self.obj.to_dataframe().replace({zone_field: par}).to_xarray()
        return zgeom_par

    def __repr__(self):
        return f"MartGrid accessor for xarray.Dataset with dimensions {self.obj.dims}"

    @wraps(gm.load_marthe_grid)
    def load_marthe_grid(*args, **kwargs):
        return gm.load_marthe_grid(*args, **kwargs)

    @wraps(gm.create_ugrid)
    def create_ugrid(self, varname=None):
        return gm.create_ugrid(self.obj, varname)
