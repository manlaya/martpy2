#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

import numpy as np
import xarray as xr

# from gridmarthe.gridmarthe import _parse_attrs, VAR_ATTRS


# EDIT THIS SHOULD BE MOVED TO gridmarthe!
def create_grid_domain(
    x0,
    y0,
    dx,
    dy,
    nx=None,
    ny=None,
    x1=None,
    y1=None,
    nlayer=1,
    default_value=1.,
    epsg=None,
):
    """ Create a Marthe grid domain as an xarray DataArray

    The MARTHE grid domain is a 3D grid with permeability values.
    This function creates a grid domain with a given origin, cell size, and
    dimensions. The grid is initialized with a default value.
    
    Parameters
    ----------
    x0 : float
        X coordinate of the origin (bottom-left if dy>0 usually, or top-left?) 
        Marthe origin convention: Lower Left corner.
    y0 : float
        Y coordinate of the origin.
    dx : float
        Cell size in X direction.
    dy : float
        Cell size in Y direction.
    nx : int, optional
        Number of cells in X direction. Required if x1 is None.
    ny : int, optional
        Number of cells in Y direction. Required if y1 is None.
    x1 : float, optional
        X coordinate of the opposite corner (Upper Right). Used to compute nx if nx is None.
    y1 : float, optional
        Y coordinate of the opposite corner (Upper Right). Used to compute ny if ny is None.
    nlayer : int, optional
        Number of layers, by default 1.
    default_value : float, optional
        Default permeability value for the grid cells, by default 1.
    epsg : int, optional
        EPSG code of the coordinate reference system, by default None.
    
    Returns
    -------
    xarray.Dataset
        Dataset representing the grid, initialized with default_value.
    """
    if x0 is None or y0 is None:
        raise ValueError("Origin (x0, y0) must be provided.")
    
    if dx is None or dy is None:
        raise ValueError("Grid spacing (dx, dy) must be provided.")

    # Compute nx, ny if not provided
    if nx is None:
        if x1 is None:
            raise ValueError("Either nx or x1 must be provided.")
        nx = int(abs(x1 - x0) / dx)
    
    if ny is None:
        if y1 is None:
             raise ValueError("Either ny or y1 must be provided.")
        ny = int(abs(y1 - y0) / dy)

    # Generate coordinates (cell centers)
    # x0 + dx/2 + i*dx
    x_coords = x0 + dx/2 + np.arange(nx) * dx
    y_coords = y0 + dy/2 + np.arange(ny) * dy
    layer_coords = np.arange(1, nlayer + 1)

    # map coords to match zone dimensions
    x_coords = np.tile(x_coords, (nlayer * ny))
    # each y coords is repeated along xcoords (nx times), then results is tiled over layers
    y_coords = np.tile(np.repeat(y_coords[::-1], nx), nlayer)
    layer_coords = np.tile(np.repeat(layer_coords, (ny * nx)), nlayer)
    
    # Create dataset
    # Dimensions: layer * y * x => gridmarthe convention = flatten array
    data = np.full((1, nlayer * ny * nx), default_value)  # (time, zone)
    
    grid = xr.Dataset(
        data_vars={
            'permeab': (['time', 'zone'], data),
            'x': (['zone'], x_coords),
            'y': (['zone'], y_coords),
            'z': (['zone'], layer_coords),
            'dx': (['zone'], np.repeat(dx, nx * ny)),
            'dy': (['zone'], np.repeat(dy, nx * ny))
        },
        coords={
            'zone': np.arange(1, np.size(data) + 1),
            'time': np.array([datetime(1850,1,1)])
        },
    )
    
    # Set attributes
    crs = pyproj.CRS(epsg) if epsg is not None else None
    grid.attrs = {
        'convention': 'CF-1.10',
        'grid_mapping': 'crs',
        'crs': str(crs.to_cf() if crs is not None else None),
        'resolution_units': crs.coordinate_system.to_cf()[0].get('units', '') if crs is not None else None,
        'marthe_grid_version' : 9.0,
        'original_dimensions': 'x,y,z [grids]: {} {} {}'.format(nx, ny, nlayer),
        'nested': str(False),
        # to harmonize with gridmarthe
        # 'origin': '({}, {})'.format(x0, y0),
        # 'spacing': '({}, {})'.format(dx, dy),
        'rotation': 0.0,
    }
    
    return grid


def create_grid_from_xy():
    # create a grid from a list of x,y coordinates
    # allow direct import of unstructured grids
    raise NotImplementedError()


def create_grid_from_shape():
    # create a grid from a shapefile
    # get bbox then create grid, and optionally set active
    # domain inside polygon
    raise NotImplementedError()

