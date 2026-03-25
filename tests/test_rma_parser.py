#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import pytest

import martpy as mart
from martpy.inputs._rma_parser import _parse_marthe_project, _write_rma_file

RMA_FILE = './tests/data/mart_hallue/hallue.rma'
FOUT = './tests/data/tmp_outputs/hallue_write.rma'


def test_reader():
    dict_rma = _parse_marthe_project(RMA_FILE)
    assert isinstance(dict_rma, dict), 'Error in parse RMA file: not a dict'
    assert len(dict_rma) == 207, 'Error in parse RMA file: wrong number of parameters'  # expert level testing... :)
    dict_rma = {k: v for k,v in dict_rma.items() if v}  # skip none
    del dict_rma['title']  # no test on title
    for k, v in dict_rma.items():
        if isinstance(v, str) and re.match(r'\w+\.\w+', v):
            # test for files:
            assert k == v.split('.')[-1], 'variable and extension does not match in RMA file'
        else:
            # print(v)
            assert isinstance(v, float), 'Uniform value not parsed as float in RMA'
    return


def test_writer():
    dict_rma = _parse_marthe_project(RMA_FILE)
    _write_rma_file(dict_rma, FOUT)
    reread = _parse_marthe_project(FOUT)
    _ = reread.pop('title', None)
    assert dict_rma == reread, 'written and read rma do not match'


def test_set_new_files():
    rma = mart.read_rma_file(RMA_FILE)
    mod_files = rma.get_files(only_active=False)
    rma.set_files(salext='toto.sal', tempe='tata.temper')
    rma.set_files({'cext_r': 'blblb.cext_r'})
    mod_files_new = rma.get_files(only_active=False)
    assert mod_files_new != mod_files
    assert mod_files_new.get('salext') == 'toto.sal'
    assert mod_files_new.get('tempe') == 'tata.temper'
    assert mod_files_new.get('cext_r') == 'blblb.cext_r'


def test_set_new_files_error():
    rma = mart.read_rma_file(RMA_FILE)
    with pytest.raises(ValueError):
        rma.set_files(blabla='toto.sal')


def main():
    test_reader()
    test_writer()


if __name__ == "__main__":
    main()
