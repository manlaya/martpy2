#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import martpy as mart

# ------------ test legacy v7.2
def test_legacy_rma_72():
    rma = mart.read_rma_file('./tests/data/mart_72/Craie_NPC.rma')
    files = rma.get_files()
    assert len(list(files.keys())) > 0, 'No files were found in legacy rma'
    assert 'debit' in files.keys()
    print(files)


def test_legacy_rma_74():
    rma = mart.read_rma_file('./tests/data/mart_74/craie_npc.rma')
    files = rma.get_files()
    assert len(list(files.keys())) > 0, 'No files were found in legacy rma'
    assert 'debit' in files.keys()
    print(files)


def test_legacy_rma_76():
    rma = mart.read_rma_file('./tests/data/mart_76/hallue.rma')
    files = rma.get_files()
    assert len(list(files.keys())) > 0, 'No files were found in legacy rma'
    assert 'debit' in files.keys()
    print(files)


def test_legacy_mart_72():
    par = mart.read_general_parameters('./tests/data/mart_72/Craie_NPC.mart')
    assert par['outputs']['save_gw_balance'] == 1
    assert par['solver']['n_iter_steady'] == 100
    assert par['river']['n_iter_river_flow'] == 100
    assert par['stdout']['max_control_screen'] == 1
    assert par['init_parameters']


def test_legacy_pastp_72():
    timesteps = mart.read_mart_timesteps('./tests/data/mart_72/Craie_NPC.pastp')
    times = timesteps.get_times()
    actions = timesteps.get_actions()
    assert times.min() == pd.Timestamp('1981-12-25')
    assert times.max() == pd.Timestamp('2010-12-25')
    assert list(actions['1982-01-05'].keys()) == ['CALCUL_HDYNAM', 'DEBIT']


def test_legacy_histo_72():
    histo = mart.read_histo_file('./tests/data/mart_72/Craie_NPC.histo')
    assert len(histo) == 287


def test_legacy_layer_72():
    layers, info_grid = mart.read_layer('./tests/data/mart_72/Craie_NPC.layer')
    assert len(layers) == 8


# ------------ test legacy v7.4


if __name__ == '__main__':
    test_legacy_rma_72()