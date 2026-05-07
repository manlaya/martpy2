#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import martpy as mart


def test_pastp_write_it_twice():
    # load timesteps
    path_data = './tests/data/mart_hallue'
    tmp = './tests/data/tmp_outputs'
    pastp = mart.read_mart_timesteps(f'{path_data}/hallue.pastp')
    print(pastp)
    pastp.add_times('2012-08-01', '2020-07-31')
    pastp.write_file(f'{tmp}/pastp_write_once.pastp')
    pastp.add_times('2020-08-01', '2025-07-31')
    pastp.write_file(f'{tmp}/pastp_write_twice.pastp')


def get_times():
    # load timesteps
    path_data = './tests/data/mart_hallue'
    tmp = './tests/data/tmp_outputs'
    pastp = mart.read_mart_timesteps(f'{path_data}/hallue.pastp')
    print(pastp)
    pastp.add_times('2012-08-01', '2020-07-31')
    t0 = time.time()
    pastp.write_file(f'{tmp}/pastp_write_once.pastp')
    t1 = time.time()
    # NOT committed version using deepcopy
    pastp.write_file(f'{tmp}/pastp_write_twice.pastp', deep=True)
    t2 = time.time()
    pastp.get_actions()

    print('First write time: {:.4f}s'.format(t1 - t0))
    print('Second write time: {:.4f}s'.format(t2 - t1))
    # >>> print('First write time: {:.4f}s'.format(t1 - t0))
    # First write time: 0.0620s
    # >>> print('Second write time: {:.4f}s'.format(t2 - t1))
    # Second write time: 0.0374s


if __name__ == "__main__":

    test_pastp_write_it_twice()
