#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
import numpy as np
import pandas as pd

from martpy.inputs.timesteps import (
    _parse_date_pastp,
    read_mart_timesteps,
    MartTimeSteps
)

FILE_PASTP = './tests/data/mart_hallue/hallue.pastp'
FILE_PASTP_UK = './tests/data/mart_uk/mart_uk_files.pastp'


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
    assert isinstance(res, MartTimeSteps), 'Results is not a MartTimeSteps object'
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
    pastp = MartTimeSteps(dt)
    assert len(pastp.times) == len(dt), 'Error while creating pastp'
    # pastp.write_file('toto.pastp')

    # with class method
    pastp = MartTimeSteps.from_dates(dates=dt2)
    pastp2 = MartTimeSteps.from_dates(
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
            file_path='TOTO_{}_{}'.format(dt.year, dt.year+1)
        )
        pastp.add_action(
            times=dt,
            variable='FLUX_PLUV',
            action='FICH_METE',
            step='*'
        )
    pastp.add_action(new_dt.iloc[0], variable='CALCUL_HDYNAM', action='ACTION', value=2)
    d = pastp.get_actions()

    assert '2012-08-01' in d, 'Error while adding actions'
    assert 'METEO_PLUIE' in d['2012-08-01'], 'Error while adding actions'
    assert len(d['2012-08-01']['METEO_PLUIE']) == 1, 'Error while adding actions'
    assert d['2012-08-01']['METEO_PLUIE'][0]['file_path'] == 'TOTO_2012_2013', 'Error while adding actions'
    assert 'FLUX_PLUV' in d['2012-08-01'], 'Error while adding actions'
    assert len(d['2012-08-01']['FLUX_PLUV']) == 1, 'Error while adding actions'
    assert d['2012-08-01']['FLUX_PLUV'][0]['step'] == '*', 'Error while adding actions'
    #
    pastp.write_file('tests/data/tmp_outputs/test_add_actions.pastp')


def test_add_action_freq():
    pastp = read_mart_timesteps(FILE_PASTP)
    # here also test action in lowercase and no value (should be automatic for edition)
    pastp.add_action(freq='ME', variable='ETAT_HYD_CLIM', action='edition')
    d = pastp.get_actions(variable='ETAT_HYD_CLIM', as_dataframe=True)
    assert len(d) == 205, 'monthly actions failed'
    assert np.all(d.index.get_level_values(0).is_month_end), 'frequency not respected in actions'


def test_add_action_no_duplicates():
    # Reproduce issue #17: identical add_action calls must not accumulate duplicates
    pastp = read_mart_timesteps(FILE_PASTP)
    pastp.add_action(freq='ME', variable='ETAT_HYD_CLIM', action='edition')
    pastp.add_action(freq='ME', variable='ETAT_HYD_CLIM', action='edition')
    pastp.add_action(freq='ME', variable='ETAT_HYD_CLIM', action='edition')
    d = pastp.get_actions(variable='ETAT_HYD_CLIM', as_dataframe=True)
    assert len(d) == 205, 'duplicate actions must be dropped (keep last), monthly count must remain 205'

    # Also check that distinct actions on the same variable are preserved (use fresh pastp)
    pastp2 = MartTimeSteps.from_dates(date_min='2000-01-01', date_max='2005-12-31', freq='ME')
    pastp2.add_action(freq='ME', variable='CALCUL_HDYNAM', action='ACTION', value=1)
    pastp2.add_action(freq='ME', variable='CALCUL_HDYNAM', action='ACTION', value=2)
    d2 = pastp2.get_actions(variable='CALCUL_HDYNAM', as_dataframe=True)
    n_months = len(pd.date_range('2000-01-01', '2005-12-31', freq='ME'))
    assert len(d2) == n_months * 2, 'distinct actions on same variable must both be kept'


def test_get_actions():
    pastp = read_mart_timesteps(FILE_PASTP)
    pastp.add_action(steps=-1, variable='CALCUL_HDYNAM', action='ACTION', value=2)

    act = pastp.get_actions()
    assert 'CALCUL_HDYNAM' in act['1995-07-31'], 'Error while getting actions'
    assert 'CALCUL_HDYNAM' in act['2012-07-31'], 'Error while getting actions'

    act = pastp.get_actions(time='2012-07-31')
    assert len(act) == 1, 'Error while getting actions for specific time'
    assert 'CALCUL_HDYNAM' in act['2012-07-31'], 'Error while getting actions for specific time'

    act = pastp.get_actions(step=[0,-1])
    assert len(act) == 2, 'Error while getting actions for specific step'
    assert list(act.keys()) == ['1995-07-31', '2012-07-31'], 'Error while getting actions for specific step'

    act = pastp.get_actions(variable='CALCUL_HDYNAM')
    assert len(act) == 2, 'get actions for a specific variable failed'
    assert list(act.keys()) == ['1995-07-31', '2012-07-31'], 'Error while getting actions for specific step'

    act = pastp.get_actions(variable='CALCUL_HDYNAM', as_dataframe=True)
    assert isinstance(act, pd.DataFrame), 'get actions as dataframe failed. Res is no DF'
    assert len(act)==2, 'get actions as dataframe failed. wrong row number'
    assert isinstance(act.index, pd.MultiIndex), "multiindex expected for actions as df"

    # just test execution
    act = pastp.get_actions(step=[0,-1], as_dataframe=True)
    act = pastp.get_actions(time='2012-07-31', as_dataframe=True)
    act = pastp.get_actions(time=['1995-07-31', '2012-07-31'], as_dataframe=True)
    assert len(act) == 9, 'get actions for multiple times as df failed'


def test_get_actions_with_variable():
    pastp = read_mart_timesteps(FILE_PASTP)
    pastp.add_action(steps=-1, variable='CALCUL_HDYNAM', action='ACTION', value=2)
    pastp.add_action(steps=[1,2], variable='CALCUL_HDYNAM', action='ACTION', value=2)
    # act_all = pastp.get_actions()
    act_var = pastp.get_actions(variable='CALCUL_HDYNAM')
    assert len(act_var) == 4, 'Error while getting actions with variable filter'


def test_slice_times():
    pastp = read_mart_timesteps(FILE_PASTP)
    pastp_slice = pastp.slice_times('2000-01-01', '2010-12-31')
    times = pastp_slice.get_times()
    assert times.iloc[0] == pd.Timestamp('2000-01-01'), 'Error while slicing times'
    assert times.iloc[-1] == pd.Timestamp('2010-12-31'), 'Error while slicing times'


def test_add_action_with_istep():
    pastp = read_mart_timesteps(FILE_PASTP)
    pastp.add_action(steps=-1, variable='CALCUL_HDYNAM', action='ACTION', value=2)
    act = pastp.get_actions()
    assert len(list(act.keys())) == 2
    pastp.add_action(steps=[1,2], variable='CALCUL_HDYNAM', action='ACTION', value=2)
    act = pastp.get_actions()
    assert len(list(act.keys())) == 4


def test_wrapper_method():
    # test wrapper method
    import pytest
    pastp = read_mart_timesteps(FILE_PASTP)
    pastp.set_met_forcings(['TOTO_{}_{}', 'TOTO2_{}_{}'])
    # pastp.write_file('tests/data/tmp_outputs/test_add_actions2.pastp')
    pastp.set_pumping_data('fake_pumping_{}_{:02d}.txt', opt=['xyv', 'init_zero'])
    pastp.write_file('tests/data/tmp_outputs/test_add_actions3.pastp')
    with pytest.raises(ValueError):
        pastp.set_pumping_data('fake_pumping_{}_{:02d}.txt', opt=['tata'])


def test_write_pastp():
    pastp = read_mart_timesteps(FILE_PASTP)
    file_pastp_out = './tests/data/tmp_outputs/test.pastp'
    pastp.write_file(file_pastp_out)
    verif = read_mart_timesteps(file_pastp_out)
    msg_error = 'Error with write/reread test for pastp'
    assert pastp.times['time'].to_list() == verif.times['time'].to_list(), "{} - times do not match".format(msg_error)
    assert pastp.times['has_action'].to_list() == verif.times['has_action'].to_list(), "{} - actions do not match".format(msg_error)


def test_pastp_uk():
    pastp = read_mart_timesteps(FILE_PASTP_UK)

    min_date = pastp.times['time'].min().strftime('%Y-%m-%d')
    max_date = pastp.times['time'].max().strftime('%Y-%m-%d')
    assert min_date == '2025-11-25', "Wrong start date read"
    assert max_date == '2026-03-05', "Wrong end date read"


def main():
    print('Test MARTHE pastp reader')
    test_parse_date_fmt()
    test_read_pastp()
    test_write_pastp()
    test_wrapper_method()
    test_add_action_with_istep()
    test_get_actions()
    test_pastp_uk()
    print('============')
    print('Test success')


if __name__ == "__main__":
    main()
