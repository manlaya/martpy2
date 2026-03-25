#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from pathlib import Path

import pytest
import martpy as mart


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
