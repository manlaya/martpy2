#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from io_utils import _write_river_tree


class RiverTree:
    def __init__(self, df_tree):
        self.tree = df_tree
        # TODO: load afluent grid here, add method to set river section, etc.

    def filter_from_grid(self, grid):
        # subset arb_r from actual grid of river afluents
        pass

    def create_from_grid(self, grid):
        # create arb_r from grid
        # by identifying with afluent goes to where...
        pass

    def write_file(self, file_tree):
        _write_river_tree(self.df, file_tree)
