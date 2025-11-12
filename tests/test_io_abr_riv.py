#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
from martpy.inputs.reader import read_river_tree


def test_river_tree_reader():
    ftree = 'tests/data/mart_hallue/hallue.arb_r'
    df = read_river_tree(ftree)
    assert isinstance(df, pd.DataFrame), 'Error while reading river tree file'
    assert len(df) == 3, 'Error while reading river tree file - wrong length'
    assert list(df.columns) == ['affluent', 'outlet'], 'Error while reading river tree file columns'


def main():
    test_river_tree_reader()


if __name__ == "__main__":
    main()