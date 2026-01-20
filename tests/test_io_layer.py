#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from martpy.inputs.mart_layer import read_layer, _write_layer


def test_single_layer():
    file_layer = 'tests/data/mart_hallue/hallue.layer'
    df, dict_geom = read_layer(file_layer)
    assert len(df) == 1, 'layer reader failed: wrong number of layers'


def test_multi_layer():
    file_layer = 'tests/data/mart_72/Craie_NPC.layer'
    df, dict_geom = read_layer(file_layer)
    assert len(df) == 8, 'layer reader failed: wrong number of layers'


def test_writer_layer():
    file_layer = 'tests/data/mart_72/Craie_NPC.layer'
    df, dict_geom = read_layer(file_layer)
    _write_layer(df, dict_geom, 'tests/data/tmp_outputs/toto.layer')
    _write_layer(df, dict_geom, 'tests/data/tmp_outputs/toto_uk.layer', lang='en')

def test_uk_reader():
    file_layer = 'tests/data/mart_uk/mart_uk_files.layer'
    df, dict_geom = read_layer(file_layer)
    assert len(df) == 1, 'layer reader failed: wrong number of layers'

def main():
    test_single_layer()
    test_multi_layer()
    test_writer_layer()


if __name__ == '__main__':
    main()