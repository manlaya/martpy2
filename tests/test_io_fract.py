#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import pytest

from martpy.inputs.mart_fract import (
    MartFract,
    _is_all_fractures_flag,
    _is_comment,
    _match_coords_mode,
    _match_fracture_type,
    _normalise_coord_file,
    _parse_coord_line,
    _parse_param_line,
    read_fract_file,
)


FRACT_FILE = './tests/data/liais_fract/Failles_NPC.fract'
ALL_TYPES_FILE = './tests/data/liais_fract/all_fracture_types.fract'
BLN_ALL_FILE = './tests/data/liais_fract/bln_all_fractures.fract'


@pytest.fixture
def fract():
    return read_fract_file(FRACT_FILE)


@pytest.fixture
def all_types():
    return read_fract_file(ALL_TYPES_FILE)


@pytest.fixture
def bln_all():
    return read_fract_file(BLN_ALL_FILE)


# ---------------------------------------------------------------------------
# Failles_NPC.fract : four semi-permeable fractures (real-world fixture)
# ---------------------------------------------------------------------------

def test_reader_returns_martfract(fract):
    assert isinstance(fract, MartFract)


def test_reader_title(fract):
    assert fract.title == 'Failles majeures NPC'


def test_reader_fracture_count(fract):
    assert len(fract) == 4


def test_reader_all_semi_perm(fract):
    for f in fract.fractures:
        assert f['type'] == 'semi_perm'
        assert f['coord_mode'] == 'inline'


def test_reader_fracture_parameters(fract):
    # The fixture declares semi-permeable fractures, so the doc-compliant
    # parameter is "Perméabilité" (normalised to 'permeability').
    f0 = fract.fractures[0]
    assert f0['params']['permeability'] == 0.0
    assert f0['params']['contact_percentage'] == 100.0
    assert f0['params']['top_layer'] == 9
    assert f0['params']['bottom_layer'] == 9

    f1 = fract.fractures[1]
    assert f1['params']['permeability'] == 1e-10
    assert f1['params']['top_layer'] == 6
    assert f1['params']['bottom_layer'] == 9


def test_reader_layer_types_are_int(fract):
    for f in fract.fractures:
        assert isinstance(f['params']['top_layer'], int)
        assert isinstance(f['params']['bottom_layer'], int)


def test_reader_coordinates_shape(fract):
    expected_lengths = [4, 5, 7, 6]
    assert [len(f['coordinates']) for f in fract.fractures] == expected_lengths


def test_reader_coordinates_dataframe(fract):
    coords = fract.fractures[0]['coordinates']
    assert isinstance(coords, pd.DataFrame)
    assert list(coords.columns) == ['x', 'y']
    assert coords.iloc[0]['x'] == 611156.84
    assert coords.iloc[0]['y'] == 2609658.22


def test_reader_skips_commented_coordinates(fract):
    # The last fracture has two commented-out coordinates at the very end
    # that must NOT be read.
    last = fract.fractures[-1]
    assert len(last['coordinates']) == 6


# ---------------------------------------------------------------------------
# all_fracture_types.fract : doc Figure 99 (p.201), five fractures of all types
# ---------------------------------------------------------------------------

def test_all_types_title(all_types):
    assert all_types.title == 'Cinq fractures de tous types'


def test_all_types_count(all_types):
    assert len(all_types) == 5


def test_all_types_sequence(all_types):
    types = [f['type'] for f in all_types.fractures]
    assert types == ['semi_perm', 'imperm', 'conduct', 'semi_perm', 'semi_perm']


def test_all_types_semi_perm_full_params(all_types):
    # Fracture 1: permeability + contact percentage + both layers
    f = all_types.fractures[0]
    assert f['params'] == {
        'permeability': 9.278e-3,
        'contact_percentage': 50.0,
        'top_layer': 2,
        'bottom_layer': 7,
    }
    assert f['coord_mode'] == 'inline'
    assert len(f['coordinates']) == 6


def test_all_types_impermeable_has_no_specific_param(all_types):
    # Fracture 2: impermeable -> only the (common) layer parameters
    f = all_types.fractures[1]
    assert f['type'] == 'imperm'
    assert f['params'] == {'top_layer': 1, 'bottom_layer': 1}
    assert 'permeability' not in f['params']
    assert 'transmissivity' not in f['params']


def test_all_types_conductive_uses_transmissivity_and_bln(all_types):
    # Fracture 3: conductive, English key "Transmissivity", coords in a .bln
    f = all_types.fractures[2]
    assert f['type'] == 'conduct'
    assert f['params']['transmissivity'] == 1e5
    assert f['params']['top_layer'] == 0
    assert f['params']['bottom_layer'] == 0
    assert f['coord_mode'] == 'file'
    assert f['coord_file'] == 'Monofrac_5_Coord_Fract.bln'
    assert f['all_fractures_from_file'] is False
    # In "reference only" mode the .bln is not read.
    assert len(f['coordinates']) == 0


def test_all_types_partial_params(all_types):
    # Fracture 4: only permeability, coords delegated via "Suite"
    f3 = all_types.fractures[3]
    assert f3['params'] == {'permeability': 6e-3}
    assert f3['coord_mode'] == 'file'
    assert f3['coord_file'] == 'Suite'

    # Fracture 5: only contact percentage, inline coords
    f4 = all_types.fractures[4]
    assert f4['params'] == {'contact_percentage': 5.0}
    assert f4['coord_mode'] == 'inline'
    assert len(f4['coordinates']) == 2


# ---------------------------------------------------------------------------
# bln_all_fractures.fract : doc Figure 102 (p.203), <Toutes les Fractures...>
# ---------------------------------------------------------------------------

def test_bln_all_count_and_types(bln_all):
    assert len(bln_all) == 2
    assert [f['type'] for f in bln_all.fractures] == ['semi_perm', 'imperm']


def test_bln_all_flag_and_files(bln_all):
    f0, f1 = bln_all.fractures
    assert f0['coord_mode'] == 'file'
    assert f0['coord_file'] == 'Monofrac_10_Fract_Semi_Perm.bln'
    assert f0['all_fractures_from_file'] is True
    assert f0['params'] == {'permeability': 6e-3}

    assert f1['coord_mode'] == 'file'
    assert f1['coord_file'] == 'Monofrac_15_Failles_Etanches.bln'
    assert f1['all_fractures_from_file'] is True
    # impermeable + file mode -> no parameter at all
    assert f1['params'] == {}


# ---------------------------------------------------------------------------
# Round-trip (semantic) across all types and both coordinate modes
# ---------------------------------------------------------------------------

def _assert_same_fracture(original, written):
    assert original['type'] == written['type']
    assert original['coord_mode'] == written['coord_mode']
    assert original['coord_file'] == written['coord_file']
    assert original['all_fractures_from_file'] == written['all_fractures_from_file']
    assert original['params'] == written['params']
    assert len(original['coordinates']) == len(written['coordinates'])
    # Empty coordinates (file mode) have nothing to compare numerically.
    if len(original['coordinates']) > 0:
        np.testing.assert_allclose(
            original['coordinates'].values,
            written['coordinates'].values,
        )


def test_round_trip_all_types(tmp_path, all_types):
    out = tmp_path / 'out.fract'
    all_types.write_file(str(out))
    re_read = read_fract_file(str(out))

    assert re_read.title == all_types.title
    assert len(re_read) == len(all_types)
    for original, written in zip(all_types.fractures, re_read.fractures, strict=True):
        _assert_same_fracture(original, written)


def test_round_trip_bln_all(tmp_path, bln_all):
    out = tmp_path / 'out.fract'
    bln_all.write_file(str(out))
    re_read = read_fract_file(str(out))

    assert len(re_read) == len(bln_all)
    for original, written in zip(bln_all.fractures, re_read.fractures, strict=True):
        _assert_same_fracture(original, written)


def test_round_trip_failles_npc(tmp_path, fract):
    out = tmp_path / 'out.fract'
    fract.write_file(str(out))
    re_read = read_fract_file(str(out))

    assert len(re_read) == len(fract)
    for original, written in zip(fract.fractures, re_read.fractures, strict=True):
        _assert_same_fracture(original, written)


# ---------------------------------------------------------------------------
# Writer : French canonical keywords for every type / coordinate mode
# ---------------------------------------------------------------------------

def test_writer_type_keywords(tmp_path, all_types):
    out = tmp_path / 'out.fract'
    all_types.write_file(str(out))
    with open(out, encoding='cp1252') as f:
        content = f.read()
    assert content.count('[Fracture Semi-Perméable]') == 3
    assert content.count('[Fracture Imperméable]') == 1
    assert content.count('[Fracture Conductrice]') == 1


def test_writer_coordinate_keywords(tmp_path, all_types):
    out = tmp_path / 'out.fract'
    all_types.write_file(str(out))
    with open(out, encoding='cp1252') as f:
        content = f.read()
    assert content.count('[Liste coordonnées]') == 3
    assert content.count('[Fichier coordonnées]') == 2
    assert 'Suite' in content


def test_writer_param_keywords_are_french(tmp_path, all_types):
    out = tmp_path / 'out.fract'
    all_types.write_file(str(out))
    with open(out, encoding='cp1252') as f:
        content = f.read()
    # The English "Transmissivity" key is emitted back in French.
    assert content.count('Transmissivité =') == 1
    assert content.count('Perméabilité =') == 2
    assert content.count('Pourcentage_Contact =') == 2


def test_writer_all_fractures_flag(tmp_path, bln_all):
    out = tmp_path / 'out.fract'
    bln_all.write_file(str(out))
    with open(out, encoding='cp1252') as f:
        content = f.read()
    assert content.count('<Toutes les Fractures du Fichier>') == 2


# ---------------------------------------------------------------------------
# Construction from user data
# ---------------------------------------------------------------------------

def test_empty_martfract_constructor():
    mf = MartFract()
    assert mf.title == 'Marthe fractures'
    assert mf.fractures == []
    assert len(mf) == 0


def test_martfract_from_user_data_inline(tmp_path):
    mf = MartFract(
        title='User fractures',
        fractures=[
            {
                'type': 'semi_perm',
                'params': {
                    'permeability': 2.5e-9,
                    'contact_percentage': 80.0,
                    'top_layer': 1,
                    'bottom_layer': 3,
                },
                'coord_mode': 'inline',
                'coordinates': pd.DataFrame({'x': [100.0, 200.0], 'y': [10.0, 20.0]}),
                'coord_file': None,
                'all_fractures_from_file': False,
            }
        ],
    )
    out = tmp_path / 'user.fract'
    mf.write_file(str(out))
    re_read = read_fract_file(str(out))

    assert re_read.title == 'User fractures'
    assert len(re_read) == 1
    f = re_read.fractures[0]
    assert f['type'] == 'semi_perm'
    assert f['params'] == {
        'permeability': 2.5e-9,
        'contact_percentage': 80.0,
        'top_layer': 1,
        'bottom_layer': 3,
    }
    assert list(f['coordinates']['x']) == [100.0, 200.0]
    assert list(f['coordinates']['y']) == [10.0, 20.0]


def test_martfract_from_user_data_file_mode(tmp_path):
    mf = MartFract(
        title='Conductive from bln',
        fractures=[
            {
                'type': 'conduct',
                'params': {'transmissivity': 1e5},
                'coord_mode': 'file',
                'coordinates': pd.DataFrame(columns=['x', 'y']),
                'coord_file': 'myfrac.bln',
                'all_fractures_from_file': True,
            }
        ],
    )
    out = tmp_path / 'user.fract'
    mf.write_file(str(out))
    re_read = read_fract_file(str(out))

    f = re_read.fractures[0]
    assert f['type'] == 'conduct'
    assert f['params'] == {'transmissivity': 1e5}
    assert f['coord_mode'] == 'file'
    assert f['coord_file'] == 'myfrac.bln'
    assert f['all_fractures_from_file'] is True


# ---------------------------------------------------------------------------
# Helper-level unit tests
# ---------------------------------------------------------------------------

def test_is_comment_helpers():
    assert _is_comment('# comment')
    assert _is_comment('! comment')
    assert _is_comment('* comment')
    assert _is_comment('<< comment')
    assert _is_comment('   ')
    assert not _is_comment('[Fracture Semi-Perméable]')
    assert not _is_comment('Perméabilité = 0')
    # The "all fractures" flag uses a single '<' and is NOT a comment.
    assert not _is_comment('<Toutes les Fractures du Fichier>')


def test_match_fracture_type():
    assert _match_fracture_type('[Fracture Semi-Perméable]') == 'semi_perm'
    assert _match_fracture_type('   [Fracture Semi-Perméable]   ') == 'semi_perm'
    assert _match_fracture_type('[Semi-pervious Fracture]') == 'semi_perm'
    assert _match_fracture_type('[Fracture Imperméable]') == 'imperm'
    assert _match_fracture_type('[Fracture Étanche]') == 'imperm'
    assert _match_fracture_type('[Insulating Fracture]') == 'imperm'
    assert _match_fracture_type('[Fracture Conductrice]') == 'conduct'
    assert _match_fracture_type('[Conductive Fracture]') == 'conduct'
    assert _match_fracture_type('[Liste coordonnées]') is None


def test_match_coords_mode():
    assert _match_coords_mode('[Liste coordonnées]') == 'inline'
    assert _match_coords_mode('[List Fracture coordinates]') == 'inline'
    assert _match_coords_mode('[Fichier coordonnées]') == 'file'
    assert _match_coords_mode('[File fracture coordinates]') == 'file'
    assert _match_coords_mode('[Fracture Semi-Perméable]') is None


def test_is_all_fractures_flag():
    assert _is_all_fractures_flag('<Toutes les Fractures du Fichier>')
    assert _is_all_fractures_flag('<All_Fractures_from_File>')
    assert not _is_all_fractures_flag('Monofrac.bln')


def test_normalise_coord_file():
    assert _normalise_coord_file('Suite') == 'Suite'
    assert _normalise_coord_file('Continue') == 'Suite'
    assert _normalise_coord_file('Monofrac.bln') == 'Monofrac.bln'


def test_parse_param_line():
    assert _parse_param_line('Perméabilité= 9.278e-3') == ('permeability', '9.278e-3')
    assert _parse_param_line('Transmissivité = 0') == ('transmissivity', '0')
    assert _parse_param_line('Conductance = 5') == ('transmissivity', '5')
    assert _parse_param_line('Couche_Haut = 9') == ('top_layer', '9')
    assert _parse_param_line('Higher_Layer = 2') == ('top_layer', '2')
    assert _parse_param_line('Pourcentage_Contact= 50') == ('contact_percentage', '50')
    # Unknown keys are preserved verbatim (no silent data loss).
    assert _parse_param_line('Unknown_key = 42') == ('Unknown_key', '42')
    assert _parse_param_line('not a param line') is None


def test_parse_coord_line():
    assert _parse_coord_line('611156.84 2609658.22') == (611156.84, 2609658.22)
    assert _parse_coord_line('   100  200   ') == (100.0, 200.0)
    assert _parse_coord_line('not coords') is None
    assert _parse_coord_line('only_one_value') is None
