#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import io
from unittest.mock import patch

from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

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


def test_read_pastp_int_float_fmt():
    res = read_mart_timesteps('tests/data/pastp/times_int.pastp')
    assert isinstance(res, MartTimeSteps), 'Results is not a MartTimeSteps object'
    assert hasattr(res, 'times'), 'Results has no time attributes'
    assert hasattr(res, 'actions'), 'Results has no actions attributes'
    assert res.times['time'].dtype == 'float64'

    res = read_mart_timesteps('tests/data/pastp/times_float.pastp')
    assert isinstance(res, MartTimeSteps), 'Results is not a MartTimeSteps object'
    assert hasattr(res, 'times'), 'Results has no time attributes'
    assert hasattr(res, 'actions'), 'Results has no actions attributes'
    assert res.times['time'].dtype == 'float64'

    res = read_mart_timesteps('tests/data/pastp/times_hybride.pastp')
    assert isinstance(res, MartTimeSteps), 'Results is not a MartTimeSteps object'
    assert hasattr(res, 'times'), 'Results has no time attributes'
    assert hasattr(res, 'actions'), 'Results has no actions attributes'
    # assert res.times['time'].dtype == 'float64'  # TODO: parse date then float?


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


def test_add_times_inserts_chronologically():
    # Anterior times must be inserted before existing ones, not appended.
    pastp = read_mart_timesteps(FILE_PASTP)  # spans 1995-07-31 .. 2012-07-31
    pastp.add_times('1990-01-01', '1990-12-31', freq='MS')

    times = pastp.times
    # times must be sorted chronologically
    assert times['time'].is_monotonic_increasing, 'Times are not sorted by date'
    # the oldest added date now starts the simulation (step 0)
    assert times['time'].iloc[0] == pd.Timestamp('1990-01-01'), 'Anterior time not inserted first'
    # steps must be renumbered from 0 without gaps
    assert list(times['step']) == list(range(len(times))), 'Steps not renumbered from 0'
    # the time window must reflect the new minimum
    assert pastp.time_window[0] == pd.Timestamp('1990-01-01'), 'Time window min not updated'


def test_add_times_warns_on_existing():
    # Adding times that already exist must warn and keep the existing timesteps.
    pastp = read_mart_timesteps(FILE_PASTP)
    pastp.add_action('2012-07-31', variable='CALCUL_HDYNAM', action='ACTION', value=2)
    pastp.get_actions(time='2012-07-31')  # make sure the action is in the dat
    old_times = pastp.times
    n_before = len(pastp.times)

    with pytest.warns(UserWarning, match='already exist'):
        # 2012-07-31 already exists in the file
        pastp.add_times(dates=['2012-07-31', '2012-08-01'])

    # only the new date is added, the duplicate is ignored
    assert len(pastp.times) == n_before + 1, 'Existing time should not be duplicated'
    assert not pastp.times['time'].duplicated().any(), 'Duplicate time was kept'
    # assert action on potentially duplicates time is untouched
    assert pastp.times['has_action'].iloc[-2] == old_times['has_action'].iloc[-1]


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
    # issue #28: slice must keep actions of the remaining timesteps
    pastp = read_mart_timesteps(FILE_PASTP)
    pastp.add_action(times='2000-01-01', variable='CALCUL_HDYNAM', action='ACTION', value=2)
    pastp_slice = pastp.slice_times('2000-01-01', '2010-12-31')
    times = pastp_slice.get_times()
    assert times.iloc[0] == pd.Timestamp('2000-01-01'), 'Error while slicing times'
    assert times.iloc[-1] == pd.Timestamp('2010-12-31'), 'Error while slicing times'
    actions = pastp.get_actions()
    actions_slice = pastp_slice.get_actions()
    assert len(actions) == 2
    assert len(actions_slice) == 1, 'Error while slicing actions'


def test_remove_times():
    # issue #30: remove_times returns a new instance and removes specific steps
    pastp = read_mart_timesteps(FILE_PASTP)
    pastp.add_action(times='2000-01-01', variable='CALCUL_HDYNAM', action='ACTION', value=2)
    n_times = len(pastp.get_times())

    # scalar time: a new instance is returned, the original is left untouched
    removed = pastp.remove_times(time=pd.Timestamp('2000-01-01'))
    assert isinstance(removed, MartTimeSteps), 'remove_times must return a new instance'
    assert len(pastp.get_times()) == n_times, 'original instance must not be mutated'
    assert pd.Timestamp('2000-01-01') not in removed.get_times().values, 'time not removed'
    assert len(removed.get_actions()) == 1, 'action of removed step must be dropped'

    # vector of times (range)
    to_remove = pd.date_range('2000-01-01', '2010-12-31')
    removed_range = pastp.remove_times(time=to_remove)
    kept = removed_range.get_times()
    assert kept[(kept >= '2000-01-01') & (kept <= '2010-12-31')].empty, 'range not removed'

    # by step number
    removed_step = pastp.remove_times(step=0)
    assert len(removed_step.get_times()) == n_times - 1, 'step not removed'


def test_string_date_arguments():
    # issue #29: str date arguments are accepted consistently
    pastp = read_mart_timesteps(FILE_PASTP)

    # add_action with a string time
    pastp.add_action(times='2000-01-01', variable='CALCUL_HDYNAM', action='ACTION', value=2)
    assert '2000-01-01' in pastp.get_actions(), 'add_action with str time failed'

    # remove_times with a string time (previously silently removed nothing)
    removed = pastp.remove_times(time='2000-01-01')
    assert pd.Timestamp('2000-01-01') not in removed.get_times().values, \
        'remove_times with str time failed'

    # slice_times with string bounds
    sliced = pastp.slice_times('2000-01-01', '2010-12-31')
    assert sliced.get_times().iloc[0] == pd.Timestamp('2000-01-01'), \
        'slice_times with str bounds failed'


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


def test_pastp_file_property():
    # issue #27: source file path is stored and reused by write_file()
    pastp = read_mart_timesteps(FILE_PASTP)
    assert pastp.pastp_file == Path(FILE_PASTP), 'source file path not stored'

    # write_file() with no filename falls back to self.pastp_file
    file_pastp_out = './tests/data/tmp_outputs/test_pastp_file.pastp'
    pastp.pastp_file = Path(file_pastp_out)
    pastp.write_file()
    assert Path(file_pastp_out).exists(), 'write_file() fallback on pastp_file failed'

    # a freshly created instance has no source file -> explicit error
    fresh = MartTimeSteps.from_dates(date_min='2000-01-01', date_max='2000-12-31', freq='D')
    assert fresh.pastp_file is None, 'pastp_file should default to None'
    with pytest.raises(ValueError):
        fresh.write_file()


def test_pastp_uk():
    pastp = read_mart_timesteps(FILE_PASTP_UK)

    min_date = pastp.times['time'].min().strftime('%Y-%m-%d')
    max_date = pastp.times['time'].max().strftime('%Y-%m-%d')
    assert min_date == '2025-11-25', "Wrong start date read"
    assert max_date == '2026-03-05', "Wrong end date read"


def test_remove_action():
    pastp = read_mart_timesteps(FILE_PASTP)
    pastp.add_times(dates=pd.date_range('2012-08-01', '2020-07-31', freq='D'))
    new_dt = pastp.get_times()
    actions_dates = (new_dt.dt.year>=2012) & (new_dt.dt.month==8) & (new_dt.dt.day == 1)

    # Add multiple actions to various timesteps
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
    pastp.add_action(new_dt.iloc[0], variable='CALCUL_HDYNAM', action='ACTION', value=2)

    # Test: remove all actions for a specific time
    pastp.remove_action(times='2012-08-01')
    d = pastp.get_actions()
    assert '2012-08-01' not in d, 'Error: action was not removed for time'
    assert '2013-08-01' in d, 'Error: action was incorrectly removed for other times'

    # Test: remove actions for a specific variable only
    pastp2 = read_mart_timesteps(FILE_PASTP)
    pastp2.add_times(dates=pd.date_range('2012-08-01', '2020-07-31', freq='D'))
    new_dt2 = pastp2.get_times()
    actions_dates2 = (new_dt2.dt.year>=2012) & (new_dt2.dt.month==8) & (new_dt2.dt.day == 1)
    for dt in new_dt2[actions_dates2]:
        pastp2.add_action(times=dt, variable='METEO_PLUIE', action='FICHIER', file='file_{}'.format(dt.year))
        pastp2.add_action(times=dt, variable='FLUX_PLUV', action='FICH_METE', step='*')

    pastp2.remove_action(times='2012-08-01', variable='METEO_PLUIE')
    d2 = pastp2.get_actions(time='2012-08-01')
    assert 'METEO_PLUIE' not in d2['2012-08-01'], 'Error: METEO_PLUIE not removed'
    assert 'FLUX_PLUV' in d2['2012-08-01'], 'Error: FLUX_PLUV was incorrectly removed'

    # Test: remove actions for specific variable and action mode
    pastp3 = read_mart_timesteps(FILE_PASTP)
    pastp3.add_times(dates=pd.date_range('2012-08-01', '2020-07-31', freq='D'))
    new_dt3 = pastp3.get_times()
    actions_dates3 = (new_dt3.dt.year==2012) & (new_dt3.dt.month==8) & (new_dt3.dt.day == 1)
    for dt in new_dt3[actions_dates3]:
        pastp3.add_action(times=dt, variable='CALCUL_HDYNAM', action='ACTION', value=1)
        pastp3.add_action(times=dt, variable='CALCUL_HDYNAM', action='ACTION', value=2)

    pastp3.remove_action(times='2012-08-01', variable='CALCUL_HDYNAM', action='ACTION')
    d3 = pastp3.get_actions(time='2012-08-01')
    assert 'CALCUL_HDYNAM' not in d3.get('2012-08-01', {}), 'Error: ACTION mode not removed'


def test_remove_action_with_steps():
    pastp = read_mart_timesteps(FILE_PASTP)
    pastp.add_action(steps=[0, 1, 2], variable='CALCUL_HDYNAM', action='ACTION', value=2)

    # Remove action by step numbers
    pastp.remove_action(steps=[0, 1])
    d = pastp.get_actions()

    time_step_0 = pastp.times.iloc[0]['time'].strftime('%Y-%m-%d')
    time_step_1 = pastp.times.iloc[1]['time'].strftime('%Y-%m-%d')
    time_step_2 = pastp.times.iloc[2]['time'].strftime('%Y-%m-%d')

    assert time_step_0 not in d, 'Error: action not removed for step 0'
    assert time_step_1 not in d, 'Error: action not removed for step 1'
    assert time_step_2 in d, 'Error: action was incorrectly removed for step 2'


def test_remove_action_with_freq():
    pastp = read_mart_timesteps(FILE_PASTP)
    pastp.add_action(freq='ME', variable='ETAT_HYD_CLIM', action='edition')

    # Remove all monthly actions
    pastp.remove_action(freq='ME', variable='ETAT_HYD_CLIM')
    d = pastp.get_actions(variable='ETAT_HYD_CLIM')
    assert len(d) == 0, 'Error: actions were not removed by frequency'


def test_remove_action_filter_without_variable():
    # Removing by action mode without naming a variable must only drop the
    # matching actions, not the whole timestep.
    pastp = read_mart_timesteps(FILE_PASTP)
    pastp.add_times(dates=pd.date_range('2012-08-01', '2013-07-31', freq='D'))
    pastp.add_action(times='2012-08-01', variable='METEO_PLUIE', action='FICHIER', file='rain.txt')
    pastp.add_action(times='2012-08-01', variable='FLUX_PLUV', action='FICH_METE', step='*')

    pastp.remove_action(times='2012-08-01', action='FICHIER')
    d = pastp.get_actions(time='2012-08-01')
    assert 'METEO_PLUIE' not in d['2012-08-01'], 'Error: FICHIER action not removed'
    assert 'FLUX_PLUV' in d['2012-08-01'], 'Error: non-matching action incorrectly removed'


def test_remove_action_filter_by_kwargs():
    # kwargs narrow the removal to a specific action configuration.
    pastp = read_mart_timesteps(FILE_PASTP)
    pastp.add_action(steps=[0], variable='CALCUL_HDYNAM', action='ACTION', value=1)
    pastp.add_action(steps=[0], variable='CALCUL_HDYNAM', action='ACTION', value=2)

    pastp.remove_action(steps=[0], variable='CALCUL_HDYNAM', action='ACTION', value=1)
    d = pastp.get_actions(variable='CALCUL_HDYNAM')
    remaining = [a for actions in d.values() for a in actions['CALCUL_HDYNAM']]
    assert len(remaining) == 1, 'Error: expected a single action left'
    assert remaining[0].get('value') == 2, 'Error: wrong action was removed'


def test_read_write_satur():
    """ test_debug_satur_not_kept_at_write #37 """

    pastp = """Fake pastp file
 #<V7.8a># --- Fin du texte libre --- ; Ne pas modifier/retirer cette ligne
 *** Début de la simulation    à la date : 31/12/1979 ; ***
  /CHARGE/EDITION          I= 1;
  /%SATURAT/EDITION        I= 1;
 *** Le pas :    1: se termine à la date : 01/01/1980 ; ***
  /*****/***** Fin de ce pas
 *** Le pas :    2: se termine à la date : 02/01/1980 ; ***
  /*****/***** Fin de ce pas
 *** Le pas :    3: se termine à la date : 03/01/1980 ; ***
  /*****/***** Fin de ce pas
"""
    with patch('builtins.open', return_value=io.StringIO(pastp)):
        times = MartTimeSteps.from_file(pastp)
    actions = times.get_actions()['1979-12-31']
    assert '%SATURAT' in actions
    times.write_file('tests/data/tmp_outputs/satur_test.pastp')
    times_rewrite = MartTimeSteps.from_file('tests/data/tmp_outputs/satur_test.pastp')
    actions = times_rewrite.get_actions()['1979-12-31']
    assert '%SATURAT' in actions


if __name__ == "__main__":
    pytest.main([__file__, '-v', '--no-cov'])
