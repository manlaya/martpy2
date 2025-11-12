#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from martpy.inputs.reader import read_nzcli


def test_read_nzcli():
    fnzcli = 'tests/data/mart_hallue/hallue.nzcli'
    nzcli = read_nzcli(fnzcli)
    assert len(nzcli) == 10, 'Error while reading nzcli file'


def main():
    test_read_nzcli()


if __name__ == "__main__":
    main()