#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime

from martpy.inputs.timesteps import (
    _parse_date_pastp,
    read_mart_timesteps,
    MartheTimeSteps
)

FILE_PASTP = './tests/data/mart_hallue/hallue.pastp'

def test_parse_date_fmt():
    date_test = [
        ('31/07/1995 00:00', datetime(1995, 7, 31, 0, 0)),
        ('31/07/1995', datetime(1995, 7, 31, 0, 0)),
        ('12.5', 12.5)
    ]
    for dt in date_test:
        res = _parse_date_pastp(dt[0])
        assert res == dt[1], 'Error while parsing date'


def test_read_pastp():
    
    res = read_mart_timesteps(FILE_PASTP)
    assert isinstance(res, MartheTimeSteps), 'Results is not a MartheTimeSteps object'
    assert hasattr(res, 'times'), 'Results has no time attributes'
    assert hasattr(res, 'actions'), 'Results has no actions attributes'
    
    min_date = res.times['date'].min().strftime('%Y-%m-%d')
    max_date = res.times['date'].max().strftime('%Y-%m-%d')
    assert min_date == '1995-07-31', "Wrong start date read"
    assert max_date == '2012-07-31', "Wrong end date read"


def test_write_pastp():
    pastp = read_mart_timesteps(FILE_PASTP)
    file_pastp_out = './tests/data/tmp_outputs/test.pastp'
    pastp.write_file(file_pastp_out)
    verif = read_mart_timesteps(file_pastp_out)
    msg_error = 'Error with write/reread test for pastp'
    assert pastp.times['date'].to_list() == verif.times['date'].to_list(), "{} - times do not match".format(msg_error)
    assert pastp.times['has_action'].to_list() == verif.times['has_action'].to_list(), "{} - actions do not match".format(msg_error)


def main():
    print('Test MARTHE pastp reader')
    
    test_parse_date_fmt()
    
    test_read_pastp()
    print('Pastp read: (head only)')

    print('Test Marthe pastp writer')
    test_write_pastp()
    print('============')
    print('Test success')


if __name__ == "__main__":
    main()
