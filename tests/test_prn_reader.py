#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import unittest
import numpy as np
import pandas as pd

from martpy.outputs import reader_prn


class TestReaderPrn(unittest.TestCase):
    def setUp(self):
        # Example directory and file paths
        self.example_dir = './tests/data/mart_outputs/simple_case'
        self.example_dir_zone = './tests/data/mart_outputs/outputs_zone'
        self.example_dir_affl = './tests/data/mart_outputs/outputs_afflu'
        self.example_dir_mass = './tests/data/mart_outputs/outputs_mass'
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
            reader_prn.read_output_water_balance('./tests/data/mart_outputs/missing.prn')

    def test_read_time_serie(self):
        result = reader_prn.read_output_time_series(
            f"{self.example_dir}/historiq.prn"
        )
        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 0)
        self.assertIn('date', result.index.names)
        self.assertIn('variable', result.columns.names)
        self.assertIn('coords', result.columns.names)
        self.assertIn('name', result.columns.names)
        self.assertTrue(np.all(result.dtypes == 'float64'))
        self.assertTrue(result.index.dtype == '<M8[ns]')

    def test_read_ts_norm_headers(self):
        result = reader_prn.read_output_time_series(
            f"{self.example_dir}/historiq.prn",
            normalize_headers=True
        )
        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 0)
        self.assertIn('date', result.index.names)
        self.assertIn('variable', result.columns.names)
        self.assertIn('coords', result.columns.names)
        self.assertIn('name', result.columns.names)
        self.assertTrue(np.all(result.dtypes == 'float64'))
        self.assertTrue(result.index.dtype == '<M8[ns]')
        heads = result.columns.get_level_values(0)
        self.assertTrue('h_head' in heads)
        self.assertTrue('Charge' not in heads)
        self.assertTrue('rvier_flow' not in heads)

    def test_read_time_serie_affl(self):
        # Assuming reader_prn.read_prn_file returns a list of dicts
        result = reader_prn.read_output_time_series(
            f"{self.example_dir_affl}/historiq.prn"
        )
        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 0)
        self.assertIn('date', result.index.names)
        self.assertIn('variable', result.columns.names)
        self.assertIn('coords', result.columns.names)
        self.assertIn('name', result.columns.names)
        self.assertIn('riv_afluent', result.columns.names)
        self.assertTrue(np.all(result.dtypes == 'float64'))
        self.assertTrue(result.index.dtype == '<M8[ns]')

    def test_read_time_serie_affl_gig(self,):
        result = reader_prn.read_output_time_series(
            f"{self.example_dir_affl}/historiq_with_gig.prn"
        )
        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 0)
        self.assertIn('date', result.index.names)
        self.assertIn('variable', result.columns.names)
        self.assertIn('coords', result.columns.names)
        self.assertIn('name', result.columns.names)
        self.assertIn('grid', result.columns.names)
        self.assertIn('riv_afluent', result.columns.names)
        self.assertTrue(np.all(result.dtypes == 'float64'))
        self.assertTrue(result.index.dtype == '<M8[ns]')

    def test_read_balance(self):
        res = reader_prn.read_output_water_balance(
            f"{self.example_dir}/histobil_debit.prn",
            normalize_headers=False
        )
        self.assertIsInstance(res, pd.DataFrame)
        self.assertIn('date', res.index.names)
        self.assertIn('zone', res.index.names)
        self.assertIn('Entr_Limit', res.columns)
        self.assertIn('Nombre_Suintem', res.columns)
        self.assertTrue(np.all(res.dtypes == 'float64'))
        self.assertTrue(res.index.get_level_values(1).dtype == '<M8[ns]')
    
    def test_read_balance_no_multiindex(self):
        res = reader_prn.read_output_water_balance(
            f"{self.example_dir}/histobil_debit.prn",
            normalize_headers=False,
            add_multiindex=False
        )
        self.assertIsInstance(res, pd.DataFrame)
        self.assertIn('date', res.index.names)
        self.assertNotIn('zone', res.index.names)
        self.assertTrue(np.all(res.dtypes == 'float64'))
        self.assertTrue(res.index.dtype == '<M8[ns]')

    def test_read_balance_zone(self):
        res = reader_prn.read_output_water_balance(
            f"{self.example_dir_zone}/histobil_debit.prn",
            normalize_headers=False
        )
        self.assertIsInstance(res, pd.DataFrame)
        self.assertIn('date', res.index.names)
        self.assertIn('zone', res.index.names)
        self.assertIn('Glob_Riv_Nappe', res.columns)
        self.assertNotIn('Glob_Riv-Nappe', res.columns)  # mind the separator, check rename is done
        zone = res.index.get_level_values('zone').unique()
        self.assertIn('2', zone)
        self.assertTrue(np.all(res.dtypes == 'float64'))
        self.assertTrue(res.index.get_level_values(1).dtype == '<M8[ns]')

    def test_read_all_kind(self):
        for f in self.all_files:
            res = reader_prn.read_output_water_balance(
                os.path.join(self.example_dir, f),
                normalize_headers=False
            )
            self.assertIsInstance(res, pd.DataFrame)
            self.assertIn('date', res.index.names)
            self.assertGreater(len(res), 0)
            self.assertTrue(np.all(res.dtypes == 'float64'))

    def test_read_mass_balance(self):
        res = reader_prn.read_output_water_balance(
            f"{self.example_dir_mass}/histomas.prn",
            normalize_headers=False
        )
        self.assertIsInstance(res, pd.DataFrame)
        self.assertIn('date', res.index.names)
        self.assertTrue(np.all(res.dtypes == 'float64'))


if __name__ == '__main__':

    # unittest.main()

    # manual test for debug
    # test_file = './tests/data/mart_hallue/histobil_debit.prn'
    # test_file = './tests/data/mart_hallue/histobil_debit.prn'
    # test_file = './tests/data/mart_hallue/histobil_nap_cumu.prn'
    # test_file = './tests/data/mart_hallue/histobil_nap_pastp.prn'
    # test_file = './tests/data/mart_hallue/histobil_riv_dra_lac.prn'
    test_file = './tests/data/mart_hallue/histoclim.prn'
    # test_file = './tests/data/mart_outputs/outputs_mass/histomas.prn'

    # import time
    # t0 = time.time()
    df = reader_prn.read_output_water_balance(test_file)
    df = reader_prn.read_output_water_balance(test_file, normalize_headers=True)
    # print(time.time() - t0)
    df = reader_prn.read_output_time_series('./tests/data/mart_outputs/simple_case/historiq.prn')
    df = reader_prn.read_output_time_series('./tests/data/mart_outputs/simple_case/historiq.prn', normalize_headers=True)

    # pymarthe version
    # t0 = time.time()
    # df2 = read_budget(test_file)
    # df2 = read_zonebudget(test_file)
    # print(time.time() - t0)
