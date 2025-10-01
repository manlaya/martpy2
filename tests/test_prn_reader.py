#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import unittest
import pandas as pd

from martpy.outputs import reader_prn


class TestReaderPrn(unittest.TestCase):
    def setUp(self):
        # Example directory and file paths
        self.example_dir = './tests/data/mart_outputs/simple_case'
        self.example_dir_zone = './tests/data/mart_outputs/outputs_zone'
        self.all_files = [
            'histobil_debit.prn',
            'histobil_nap_cumu.prn',
            'histobil_nap_pastp.prn',
            'histobil_riv_dra_lac.prn',
            'histoclim.prn',
        ]

    # def tearDown(self):
    #     if os.path.exists(self.example_file):
    #         os.remove(self.example_file)
    
    def test_read_prn_file_missing(self):
        with self.assertRaises(FileNotFoundError):
            reader_prn.read_prn_file('./tests/data/mart_outputs/missing.prn')
    
    def test_read_time_serie(self):
        # Assuming reader_prn.read_prn_file returns a list of dicts
        result = reader_prn.read_output_time_series(
            f"{self.example_dir}/historiq.prn"
        )
        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 0)
        self.assertIn('date', result.index.names)
        self.assertIn('field', result.columns.names)
        self.assertIn('coords', result.columns.names)
        self.assertIn('name', result.columns.names)

    def test_read_balance(self):
        res = reader_prn.read_output_balance(
            f"{self.example_dir}/histobil_debit.prn"
        )
        self.assertIsInstance(res, pd.DataFrame)
        self.assertIn('date', res.index.names)
        self.assertIn('zone', res.index.names)
        self.assertIn('Entr_Limit', res.columns)
        self.assertIn('Nombre_Suintem', res.columns)
    
    def test_read_balance_zone(self):
        res = reader_prn.read_output_balance(
            f"{self.example_dir_zone}/histobil_debit.prn"
        )
        self.assertIsInstance(res, pd.DataFrame)
        self.assertIn('date', res.index.names)
        self.assertIn('zone', res.index.names)
        self.assertIn('Glob_Riv_Nappe', res.columns)
        self.assertNotIn('Glob_Riv-Nappe', res.columns)  # mind the separator, check rename is done
        zone = res.index.get_level_values('zone').unique()
        self.assertIn('2', zone)

    
    def test_read_all_kind(self):
        for f in self.all_files:
            res = reader_prn.read_output_balance(
                os.path.join(self.example_dir, f)
            )
            self.assertIsInstance(res, pd.DataFrame)
            self.assertIn('date', res.index.names)
            self.assertGreater(len(res), 0)


if __name__ == '__main__':
    
    unittest.main()

    # test_file = './tests/data/mart_hallue/histobil_debit.prn'
    # test_file = '/home/manlaya/mylib/mart_hallue/mart_hallue_zgeom/histobil_debit.prn'
    # test_file = '/home/manlaya/mylib/mart_hallue/mart_hallue_zgeom/histobil_nap_cumu.prn'
    # test_file = '/home/manlaya/mylib/mart_hallue/mart_hallue_zgeom/histobil_nap_pastp.prn'
    # test_file = '/home/manlaya/mylib/mart_hallue/mart_hallue_zgeom/histobil_riv_dra_lac.prn'
    # test_file = '/home/manlaya/mylib/mart_hallue/mart_hallue_zgeom/histoclim.prn'

    # import time
    # t0 = time.time()
    # df = read_output_water_balance(test_file)
    # print(time.time() - t0)

    # pymarthe version
    # t0 = time.time()
    # df2 = read_budget(test_file)
    # df2 = read_zonebudget(test_file)
    # print(time.time() - t0)