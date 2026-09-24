#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import pandas as pd
import martpy as mart
from conftest import TMP_OUTPUTS_DIR


def test_debug_parsing_empty_value():
    line = '          =Schéma pour dénoyages : [0=Pseudo-Non-Saturé ; 2=ZNS_automatique]'
    match = re.match(r'(\S+|\s*)=([^\[]+)', line.strip())
    assert match is not None, 'Error while parsing line with empty value'
    value = match.group(1).strip()
    assert value == '', 'Error while parsing line with empty value'


def test_debug_mart_write_float_fmt():
    the_usual_suspect = 'tests/debug/MOD82_bug_f_fmt_write.mart'
    param = mart.MartParams.from_file(the_usual_suspect)
    param.write_file(str(TMP_OUTPUTS_DIR / 'debug_mart_write_float_fmt.mart'))


def test_concat_histo():
    histo = mart.MartHisto.from_histo_file('./tests/data/mart_hallue/hallue.histo')
    # histo2 = mart.MartHisto.from_histo_file('./tests/data/mart_uk/mart_uk_files.histo')
    histo2 = histo.iloc[-2:,:]
    df = pd.concat([histo.iloc[:-2], histo2], ignore_index=True)
    assert isinstance(df, pd.DataFrame), 'Error while concatenating histo dataframes'
    assert isinstance(df, mart.MartHisto), 'Error while concatenating histo dataframes'
    df.write_file(str(TMP_OUTPUTS_DIR / 'debug_concat_histo.histo'))


if __name__ == '__main__':
    test_debug_mart_write_float_fmt()
