#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from martpy.inputs._rma_parser import _parse_marthe_project, _write_rma_file

RMA_FILE = './tests/data/mart_hallue/hallue.rma'
FOUT = './tests/data/tmp_outputs/hallue_write.rma'


def test_reader():
    dict_rma = _parse_marthe_project(RMA_FILE)
    assert isinstance(dict_rma, dict), 'Error in parse RMA file: not a dict'
    assert len(dict_rma) == 205, 'Error in parse RMA file: wrong number of parameters'  # expert level testing... :)


def test_writer():
    dict_rma = _parse_marthe_project(RMA_FILE)
    _write_rma_file(dict_rma, FOUT)


def main():
    test_reader()
    test_writer()


if __name__ == "__main__":
    main()