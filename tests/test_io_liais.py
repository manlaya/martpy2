#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

import pandas as pd
import pytest

from martpy.inputs.mart_liais import (
    MartLiais,
    _build_liais_line,
    read_liais_file,
)


LIAIS_CRAIE = './tests/data/liais_fract/craie_npc.liais'
LIAIS_TRIPLE = './tests/data/liais_fract/triple.liais'
LIAIS_GIGOGNE = './tests/data/liais_fract/triple_gigogne.liais'


@pytest.fixture
def liais_craie():
    return read_liais_file(LIAIS_CRAIE)


@pytest.fixture
def liais_gigogne():
    return read_liais_file(LIAIS_GIGOGNE)


def test_reader_returns_martliais(liais_craie):
    assert isinstance(liais_craie, MartLiais)
    assert isinstance(liais_craie, pd.DataFrame)


def test_reader_columns(liais_craie):
    expected = ['col', 'row', 'layer', 'H', 'B', 'N', 'E', 'S', 'W', 'igrid']
    assert list(liais_craie.columns) == expected


def test_reader_dtypes(liais_craie):
    assert liais_craie['col'].dtype == int
    assert liais_craie['row'].dtype == int
    assert liais_craie['layer'].dtype == int
    assert liais_craie['igrid'].dtype == int
    for direction in ['H', 'B', 'N', 'E', 'S', 'W']:
        assert liais_craie[direction].dtype == bool


def test_reader_row_count(liais_craie):
    # craie_npc.liais has 44 data lines (after the header)
    assert len(liais_craie) == 44


def test_reader_first_row(liais_craie):
    # First data line: ` 141 141   4    1    0`
    # HBNESW chars at positions 13..18 = `   1  ` -> only E is impermeable
    row = liais_craie.iloc[0]
    assert row['col'] == 141
    assert row['row'] == 141
    assert row['layer'] == 4
    assert not row['H']
    assert not row['B']
    assert not row['N']
    assert row['E']
    assert not row['S']
    assert not row['W']
    assert row['igrid'] == 0


def test_reader_multi_direction_row():
    # In triple.liais, row `  78  70   3   1  1  0` has both N and W set
    df = read_liais_file(LIAIS_TRIPLE)
    mask = (df['col'] == 78) & (df['row'] == 70) & (df['layer'] == 3)
    selected = df[mask]
    assert len(selected) == 1
    row = selected.iloc[0]
    assert row['N']
    assert row['W']
    assert not row['H']
    assert not row['B']
    assert not row['E']
    assert not row['S']


def test_reader_gigogne_indices(liais_gigogne):
    # triple_gigogne.liais contains cells in both global (0) and nested (1) grids
    unique_igrids = sorted(liais_gigogne['igrid'].unique())
    assert unique_igrids == [0, 1]
    assert (liais_gigogne['igrid'] == 0).sum() > 0
    assert (liais_gigogne['igrid'] == 1).sum() > 0


def test_reader_top_bottom_in_gigogne(liais_gigogne):
    # Line ` 274 342   2 11      1` has H=1, B=1, igrid=1
    mask = (
        (liais_gigogne['col'] == 274)
        & (liais_gigogne['row'] == 342)
        & (liais_gigogne['layer'] == 2)
    )
    row = liais_gigogne[mask].iloc[0]
    assert row['H']
    assert row['B']
    assert not row['N']
    assert not row['E']
    assert not row['S']
    assert not row['W']
    assert row['igrid'] == 1


def test_writer_round_trip(tmp_path, liais_craie):
    out = tmp_path / 'out.liais'
    liais_craie.write_file(str(out))
    df_re = read_liais_file(str(out))
    assert df_re.equals(liais_craie)


def test_writer_byte_identical(tmp_path):
    # Round-trip should produce a file byte-identical to the input,
    # as long as input has LF line endings (the writer's convention).
    for source in [LIAIS_CRAIE, LIAIS_TRIPLE, LIAIS_GIGOGNE]:
        df = read_liais_file(source)
        out = tmp_path / os.path.basename(source)
        df.write_file(str(out))
        with open(source, encoding='cp1252') as f_in, \
             open(out, encoding='cp1252') as f_out:
            assert f_in.read() == f_out.read(), (
                f'round-trip differs for {source}'
            )


def test_build_liais_line_format():
    # Single E direction, igrid=0 -> reproduces the first row of craie_npc.liais
    line = _build_liais_line(
        col=141, row=141, layer=4,
        H=False, B=False, N=False, E=True, S=False, W=False,
        igrid=0,
    )
    assert line == ' 141 141   4    1    0'
    assert len(line) == 22


def test_build_liais_line_multi_direction():
    # H + B together, gigogne 1
    line = _build_liais_line(
        col=274, row=342, layer=2,
        H=True, B=True, N=False, E=False, S=False, W=False,
        igrid=1,
    )
    assert line == ' 274 342   2 11      1'


def test_reader_handles_crlf(tmp_path, liais_craie):
    # Reader should accept files with CRLF line endings (MARTHE default on Windows)
    out = tmp_path / 'crlf.liais'
    with open(LIAIS_CRAIE, encoding='cp1252') as f:
        content = f.read()
    with open(out, 'w', encoding='cp1252', newline='') as f:
        f.write(content.replace('\n', '\r\n'))
    df = read_liais_file(str(out))
    assert df.equals(liais_craie)


def test_invalid_line_raises(tmp_path):
    bad = tmp_path / 'bad.liais'
    bad.write_text(' Col Lig Cou;HBNESW  #\nnot a valid line\n', encoding='cp1252')
    with pytest.raises(ValueError, match='Cannot parse'):
        read_liais_file(str(bad))


def main():
    test_build_liais_line_multi_direction()
    df = read_liais_file(LIAIS_CRAIE)
    test_reader_returns_martliais(df)
    test_reader_columns(df)
    test_reader_dtypes(df)
    test_reader_row_count(df)
    test_reader_first_row(df)
    test_reader_multi_direction_row()
    test_reader_gigogne_indices(read_liais_file(LIAIS_GIGOGNE))


if __name__ == '__main__':
    main()
