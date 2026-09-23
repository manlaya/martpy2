#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test module for utils/trajectory.py

The test model (``tests/data/mrn_traj``) is a trajectory run (on 4 seeding locations) of the
mrn_v11 model, 100 particles each, cut down to what the module actually
reads: the project (`.rma`), the grid the cell records are located on
(`.permh`), the seeding file and `trajmar.out`.  The `.rma` still points at
the other files of the full model (pastp, layer, hsubs ...); none of them is
opened here, and they are deliberately not shipped as test dataset.

The seeding file carries both record forms MARTHE accepts -- two (X, Y, Z)
records and two (Column, Line, Layer, Gigogne) records -- so the cell lookup
and the coordinate form are both exercised.  Its `G=` tags are 1, 20, 33 and
4: unique, out of order, and two of them larger than the number of seeding
points, which is what separates a group tag from a position in file order.
"""

import gzip
import os
import shutil

import numpy as np
import pandas as pd
import pytest

import martpy as mart
from martpy.utils.trajectory import (
    CaptureMask,
    Trajectory,
    read_deptr,
    read_trajmar,
)


DATA = os.path.join('tests', 'data', 'mrn_traj')
RMA = os.path.join(DATA, 'mrn_v11.rma')
DEPTR = os.path.join(DATA, 'mrn_v11_test.deptr')
TRAJMAR = os.path.join(DATA, 'trajmar.out')

# TRUE DATA: what the seeding file declares, in file order 
KEYS = ['W01', 'W02', 'W03', 'W04']
GROUPS = [1, 20, 33, 4]
NPART = 100  # number of particles at each seeding loc
NTRAJ = 400 # total produced trajectory 

# geopandas/shapely are an optional extra of martpy (in practice gridmarthe
# pulls them in): the readers, the attribution and the mask are tested
# without them, the capture zone only where they are installed.
try:
    import geopandas as gpd  # noqa: F401, ICN002
    from shapely.geometry import MultiPoint
    HAS_GEO = True
except (ImportError, ModuleNotFoundError):
    HAS_GEO = False

needs_geo = pytest.mark.skipif(not HAS_GEO, reason='geopandas/shapely not installed')


@pytest.fixture(scope='module')
def traj():
    """The test run, read once for the whole module."""
    return mart.read_trajectory(RMA)


@pytest.fixture()
def fresh():
    """A trajectory with nothing built on it yet."""
    return mart.read_trajectory(RMA)


def vertices_of(tr, key):
    """Every vertex of the paths attributed to one seeding point."""
    sel = tr.paths_of(tr.keys.index(key))
    return np.concatenate([tr.xy[tr.start[j]:tr.start[j + 1]] for j in sel])


def write_trajmar(path, paths, groups=None):
    """Write a small trajmar.out by hand.

    `paths` is a list of trajectories, each a list of (x, y, z, t, layer).
    `groups` gives the `Group =` tag of each one; without it the file carries
    no tag, as a run of an older MARTHE does.
    """
    lines = [f" {len(paths)} <Trajectoires> : (X,Y,Z,T,C) X=1,Y=1,Z=1,C=1 test\n"]
    for k, pts in enumerate(paths, 1):
        tag = '' if groups is None else f" Group = {groups[k - 1]} ;"
        lines.append(f"# Nombre de Points = {len(pts)} ;{tag}\n")
        lines.append(f"# Trajectoire n    {k} ==============================\n")
        for x, y, z, t, lay in pts:
            lines.append(f"   {x:.6f} {y:.6f} {z:.6f} {t:.6f} {int(lay):d}\n")
    with open(path, 'w', encoding='ISO-8859-1') as f:
        f.writelines(lines)
    return str(path)


# ==========================================================================
# the readers
# ==========================================================================
def test_read_deptr_both_forms():
    """Both seeding record forms are read, and keyed in file order."""
    seeds = read_deptr(DEPTR)

    assert list(seeds.index) == KEYS, 'seeding points are keyed W01, W02 ... in file order'
    assert seeds['form'].tolist() == ['xy', 'xy', 'cell', 'cell'], (
        'the file declares two (X, Y, Z) records then two cell records'
    )
    assert seeds['group'].tolist() == GROUPS, 'the G= tag is read as written'
    assert (seeds['npart'] == NPART).all(), 'N= is the number of particles'
    assert (seeds['radius'] == 142.0).all(), 'R= is the seeding radius'

    # an (X, Y, Z) record carries its coordinates and no cell
    xy = seeds.loc['W01']
    assert (xy.x, xy.y, xy.z) == (567056.0, 6933156.0, 64.95)
    assert (xy.col, xy.row, xy.layer, xy.inest) == (-1, -1, -1, -1), (
        'an (X, Y, Z) record states no cell'
    )

    # a cell record carries its cell and no coordinates until it is located
    cell = seeds.loc['W03']
    assert (cell.col, cell.row, cell.layer, cell.inest) == (152, 45, 3, 1)
    assert np.isnan(cell.x) and np.isnan(cell.y), (
        'a cell record has no x, y until the grid is read'
    )


def test_read_deptr_skips_non_records(tmp_path):
    """Header, footer, wildcards and unparsable lines are not seeding points."""
    p = tmp_path / 'mixed.deptr'
    p.write_text(
        'Fichier projet Marthe : x.rma\n'
        'M             1             *\n'            # wildcard, whole gigogne
        'M            10            20             3             1 N= 7 R= 12.5 G= 9\n'
        'X= 1.0 Y= 2.0 Z= 3.0 N= 4 R= 8 G= 2\n'
        'not a record at all\n'
        ' *** Fin du fichier Depart de Trajectoires ***\n',
        encoding='latin-1')
    seeds = read_deptr(str(p))

    assert len(seeds) == 2, 'only the two complete records are seeding points'
    assert seeds['form'].tolist() == ['cell', 'xy']
    assert seeds['npart'].tolist() == [7, 4]
    assert seeds['radius'].tolist() == [12.5, 8.0]


def test_read_deptr_empty_keeps_columns(tmp_path):
    """A file with no record gives an empty frame, not a shapeless one."""
    p = tmp_path / 'empty.deptr'
    p.write_text('Fichier projet Marthe : x.rma\n *** Fin ***\n', encoding='latin-1')
    seeds = read_deptr(str(p))

    assert len(seeds) == 0
    assert 'group' in seeds.columns and 'radius' in seeds.columns, (
        'the columns are there even with no record, so callers can index them'
    )


def test_read_trajmar():
    """Vertices, offsets, altitude, travel time, layer and group tags."""
    t = read_trajmar(TRAJMAR)

    assert t['start'][0] == 0
    assert len(t['start']) == NTRAJ + 1, 'one offset per trajectory, plus the end'
    assert t['start'][-1] == len(t['xy']), 'the offsets cover every vertex'
    assert (np.diff(t['start']) > 0).all(), 'every trajectory has at least one vertex'

    for k in ('z', 't', 'layer'):
        assert len(t[k]) == len(t['xy']), f'{k} is given for every vertex'

    assert len(t['group']) == NTRAJ, 'one group tag per trajectory'
    assert sorted(set(t['group'])) == sorted(GROUPS), (
        'the tags are those of the seeding file'
    )
    assert set(np.unique(t['layer'])) <= {1, 2, 3}, (
        'the layer is the fifth column, within the layers of the model'
    )
    # MARTHE closes every trajectory with a sentinel travel time
    last = t['start'][1:] - 1
    assert (t['t'][last] >= 1e11).all(), 'the last vertex carries the 1e12 sentinel'
    assert (t['t'][t['t'] < 1e11] >= 0).all(), 'travel times are positive'


def test_read_trajmar_exact_values(tmp_path):
    """Every column of a hand-written file comes back as it was written."""
    first = [(1.0, 2.0, 30.0, 0.0, 1), (3.0, 4.0, 25.0, 0.5, 2)]
    second = [(5.0, 6.0, 20.0, 0.0, 3)]
    p = write_trajmar(tmp_path / 'small.out', [first, second], groups=[7, 12])
    t = read_trajmar(p)

    assert t['start'].tolist() == [0, 2, 3], 'two paths, of two and one vertices'
    assert t['xy'].tolist() == [[1., 2.], [3., 4.], [5., 6.]]
    assert t['z'].tolist() == [30., 25., 20.], 'the third column is the altitude'
    assert t['t'].tolist() == [0., 0.5, 0.], 'the fourth is the travel time'
    assert t['layer'].tolist() == [1, 2, 3], 'the fifth is the layer'
    assert t['group'].tolist() == [7, 12], 'one tag per trajectory'


def test_read_trajmar_without_group_tags(tmp_path):
    """A file written without any `Group =` reads, and says so with -1."""
    p = write_trajmar(tmp_path / 'untagged.out',
                      [[(1., 2., 3., 0., 1)], [(4., 5., 6., 0., 1)]])
    t = read_trajmar(p)

    assert len(t['start']) == 3, 'the two trajectories are still separated'
    assert t['group'].tolist() == [-1, -1], 'no tag is -1, not a wrong tag'


def test_read_trajmar_gz(tmp_path):
    """A gzipped trajmar.out reads identically."""
    gz = tmp_path / 'trajmar.out.gz'
    with open(TRAJMAR, 'rb') as fi, gzip.open(gz, 'wb') as fo:
        shutil.copyfileobj(fi, fo)

    plain, packed = read_trajmar(TRAJMAR), read_trajmar(str(gz))
    for k in plain:
        assert np.array_equal(plain[k], packed[k], equal_nan=True), f'{k} differs'


# ==========================================================================
# reading through the project
# ==========================================================================
def test_from_project_reads_the_whole_run(traj):
    """The project gives the seeding file and the grid; trajmar.out sits next to it."""
    assert traj.ntraj == NTRAJ
    assert traj.keys == KEYS
    assert len(traj.xy) == traj.start[-1]
    assert traj.crs == 'EPSG:2154', 'Lambert-93 unless asked otherwise'


def test_from_project_accepts_path_or_project():
    """`read_rma_file` output and the .rma path itself are interchangeable."""
    from_path = mart.read_trajectory(RMA)
    from_project = Trajectory.from_project(mart.read_rma_file(RMA))

    assert from_path.keys == from_project.keys
    assert np.array_equal(from_path.owner, from_project.owner)


def test_trajmar_argument_overrides_the_default(tmp_path):
    """`trajmar=` points the reader somewhere other than next to the .rma."""
    other = tmp_path / 'elsewhere.out'
    shutil.copy(TRAJMAR, other)
    tr = mart.read_trajectory(RMA, trajmar=str(other))

    assert tr.ntraj == NTRAJ


def test_cell_records_are_located_on_the_grid(traj):
    """A cell record gets the coordinates of its cell.

    The check is geometric rather than a hard-coded pair of coordinates: the
    particles of a seeding point are released on the circle of radius R about
    it, so if the (layer, gigogne, col, row) lookup were off by so much as one
    cell the trajectories of that point would no longer start on its ring.
    """
    located = traj.seeds.loc[traj.seeds['form'] == 'cell']
    assert len(located) == 2
    assert np.isfinite(located[['x', 'y']].to_numpy()).all(), 'every cell is located'

    for key, w in located.iterrows():
        sel = traj.paths_of(traj.keys.index(key))
        d = np.linalg.norm(traj.xy[traj.start[sel]] - [w.x, w.y], axis=1)
        assert np.abs(d - w.radius).max() < 1.0, (
            f'{key}: its particles do not start on the ring of the located cell'
        )

    # rows are numbered from the north, so a higher row is a lower y
    w3, w4 = traj.seeds.loc['W03'], traj.seeds.loc['W04']
    assert w3.row > w4.row and w3.y < w4.y, 'y decreases as the row number grows'
    assert w3.x == w4.x, 'both records are in the same column'
    assert abs(w4.y - w3.y) == pytest.approx(400.0), (
        'two rows apart on the 200 m gigogne'
    )


# ==========================================================================
# attributing a trajectory to a seeding point
# ==========================================================================
def test_attribution_auto_trusts_usable_tags(traj):
    """The tags here are complete and unique, so `auto` uses them."""
    assert traj.method == 'group'
    assert (traj.owner >= 0).all(), 'every trajectory belongs to a seeding point'
    assert np.bincount(traj.owner).tolist() == [NPART] * len(KEYS), (
        'each seeding point gets the N= particles it asked for'
    )


def test_attribution_ring_agrees_with_the_tags(traj):
    """The geometric fallback reproduces the tags on this run.

    The two are independent -- one reads the `Group =` MARTHE wrote, the other
    measures where the particles start -- so agreeing on all 400 trajectories
    is a check of both.
    """
    ring = mart.read_trajectory(RMA, method='ring')

    assert ring.method == 'ring'
    assert np.array_equal(ring.owner, traj.owner)


def test_attribution_ring_residual(traj):
    """Every trajectory starts on the seeding circle of its own point."""
    for k, key in enumerate(traj.keys):
        w = traj.seeds.iloc[k]
        sel = traj.paths_of(k)
        d = np.linalg.norm(traj.xy[traj.start[sel]] - [w.x, w.y], axis=1)
        assert np.abs(d - w.radius).max() < 1.0, f'{key}: particles off its ring'


def test_attribution_group_without_tags_raises(tmp_path):
    """Asking for the tags when the file has none says so."""
    untagged = read_trajmar(write_trajmar(
        tmp_path / 'untagged.out', [[(567056., 6933298., 60., 0., 3)]]))

    with pytest.raises(ValueError, match='Group tag'):
        Trajectory(read_deptr(DEPTR), untagged, method='group')


def test_attribution_falls_back_to_the_tags_without_seeds():
    """With no seeding file the paths are grouped by their own tag."""
    tr = Trajectory(pd.DataFrame(), read_trajmar(TRAJMAR))

    assert tr.method == 'tag'
    assert tr.keys == ['G1', 'G4', 'G20', 'G33'], 'one key per tag, in tag order'
    assert np.bincount(tr.owner).tolist() == [NPART] * len(KEYS)


def test_attribution_without_seeds_or_tags(tmp_path):
    """Neither seeding points nor tags: one group holding everything."""
    untagged = read_trajmar(write_trajmar(
        tmp_path / 'untagged.out',
        [[(1., 2., 3., 0., 1)], [(4., 5., 6., 0., 1)]]))
    tr = Trajectory(pd.DataFrame(), untagged)

    assert tr.keys == ['ALL'], 'nothing to tell the paths apart, so one group'
    assert tr.method == 'none'
    assert (tr.owner == 0).all()
    assert tr.ntraj == 2


# ==========================================================================
# selecting seeding points
# ==========================================================================
def test_select_by_key_group_or_position(traj):
    """`id` takes a key, a G= group, a position in file order, or a list."""
    assert [k for _, k in traj._select(-1)] == KEYS, '-1 is every seeding point'
    assert [k for _, k in traj._select('W03')] == ['W03']
    assert [k for _, k in traj._select(33)] == ['W03'], '33 is the G= tag of W03'
    assert [k for _, k in traj._select('33')] == ['W03'], 'as a string too'
    assert [k for _, k in traj._select(20)] == ['W02'], (
        '20 is a group tag, not the twentieth seeding point'
    )
    assert [k for _, k in traj._select(3)] == ['W03'], (
        'no point carries the tag 3, so it is read as the third in file order'
    )
    assert [k for _, k in traj._select([1, 'W02', 33])] == ['W01', 'W02', 'W03']
    assert [k for _, k in traj._select([33, 1])] == ['W03', 'W01'], (
        'the points come back in the order they were asked for'
    )


def test_select_rejects_the_unknown(traj):
    for bad in ('W99', 999, 'nonsense'):
        with pytest.raises(KeyError):
            traj._select(bad)


# ==========================================================================
# exporting the paths
# ==========================================================================
@needs_geo
def test_to_shape_point_writes_the_file_values(traj, tmp_path):
    """A point feature per vertex, carrying trajmar.out's own values."""
    out = tmp_path / 'points.shp'
    gdf = traj.to_shape(str(out), kind='point', id='W01')

    assert out.exists(), 'the shapefile is written'
    assert list(gdf.columns) == ['key', 'group', 'traj', 'vertex', 'x', 'y',
                                 'z', 't', 'layer', 'geometry']
    assert gdf.crs.to_epsg() == 2154
    assert (gdf.key == 'W01').all()
    assert (gdf.group == 1).all(), 'the G= tag of W01, not its position'
    assert gdf.traj.nunique() == NPART

    sel = traj.paths_of(0)
    assert len(gdf) == sum(traj.start[j + 1] - traj.start[j] for j in sel), (
        'one feature per vertex of the selected paths'
    )

    # the attributes are the file's own values, not derived ones
    first = gdf.iloc[0]
    a = traj.start[sel[0]]
    assert (first.x, first.y) == (traj.xy[a, 0], traj.xy[a, 1])
    assert first.z == traj.z[a] and first.t == traj.t[a]
    assert first.layer == traj.layer[a]
    assert (first.geometry.x, first.geometry.y) == (first.x, first.y), (
        'the geometry is the vertex it describes'
    )


@needs_geo
def test_to_shape_line_segments(traj, tmp_path):
    """A line feature per pair of consecutive vertices, with averaged values."""
    out = tmp_path / 'lines.gpkg'
    gdf = traj.to_shape(str(out), kind='line', id=['W01', 'W02'])

    assert out.exists(), 'the extension picks the driver'
    for col in ('key', 'group', 'traj', 'seg', 'from', 'to', 'z', 't', 'layer'):
        assert col in gdf.columns, f'{col} is missing'
    assert set(gdf.key) == {'W01', 'W02'}
    assert set(gdf.group) == {1, 20}

    sel = np.concatenate([traj.paths_of(0), traj.paths_of(1)])
    n_vertices = sum(traj.start[j + 1] - traj.start[j] for j in sel)
    assert len(gdf) == n_vertices - len(sel), 'a path of n vertices gives n-1 segments'

    # a segment joins the two vertices it was built from, and averages them
    a = traj.start[sel[0]]
    row = gdf.iloc[0]
    coords = list(row.geometry.coords)
    assert coords[0] == (traj.xy[a, 0], traj.xy[a, 1])
    assert coords[1] == (traj.xy[a + 1, 0], traj.xy[a + 1, 1])
    assert row.z == pytest.approx(0.5 * (traj.z[a] + traj.z[a + 1]))
    assert row.t == pytest.approx(0.5 * (traj.t[a] + traj.t[a + 1]))
    assert row.layer == max(traj.layer[a], traj.layer[a + 1]), 'the deeper of the two'
    assert row['from'].startswith('(') and row['to'].startswith('('), (
        'the two ends are written out so a path can be followed in a GIS'
    )


@needs_geo
def test_to_shape_crs_argument(traj, tmp_path):
    gdf = traj.to_shape(str(tmp_path / 'p.shp'), kind='point', id=1,
                        crs='EPSG:27572')
    assert gdf.crs.to_epsg() == 27572


@needs_geo
def test_to_shape_rejects_other_kinds(traj, tmp_path):
    with pytest.raises(ValueError, match="'point' or 'line'"):
        traj.to_shape(str(tmp_path / 'x.shp'), kind='polygon')


# ==========================================================================
# capture zones
# ==========================================================================
@needs_geo
def test_build_capture_envelope_encloses_its_paths(traj):
    """No pathline may fall outside the envelope built from it.

    This is what the envelope construction claims over a hull: every pathline
    is an edge of two stream tubes, so the union cannot leave one outside.
    """
    cz = traj.build_capture(offset_m=20.)
    zones = cz.gdf.set_index('key')

    assert len(cz.gdf) == len(KEYS), 'one zone per seeding point'
    assert (cz.gdf.area_km2 > 0).all()
    assert cz.gdf.crs.to_epsg() == 2154
    assert cz.gdf['group'].tolist() == GROUPS, 'the zone carries its G= tag'
    assert (cz.gdf.ntraj == NPART).all()

    for key in KEYS:
        pts = MultiPoint(vertices_of(traj, key))
        assert zones.geometry.loc[key].buffer(1e-6).covers(pts), (
            f'{key}: a pathline runs outside its own capture zone'
        )


@needs_geo
def test_build_capture_offset_grows_the_zone(traj):
    """`offset_m` is the standoff, and the only argument that expands a zone."""
    tight = traj.build_capture(offset_m=0.).gdf.set_index('key')
    wide = traj.build_capture(offset_m=100.).gdf.set_index('key')

    assert (wide.area_km2 > tight.area_km2).all(), 'a larger standoff is a larger zone'
    for key in KEYS:
        assert wide.geometry.loc[key].buffer(1e-6).covers(tight.geometry.loc[key]), (
            f'{key}: the offset zone does not contain the un-offset one'
        )


@needs_geo
def test_build_capture_is_the_envelope(traj):
    """One delineation, the envelope, and it says so on every zone."""
    cz = traj.build_capture()

    assert cz.method == 'envelope'
    assert (cz.gdf.method == 'envelope').all(), 'the zone records how it was drawn'
    assert cz.gdf.geometry.is_valid.all(), 'an invalid polygon'
    assert traj.capture is cz, 'the last zone built is kept on the trajectory'


@needs_geo
def test_build_capture_envelope_parameters(traj):
    """The envelope thresholds reach the construction.

    `gap_factor` decides whether the tube between two adjacent pathlines is
    filled, so filling every one of them can only add ground.
    """
    default = traj.build_capture().gdf.set_index('key')
    fill_all = traj.build_capture(gap_factor=0).gdf.set_index('key')
    wider = traj.build_capture(min_width=200.).gdf.set_index('key')

    assert (fill_all.area_km2 >= default.area_km2).all(), (
        'filling every stream tube cannot shrink a zone'
    )
    assert (wider.area_km2 >= default.area_km2).all(), (
        'a wider pathline cannot shrink a zone'
    )


@needs_geo
def test_build_capture_subset(traj):
    cz = traj.build_capture(id=[33, 'W01'])
    assert cz.gdf.key.tolist() == ['W03', 'W01'], 'in the order they were asked for'
    assert cz.gdf['group'].tolist() == [33, 1]


@needs_geo
def test_build_capture_min_paths(traj):
    """A zone needs paths to bound it; asking for more than exist gives none."""
    cz = traj.build_capture(min_paths=NPART + 1)

    assert len(cz.gdf) == 0
    assert 'area_km2' in cz.gdf.columns, (
        'an empty result keeps its columns, so callers can still index it'
    )


@needs_geo
def test_capture_to_shape(traj, tmp_path):
    out = tmp_path / 'capture.shp'
    cz = traj.build_capture(id='W01')
    cz.to_shape(str(out))

    assert out.exists()
    back = gpd.read_file(out)
    assert len(back) == 1
    assert back.crs.to_epsg() == 2154
    assert back.geometry.iloc[0].area == pytest.approx(
        cz.gdf.geometry.iloc[0].area, rel=1e-6)


# ==========================================================================
# capture masks
# ==========================================================================
def test_build_mask_is_on_the_model_cells(traj):
    """The mask is the model's own cells, not a raster of our choosing."""
    cm = traj.build_mask()

    assert cm.array.shape == (len(KEYS), cm.grid.nzone), (
        'one boolean per model cell, per seeding point'
    )
    assert cm.array.dtype == bool
    assert cm.keys == KEYS
    assert cm.grid.nzone == 203 * 176 * 3 + 308 * 266 * 3, (
        'every cell of the main grid and of the gigogne, in every layer'
    )
    assert sorted(cm.grid.grids) == [0, 1], 'the main grid and one gigogne'
    assert cm.grid.min_cell == 200.0, 'the gigogne mesh is the finest cell'
    assert traj.cz_mask is cm, 'the last mask built is kept on the trajectory'
    assert cm.any.sum() > 0


def test_build_mask_marks_the_cell_each_vertex_is_in(traj):
    """Every vertex of a path marks the cell of its own layer.

    The check goes through the grid rather than through the mask's own
    bookkeeping: each vertex is located in the model, and the cell it lands in
    must carry the mask of the seeding point the path belongs to.
    """
    cm = traj.build_mask()
    d = cm.grid

    for i, key in enumerate(cm.keys):
        sel = traj.paths_of(traj.keys.index(key))
        idx = np.concatenate([np.arange(traj.start[j], traj.start[j + 1])
                              for j in sel])
        zone = d.locate(traj.xy[idx, 0], traj.xy[idx, 1], traj.layer[idx])
        assert (zone >= 0).all(), f'{key}: a vertex falls outside the model grid'
        assert cm.array[i][zone].all(), f'{key}: a vertex is not in the mask'
        assert np.array_equal(d.zone_layer[zone], traj.layer[idx]), (
            f'{key}: a cell was marked in the wrong layer'
        )


def test_build_mask_marks_only_active_cells(traj):
    """A marked cell is a cell the model actually has.

    MARTHE does not route a particle through an absent cell, so if the
    location were off by a cell or a row this would fail.
    """
    cm = traj.build_mask()
    permh = np.asarray(traj.grid['permeab'].values).ravel()
    marked = permh[cm.any]

    assert len(marked) > 0
    assert not np.isin(marked, [0., -9999., 9999.]).any(), (
        'a cell was marked where the model has no cell'
    )


def test_grid_index_resolves_the_layer_it_is_asked_for(traj):
    """The grid holding a point is decided layer by layer.

    Most cells of this model exist in some layers and not in others, and a
    gigogne cell absent in one layer leaves the parent cell underneath it in
    use there.  Deciding on activity pooled over the layers would pick a cell
    the model does not have in the layer asked for.
    """
    grid = traj._model_grid()
    permh = np.asarray(traj.grid['permeab'].values).ravel()
    layers = np.asarray(traj.grid['z'].values).ravel()

    zone = grid.locate(traj.xy[:, 0], traj.xy[:, 1], traj.layer)
    assert (zone >= 0).all(), 'a vertex could not be placed in any cell'
    assert np.array_equal(layers[zone], traj.layer), (
        'a vertex was placed in the wrong layer'
    )
    assert not np.isin(permh[zone], [0., -9999., 9999.]).any(), (
        'a vertex was placed in a cell the model does not have in that layer'
    )

    # the rule only matters because activity really does vary by layer here
    varying = 0
    for g, G in grid.grids.items():
        act = G['active']
        varying += int((act.any(axis=0) & ~act.all(axis=0)).sum())
    assert varying > 0, 'this model no longer exercises the per-layer rule'


def test_build_mask_separates_the_layers(traj):
    """The mask is three-dimensional: it is counted layer by layer."""
    cm = traj.build_mask()
    by_layer = cm.cells_by_layer()

    assert set(by_layer.columns) == {'grid', 'layer', 'cells', 'area_km2'}
    assert by_layer.cells.sum() == cm.any.sum(), 'every marked cell is counted once'
    assert set(by_layer.grid) == {0, 1}, 'the main grid and the gigogne'
    assert set(by_layer.layer) == {1, 2, 3}
    assert (by_layer.cells > 0).any()
    assert by_layer.area_km2.sum() == pytest.approx(cm.area_km2(), abs=1e-3), (
        'the area is the sum of the cells own areas'
    )


def test_build_mask_counts_each_cell_at_its_own_size(traj):
    """Area comes from the cells themselves, which are not all the same size."""
    cm = traj.build_mask()
    sizes = np.unique(cm.grid.cell_area[cm.any])

    assert len(sizes) > 1, 'this model mixes 400 m and 200 m cells'
    assert cm.area_km2() == pytest.approx(
        cm.grid.cell_area[cm.any].sum() / 1e6)
    assert cm.area_km2('W01') <= cm.area_km2(), 'one point covers no more than all'


def test_build_mask_subset(traj):
    cm = traj.build_mask(id=[33, 'W01'])

    assert cm.keys == ['W03', 'W01'], 'in the order they were asked for'
    assert cm.array.shape[0] == 2
    assert cm.area_km2('W03') > 0


def test_build_mask_densify(traj):
    """Resampling the segments can only add cells, never drop one."""
    raw = traj.build_mask(densify=False)
    dense = traj.build_mask(densify=True)

    assert (dense.any | raw.any == dense.any).all(), (
        'a cell marked by a vertex stays marked'
    )
    assert dense.any.sum() >= raw.any.sum()


def test_build_mask_needs_a_grid():
    """Without the model grid there are no cells to mark, and it says so."""
    bare = Trajectory(read_deptr(DEPTR), read_trajmar(TRAJMAR))

    assert bare.grid is None
    with pytest.raises(ValueError, match='permh'):
        bare.build_mask()


def test_save_mask_writes_a_marthe_grid(traj, tmp_path):
    """The mask is written as a MARTHE grid file and reads back identically."""
    cm = traj.build_mask()
    path = cm.save_mask(str(tmp_path / 'mrn_v11.tmask'))

    assert os.path.exists(path)
    assert path.endswith('.tmask')
    head = open(path, encoding='ISO-8859-1').read(400)
    assert head.startswith('Marthe_Grid Version=9.0'), 'it is a MARTHE grid file'
    assert 'Field=TMASK' in head

    back = CaptureMask.load_mask(path)
    assert np.array_equal(back.any, cm.any), 'the mask changed on the way to disk'
    assert back.grid.nzone == cm.grid.nzone
    assert back.area_km2() == pytest.approx(cm.area_km2())


def test_save_mask_writes_gigogne_cells_in_the_gigogne_blocks(traj, tmp_path):
    """A gigogne cell must be written in its gigogne block, not the parent's.

    A MARTHE grid file is a sequence of blocks, one per layer and per nested
    grid.  Putting a cell in the wrong block would still read back as a valid
    file, so the file itself is parsed here and its blocks counted against
    what the mask holds.
    """
    cm = traj.build_mask()
    path = cm.save_mask(str(tmp_path / 'blocks.tmask'))

    blocks, cur = [], None
    for line in open(path, encoding='ISO-8859-1'):
        if line.startswith('[Infos]'):
            cur = {'ones': 0}
        elif cur is None:
            continue
        elif line.startswith('Layer='):
            cur['layer'] = int(line.split('=')[1])
        elif line.startswith('Nest_grid='):
            cur['nest'] = int(line.split('=')[1])
        elif line.startswith('[End_Grid]'):
            blocks.append(cur)
            cur = None
        elif line[:1].isdigit():
            f = line.split()
            if f[0] != '0':              # 0 heads the index, x and dx rows
                cur['ones'] += sum(1 for v in f[2:-1] if v == '1')

    counted = {(b['nest'], b['layer']): b['ones'] for b in blocks}
    expected = {(r.grid, r.layer): r.cells
                for r in cm.cells_by_layer().itertuples()}
    assert counted == expected, (
        'the cells of a grid were not written in that grid s own blocks'
    )
    assert sum(counted.values()) == cm.any.sum()


def test_save_mask_by_id(traj, tmp_path):
    """One file per seeding point, each holding only its own cells."""
    cm = traj.build_mask(id=['W01', 'W02'])
    paths = cm.save_mask(str(tmp_path / 'well.tmask'), by_id=True)

    assert len(paths) == 2
    assert [os.path.basename(p) for p in paths] == ['well_W01.tmask',
                                                    'well_W02.tmask']
    one = CaptureMask.load_mask(paths[0])
    assert np.array_equal(one.any, cm.array[0]), 'each file holds one point'
    assert one.any.sum() < cm.any.sum(), 'and not the union'


def test_mask_dataset_is_a_grid_dataset(traj):
    """`to_dataset` gives a Dataset the grid tools can take."""
    cm = traj.build_mask()
    ds = cm.to_dataset()

    assert 'tmask' in ds.data_vars
    assert ds.sizes['zone'] == cm.grid.nzone
    for coord in ('x', 'y', 'dx', 'dy'):
        assert coord in ds.variables, f'{coord} is needed to write the grid'
    assert 'original_dimensions' in ds.attrs, 'the geometry of both grids'
    assert set(np.unique(ds['tmask'].values)) <= {0., 1.}


# ==========================================================================
# the summary table
# ==========================================================================
def test_summary_without_products(fresh):
    """One row per seeding point, describing the run alone."""
    df = fresh.summary()

    assert list(df.index) == KEYS
    assert df['group'].tolist() == GROUPS, 'the G= tag, not the position'
    assert (df['npart'] == NPART).all()
    assert (df['ntraj'] == NPART).all(), 'every particle produced a trajectory'
    assert (df['method'] == 'group').all()
    assert (df['path_m'] > 0).all()
    assert (df['t_max'] < 1e11).all(), 'the travel-time sentinel is left out'
    assert (df['layer'] > 0).all(), (
        'an (X, Y, Z) record states no layer, so it is taken from its paths'
    )
    for absent in ('capture_km2', 'mask_cells', 'mask_km2'):
        assert absent not in df.columns, 'nothing is reported before it is built'


@needs_geo
def test_summary_with_products(fresh):
    """Once built, the zone and the mask are reported beside the run."""
    cz = fresh.build_capture(offset_m=20.)
    cm = fresh.build_mask()
    df = fresh.summary()

    assert (df['capture_method'] == 'envelope').all()
    assert df['capture_km2'].tolist() == pytest.approx(
        cz.gdf.set_index('key').loc[KEYS, 'area_km2'].tolist())
    assert df['mask_cells'].tolist() == cm.array.sum(axis=1).tolist()
    assert df['mask_km2'].tolist() == pytest.approx(
        [cm.area_km2(k) for k in KEYS])


@needs_geo
def test_summary_reports_what_a_product_does_not_cover(fresh):
    """A seeding point outside the built zone is NaN, not silently zero."""
    fresh.build_capture(id='W01')
    df = fresh.summary()

    assert df.loc['W01', 'capture_km2'] > 0
    assert np.isnan(df.loc['W02', 'capture_km2']), (
        'W02 has no zone built, which is not the same as a zone of no area'
    )


def test_summary_subset(fresh):
    assert list(fresh.summary(id=[33, 1]).index) == ['W03', 'W01'], (
        'the rows follow the order asked for'
    )


# ==========================================================================
# plotting
# ==========================================================================
@pytest.fixture(autouse=True, scope='module')
def _agg_backend():
    import matplotlib
    matplotlib.use('Agg')


def test_plot_paths_by_layer(traj):
    """The default map: the pathlines, coloured by the layer they travel in."""
    import matplotlib.pyplot as plt

    fig, ax = traj.plot(basemap=False, color_by='layer', id=[1, 20])

    assert ax.collections, 'the pathlines are drawn'
    assert ax.get_legend() is not None, 'the layers are listed'
    assert ax.get_xlabel() and ax.get_ylabel()
    assert ax.get_aspect() == 1.0, 'a map is drawn to scale'
    plt.close(fig)


def test_plot_by_altitude_adds_a_colorbar(traj):
    """Colouring by z is a continuous ramp, so it gets a colorbar."""
    import matplotlib.pyplot as plt

    fig, _ = traj.plot(basemap=False, color_by='z', id='W01', title='W01')
    assert len(fig.axes) > 1, 'the colorbar has its own axes'
    plt.close(fig)

    fig2, _ = traj.plot(basemap=False, color_by='depth', id='W01')
    assert len(fig2.axes) > 1, "'depth' is still accepted for 'z'"
    plt.close(fig2)


@needs_geo
def test_plot_capture_and_mask(traj, tmp_path):
    """The zone and the mask are drawn once they have been built, and saved."""
    import matplotlib.pyplot as plt

    traj.build_capture(id='W01')
    traj.build_mask(id='W01')
    out = tmp_path / 'map.png'
    fig, ax = traj.plot(capture=True, cz_mask=True, id='W01', basemap=False,
                        base_fontsize=8, save=str(out))

    assert out.exists(), 'the figure is written where asked'
    assert ax.collections, 'the mask cells are drawn'
    plt.close(fig)


def test_plot_mask_of_one_layer(traj):
    """`mask_layer` draws the cells of a single model layer."""
    import matplotlib.pyplot as plt

    traj.build_mask()
    fig, ax = traj.plot(path=False, cz_mask=True, mask_layer=3, basemap=False)
    assert any('layer 3' in (h.get_label() or '') for h in ax.get_legend().legend_handles)
    plt.close(fig)


def test_plot_needs_the_products_first(fresh):
    """Asking for a zone that was never built says so, rather than drawing nothing."""
    with pytest.raises(ValueError, match='build_capture'):
        fresh.plot(capture=True, basemap=False)
    with pytest.raises(ValueError, match='build_mask'):
        fresh.plot(cz_mask=True, basemap=False)


def test_plot_rejects_other_colourings(traj):
    with pytest.raises(ValueError, match='color_by'):
        traj.plot(color_by='speed', basemap=False)


def test_plot_on_given_axes(traj):
    """A caller's axes are used, so maps can be laid out side by side."""
    import matplotlib.pyplot as plt

    fig, axs = plt.subplots(1, 2)
    traj.plot(ax=axs[0], id='W01', basemap=False, legend=False)
    traj.plot(ax=axs[1], id='W02', basemap=False, legend=False)

    assert axs[0].collections and axs[1].collections
    plt.close(fig)
