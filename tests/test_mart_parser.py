#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from martpy.inputs._mart_parser import (
    _parse_mart_file,
    _write_mart_file,
    _parse_parameter_line,
    BLOCK_MART
)

from martpy.inputs.io_utils import _build_parameter_line


MART_FILE = './tests/data/mart_hallue/hallue_for_test.mart'


def test_parse_parameter_line():
    # line = '  /PERM_LIT_RIVI/TRONCON   A=      *T=      *V=         *;'
    line = '  /DEBIT/COUCHE            C=  1:2  V=         *;'
    expected = {'DEBIT': {'mode': 'COUCHE', 'grid_id': 0, 'layer': [1, 2], 'value': '*'}}
    res = _parse_parameter_line(line)
    assert res == expected, 'Error while parsing parameter line'


def test_reader():
    reversed_block_mart = {v: k for k, v in BLOCK_MART.items()}
    verif_dict_init = {}

    dict_res = _parse_mart_file(MART_FILE, verbose=True)
    #dict_res['init_parameters'].get('PERM_LIT_RIVI')
    assert list(dict_res.keys()) == [x for x in reversed_block_mart.keys() if x != 'dummy'], \
        'Error while parsing block parameters'
    
    return dict_res


def test_build_line():
    test = {'grid_id': 0, 'layer': 1, 'value': '*'}
    test_str = _build_parameter_line('DEBIT', 'COUCHE', **test)
    return


def test_writer(dict_value, mart_file):
    dict_value['toto'] = 1
    _write_mart_file(dict_value, mart_file)
    tmp = _parse_mart_file()
    #assert tmp['toto'] == 1, 'Error with writer/re parsed.'
    return None


def test():
    test_parse_parameter_line()
    res_reader = test_reader()
    # test_writer(res_reader, './tests/data/tmp_outputs/test_writer.mart')


if __name__ == '__main__':
    test()
