#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd

def read_river_tree(file_tree, encoding='ISO-8859-1'):
    # TODO better: not always 1 row to skip ?
    return pd.read_csv(
        file_tree,
        sep=r'\s+',
        header=None,
        names=['affluent', 'outlet'],
        encoding=encoding,
        skiprows=1,
        skipfooter=1,
        engine='python'  # c-engine does not support skipfooter
    )


def _write_river_tree(tree_df, file_tree, title='Branchement affluents'):
    """ Write a river tree file (`*.arb_r`)
    """
    with open(file_tree, mode='w', encoding='ISO-8859-1') as f:
        f.write(f"{title}\n")
        tree_df.to_csv(f, sep='\t', index=False, header=False, float_format='10i')
        f.write(' *** Fin du fichier Arbre des Affluents de Rivière   ***\n')
    return


class RiverTree:
    def __init__(self, df_tree):
        self.tree = df_tree
        # TODO: load afluent grid here, add method to set river section, etc.

    def filter_from_grid(self, grid):
        # subset arb_r from actual grid of river afluents
        raise NotImplementedError

    def create_from_grid(self, grid):
        # create arb_r from grid
        # by identifying with afluent goes to where...
        raise NotImplementedError

    def write_file(self, file_tree):
        _write_river_tree(self.df, file_tree)
