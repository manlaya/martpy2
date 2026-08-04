#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from pathlib import Path
import tempfile

import pytest
import martpy as mart

import xarray as xr


# Using absolute path relative to the test execution context for safety
# Assuming tests are run from the project root
MODEL_DIR = os.path.abspath('tests/data/mart_hallue')
MODEL_FILE = os.path.join(MODEL_DIR, 'hallue.rma')
MARTBIN = Path.home() / '.local' / 'bin' / 'marthe'


def test_instantiate_model():
    model = mart.MartModel(MODEL_FILE)
    assert model.model_name == 'hallue'
    assert model.model_path == MODEL_DIR
    print(model)


def test_instantiate_model_pathlib():
    model = mart.MartModel(Path(MODEL_FILE))
    assert model.model_name == 'hallue'
    assert model.model_path == MODEL_DIR


def test_get_outputs():
    # Only test if output files exist (they should be in test data)
    model = mart.MartModel(MODEL_FILE)

    # We don't run the model here to rely on committed test data
    outputs = model.get_outputs()

    if os.path.exists(os.path.join(MODEL_DIR, 'historiq.prn')):
        assert 'historiq' in outputs
        assert not outputs['historiq'].empty

    if os.path.exists(os.path.join(MODEL_DIR, 'histobil_debit.prn')):
        assert 'histobil_debit' in outputs
        assert not outputs['histobil_debit'].empty

    if os.path.exists(os.path.join(MODEL_DIR, 'chasim.out')):
        assert 'charge' in outputs
        assert outputs['charge'].zone.size != 0

def test_load_model():
    model = mart.MartModel(MODEL_FILE)

    model.load_model()

    assert model._mart_histo is not None # should have MartHisto object
    assert model._mart_layer[0] is not None
    assert model._mart_layer[1] is not None
    assert model._mart_params is not None

def test_load_all_grid():
    model = mart.MartModel(MODEL_FILE)
    
    model.load_all_grid()

    assert model.grid is not None
    assert isinstance(model.grid['permeab'], xr.DataArray)


def test_load_outputs():
    model = mart.MartModel(MODEL_FILE)

    model.load_outputs()

    assert model.outputs is not None


def test_get_da():
    model = mart.MartModel(MODEL_FILE)

    model.load_all_grid()

    result = model.get_da('PERMEAB')

    assert result is not None
    assert isinstance(result, xr.DataArray)


def test_set_value():
    model = mart.MartModel(MODEL_FILE)

    model.load_all_grid()

    result = model.set_value(zone=1, value=10000.0, varname='charge')

    assert result 

def test_to_marthe_grid():
    model = mart.MartModel(MODEL_FILE)
    
    model.load_all_grid()
    file = tempfile.NamedTemporaryFile(mode='w+', suffix='.charg', delete=True)
    result = model.to_marthe_grid(file.name, 'charge')

    assert not result # should return 0 if success

    file.seek(0)
    content = file.read()
    assert 'Field=CHARGE' in content

def test_to_config():
    model = mart.MartModel(MODEL_FILE)
    
    model.load_model()
    file = tempfile.NamedTemporaryFile(mode='w+', encoding='latin-1', suffix='.mart', delete=True)
    model.to_config(file.name, 'PARAM')

    file.seek(0)
    content = file.read()
    assert 'Sauvegardes' in content
    assert 'Pas de Temps et sous-pas de temps' in content

def test_to_rma():
    model = mart.MartModel(MODEL_FILE)
        
    model.load_model()
    model.load_all_grid()
    file = tempfile.NamedTemporaryFile(mode='w+', encoding='latin-1', suffix='.rma', delete=True)
    result = model.to_rma(file.name)

    assert result
    file.seek(0)
    content = file.read()
    assert 'hallue.permh' in content
    assert 'hallue.charg' in content

@pytest.mark.skipif(not os.path.exists(MARTBIN), reason="MARTHE binary not found")
def test_run_model():
    model = mart.MartModel(MODEL_FILE)
    # Use a temporary output directory or just run in place if safe (test data might be modified?)
    # usually better to run in tmpdir

    # For now ensuring existing file runs (this might fail if marthe not installed)
    status = model.run(martbin=MARTBIN, mute=True)
    assert status == 0, "MARTHE model did not run successfully"


if __name__ == '__main__':
    test_instantiate_model()
    test_load_model_inputs()
    test_get_outputs()
