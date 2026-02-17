#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from martpy.inputs.mart_param import MartheParams
from martpy.inputs._mart_parser import (
    _parse_mart_file,
    _write_mart_file,
    BLOCK_MART
)


MART_FILE = './tests/data/mart_hallue/hallue_for_test.mart'


def test_reader():
    reversed_block_mart = {v: k for k, v in BLOCK_MART.items()}
    # verif_dict_init = {}

    dict_res = _parse_mart_file(MART_FILE, verbose=True)
    #dict_res['init_parameters'].get('PERM_LIT_RIVI')
    assert list(dict_res.keys()) == [x for x in reversed_block_mart.keys() if x != 'dummy'], \
        'Error while parsing block parameters'


# TODO: check format when writing list of cell, layer, etc.: use same spacing as in MART file?
# when 'X:Y' format is used, marthe does not align right but center. Does not seems critical though
# (test with winmarthe of reading right align  1:2 or center  1:2 gives same result)
def test_writer():
    fout = './tests/data/tmp_outputs/test_writer.mart'
    dict_value = _parse_mart_file(MART_FILE)
    dict_value['outputs']['gen_list'] = 1
    # dict_value['toto'] = 1
    _write_mart_file(dict_value, fout)
    tmp = _parse_mart_file(fout)
    assert tmp['outputs']['gen_list'] == 1, 'Error with writer/re parsed.'


def test_parse_modin():
    mart_file = './tests/data/modin/MOD82_Safran_BV_Ext_1958-2021.mart'
    dict_res = _parse_mart_file(mart_file)
    init_par = dict_res['init_parameters']
    assert 'MODIFIC' not in init_par.keys(), \
        "MODIFIC not merged with init parameters"
    test2 = init_par.get('NZON_RIV_EXT')[0].get('external_file') is not None
    # verif que external_file est bien stocké
    assert test2, 'Error while parsing external file'


def test_from_tpl():
    mart = MartheParams.from_template()
    assert len(mart.get_param_groups()) == 21, 'Wrong block param number from template'


def test_mart_class_attrs():
    mart = MartheParams.from_file(MART_FILE)
    assert hasattr(mart, 'groups')
    mart.get_param_groups()
    mart.get_param_keys()
    print(mart)

    mart = MartheParams.from_template()
    assert hasattr(mart, 'groups')
    mart.get_param_groups()
    mart.get_param_keys()
    print(mart)


def test_get_parameter_help_method():
    mart = MartheParams.from_template()
    help = mart.get_param_help(group='outputs', key='gen_list', lang='en')
    assert help['outputs']['gen_list'].keys() == {'default', 'type', 'description'}, \
        'Error while getting parameter help from MartheParams class'


# def test_param_uk():
#     MART_FILE_UK = './tests/data/mart_uk/mart_uk_files.mart'
#     mart = MartheParams.from_file(MART_FILE_UK)
#     print(mart)


def main():
    # test_parse_parameter_line()
    # test_reader()
    # test_get_parameter_help()
    # test_parse_modin()
    # test_writer()
    test_from_tpl()


if __name__ == '__main__':
    main()
