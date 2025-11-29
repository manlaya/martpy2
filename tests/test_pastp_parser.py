#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
import pandas as pd

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
    
    min_date = res.times['time'].min().strftime('%Y-%m-%d')
    max_date = res.times['time'].max().strftime('%Y-%m-%d')
    assert min_date == '1995-07-31', "Wrong start date read"
    assert max_date == '2012-07-31', "Wrong end date read"


def test_create_pastp():
    dt1 = pd.date_range('1990-01-01', '2000-01-01', freq='YS')
    dt2 = pd.date_range('2000-02-01', '2025-07-31', freq='D')
    # dt = pd.concat([dt1.to_series(), dt2.to_series()]).reset_index()
    dt = dt1.union(dt2)
    dt = pd.Series(dt).reset_index()
    dt.columns = ['step', 'time']
    dt = dt.assign(has_action=False)
    pastp = MartheTimeSteps(dt)
    assert len(pastp.times) == len(dt), 'Error while creating pastp'
    # pastp.write_file('toto.pastp')

    # with class method
    pastp = MartheTimeSteps.from_dates(dates=dt2)
    pastp2 = MartheTimeSteps.from_dates(
        date_min='2000-02-01', date_max='2025-07-31', freq='D'
    )
    assert pastp.times.equals(pastp2.times), 'Error while creating pastp'


def test_add_steps():
    pastp = read_mart_timesteps(FILE_PASTP)
    pastp.add_times('2012-08-01', '2013-01-01', freq='D')
    assert pastp.times['time'].iloc[-1] == pd.Timestamp('2013-01-01'), \
        'Error while adding steps'
    # pastp.write_file('toto.pastp')


def test_add_action():
    # pastp2 = read_mart_timesteps('tests/data/pastp/long_timesteps.pastp')
    # pastp2.get_actions().get('1982-08-01')
    pastp = read_mart_timesteps(FILE_PASTP)
    dt = pd.date_range('2012-08-01', '2020-07-31', freq='D')
    pastp.add_times(dates=dt)
    new_dt = pastp.get_times()
    actions_dates = (new_dt.dt.year>=2012) & (new_dt.dt.month==8) & (new_dt.dt.day == 1)
    
    for dt in new_dt[actions_dates]:
        pastp.add_action(
            times=dt,
            variable='METEO_PLUIE',
            action='FICHIER',
            file='TOTO_{}_{}'.format(dt.year, dt.year+1)
        )
        pastp.add_action(
            times=dt,
            variable='FLUX_PLUV',
            action='FICH_METE',
            step='*'
        )
    d = pastp.get_actions()
    assert '2012-08-01' in d, 'Error while adding actions'
    assert 'METEO_PLUIE' in d['2012-08-01'], 'Error while adding actions'
    assert len(d['2012-08-01']['METEO_PLUIE']) == 1, 'Error while adding actions'
    assert d['2012-08-01']['METEO_PLUIE'][0]['file'] == 'TOTO_2012_2013', 'Error while adding actions'
    assert 'FLUX_PLUV' in d['2012-08-01'], 'Error while adding actions'
    assert len(d['2012-08-01']['FLUX_PLUV']) == 1, 'Error while adding actions'
    assert d['2012-08-01']['FLUX_PLUV'][0]['step'] == '*', 'Error while adding actions'
    #
    pastp.write_file('tests/data/tmp_outputs/test_add_actions.pastp')


def test_write_pastp():
    pastp = read_mart_timesteps(FILE_PASTP)
    file_pastp_out = './tests/data/tmp_outputs/test.pastp'
    pastp.write_file(file_pastp_out)
    verif = read_mart_timesteps(file_pastp_out)
    msg_error = 'Error with write/reread test for pastp'
    assert pastp.times['time'].to_list() == verif.times['time'].to_list(), "{} - times do not match".format(msg_error)
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
