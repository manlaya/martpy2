#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from martpy.inputs._rma_parser import _parse_marthe_project, _write_rma_file


def test_reader(rma_file):
    dict_rma = _parse_marthe_project(rma_file)
    assert isinstance(dict_rma, dict)
    assert len(dict_rma) == 206
    return dict_rma


def test_writer(dict_rma, file_out):
    _write_rma_file(dict_rma, file_out)
    return


def test_all():
    rma_file = './tests/data/mart_hallue/hallue.rma'
    fout = './tests/data/tmp_outputs/hallue_write.rma'
    dict_rma = test_reader(rma_file)
    test_writer(dict_rma, fout)
    return
