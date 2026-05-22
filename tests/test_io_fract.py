#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import pytest

from martpy.inputs.mart_fract import (
    MartFract,
    _is_comment,
    _is_coords_header,
    _is_fracture_header,
    _parse_coord_line,
    _parse_param_line,
    read_fract_file,
)


FRACT_FILE = './tests/data/liais_fract/Failles_NPC.fract'


@pytest.fixture
def fract():
    return read_fract_file(FRACT_FILE)


def test_reader_returns_martfract(fract):
    assert isinstance(fract, MartFract)


def test_reader_title(fract):
    assert fract.title == 'Failles majeures NPC'


def test_reader_fracture_count(fract):
    # Four [Fracture Semi-Perméable] blocks in the fixture
    assert len(fract) == 4


def test_reader_fracture_parameters(fract):
    # First fracture (Marqueffles part 1 Bruay)
    f0 = fract.fractures[0]
    assert f0['transmissivity'] == 0.0
    assert f0['contact_percentage'] == 100.0
    assert f0['top_layer'] == 9
    assert f0['bottom_layer'] == 9

    # Second fracture has scientific-notation transmissivity
    f1 = fract.fractures[1]
    assert f1['transmissivity'] == 1e-10
    assert f1['top_layer'] == 6
    assert f1['bottom_layer'] == 9


def test_reader_layer_types_are_int(fract):
    for f in fract.fractures:
        assert isinstance(f['top_layer'], int)
        assert isinstance(f['bottom_layer'], int)


def test_reader_coordinates_shape(fract):
    # number of (x, y) points per fracture in the fixture
    expected_lengths = [4, 5, 7, 6]
    assert [len(f['coordinates']) for f in fract.fractures] == expected_lengths


def test_reader_coordinates_dataframe(fract):
    coords = fract.fractures[0]['coordinates']
    assert isinstance(coords, pd.DataFrame)
    assert list(coords.columns) == ['x', 'y']
    # First point of the first fracture
    assert coords.iloc[0]['x'] == 611156.84
    assert coords.iloc[0]['y'] == 2609658.22


def test_reader_skips_commented_coordinates(fract):
    # The last fracture has two commented-out coordinates at the very end
    # ("# 620931.45 ..." and "# 622356.43 ...") that must NOT be read.
    last = fract.fractures[-1]
    assert len(last['coordinates']) == 6


def test_writer_round_trip(tmp_path, fract):
    out = tmp_path / 'out.fract'
    fract.write_file(str(out))
    re_read = read_fract_file(str(out))

    assert re_read.title == fract.title
    assert len(re_read) == len(fract)
    for original, written in zip(fract.fractures, re_read.fractures, strict=True):
        assert original['transmissivity'] == pytest.approx(written['transmissivity'])
        assert original['contact_percentage'] == pytest.approx(
            written['contact_percentage']
        )
        assert original['top_layer'] == written['top_layer']
        assert original['bottom_layer'] == written['bottom_layer']
        np.testing.assert_allclose(
            original['coordinates'].values,
            written['coordinates'].values,
        )


def test_writer_creates_expected_headers(tmp_path, fract):
    out = tmp_path / 'out.fract'
    fract.write_file(str(out))
    with open(out, encoding='cp1252') as f:
        content = f.read()
    assert content.startswith('Failles majeures NPC')
    assert '--- Fin du texte libre ---' in content
    assert content.count('[Fracture Semi-Perméable]') == 4
    assert content.count('[Liste coordonnées]') == 4


def test_writer_writes_each_param_key(tmp_path, fract):
    out = tmp_path / 'out.fract'
    fract.write_file(str(out))
    with open(out, encoding='cp1252') as f:
        content = f.read()
    # Each fracture writes the 4 parameter lines in French
    for key in ['Transmissivité', 'Pourcentage_Contact', 'Couche_Haut', 'Couche_Bas']:
        assert content.count(f'{key} =') == 4


def test_empty_martfract_constructor():
    mf = MartFract()
    assert mf.title == 'Marthe fractures'
    assert mf.fractures == []
    assert len(mf) == 0


def test_martfract_from_user_data(tmp_path):
    mf = MartFract(
        title='User fractures',
        fractures=[
            {
                'transmissivity': 2.5e-9,
                'contact_percentage': 80.0,
                'top_layer': 1,
                'bottom_layer': 3,
                'coordinates': pd.DataFrame(
                    {'x': [100.0, 200.0], 'y': [10.0, 20.0]}
                ),
            }
        ],
    )
    out = tmp_path / 'user.fract'
    mf.write_file(str(out))
    re_read = read_fract_file(str(out))
    assert re_read.title == 'User fractures'
    assert len(re_read) == 1
    f = re_read.fractures[0]
    assert f['transmissivity'] == 2.5e-9
    assert f['contact_percentage'] == 80.0
    assert f['top_layer'] == 1
    assert f['bottom_layer'] == 3
    assert list(f['coordinates']['x']) == [100.0, 200.0]
    assert list(f['coordinates']['y']) == [10.0, 20.0]


def test_is_comment_helpers():
    assert _is_comment('# comment')
    assert _is_comment('! comment')
    assert _is_comment('* comment')
    assert _is_comment('<< comment')
    assert _is_comment('   ')
    assert not _is_comment('[Fracture Semi-Perméable]')
    assert not _is_comment('Transmissivité = 0')


def test_is_fracture_header_helpers():
    assert _is_fracture_header('[Fracture Semi-Perméable]')
    assert _is_fracture_header('   [Fracture Semi-Perméable]   ')
    assert not _is_fracture_header('[Liste coordonnées]')


def test_is_coords_header_helpers():
    assert _is_coords_header('[Liste coordonnées]')
    assert not _is_coords_header('[Fracture Semi-Perméable]')


def test_parse_param_line():
    assert _parse_param_line('Transmissivité = 0') == ('transmissivity', '0')
    assert _parse_param_line('Couche_Haut = 9') == ('top_layer', '9')
    assert _parse_param_line('Pourcentage_Contact = 100') == (
        'contact_percentage', '100',
    )
    assert _parse_param_line('Unknown_key = 42') is None
    assert _parse_param_line('not a param line') is None


def test_parse_coord_line():
    assert _parse_coord_line('611156.84 2609658.22') == (611156.84, 2609658.22)
    assert _parse_coord_line('   100  200   ') == (100.0, 200.0)
    assert _parse_coord_line('not coords') is None
    assert _parse_coord_line('only_one_value') is None


def main():
    fract = read_fract_file(FRACT_FILE)
    test_reader_returns_martfract(fract)
    test_reader_title(fract)
    test_reader_fracture_count(fract)
    test_reader_fracture_parameters(fract)
    test_reader_coordinates_shape(fract)
    test_reader_skips_commented_coordinates(fract)


if __name__ == '__main__':
    main()
