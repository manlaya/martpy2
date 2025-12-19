#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import martpy as mart


MODEL_FILE = 'tests/data/mart_hallue/hallue.rma'


def test_run_model():
    model = mart.MartModel(MODEL_FILE)
    print(model)
    # model.load_model()
    
    # status = model.run(martbin='/home/manlaya/.local/bin/marthe784_static', debug=True)
    status = model.run(martbin='/home/manlaya/.local/bin/marthe784_static', mute=True)
    assert status == 0, "MARTHE model did not run successfully"
    
    # outputs = model.get_outputs()
    # assert 'historiq.prn' in outputs
    # assert 'histobil_debit.prn' in outputs
