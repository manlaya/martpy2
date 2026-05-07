#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
from martpy.inputs.mart_param import MartParams
from martpy.inputs._mart_parser import (
    _parse_mart_file,
    _write_mart_file,
    BLOCK_MART
)

# import pprint


# MART_FILE = './tests/data/modin/MOD82_Safran_BV_Ext_1958-2021.mart'
MART_FILE = './tests/data/modin/param_with_modin_and_init.mart'  # lighter version for testing


def test_parse_modin():
    dict_res = _parse_mart_file(MART_FILE)

    # check init params, all modin instructions should be there
    init_par = dict_res['init_parameters']
    assert 'MODIFIC' not in init_par.keys(), \
        "MODIFIC not merged with init parameters"

    # verif que external_file est bien stocké
    test2 = init_par.get('NZON_RIV_EXT')[0].get('external_file') is not None
    assert test2, 'Error while parsing external file'

    assert 'PERMEAB' in init_par.keys(), "PERMEAB not in init parameters"
    # check for dups
    for k, v in init_par.items():
        # pprint.pprint(v)
        df = pd.DataFrame.from_dict(v)
        assert len(df.drop_duplicates()) == len(df), f"duplicates in init par for modin in key {k}"

        if k in ['CAP_SOL_PROGR', 'EQU_RUIS_PERC','FACT_ECH_SOUT',
        'T_1/2_TARIS_1', 'T_DEMI_PERCOL', 'FONT_SOL_NEIG', 'TEMPER_FONTE',
        'DEGR_JOUR_NEI', 'RETEN_NEIGE']:
            assert len(df) == 2, f"MODIN parameters not correctly merged for key {k}"

        elif k in ['NZON_RIV_EXT', 'SUPERF_BV_EXT']:
            assert len(df) == 3, f"MODIN parameters not correctly merged for key {k}"


# future
# def test_write_modin():
#     pass


if __name__ == "__main__":
    test_parse_modin()
