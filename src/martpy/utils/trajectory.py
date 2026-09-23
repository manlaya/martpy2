#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modules for Particle trajectories of a MARTHE run, and the capture zones.

Reads the seeding file (.deptr) the marthe project points at and the trajmar.out,
attributes every trajectory to its seeding point (source/sinks), and turns each
bundle of pathlines into a capture-zone polygon and a boolean mask.

    >>> import martpy as mart
    >>> prj = mart.read_rma_file('model.rma')
    >>> tr = mart.Trajectory.from_project(prj)     # trajmar.out next to the rma
    >>> tr.to_shape('paths.shp', kind='line')
    >>> cz = tr.build_capture(offset_m=20.)
    >>> cm = tr.build_mask()                        # on the MARTHE cells themselves
    >>> cz.to_shape('capture.shp')
    >>> cm.save_mask('capture_mask.tmask')          # a MARTHE grid file
    >>> tr.plot(capture=True, cz_mask=True, color_by='z')

The model is handled through martpy: the project gives the file paths,
:func:`martpy.grid.load_marthe_grid` gives the geometry.  Two readers martpy
does not have yet live here, and would sit naturally in martpy.inputs and
martpy.outputs once they are wanted elsewhere:

    read_deptr    the .deptr seeding file (cell and X, Y, Z forms)
    read_trajmar  trajmar.out -- vertices, elevation, travel time, layer

A note on the mask
------------------
The mask is built on the model's own cells rather than on a raster of the
user's choosing: one boolean per cell of the main grid and of every gigogne,
in every layer, marking the cells a particle path runs through.  It is
written back as a MARTHE grid file (``.tmask``), so it reopens with
:func:`martpy.grid.load_marthe_grid` like any other field of the model.


A note on the group tag
-----------------------
MARTHE writes the `Group =` tag of a trajectory with a single digit if built
through WinMARTHE, so with more than nine seeding points the tags wrap (1, 10,
11 ... all read 1).  Trajectories are therefore attributed geometrically by
default: MARTHE releases the N particles of a seeding point on the *circle* of
radius R about it, so |d - R| ~ 0 is an unambiguous test.  `method='group'`
trusts the tag, `method='auto'` trusts it only when it survives a consistency
check.

Dependencies
---------------
numpy
pandas
shapely
matplotlib
contextily -- handles the basemap during plotting
geopandas
"""

import gzip
import os
import re

import numpy as np
import pandas as pd


DEFAULT_CRS = 'EPSG:2154'      # RGF93 / Lambert-93

# --------------------------------------------------------------------------
# .deptr -- the seeding points
# --------------------------------------------------------------------------
_NUM = r"[-+]?\d*\.?\d+(?:[eEdD][-+]?\d+)?"
_TAIL = re.compile(rf"N=\s*(\d+)\s+R=\s*({_NUM})\s+G=\s*(\d+)", re.I)
_CELL = re.compile(r"^M\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(.*)$", re.I)
_KEYWORD = re.compile(
    rf"^\s*[A-Za-z]?\s*X\s*=\s*({_NUM})\s*[,;]?\s*Y\s*=\s*({_NUM})"
    rf"(?:\s*[,;]?\s*(?:Z|L)\s*=\s*({_NUM}))?\s*(.*)$", re.I)
_POSXYZ = re.compile(rf"^([A-Za-z]{{1,2}})?\s*({_NUM})\s+({_NUM})"
                     rf"(?:\s+({_NUM}))?\s+(.*)$")


def _f(v):
    if v is None:
        return np.nan
    return float(str(v).replace('d', 'e').replace('D', 'E'))


def _parse_deptr_line(line):
    """One .deptr record -> dict, or None when the line is not a record.

    A record is either a cell (M col row layer nest) or a position
    (X x y z / X= .. Y= .. Z= ..), always followed by N= R= G=.
    """
    s = line.strip()
    if not s or s.startswith('*') or s.lower().startswith('fichier'):
        return None
    m = _CELL.match(s)
    if m:
        tail = _TAIL.search(m.group(5))
        if not tail:
            return None
        n, r, g = tail.groups()
        return {'form': 'cell', 'col': int(m.group(1)), 'row': int(m.group(2)),
                    'layer': int(m.group(3)), 'inest': int(m.group(4)),
                    'x': np.nan, 'y': np.nan, 'z': np.nan,
                    'npart': int(n), 'radius': _f(r), 'group': int(g)}
    m = _KEYWORD.match(s)
    if m:
        tail = _TAIL.search(m.group(4))
        if not tail:
            return None
        n, r, g = tail.groups()
        return {'form': 'xy', 'col': -1, 'row': -1, 'layer': -1, 'inest': -1,
                    'x': _f(m.group(1)), 'y': _f(m.group(2)), 'z': _f(m.group(3)),
                    'npart': int(n), 'radius': _f(r), 'group': int(g)}
    m = _POSXYZ.match(s)
    if m and (m.group(1) or '').upper() != 'M':
        tail = _TAIL.search(m.group(5))
        if not tail:
            return None
        n, r, g = tail.groups()
        return {'form': 'xy', 'col': -1, 'row': -1, 'layer': -1, 'inest': -1,
                    'x': _f(m.group(2)), 'y': _f(m.group(3)), 'z': _f(m.group(4)),
                    'npart': int(n), 'radius': _f(r), 'group': int(g)}
    return None


def read_deptr(path):
    """Read a .deptr seeding file.

    Returns a DataFrame with one row per seeding point, indexed by a stable
    key in file order (W01, W02 ...): form, col, row, layer, inest, x, y, z,
    npart, radius, group (the G= tag).  Cell records carry no x, y until
    :meth:`Trajectory.from_project` fills them from the grid.  Wildcard
    records (``M * * * 1 ...``) are not seeding points and are skipped.
    """
    rows = []
    with open(path, encoding='ISO-8859-1') as f:
        for line in f:
            rec = _parse_deptr_line(line)
            if rec:
                rows.append(rec)
    df = pd.DataFrame(rows, columns=['form', 'col', 'row', 'layer', 'inest',
                                     'x', 'y', 'z', 'npart', 'radius', 'group'])
    df.index = [f"W{i + 1:02d}" for i in range(len(df))]
    df.index.name = 'key'
    return df


def _seed_xy(seeds, grid):
    """Give every cell record its x, y from the martpy grid.

    `grid` is the Dataset of :func:`martpy.grid.load_marthe_grid`, loaded
    with ``add_col_row=True`` (and ``add_id_grid=True`` on a nested model).
    The join is on (layer, gigogne, col, row) as MARTHE numbers them.
    """
    if not (seeds['form'] == 'cell').any():
        return seeds
    g = grid.to_dataframe().reset_index()
    for c in ('col', 'row'):
        if c not in g.columns:
            raise KeyError(f"the grid has no '{c}' -- reload it with "
                           "load_marthe_grid(..., add_col_row=True)")
    if 'layer' not in g.columns:             # gridmarthe names the layer 'z'
        g['layer'] = g['z'] if 'z' in g.columns else 1
    nest = next((c for c in ('id_grid', 'gigogne', 'inest') if c in g.columns),
                None)
    if nest is None:
        g['id_grid'] = 0                     # no nested grid
        nest = 'id_grid'
    lut = (g[['layer', nest, 'col', 'row', 'x', 'y']]
           .drop_duplicates(['layer', nest, 'col', 'row'])
           .set_index(['layer', nest, 'col', 'row']))
    out = seeds.copy()
    for key, w in out[out['form'] == 'cell'].iterrows():
        cell = (int(w.layer), int(w.inest), int(w.col), int(w.row))
        if cell not in lut.index:
            raise KeyError(f"{key}: cell (layer={w.layer}, gigogne={w.inest}, "
                           f"col={w.col}, row={w.row}) is not in the grid")
        out.loc[key, ['x', 'y']] = lut.loc[cell, ['x', 'y']].to_numpy(dtype=float)
    return out


# --------------------------------------------------------------------------
# trajmar.out -- handelling the trajectories dataset
# --------------------------------------------------------------------------
_GROUP = re.compile(r"Group\s*=\s*(\d+)", re.I)


def read_trajmar(path):
    """Read a trajmar.out (plain or .gz).

    Returns a dict:

        xy     (npoints, 2)  vertices, in file order
        start  (ntraj + 1,)  offsets: trajectory k is xy[start[k]:start[k+1]]
        z      (npoints,)    elevation
        t      (npoints,)    travel time from the seeding point, model unit
                             (MARTHE writes 1e12 on the last vertex)
        layer  (npoints,)    model layer of the vertex (fifth column)
        group  (ntraj,)      the `Group =` tag, -1 where the file has none
    """
    coords, zs, ts, lays, groups = [], [], [], [], []
    start = [0]
    n, cur, pending = 0, -1, False
    opener = gzip.open if str(path).endswith('.gz') else open
    with opener(path, 'rt', encoding='ISO-8859-1', errors='replace') as f:
        f.readline()                                     # file header
        for line in f:
            if line[:1] == '#':
                if 'Group' in line:
                    m = _GROUP.search(line)
                    cur = int(m.group(1)) if m else -1
                elif 'Trajectoire' in line:
                    if n:
                        start.append(n)
                    pending = True
                continue
            p = line.split()
            if len(p) < 2:
                continue
            if pending:
                groups.append(cur)
                pending, cur = False, -1
            coords.append((p[0], p[1]))
            zs.append(p[2] if len(p) > 2 else 'nan')
            ts.append(p[3] if len(p) > 3 else 'nan')
            lays.append(p[4] if len(p) > 4 else '-1')
            n += 1
    start.append(n)
    return {
        'xy': np.array(coords, dtype=float) if coords else np.zeros((0, 2)),
        'start': np.asarray(start, dtype=np.int64),
        'z': np.array(zs, dtype=float), 't': np.array(ts, dtype=float),
        'layer': np.array(lays, dtype=float).astype(int),
        'group': np.asarray(groups, dtype=np.int64),
    }


def _assign(xy, start, seeds, method='auto', tol=1.0, groups=None):
    """Attribute each trajectory to a seeding point.

    Returns (owner, method): the positional index into `seeds` (-1 if none)
    and the method actually used once 'auto' has decided.

    'ring'   |d - R| <= tol from the seeding point, on the release circle
    'group'  the `Group =` tag, matched to the G= of the seeding records
             (or to file order when the G= are not unique)
    'auto'   the tag when every trajectory carries one, the G= are unique
             and every tag is among them -- which a truncated tag fails --
             else 'ring'
    """
    ntraj = max(len(start) - 1, 0)
    if ntraj == 0 or len(seeds) == 0:
        return np.full(ntraj, -1, dtype=int), 'none'
    nw = len(seeds)
    method = (method or 'auto').lower()
    tags = np.asarray(groups, dtype=int) if groups is not None else np.zeros(0, int)
    gtag = seeds['group'].to_numpy(dtype=int)
    unique = len(set(gtag)) == nw
    tags_ok = len(tags) == ntraj and (tags >= 1).all()
    if method == 'group' and not tags_ok:
        raise ValueError("method='group' but trajmar.out carries no usable "
                         "Group tag -- use method='ring'")
    if method == 'auto':
        method = ('group' if tags_ok and unique and np.isin(tags, gtag).all()
                  else 'ring')
    if method == 'group':
        if unique:
            lut = {int(t): i for i, t in enumerate(gtag)}
            return np.array([lut.get(int(t), -1) for t in tags], dtype=int), 'group'
        g = tags - 1                                   # file order
        return np.where((g >= 0) & (g < nw), g, -1), 'group'
    first = xy[start[:-1]]
    wxy = seeds[['x', 'y']].to_numpy(dtype=float)
    radius = seeds['radius'].to_numpy(dtype=float)
    d = np.linalg.norm(first[:, None, :] - wxy[None, :, :], axis=2)
    ring = np.abs(d - radius[None, :])
    best = ring.argmin(axis=1)
    return np.where(ring[np.arange(len(first)), best] <= tol, best, -1), 'ring'


# --------------------------------------------------------------------------
# polygons from the particle pathlines
# --------------------------------------------------------------------------
def _valid(g):
    """A valid version of `g`, or None if nothing usable survives."""
    if g is None or g.is_empty:
        return None
    if g.is_valid:
        return g
    try:
        import shapely
        g2 = shapely.make_valid(g)
    except Exception:
        g2 = g.buffer(0)
    if g2 is None or g2.is_empty:
        return None
    if not g2.is_valid:
        g2 = g2.buffer(0)
    return g2 if (g2 is not None and not g2.is_empty and g2.is_valid) else None


def _merge(pieces):
    """unary_union, repaired when GEOS refuses the shared edges as given."""
    from shapely.ops import unary_union
    try:
        return unary_union(pieces)
    except Exception:
        pass
    try:
        from shapely import set_precision
        snapped = [_valid(set_precision(g, 0.001)) for g in pieces]
        snapped = [g for g in snapped if g is not None]
        if snapped:
            return unary_union(snapped)
    except Exception:
        pass
    g = None
    for piece in pieces:
        g = piece if g is None else _valid(g.union(piece))
        if g is None:
            break
    return g


def _envelope(xy, start, sel, centre, offset_m=0.0, min_width=5.0,
              gap_factor=6.0, max_gap=None, smooth=0.0, simplify=0.0):
    """The capture zone as the envelope of the pathlines (Tosco et al. 2008).

    MARTHE releases the particles at equal angles on a ring about the seeding
    point, so sorting the paths by seeding angle gives the true neighbour
    relation.  The zone is the union of the paths between angularly
    adjacent pathlines -- each closed by running out along one and back along
    the other -- so no pathline can fall outside it.  A line whose two paths
    finish more than `gap_factor` times the median gap apart (or `max_gap`
    metres) has split around a stagnation point and is not filled.
    
    
    """
    from shapely.geometry import LineString, Polygon

    paths = [xy[start[k]:start[k + 1]] for k in np.asarray(sel, dtype=int)]
    paths = [p for p in paths if len(p) >= 2]
    if not paths:
        return None
    seeds = np.array([p[0] for p in paths])
    order = np.argsort(np.arctan2(seeds[:, 1] - centre[1], seeds[:, 0] - centre[0]))
    paths = [paths[i] for i in order]
    seeds = seeds[order]
    n = len(paths)

    width = max(float(offset_m or 0.0), float(min_width))
    pieces = [q for q in (_valid(LineString(p).buffer(width, join_style=1))
                          for p in paths) if q is not None]
    # the disc the particles were released on is captured ground too
    if n >= 3:
        fan = _valid(Polygon(seeds))
        if fan is not None:
            pieces.append(fan)
    elif n == 2:
        fan = _valid(LineString(seeds).buffer(width, join_style=1))
        if fan is not None:
            pieces.append(fan)

    pairs = ([(i, (i + 1) % n) for i in range(n)] if n > 2
             else [(0, 1)] if n == 2 else [])
    if pairs:
        ends = np.array([p[-1] for p in paths])
        gaps = np.array([float(np.hypot(*(ends[i] - ends[j]))) for i, j in pairs])
        limit = None
        if max_gap:
            limit = float(max_gap)
        elif gap_factor and len(gaps) > 2:
            limit = float(gap_factor) * max(float(np.median(gaps)), 1.0)
        for w, (i, j) in enumerate(pairs):
            if limit is not None and gaps[w] > limit:
                continue
            try:
                q = _valid(Polygon(np.vstack([paths[i], paths[j][::-1]])))
            except Exception:
                q = None
            if q is not None:
                pieces.append(q)

    g = _merge(pieces)
    if g is None or g.is_empty:
        return None
    if offset_m:
        g = g.buffer(float(offset_m), join_style=1)
    if simplify:
        # never more than the standoff, so it cannot cut back inside a path
        g = g.simplify(min(float(simplify), float(offset_m or 0.0)))
    if smooth:
        g = g.buffer(smooth, join_style=1).buffer(-smooth, join_style=1)
    g = _valid(g)
    return g


# --------------------------------------------------------------------------
# time to harvest fruits :)
# --------------------------------------------------------------------------
class CaptureZone:
    """Capture-zone polygons, one per seeding point, as a GeoDataFrame.

    Drawn as the envelope of the pathlines -- see
    :meth:`Trajectory.build_capture`.
    """

    def __init__(self, gdf, method):
        self.gdf = gdf
        self.method = method

    def to_shape(self, path):
        """Write the polygons -- the extension picks the driver (.shp, .gpkg)."""
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.gdf.to_file(path)
        return path

    def __repr__(self):
        return (f"CaptureZone({self.method}): {len(self.gdf)} zones, "
                f"{self.gdf.area.sum() / 1e6:.3f} km2")


class GridIndex:
    """An index onto a MARTHE grid: which cell holds a point.

    Not a grid of its own -- the grid is read, written and held by
    gridmarthe, through :func:`martpy.grid.load_marthe_grid`, which stores
    every cell of every layer of every grid in one ``zone`` vector.  This
    class only indexes that vector, to answer for many points at once the
    question :func:`gridmarthe.search_zone` answers for one: which cell of
    which grid, in a given layer, a point falls in.

    A gigogne is declared with a border ring of parent-sized cells, and a
    MARTHE grid may in any case have columns of unequal width, so a point is
    located against the actual cell *edges* rather than by dividing by a cell
    size.  The finest grid with an active cell at the point wins, which is how
    MARTHE occults the main-grid cells underneath a gigogne.

    Activity is read layer by layer, not over the model as a whole: most
    cells of a MARTHE model exist in some layers and not in others, so a
    gigogne that covers the ground in layer 1 need not cover it in layer 3,
    and the layer asked for is the one that decides which grid holds the
    point.
    """

    # a MARTHE field marks an absent cell with one of these
    NAN_VALUES = (0., -9999., 9999., 8888.)

    def __init__(self, ds, field=None, nan_values=NAN_VALUES):
        self.ds = ds
        self.nzone = int(ds.sizes['zone'])
        d = {k: np.asarray(ds[k].values).ravel()
             for k in ('x', 'y', 'dx', 'dy', 'col', 'row')}
        lay = (np.asarray(ds['z'].values).ravel() if 'z' in ds.variables
               else np.ones(self.nzone, dtype=int))
        nest = (np.asarray(ds['id_grid'].values).ravel() if 'id_grid' in ds.variables
                else np.zeros(self.nzone, dtype=int))
        if field is None:
            field = next((v for v in ds.data_vars
                          if v not in ('x', 'y', 'dx', 'dy', 'col', 'row',
                                       'id_grid', 'z', 'izone')), None)
        values = (np.asarray(ds[field].values).ravel()
                  if field is not None else None)

        zone = np.arange(self.nzone)
        self.zone_grid, self.zone_layer = nest.astype(int), lay.astype(int)
        self.cell_area = d['dx'] * d['dy']
        self.grids = {}
        for g in np.unique(nest):
            s_ = nest == g
            nlay = int(lay[s_].max())
            nrow, ncol = int(d['row'][s_].max()), int(d['col'][s_].max())
            i, j = d['row'][s_].astype(int) - 1, d['col'][s_].astype(int) - 1
            # (layer, row, col) -> position in the zone vector, taken from the
            # data rather than assumed, so any file ordering is followed
            index = np.full((nlay, nrow, ncol), -1, dtype=np.int64)
            index[lay[s_].astype(int) - 1, i, j] = zone[s_]

            top = s_ & (lay == lay[s_].min())
            order = np.lexsort((d['col'][top], d['row'][top]))
            x = d['x'][top][order].reshape(nrow, ncol)
            y = d['y'][top][order].reshape(nrow, ncol)
            dx = d['dx'][top][order].reshape(nrow, ncol)
            dy = d['dy'][top][order].reshape(nrow, ncol)
            ex = np.concatenate([[x[0, 0] - dx[0, 0] / 2], x[0] + dx[0] / 2])
            ey = np.concatenate([[y[0, 0] + dy[0, 0] / 2], y[:, 0] - dy[:, 0] / 2])

            if values is None:
                active = np.ones((nlay, nrow, ncol), dtype=bool)
            else:
                # per layer: a cell present in one layer is often absent in
                # another, so the layer asked for is the one that decides
                v = values[s_]
                active = np.zeros((nlay, nrow, ncol), dtype=bool)
                active[lay[s_].astype(int) - 1, i, j] = (
                    np.isfinite(v) & ~np.isin(v, list(nan_values)))
            self.grids[int(g)] = {'index': index, 'ex': ex, 'ey': ey,
                                  'nrow': nrow, 'ncol': ncol, 'nlay': nlay,
                                  'active': active, 'dx': dx, 'dy': dy}

    @property
    def nlay(self):
        return max(g['nlay'] for g in self.grids.values())

    @property
    def min_cell(self):
        """The smallest cell of the model -- the finest gigogne mesh."""
        return float(min(min(g['dx'].min(), g['dy'].min())
                         for g in self.grids.values()))

    def locate(self, x, y, layer):
        """Zone index of the cell holding each (x, y, layer), -1 if none."""
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        layer = np.asarray(layer, dtype=int)
        out = np.full(len(x), -1, dtype=np.int64)
        todo = np.ones(len(x), dtype=bool)
        for g in sorted(self.grids, reverse=True):       # finest grid first
            G = self.grids[g]
            j = np.searchsorted(G['ex'], x, 'right') - 1
            i = np.searchsorted(-G['ey'], -y, 'right') - 1
            ok = (todo & (j >= 0) & (j < G['ncol'])
                  & (i >= 0) & (i < G['nrow'])
                  & (layer >= 1) & (layer <= G['nlay']))
            hit = np.flatnonzero(ok)
            if not len(hit):
                continue
            ok[hit[~G['active'][layer[hit] - 1, i[hit], j[hit]]]] = False
            hit = np.flatnonzero(ok)
            z = G['index'][layer[hit] - 1, i[hit], j[hit]]
            out[hit] = z
            todo[hit[z >= 0]] = False
        return out

    def plane(self, values, grid, layer=None):
        """One grid's cells as a 2-D array, for a layer or over all of them."""
        G = self.grids[grid]
        idx = G['index'] if layer is None else G['index'][layer - 1][None]
        out = np.zeros(idx.shape, dtype=bool)
        here = idx >= 0
        out[here] = np.asarray(values, dtype=bool)[idx[here]]
        return out.any(axis=0)

    def edges(self, grid):
        """The cell edges of one grid: (x edges, y edges), for pcolormesh."""
        return self.grids[grid]['ex'], self.grids[grid]['ey']

    def __repr__(self):
        g = ', '.join(f"{k}: {v['ncol']}x{v['nrow']}x{v['nlay']}"
                      for k, v in sorted(self.grids.items()))
        return f"GridIndex({self.nzone} cells; grid {g})"


class CaptureMask:
    """Cells of the MARTHE grid a particle path runs through.

    One boolean per model cell, so the mask is three-dimensional in the way
    the model is: every layer of the main grid and of every gigogne, at the
    model's own resolution.  Stored as ``(nseed, nzone)`` over the grid's zone
    vector, which is the order a MARTHE grid file is written in.

    :meth:`save_mask` writes it back as a MARTHE grid (``.tmask``), so it
    reopens with :func:`martpy.grid.load_marthe_grid` like any other field.
    """

    def __init__(self, array, grid, keys, crs=DEFAULT_CRS, source=None):
        self.array = np.atleast_2d(np.asarray(array, dtype=bool))
        self.grid = grid
        self.keys = list(keys)
        self.crs = crs
        self.source = source              # the model the grid was read from

    @property
    def any(self):
        """One plane: a cell on the path of at least one seeding point."""
        return self.array.any(axis=0)

    def _plane(self, id=-1):
        if id is None or (np.isscalar(id) and not isinstance(id, str) and id == -1):
            return self.any
        wanted = [id] if np.isscalar(id) or isinstance(id, str) else id
        out = np.zeros(self.grid.nzone, dtype=bool)
        for key in wanted:
            if key not in self.keys:
                raise KeyError(f"{key!r} is not in this mask; keys: {self.keys}")
            out |= self.array[self.keys.index(key)]
        return out

    def area_km2(self, id=-1):
        """Ground covered, counting each cell at its own size."""
        return float(self.grid.cell_area[self._plane(id)].sum() / 1e6)

    def cells_by_layer(self, id=-1):
        """Cells marked per grid and layer -- the mask read layer by layer."""
        plane = self._plane(id)
        area = self.grid.cell_area
        recs = []
        for g in sorted(self.grid.grids):
            for lay in range(1, self.grid.grids[g]['nlay'] + 1):
                sel = plane & (self.grid.zone_grid == g) & (self.grid.zone_layer == lay)
                recs.append({'grid': g, 'layer': lay, 'cells': int(sel.sum()),
                             'area_km2': round(float(area[sel].sum() / 1e6), 4)})
        return pd.DataFrame(recs)

    def to_dataset(self, id=-1, name='tmask'):
        """The mask as a MARTHE grid Dataset, ready to write or to plot."""
        keep = ('x', 'y', 'dx', 'dy')
        ds = self.grid.ds
        out = ds.drop_vars([v for v in ds.data_vars if v not in keep])
        out[name] = (('time', 'zone'),
                     self._plane(id).astype(float)[None, :])
        out.attrs = dict(ds.attrs)
        return out

    def save_mask(self, path, id=-1, by_id=False, name='tmask', title=None):
        """Write the mask as a MARTHE grid file.

        The file is a grid like any other model field -- one block per layer
        and per gigogne, 1 where a path runs through the cell and 0 elsewhere
        -- so it reopens with :func:`martpy.grid.load_marthe_grid` and can be
        handed to MARTHE.  ``.tmask`` is the extension used for it, and is
        added when `path` carries none.

        Parameters
        ----------
        path : str
            File to write.  With `by_id`, the seeding point's key is inserted
            before the extension.
        id : -1, key or list
            Which seeding points go into the mask; -1 (default) is all of
            them, as one field.
        by_id : bool
            Write one file per seeding point instead of one field for all.
        name : str
            Field name written in the file (``Field=`` line).
        title : str, optional
            Title line of the file.
        """
        from martpy.grid import write_marthe_grid

        base, ext = os.path.splitext(str(path))
        ext = ext or '.tmask'
        os.makedirs(os.path.dirname(os.path.abspath(path)) or '.', exist_ok=True)

        targets = ([(key, f"{base}_{key}{ext}") for key in self.keys] if by_id
                   else [(id, base + ext)])
        written = []
        for which, fpath in targets:
            ds = self.to_dataset(which, name=name)
            label = which if by_id else 'all seeding points'
            write_marthe_grid(ds, fpath, varname=name, nan_value=0.,
                              title=title or f"Particle path mask ({label})")
            written.append(fpath)
        return written if by_id else written[0]

    @classmethod
    def load_mask(cls, path, name=None, crs=DEFAULT_CRS):
        """Read back a mask written by :meth:`save_mask`."""
        from martpy.grid import load_marthe_grid

        ds = load_marthe_grid(path, varname=name, add_col_row=True,
                              add_id_grid=True)
        var = name or next(v for v in ds.data_vars
                           if v not in ('x', 'y', 'dx', 'dy', 'col', 'row',
                                        'id_grid', 'z', 'izone'))
        grid = GridIndex(ds, field=None)
        values = np.asarray(ds[var].values).ravel().astype(bool)
        return cls(values[None, :], grid, ['ALL'], crs, source=str(path))

    def __repr__(self):
        n = int(self.any.sum())
        lays = sorted(set(self.grid.zone_layer[self.any].tolist()))
        return (f"CaptureMask: {len(self.keys)} seeding point(s), {n} cells of "
                f"the MARTHE grid in layer(s) {lays}, {self.area_km2():.3f} km2")


# --------------------------------------------------------------------------
# the trajectories
# --------------------------------------------------------------------------
class Trajectory:
    """Particle trajectories of one MARTHE run, keyed to their seeding points.

    Built with :meth:`from_project` (or :func:`read_trajectory`).  Attributes:

        seeds   DataFrame from the .deptr, one row per seeding point, with x, y
        xy, start, z, t, layer, group   as returned by :func:`read_trajmar`
        owner   (ntraj,) positional index into `seeds`, -1 if unattributed
        method  how they were attributed: 'group', 'ring' or 'tag' / 'none'
        keys    the seeding-point keys, in file order
        grid    the martpy grid Dataset the seeds were located on (or None)
        crs     CRS of the model coordinates

    Without a usable .deptr the trajectories are grouped by their `Group =`
    tag (keys 1, 2 ...), or all together under 'ALL' when there is none.
    """

    def __init__(self, seeds, traj, grid=None, crs=DEFAULT_CRS, method='auto',
                 ring_tol=1.0):
        self.seeds = seeds if seeds is not None else pd.DataFrame()
        self.xy, self.start = traj['xy'], traj['start']
        self.z, self.t = traj['z'], traj['t']
        self.layer, self.group = traj['layer'], traj['group']
        self.grid = grid
        self.crs = crs
        self.rma_file = None
        self._grid_index = None
        self.capture = None
        self.cz_mask = None
        if len(self.seeds):
            self.keys = list(self.seeds.index)
            self.owner, self.method = _assign(self.xy, self.start, self.seeds,
                                              method, ring_tol, self.group)
        elif len(self.group) and (self.group >= 1).any():
            tags = sorted({int(g) for g in self.group if g >= 1})
            self.keys = [f"G{g}" for g in tags]
            self.owner = np.array([tags.index(int(g)) if g >= 1 else -1
                                   for g in self.group], dtype=int)
            self.method = 'tag'
        else:
            self.keys = ['ALL']
            self.owner = np.zeros(self.ntraj, dtype=int)
            self.method = 'none'
        lost = int((self.owner < 0).sum())
        if lost:
            print(f"    [{lost} of {self.ntraj} trajectories match no seeding point "
                  f"({self.method}) -- is trajmar.out the run made from this .deptr?]")

    @classmethod
    def from_project(cls, project, trajmar=None, grid=None, crs=DEFAULT_CRS,
                     method='auto', ring_tol=1.0):
        """Build from a MARTHE project.

        Parameters
        ----------
        project : MartProject, MartModel or str
            The project, or the path of its .rma file.  Its `deptr` entry is
            the seeding file; its `permh` entry is the grid to locate cell
            records on.
        trajmar : str, optional
            Path of trajmar.out (plain or .gz).  Default: next to the .rma.
        grid : xarray.Dataset, optional
            A grid already loaded with :func:`martpy.grid.load_marthe_grid`
            (``add_col_row=True, add_id_grid=True``).  Loaded from `permh`
            when omitted: it locates cell records and gives the native cell
            size and extent of the masks.
        crs : str, optional
            CRS of the model coordinates, default Lambert-93.
        method : {'auto', 'ring', 'group'}, optional
            How a trajectory is attributed to a seeding point -- see the
            module note on the group tag.
        ring_tol : float, optional
            Tolerance on |d - R| for the ring test, in model length units.
        """
        from martpy.inputs.mart_model import MartProject

        if isinstance(project, (str, os.PathLike)):
            project = MartProject.from_rma_file(project)
        mdir = os.path.dirname(os.path.abspath(project.rma_file))
        files = project.get_files()

        def _resolve(p):
            return p if os.path.isabs(p) else os.path.join(mdir, p)

        seeds = pd.DataFrame()
        if files.get('deptr'):
            seeds = read_deptr(_resolve(files['deptr']))
        if grid is None and files.get('permh'):
            from martpy.grid import load_marthe_grid
            grid = load_marthe_grid(_resolve(files['permh']),
                                    add_col_row=True, add_id_grid=True)
        if len(seeds) and (seeds['form'] == 'cell').any():
            if grid is None:
                raise ValueError("the .deptr has cell records but the project "
                                 "has no permh grid to locate them")
            seeds = _seed_xy(seeds, grid)
        if trajmar is None:
            trajmar = os.path.join(mdir, 'trajmar.out')
        out = cls(seeds, read_trajmar(trajmar), grid, crs, method, ring_tol)
        out.rma_file = project.rma_file
        return out

    # -- selection -----------------------------------------------------------
    @property
    def ntraj(self):
        return max(len(self.start) - 1, 0)

    def _select(self, id=-1):
        """(positional index, key) of the seeding points asked for.

        `id` is -1 for all, a key ('W03'), the G= group number of the seeding
        record (111), a 1-based number in file order, or a list of any of
        these.  A number is taken as a G= group when one seeding point
        carries it, else as the file-order number.
        """
        if id is None or (np.isscalar(id) and not isinstance(id, str) and id == -1):
            return list(enumerate(self.keys))
        tags = [self._group_of(k) for k in range(len(self.keys))]
        out = []
        for g in ([id] if np.isscalar(id) or isinstance(id, str) else id):
            if isinstance(g, str) and g in self.keys:
                out.append((self.keys.index(g), g))
                continue
            try:
                n = int(g)
            except (TypeError, ValueError):
                raise KeyError(f"unknown seeding point {g!r}; "
                               f"keys: {self.keys}") from None
            if tags.count(n) == 1:
                k = tags.index(n)
            elif 1 <= n <= len(self.keys):
                k = n - 1
            else:
                raise KeyError(f"seeding point {g!r} is neither a key, a G= group "
                               f"nor a number in 1..{len(self.keys)}")
            out.append((k, self.keys[k]))
        return out

    def paths_of(self, k):
        """Trajectory indices attributed to seeding point `k` (positional)."""
        return np.flatnonzero(self.owner == k)

    def _group_of(self, k):
        """The G= group of seeding point `k`, or the trajmar tag when no seeds."""
        if len(self.seeds):
            return int(self.seeds.iloc[k].group)
        sel = self.paths_of(k)
        return int(self.group[sel[0]]) if len(sel) and len(self.group) else -1

    def _centre(self, k):
        if len(self.seeds):
            w = self.seeds.iloc[k]
            return float(w.x), float(w.y)
        sel = self.paths_of(k)
        first = self.xy[self.start[sel]] if len(sel) else self.xy[:1]
        return float(first[:, 0].mean()), float(first[:, 1].mean())

    def _native_cellsize(self):
        """The smallest cell of the model grid -- the gigogne mesh."""
        if self.grid is None:
            raise ValueError("no grid loaded: pass cellsize explicitly")
        dx = np.asarray(self.grid['dx']).ravel()
        return float(np.nanmin(dx[dx > 0]))

    # -- export --------------------------------------------------------------
    def to_shape(self, path, kind='point', id=-1, crs=None):
        """Write the trajectories as a shapefile / geopackage.

        Every feature carries `key` (the seeding point, W01 ...), `group`
        (its G= tag, the `Group =` MARTHE writes) and `traj` (the trajectory
        number in trajmar.out).

        kind='point'  one feature per vertex, with the values exactly as
                      trajmar.out writes them: x, y, z (the altitude), t
                      (travel time from the seed), layer; `vertex` is the
                      position along the path.
        kind='line'   one feature per pair of consecutive vertices, so a path
                      can be classified along its length in QGIS: seg, from,
                      to (the vertex coordinates as text), z and t as the
                      mean of the two ends, layer as the deeper of the two.
        id            -1 for all (default), a key, a G= group, a file-order
                      number, or a list of these -- see :meth:`_select`.
        """
        import geopandas as gpd  # noqa: ICN002
        from shapely.geometry import LineString, Point

        kind = str(kind).lower()
        if kind not in ('point', 'line'):
            raise ValueError("kind must be 'point' or 'line'")
        recs, geoms = [], []
        for k, key in self._select(id):
            tag = self._group_of(k)
            for j in self.paths_of(k):
                a, b = self.start[j], self.start[j + 1]
                p, z, t, lay = self.xy[a:b], self.z[a:b], self.t[a:b], self.layer[a:b]
                head = {'key': key, 'group': tag, 'traj': int(j + 1)}
                if kind == 'point':
                    for i in range(len(p)):
                        recs.append({**head, 'vertex': i,
                                     'x': float(p[i, 0]), 'y': float(p[i, 1]),
                                     'z': float(z[i]), 't': float(t[i]),
                                     'layer': int(lay[i])})
                        geoms.append(Point(p[i]))
                else:
                    for i in range(len(p) - 1):
                        recs.append({**head, 'seg': i,
                                     'from': f"({p[i, 0]:.2f}, {p[i, 1]:.2f})",
                                     'to': f"({p[i + 1, 0]:.2f}, {p[i + 1, 1]:.2f})",
                                     'z': float(0.5 * (z[i] + z[i + 1])),
                                     't': float(0.5 * (t[i] + t[i + 1])),
                                     'layer': int(max(lay[i], lay[i + 1]))})
                        geoms.append(LineString([p[i], p[i + 1]]))
        gdf = gpd.GeoDataFrame(recs, geometry=geoms, crs=crs or self.crs)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        gdf.to_file(path)
        return gdf

    # -- delineation ---------------------------------------------------------
    def build_capture(self, id=-1, min_paths=2, offset_m=20.0, **params):
        """Delineate the capture zone of each seeding point.

        The zone is the envelope of the pathlines (Tosco et al. 2008): the
        union of the stream tubes between angularly adjacent trajectories.
        MARTHE releases the particles at equal angles on a ring about the
        seeding point, so sorting them by seeding angle gives the true
        neighbour relation, and every pathline is then an edge of two tubes --
        none can be left outside the zone it was built from.

        Parameters
        ----------
        id : -1, key, G= group, number or list
            Which seeding points; -1 (default) for all.
        min_paths : int
            A zone needs at least this many paths -- one pathline has no
            second streamline to bound it.  The path is still plotted.
        offset_m : float
            Standoff between the outermost path and the boundary, in metres.
            The only argument that expands a zone.
        **params
            Passed to the envelope: `min_width` (5 m, the width given to a
            lone pathline), `gap_factor` (6) and `max_gap` (None) -- how far
            two adjacent pathlines may end apart before the tube between them
            is taken to have split around a stagnation point and is left
            unfilled -- `smooth` (0) and `simplify` (0).

        Returns the :class:`CaptureZone`, also kept as ``self.capture``.
        """
        import geopandas as gpd 

        recs, geoms = [], []
        for k, key in self._select(id):
            sel = self.paths_of(k)
            if len(sel) < int(min_paths):
                continue
            g = _envelope(self.xy, self.start, sel, self._centre(k),
                          offset_m=offset_m, **params)
            if g is None or g.is_empty:
                continue
            x, y = self._centre(k)
            recs.append({'key': key, 'group': self._group_of(k), 'x': x, 'y': y,
                         'ntraj': int(len(sel)), 'area_km2': round(g.area / 1e6, 4),
                         'method': 'envelope'})
            geoms.append(g)
        cols = ['key', 'group', 'x', 'y', 'ntraj', 'area_km2', 'method']
        self.capture = CaptureZone(
            gpd.GeoDataFrame(recs, columns=cols, geometry=geoms, crs=self.crs),
            'envelope')
        return self.capture

    def _model_grid(self):
        """The cell structure of the model, read once."""
        if getattr(self, '_grid_index', None) is None:
            if self.grid is None:
                raise ValueError(
                    "no model grid: the mask is built on the MARTHE cells, so "
                    "the project needs a permh grid (or pass grid= when "
                    "reading the trajectories)")
            self._grid_index = GridIndex(self.grid)
        return self._grid_index

    def _path_points(self, sel, step=None):
        """Every vertex of the selected paths, with the segments filled in.

        MARTHE writes a vertex per time step, so two of them can be a cell or
        more apart; without resampling, the cells a path crosses in between
        would be missed.  A resampled point takes the layer of the vertex it
        is nearer to.
        """
        xs, ys, ls = [], [], []
        for j in sel:
            a, b = self.start[j], self.start[j + 1]
            p, lay = self.xy[a:b], self.layer[a:b]
            if step is None or len(p) < 2:
                xs.append(p[:, 0])
                ys.append(p[:, 1])
                ls.append(lay)
                continue
            seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
            nsub = np.maximum(1, np.ceil(seg / step).astype(np.int64))
            for (x0, y0), (x1, y1), n, l0, l1 in zip(p[:-1], p[1:], nsub,
                                                     lay[:-1], lay[1:],
                                                     strict=True):
                t = np.linspace(0.0, 1.0, n + 1)
                xs.append(x0 + (x1 - x0) * t)
                ys.append(y0 + (y1 - y0) * t)
                ls.append(np.where(t < 0.5, l0, l1))
        if not xs:
            return np.empty(0), np.empty(0), np.empty(0, dtype=int)
        return (np.concatenate(xs), np.concatenate(ys),
                np.concatenate(ls).astype(int))

    def build_mask(self, id=-1, densify=True, step=None):
        """Mark the MARTHE cells a particle path runs through.

        The mask is built on the model's own cells -- the main grid and every
        gigogne, at their own sizes -- and layer by layer, taking the layer
        MARTHE writes with each vertex.  There is no cell size to choose: it
        is the model's.

        Parameters
        ----------
        id : -1, key, G= group, number or list
            Which seeding points; -1 (default) for all.  Each gets its own
            plane of the mask.
        densify : bool
            Fill in the segments between vertices, so a path marks every cell
            it crosses and not only those holding a vertex.
        step : float, optional
            Resampling step, in model length units.  Default: a third of the
            smallest cell of the model.

        Returns the :class:`CaptureMask`, also kept as ``self.cz_mask``.
        """
        grid = self._model_grid()
        chosen = self._select(id)
        out = np.zeros((len(chosen), grid.nzone), dtype=bool)
        step = float(step) if step else grid.min_cell / 3.0
        for i, (k, _) in enumerate(chosen):
            sel = self.paths_of(k)
            if not len(sel):
                continue
            x, y, lay = self._path_points(sel, step if densify else None)
            zone = grid.locate(x, y, lay)
            out[i, zone[zone >= 0]] = True
        self.cz_mask = CaptureMask(out, grid, [key for _, key in chosen],
                                   self.crs, source=self.rma_file)
        return self.cz_mask

    # -- summary -------------------------------------------------------------
    def summary(self, id=-1):
        """One row per seeding point: the seed, its paths, the products so far.

        Columns: key, group (the G= tag), x, y, z, layer (from the .deptr,
        else the layer the paths start in), radius, npart (asked for), ntraj
        (attributed, by `method`), path_m (mean path length), t_max (longest
        finite travel time, model unit), then capture_method / capture_km2 when
        :meth:`build_capture` has run and mask_cells / mask_km2 when
        :meth:`build_mask` has -- NaN for a seed the product does not cover.
        """
        recs = []
        for k, key in self._select(id):
            sel = self.paths_of(k)
            seg = [np.linalg.norm(np.diff(self.xy[self.start[j]:self.start[j + 1]],
                                          axis=0), axis=1).sum() for j in sel]
            t = (np.concatenate([self.t[self.start[j]:self.start[j + 1]] for j in sel])
                 if len(sel) else np.zeros(0))
            t = t[np.isfinite(t) & (t < 1e11)]                # drop the sentinel
            w = self.seeds.iloc[k] if len(self.seeds) else None
            layer = int(w.layer) if w is not None else -1
            if layer < 1 and len(sel):
                first = self.layer[self.start[sel]]           # where the paths start
                layer = int(np.bincount(first[first >= 0]).argmax())
            rec = {'key': key,
                   'group': self._group_of(k),
                   'x': self._centre(k)[0], 'y': self._centre(k)[1],
                   'z': float(w.z) if w is not None else np.nan,
                   'layer': layer,
                   'radius': float(w.radius) if w is not None else np.nan,
                   'npart': int(w.npart) if w is not None else -1,
                   'ntraj': int(len(sel)), 'method': self.method,
                   'path_m': float(np.mean(seg)) if seg else np.nan,
                   't_max': float(t.max()) if len(t) else np.nan}
            if self.capture is not None:
                g = self.capture.gdf.set_index('key')
                rec['capture_method'] = self.capture.method
                rec['capture_km2'] = float(g.area_km2.get(key, np.nan))
            if self.cz_mask is not None:
                cm = self.cz_mask
                inside = key in cm.keys
                rec['mask_cells'] = (int(cm.array[cm.keys.index(key)].sum())
                                     if inside else np.nan)
                rec['mask_km2'] = cm.area_km2(key) if inside else np.nan
            recs.append(rec)
        return pd.DataFrame(recs).set_index('key')

    # -- plotting ------------------------------------------------------------
    def plot(self, path=True, capture=False, cz_mask=False, seeds=True, id=-1,
             color_by='layer', cmap='viridis', layer_colors=None, path_width=0.5,
             path_alpha=0.7, path_color='#1f6fb4',
             zone_color='#0b3d91', zone_fill='#1f6fb4', zone_alpha=0.18,
             zone_width=1.2, mask_color='#d95f02', mask_alpha=0.35,
             mask_layer=None,
             seed_color='#b3122b', seed_size=6,
             basemap=True, basemap_source='esri', tile='auto', tile_cache=None,
             basemap_alpha=1.0,
             figsize=(7.0, 6.2), font='DejaVu Sans', base_fontsize=9.0, dpi=110,
             margin=0.05, title=None, legend=True, legend_loc='best',
             scale_bar=True, north_arrow=True, ax=None, save=None):
        """Map of the trajectories, the capture zone and the mask.

        Everything drawn is a switch, everything cosmetic a keyword -- there
        is no case file.  `capture` and `cz_mask` need :meth:`build_capture`
        and :meth:`build_mask` to have been called first.

        Parameters
        ----------
        path, capture, cz_mask, seeds : bool
            What to draw: the pathlines, the capture polygons, the boolean
            mask, the seeding points.
        id : -1, key, G= group, number or list
            Which seeding points; -1 (default) for all.
        color_by : {'layer', 'z', None}
            'layer' colours each segment by the model layer it travels in,
            listed in the legend; 'z' by the vertex altitude, on a continuous
            ramp with a colorbar ('depth' is accepted and means the same);
            None draws every path in `path_color`.
        cmap : str
            Colormap of the altitude ramp.
        layer_colors : list of colours, optional
            One colour per layer (default: matplotlib tab10).
        path_width, path_alpha, path_color
            Line width, transparency and single colour of the paths.
        zone_color, zone_fill, zone_alpha, zone_width
            Capture polygon: outline colour, fill colour and alpha, outline
            width.
        mask_color, mask_alpha
            Colour and transparency of the mask cells.
        mask_layer : int, optional
            Draw the mask of this model layer only; by default the cells of
            every layer are drawn together.
        seed_color, seed_size
            Marker of the seeding points.
        basemap : bool
            Draw a background map (needs contextily; never fatal -- a neutral
            ground is used if the tiles cannot be had).
        basemap_source : str
            'esri', 'esri_gray', 'esri_street', 'esri_imagery', 'topo',
            'positron', 'voyager', 'osm', or any XYZ tile URL template.
        tile : 'auto' or int
            Tile zoom level.
        tile_cache : str, optional
            Directory the tiles are cached in.
        basemap_alpha : float
            Transparency of the background map.
        figsize : (w, h)
            Figure size in inches (ignored when `ax` is given).
        font : str
            Font family.
        base_fontsize : float
            Base size in points; title 1.4x, axis labels 1.05x, ticks 0.95x,
            legend 0.9x, annotations 0.8x, attribution 0.7x.
        dpi : int
            Figure resolution (and the saved file's).
        margin : float
            Fraction of the content span left around it.
        title : str, optional
            Figure title.
        legend, scale_bar, north_arrow : bool
            Map furniture.
        legend_loc : str
            Any matplotlib legend location ('best', 'upper left', ...).
        ax : matplotlib.axes.Axes, optional
            Draw on existing axes.
        save : str, optional
            Write the figure to this path.

        Returns (fig, ax).
        """
        import matplotlib.pyplot as plt
        from matplotlib.collections import LineCollection
        from matplotlib.colors import BoundaryNorm, ListedColormap, Normalize
        from matplotlib.lines import Line2D
        from matplotlib.patches import Patch

        color_by = 'z' if color_by == 'depth' else color_by
        if color_by not in ('layer', 'z', None):
            raise ValueError("color_by must be 'layer', 'z' or None")
        if capture and self.capture is None:
            raise ValueError("call build_capture() before plot(capture=True)")
        if cz_mask and self.cz_mask is None:
            raise ValueError("call build_mask() before plot(cz_mask=True)")

        fs = lambda m: base_fontsize * m                      # noqa: E731
        fig, ax = (ax.figure, ax) if ax is not None else plt.subplots(
            figsize=figsize, dpi=dpi)
        chosen = self._select(id)
        handles, bounds, mappable = [], [], None

        # -- the mask, under everything else ---------------------------------
        if cz_mask:
            cm = self.cz_mask
            keys = [key for _, key in chosen if key in cm.keys]
            plane = cm._plane(keys if keys else -1)
            drawn = False
            for g in sorted(cm.grid.grids):          # coarse first, nested over it
                block = cm.grid.plane(plane, g, mask_layer)
                if not block.any():
                    continue
                ex, ey = cm.grid.edges(g)
                ax.pcolormesh(ex, ey, np.ma.masked_where(~block, block),
                              cmap=ListedColormap([mask_color]),
                              alpha=mask_alpha, shading='flat', zorder=2)
                rr, cc = np.nonzero(block)
                bounds.append((ex[cc.min()], ey[rr.max() + 1],
                               ex[cc.max() + 1], ey[rr.min()]))
                drawn = True
            if drawn:
                label = ('Cells with a path' if mask_layer is None
                         else f'Cells with a path (layer {mask_layer})')
                handles.append(Patch(facecolor=mask_color, alpha=mask_alpha,
                                     label=label))

        # -- the paths -------------------------------------------------------
        if path:
            sel = np.concatenate([self.paths_of(k) for k, _ in chosen]) \
                if chosen else np.array([], dtype=int)
            segs, val = [], []
            for j in sel:
                a, b = self.start[j], self.start[j + 1]
                p = self.xy[a:b]
                if len(p) < 2:
                    continue
                segs.append(np.stack([p[:-1], p[1:]], axis=1))
                if color_by == 'z':
                    z = self.z[a:b]
                    val.append(0.5 * (z[:-1] + z[1:]))
                elif color_by == 'layer':
                    lay = self.layer[a:b]
                    val.append(np.maximum(lay[:-1], lay[1:]))       # deeper end
            if segs:
                segs = np.concatenate(segs, axis=0)
                bounds.append((*segs.reshape(-1, 2).min(axis=0),
                               *segs.reshape(-1, 2).max(axis=0)))
                if color_by == 'z':
                    val = np.concatenate(val)
                    good = np.isfinite(val)
                    lo, hi = (np.percentile(val[good], [1, 99]) if good.any()
                              else (0, 1))
                    lc = LineCollection(segs, cmap=cmap, norm=Normalize(lo, hi),
                                        linewidths=path_width, alpha=path_alpha,
                                        zorder=3)
                    lc.set_array(val)
                    mappable = lc
                elif color_by == 'layer':
                    val = np.concatenate(val)
                    nlay = int(max(val.max(), 1))
                    colors = list(layer_colors) if layer_colors else \
                        [plt.get_cmap('tab10')(i % 10) for i in range(nlay)]
                    norm = BoundaryNorm(np.arange(0.5, nlay + 1.5), nlay)
                    lc = LineCollection(segs, cmap=ListedColormap(colors[:nlay]),
                                        norm=norm, linewidths=path_width,
                                        alpha=path_alpha, zorder=3)
                    lc.set_array(val.astype(float))
                    handles += [Line2D([], [], color=colors[i - 1], lw=1.6,
                                       label=f'Layer {i}')
                                for i in sorted({int(v) for v in val})
                                if 1 <= i <= nlay]
                else:
                    lc = LineCollection(segs, colors=path_color,
                                        linewidths=path_width, alpha=path_alpha,
                                        zorder=3)
                    handles.append(Line2D([], [], color=path_color, lw=1.6,
                                          label='Pathlines'))
                ax.add_collection(lc)

        # -- the capture polygons --------------------------------------------
        if capture:
            gdf = self.capture.gdf
            sub = gdf[gdf.key.isin([key for _, key in chosen])]
            if len(sub):
                sub.plot(ax=ax, facecolor=zone_fill, edgecolor='none',
                         alpha=zone_alpha, zorder=4)
                sub.boundary.plot(ax=ax, color=zone_color, lw=zone_width, zorder=5)
                bounds.append(tuple(sub.total_bounds))
                handles.append(Line2D([], [], color=zone_color, lw=zone_width,
                                      label=f'Capture zone ({self.capture.method})'))

        # -- the seeding points ----------------------------------------------
        if seeds and len(self.seeds):
            sub = self.seeds.iloc[[k for k, _ in chosen]]
            ax.plot(sub.x, sub.y, ls='none', marker='o', ms=seed_size,
                    mfc=seed_color, mec='white', mew=0.8, zorder=8)
            handles.append(Line2D([], [], ls='none', marker='o', ms=seed_size,
                                  mfc=seed_color, mec='white', mew=0.8,
                                  label='Seeding point'))

        # -- framing and furniture -------------------------------------------
        if bounds:
            b = np.array(bounds)
            xmin, ymin = b[:, 0].min(), b[:, 1].min()
            xmax, ymax = b[:, 2].max(), b[:, 3].max()
            mx, my = margin * (xmax - xmin), margin * (ymax - ymin)
            ax.set_xlim(xmin - mx, xmax + mx)
            ax.set_ylim(ymin - my, ymax + my)
        ax.set_aspect('equal')

        if basemap:
            _basemap(ax, self.crs, basemap_source, tile, tile_cache, basemap_alpha)
            ax.text(0.995, 0.006, _ATTRIBUTION.get(basemap_source, ''),
                    transform=ax.transAxes, ha='right', va='bottom',
                    fontsize=fs(0.7), fontfamily=font, color='#808080', zorder=20,
                    bbox={'fc': 'white', 'ec': 'none', 'alpha': 0.6, 'pad': 1.0})

        ax.ticklabel_format(style='plain', useOffset=False)
        ax.set_xlabel('Easting (m)', fontsize=fs(1.05), fontfamily=font)
        ax.set_ylabel('Northing (m)', fontsize=fs(1.05), fontfamily=font)
        ax.tick_params(labelsize=fs(0.95))
        for lbl in ax.get_xticklabels() + ax.get_yticklabels():
            lbl.set_fontfamily(font)
        if title:
            ax.set_title(title, fontsize=fs(1.4), fontfamily=font, loc='left')
        if mappable is not None:
            cb = fig.colorbar(mappable, ax=ax, fraction=0.04, pad=0.02)
            cb.set_label('Pathline altitude z (m)', fontsize=fs(1.05),
                         fontfamily=font)
            cb.ax.tick_params(labelsize=fs(0.9))
            for lbl in cb.ax.get_yticklabels():
                lbl.set_fontfamily(font)
        if scale_bar:
            _scale_bar(ax, fs(0.8), font)
        if north_arrow:
            ax.annotate('N', xy=(0.955, 0.90), xytext=(0.955, 0.825),
                        xycoords='axes fraction', textcoords='axes fraction',
                        ha='center', va='center', fontsize=fs(1.0),
                        fontfamily=font, zorder=20,
                        arrowprops={'arrowstyle': '-|>', 'color': '#1a1a1a', 'lw': 1.1})
        if legend and handles:
            leg = ax.legend(handles=handles, loc=legend_loc, frameon=True,
                            framealpha=0.9, prop={'family': font, 'size': fs(0.9)})
            leg.get_frame().set_linewidth(0.6)
        if save:
            os.makedirs(os.path.dirname(os.path.abspath(save)), exist_ok=True)
            fig.savefig(save, dpi=dpi, bbox_inches='tight')
        return fig, ax

    def __repr__(self):
        n = np.bincount(self.owner[self.owner >= 0], minlength=len(self.keys))
        msg = (f"Trajectory: {self.ntraj} paths, {len(self.xy)} vertices, "
               f"{len(self.keys)} seeding points ({int((self.owner < 0).sum())} "
               f"unattributed)\n")
        for key, c in zip(self.keys, n, strict=True):
            msg += f"    {key}: {int(c)} paths\n"
        return msg


# --------------------------------------------------------------------------
# map artifacts
# --------------------------------------------------------------------------

_PROVIDERS = {
    'esri': ('Esri', 'WorldTopoMap'),
    'esri_gray': ('Esri', 'WorldGrayCanvas'),
    'esri_street': ('Esri', 'WorldStreetMap'),
    'esri_imagery': ('Esri', 'WorldImagery'),
    'topo': ('OpenTopoMap', None),
    'positron': ('CartoDB', 'Positron'),
    'voyager': ('CartoDB', 'Voyager'),
    'osm': ('OpenStreetMap', 'Mapnik'),
}
_ATTRIBUTION = {
    'esri': 'Basemap © Esri, HERE, Garmin, USGS, NGA',
    'esri_gray': 'Basemap © Esri, HERE, Garmin, USGS, NGA',
    'esri_street': 'Basemap © Esri, HERE, Garmin, USGS, NGA',
    'esri_imagery': 'Imagery © Esri, Maxar, Earthstar Geographics',
    'topo': 'Basemap © OpenTopoMap (CC-BY-SA) © OpenStreetMap contributors',
    'positron': 'Basemap © OpenStreetMap contributors © CARTO',
    'voyager': 'Basemap © OpenStreetMap contributors © CARTO',
    'osm': 'Basemap © OpenStreetMap contributors',
}


def _basemap(ax, crs, source='esri', zoom='auto', cache=None, alpha=1.0):
    """Background tiles, reprojected to `crs`.  Never fatal."""
    try:
        import contextily as cx
        if cache:
            os.makedirs(cache, exist_ok=True)
            cx.set_cache_dir(cache)
        if str(source).startswith('http'):
            src = source
        else:
            grp, sub = _PROVIDERS.get(str(source).lower(), _PROVIDERS['esri'])
            src = getattr(cx.providers, grp)
            src = getattr(src, sub) if sub else src
        cx.add_basemap(ax, crs=crs, source=src, zoom=zoom, attribution='',
                       alpha=alpha)
    except Exception as exc:
        print(f"    [basemap unavailable: {type(exc).__name__}: {str(exc)[:60]}]")
        ax.set_facecolor('#f4f4f2')


def _scale_bar(ax, fontsize, font, loc=(0.06, 0.045)):
    import matplotlib.pyplot as plt
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    target = (x1 - x0) / 4.0
    L = next((v for v in (10, 20, 50, 100, 200, 250, 500, 1000, 2000, 2500,
                          5000, 10000, 20000, 50000) if v >= target), 50000)
    xs, ys = x0 + loc[0] * (x1 - x0), y0 + loc[1] * (y1 - y0)
    h = 0.010 * (y1 - y0)
    for i, a in enumerate((0.0, 0.5)):
        ax.add_patch(plt.Rectangle((xs + a * L, ys), 0.5 * L, h,
                                   facecolor='#1a1a1a' if i == 0 else 'white',
                                   edgecolor='#1a1a1a', lw=0.6, zorder=20))
    lab = f"{L / 1000:g} km" if L >= 1000 else f"{L:g} m"
    ax.text(xs + L / 2, ys + 1.5 * h, lab, ha='center', va='bottom',
            fontsize=fontsize, fontfamily=font, zorder=20,
            bbox={'fc': 'white', 'ec': 'none', 'alpha': 0.75, 'pad': 1.0})


def read_trajectory(project, **kwargs):
    """Shortcut for :meth:`Trajectory.from_project`."""
    return Trajectory.from_project(project, **kwargs)
