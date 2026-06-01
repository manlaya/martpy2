#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

from martpy.inputs._io_utils import (
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
    assert res['file_path'] == 'tata.emmli', 'Error while parsing list mail file'
    # assert res['opt_list_mail'] == ['Init_a_Zero', 'X_Y_C', 'Moyenne', 'Keep_9999'], \
    assert res['opt_list_mail'] == ['init_zero', 'xyc', 'mean', 'keep_9999'], \
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

    line = '  /DEBIT/EDITION           *= 1;V= 0;L= 0;S= 0;Z= 0;'
    res = _parse_parameter_line(line)['DEBIT']
    assert res['mode'] == 'EDITION', 'Error while parsing mode edition'
    assert res['edit'] == 1, 'Error while parsing edit'

    line = ' 1/EMMAG_LIBR/ZONE_GEO     Z=      1V=     1.271;'
    res = _parse_parameter_line(line)['EMMAG_LIBR']
    assert res['mode'] == 'ZONE_GEO', 'Error while parsing mode zone geo'
    assert res['zone'] == 1, 'Error while parsing zone'
    assert abs(res['value'] - 1.271) < 1e-6, 'Error while parsing value'
    assert res['grid_id'] == 1, 'Error while parsing grid id'

    line = '  /CALCUL_HDYNAM/ACTION    I= 1;'
    res = _parse_parameter_line(line)['CALCUL_HDYNAM']
    assert res['mode'] == 'ACTION'
    assert res['value'] == 1

    line = '  /CALCUL_HDYNAM/ACTION    I=-1;'
    res = _parse_parameter_line(line)['CALCUL_HDYNAM']
    assert res['mode'] == 'ACTION'
    assert res['value'] == -1

    line = '  /T_1/2_TARIS_1/ZONE_SOL  Z=    132V=5.4483E+01;'
    res = _parse_parameter_line(line)
    assert res['T_1/2_TARIS_1']['mode'] == 'ZONE_SOL', 'Error while parsing mode zone sol'
    assert res['T_1/2_TARIS_1']['zone'] == 132, 'Error while parsing zone'
    assert abs(res['T_1/2_TARIS_1']['value'] - 54.483) < 1e-6, 'Error while parsing value'

    line = '  /OIL_HYDR_HEAD/ZONE_GEO/FIX=NAQ;Z=  1:2  V=         3;'
    res = _parse_parameter_line(line)
    assert res['OIL_HYDR_HEAD']['mode'] == 'ZONE_GEO', 'Error while parsing mode geo zone 2'
    assert res['OIL_HYDR_HEAD']['grid_id'] == 0, 'Error while parsing grid id'
    assert res['OIL_HYDR_HEAD']['fix'] == 'NAQ', 'Error while parsing fix mode'
    assert res['OIL_HYDR_HEAD']['zone'] == [1, 2], 'Error while parsing zone'
    assert res['OIL_HYDR_HEAD']['value'] == 3, 'Error while parsing value'

    line = "/PERMEAB/ZONE_GEO        Z=      102V=     TO_CALIB;"
    res = _parse_parameter_line(line)
    assert res['PERMEAB']['mode'] == 'ZONE_GEO', 'Error while parsing mode geo zone'
    assert res['PERMEAB']['zone'] == 102, 'Error while parsing zone'
    assert res['PERMEAB']['value'] == 'TO_CALIB', 'Error while parsing value'

    line = "  /CALCUL_HDYNAM/ACTION    I= 2; File= ./_calcul_hdynam_mensuel_1982"
    res = _parse_parameter_line(line)
    assert res['CALCUL_HDYNAM']['mode'] == 'ACTION', 'Error while parsing mode'
    assert res['CALCUL_HDYNAM']['value'] == 2, 'Error while parsing value'
    assert res['CALCUL_HDYNAM']['transient_file_path'] == './_calcul_hdynam_mensuel_1982', 'Error while parsing file'

    line = '  /DEBIT/MAILLE            C=     37L=     15P=      1V=         0; File= prelevements_souterrains.txt; Col=4'
    res = _parse_parameter_line(line)
    assert res['DEBIT']['data_column_index'] == 4, 'error while parsing external file column'


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


def test_build_line():
    test = {'grid_id': 0, 'layer': 1, 'value': '*'}
    test_str = _build_parameter_line('DEBIT', 'COUCHE', **test)
    expected = '  /DEBIT/COUCHE            C=      1V=         *;'
    assert test_str == expected, 'Error while building parameter line'

    test = {'grid_id': 0, 'file_path': 'toto.txt', 'opt_list_mail': ['init_zero', 'keep_9999', 'xyc', 'mean']}
    test_str = _build_parameter_line('DEBIT', 'LIST_MAIL', **test)
    expected = '  /DEBIT/LIST_MAIL         N: toto.txt <Init_a_Zero> <Keep_9999> <X_Y_C> <Moyenne>'
    assert test_str == expected, 'Error while building parameter line'

    test = {'grid_id': 0, 'zone': 0, 'value': 0}
    test_str = _build_parameter_line('T_1/2_TARIS_1', 'ZONE_SOL', **test)
    expected = '  /T_1/2_TARIS_1/ZONE_SOL  Z=      0V=         0;'
    assert test_str == expected, 'Error while building parameter line with default values'


def test_edition_fmt():
    test = {'edit': 1}
    test_str = _build_parameter_line('DEBIT', 'EDITION', **test)
    assert test_str == '  /DEBIT/EDITION           *= 1;V=  ;L=  ;S=  ;Z=  ;'
    test_str = _build_parameter_line('CHARGE', 'EDITION', **test)
    assert test_str == '  /CHARGE/EDITION          I= 1;'


if __name__ == '__main__':
    test_parse_parameter_line()
