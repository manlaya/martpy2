#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

from martpy.inputs._mart_parser import (
    _parse_mart_file,
    _write_mart_file,
    get_parameter_help,
    BLOCK_MART
)

from martpy.inputs.io_utils import (
    _build_parameter_line,
    _parse_parameter_line,
    _parse_parameter_block
)


MART_FILE = './tests/data/mart_hallue/hallue_for_test.mart'


def test_parse_parameter_line():
    line = '  /DEBIT/COUCHE            C=  1:2  V=         *;'
    expected = {'DEBIT': {'mode': 'COUCHE', 'grid_id': 0, 'layer': [1, 2], 'value': '*'}}
    res = _parse_parameter_line(line)
    assert res == expected, 'Error while parsing parameter line by layer'

    line = '  /EMMAG_CAPT/MAILLE       C=      *L=      2P=      1V=        12;'
    res = _parse_parameter_line(line)['EMMAG_CAPT']
    assert res['mode'] == 'MAILLE', 'Error while parsing mode maille'
    assert res['grid_id'] == 0, 'Error while parsing grid id'
    assert res['col'] == '*', 'Error while parsing col'
    assert res['row'] == 2, 'Error while parsing row'
    assert res['layer'] == 1, 'Error while parsing layer'
    assert res['value'] == 12, 'Error while parsing value'

    line = '  /EMMAG_LIBR/LIST_MAIL    N: tata.emmli <Init_a_Zero> <X_Y_C> <Moyenne> <Keep_9999>'
    res = _parse_parameter_line(line)['EMMAG_LIBR']
    assert res['file'] == 'tata.emmli', 'Error while parsing list mail file'
    assert res['opt_list_mail'] == ['Init_a_Zero', 'X_Y_C', 'Moyenne', 'Keep_9999'], \
        'Error while parsing list mail options'

    line = '  /ALT_SEUIL_LAC/LAC_EXUT  L=      *A=      0V=         *;'
    res = _parse_parameter_line(line)['ALT_SEUIL_LAC']
    assert res['mode'] == 'LAC_EXUT', 'Error while parsing mode lac exut'
    assert res['lake'] == '*', 'Error while parsing lake'
    assert res['afluent'] == 0, 'Error while parsing afluent'
    assert res['value'] == '*', 'Error while parsing value'

    line = '  /PERM_LIT_RIVI/TRONCON   A=      *T=      *V=         *;'
    res = _parse_parameter_line(line)['PERM_LIT_RIVI']
    assert res['mode'] == 'TRONCON', 'Error while parsing mode troncon'
    assert res['afluent'] == '*', 'Error while parsing afluent'
    assert res['tronc'] == '*', 'Error while parsing tronc'
    assert res['value'] == '*', 'Error while parsing value'

    line = '  /TEST/EDITION        I=  2;'
    res = _parse_parameter_line(line)['TEST']
    assert res['mode'] == 'EDITION', 'Error while parsing mode edition'
    assert res['edit'] == 2, 'Error while parsing edit'

    line = '  /EMMAG_LIBR/ZONE_GEO     Z=      1V=     1.271;'
    res = _parse_parameter_line(line)['EMMAG_LIBR']
    assert res['mode'] == 'ZONE_GEO', 'Error while parsing mode zone geo'
    assert res['zone'] == 1, 'Error while parsing zone'
    assert abs(res['value'] - 1.271) < 1e-6, 'Error while parsing value'


def test_parse_block_param():
    with open(MART_FILE, mode='r', encoding='ISO-8859-1') as f:
        lines = f.read()
    istart = re.search('Initialisation avant calcul', lines).start()
    lines = lines[istart:].split('\n')
    d = _parse_parameter_block(lines)
    for k, v in d.items():
        for val in v:
            print(k, val)
            assert 'mode' in val.keys(), 'Error while parsing mode for {}-{}'.format(k, val)


def test_reader():
    reversed_block_mart = {v: k for k, v in BLOCK_MART.items()}
    # verif_dict_init = {}

    dict_res = _parse_mart_file(MART_FILE, verbose=True)
    #dict_res['init_parameters'].get('PERM_LIT_RIVI')
    assert list(dict_res.keys()) == [x for x in reversed_block_mart.keys() if x != 'dummy'], \
        'Error while parsing block parameters'


def test_get_parameter_help():
    dict_res = _parse_mart_file(MART_FILE, verbose=True)
    res = get_parameter_help('max_num_drains')
    assert res is not None, 'Error while getting parameter help'


def test_build_line():
    test = {'grid_id': 0, 'layer': 1, 'value': '*'}
    test_str = _build_parameter_line('DEBIT', 'COUCHE', **test)
    expected = '  /DEBIT/COUCHE            C=      1V=         *;'
    assert test_str == expected, 'Error while building parameter line'


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


def main():
    test_parse_parameter_line()
    test_reader()
    test_get_parameter_help()
    test_parse_modin()
    test_writer()


if __name__ == '__main__':
    main()
