#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import numpy as np
import pandas as pd

from datetime import datetime

from martpy.inputs.io_utils import (
    _build_header,
    _parse_parameter_block,
    _build_parameter_line
)


# --- Parser pattern --- #
# more regex hell
_FLOAT_FMT = r'\d+\.\d+'
_DATE_FMT = r'(\d{2}/\d{2}/\d{4})( \d{2}:\d{2})?'

PATTERN_STEADY_STEP = (
    r' \*\*\* D.*but de la simulation.*:\s*'
    r'(?P<time>\d+\.\d+|\d{2}/\d{2}/\d{4}( \d{2}:\d{2})?)\s*;'
)
PATTERN_TRANSIENT_STEP = (
    r"Le pas\s*:\s*(?P<step>\d+):\s*se termine.*la date\s*:\s*"
    r"(?P<time>\d+\.\d+|\d{2}/\d{2}/\d{4}(\s\d{2}:\d{2})?)\s*;"
)
PATTERN_END_STEP = r'\s{2}/\*{5}/\*{5} Fin de ce pas'
PATTERN_END_SIM = r'.*Fin de la simulation.*'

#  ---- Writer format ---- #
FMT_START_SIM  = ' *** Début de la simulation    à la date :{init_time}; ***'
FMT_START_TIMESTEP = ' *** Le pas :{istep:5d}: se termine à la date :{time_step}; ***'
FMT_END_TIMESTEP = '  /*****/***** Fin de ce pas'
FMT_END_SIM = ' ***        :     : Fin de la simulation :            ; ***'


def _create_times(dates, date_min, date_max, freq, step=0):
    # creation of date sequence for time steps
    # either with dates or range of dates
    if dates is not None:
        dt = pd.Series(pd.to_datetime(dates)).reset_index()
        dt.columns = ['step', 'time']
        dt = dt.assign(has_action=False)
    elif (date_min is not None and date_max is not None):
        dt = pd.date_range(date_min, date_max, freq=freq)
        dt = pd.DataFrame(dt).reset_index()
        dt.columns = ['step', 'time']
        dt = dt.assign(has_action=False)
    else:
        raise ValueError('Either dates or date_min and date_max must be provided')
    if step != 0:
        dt['step'] = np.arange(step, step + len(dt))  # reset step number
    return dt


class MartheTimeSteps:
    """ Object to create/edit Marthe timesteps

    Parameters
    ----------
    times: pd.DataFrame
        DataFrame with columns ['step', 'time', 'has_action']
    actions: dict, optional
        keys are dates in 'YYYY-MM-DD' format, values are list of actions (dicts)
    """

    def __init__(self, times, actions={}):
        self.times = times
        self.actions = actions

        min_date = self.times['time'].min()
        max_date = self.times['time'].max()
        self.time_window = (min_date, max_date)
    
    def get_timesteps(self):
        """ Get times and steps number"""
        return self.times
    
    def get_times(self):
        """ Get datetime of the timesteps"""
        return self.times['time']
    
    def add_times(self, date_min=None, date_max=None, freq='D', dates=None):
        """ Add times to the timesteps
        
        Parameters
        ----------
        dates : pandas.DateTimeIndex or pandas.Series, optional
            a times/dates sequence to use, by default None. If None, use date_min and date_max
            to create a sequence of times with the frequency provided in parameter 
            `freq`.
        date_min : str or datetime, optional
            date of the first step to create a sequence, by default None.
        date_max : str or datetime, optional
            date of the last step to create a sequence, by default None
        freq : _type_, optional
            frequency of the sequence to create, by default 'D' (Daily).
            See pandas documentation for more information on available frequencies:
            https://pandas.pydata.org/docs/user_guide/timeseries.html#timeseries-offset-aliases
        
        Returns
        -------
        None
            Add dates to the timestep instance, in 'times' attribute
        """
        istep = self.times['step'].max() + 1
        dt = _create_times(dates, date_min, date_max, freq, step=istep)
        self.times = pd.concat([self.times, dt], ignore_index=True)
        self.time_window = (self.times['time'].min(), self.times['time'].max())
    
    def remove_times(self, time=None, step=None, min_date=None, max_date=None):
        """ Remove times from the timesteps

        Parameters
        ----------
        time : datetime, optional
            time to remove, by default None
        step : int, optional
            timestep number to remove, by default None
        min_date : datetime, optional
            min date for slice
        max_date : datetime, optional
            max date for slice

        Returns
        -------
        None
            Remove the timestep(s) from the timestep instance
        """
        if time is not None:
            time_key = _convert_date_to_str_iso(time)
            self.times = self.times.loc[self.times['time'] != time_key]
            self.actions.pop(time_key, None)
        elif step is not None:
            self.times = self.times.loc[~self.times['step'].isin(step)]
            self.times['step'] = self.times['step'].rank(method='first').astype(int) - 1
            self.times = self.times.sort_values(by='step')
            self.actions = {
                k: v for k, v in self.actions.items() if k in self.times['time'].dt.strftime('%Y-%m-%d')
            }
        elif min_date is not None or max_date is not None:
            if min_date is not None:
                self.times = self.times.loc[self.times['time'] >= min_date]
            if max_date is not None:
                self.times = self.times.loc[self.times['time'] <= max_date]
            self.times['step'] = self.times['step'].rank(method='first').astype(int) - 1
            self.times = self.times.sort_values(by='step')
            self.actions = {
                k: v for k, v in self.actions.items() if k in self.times['time'].dt.strftime('%Y-%m-%d')
            }
        else:
            pass

    def get_actions(self, time=None, step=None):
        """ Get actions for all or selected timestep

        Parameters
        ----------
        time : datetime, optional
            time to get actions for, by default None
        step : int, optional
            timestep number to get actions for, by default None
        
        Returns
        -------
        dict
            dictionnary of actions for the timestep(s) requested.
        """
        if time is not None:
            time_key = _convert_date_to_str_iso(time)
            return self.actions.get(time_key, {})
        elif step is not None:
            time_key = self.times.loc[self.times['step'].isin(step), 'time']
            if len(time_key) == 0:
                return {}
            time_key = _convert_date_to_str_iso(time_key.iloc[0])
            return self.actions.get(time_key, {})
        else:
            return self.actions

    def add_action(
        self,
        times=None,
        steps=None,
        variable=None,
        action=None,
        **kwargs
    ):
        """ Add actions to any timesteps

        Parameters
        ----------
        times : datetime or pandas.DateTimeIndex or pandas.Series, optional
            times to add actions, by default None.
        steps : int or list, optional
            timesteps number if no times are provided, by default None
        variable : str, optional
            marthe variable for the action, by default None
        action : str, optional
            action to do, by default None
        **kwargs
            parameters to the VARIABLE/ACTION to add.
            TODO: add documentation to implement kwargs for users.
            TODO: check action/variable and kwargs validity
        """
        new_actions = {}
        if times is None:
            if steps is not None:
                times = self.times.loc[self.times['step'].isin(steps), :]
        if isinstance(times, (str, datetime)):
            if type(times) is str:
                times = datetime.strptime(times, '%Y-%m-%d')
            times = [times]
        for time in times:
            key = _convert_date_to_str_iso(time)
            new_actions[key] = {
                # keep previous actions if any, order matters
                **self.actions.get(key, {}),
                variable.upper(): self.actions.get(key, {}).get(variable.upper(), [])+
                [
                    {**{'mode': action.upper()}, **kwargs}
                ],
            }
        self.actions = {**self.actions, **new_actions}
        self.times.loc[self.times['time'].isin(times), 'has_action'] = True

    def remove_action(
        self,
        times=None,
        steps=None,
        freq=None,
        variable=None,
        action=None,
        **kwargs
    ):
        raise NotImplementedError(
            'Method is not yet implemented. '
            'You can remove actions in self.actions dictionnary'
        )

    def write_file(self, filename, title='Marthe TimeSteps', encoding='ISO-8859-1'):
        """ Build a Timestep (`*.pastp`) file

        Parameters
        ----------
        filename : str
            name of the pastp file
        title : str, optional.
            First line of file (description, title)
        encoding : str, optional.
            encoding for file to write. Default
        """
        lines = []
        lines.extend(_build_header(title))
        lines.extend(_build_pastp(self.times['time'].to_list(), self.actions))
        lines.append(FMT_END_SIM)
        with open(filename, 'w', encoding=encoding) as f:
            f.write('\n'.join(lines))

    @staticmethod
    def from_file(file_pastp, encoding='ISO-8859-1'):
        return read_mart_timesteps(file_pastp, encoding)
    
    @classmethod
    def from_dates(self, date_min=None, date_max=None, freq='D', dates=None,):
        """ Create a MartheTimeSteps instance based on a list of dates or a frequency

        Parameters
        ----------
        dates : pandas.DateTimeIndex or pandas.Series, optional
            a dates sequence to use, by default None. If None, use date_min and date_max
            to create a sequence of dates with the frequency provided in parameter 
            `freq`.
        date_min : str or datetime, optional
            date of the first step to create a sequence, by default None.
        date_max : str or datetime, optional
            date of the last step to create a sequence, by default None
        freq : str, optional
            frequency of the sequence to create, by default 'D' (Daily).
            See pandas documentation for more information on available frequencies:
            https://pandas.pydata.org/docs/user_guide/timeseries.html#timeseries-offset-aliases

        Returns
        -------
        MartheTimeSteps
            a time step instance with the dates provided
        """
        dt = _create_times(dates, date_min, date_max, freq)
        return MartheTimeSteps(dt)
    
    def set_hdynam_computation(
        self,
        freq=None,
        times=None,
        itimes=None,
        as_ext_file=False,
        as_freq_param=False,
    ):
        # TODO this exists in pymarthe - check first
        raise NotImplementedError('Not yet available.... But Soon ! :)')
    
    def __repr__(self):
        print('\nMarthe timesteps')
        print('================')
        print('Datetime From: {}, to: {}'.format(self.time_window[0], self.time_window[1]))
        print('Number of steps: {}'.format(len(self.times)))
        print('Number of steps with action: {}'.format(len(self.actions)))
        return ''


def _parse_date_pastp(date_str):
    """ Parse a date string, read from pastp file into:
        - float if it is a numeric value,
        - datetime if it is a date with fmt DD/MM/YYYY or DD/MM/YYYY HH:MM
    """
    if date_str is None:
        return None
    elif re.match(_FLOAT_FMT, date_str):
        return float(date_str)
    elif re.match(_DATE_FMT, date_str):
        date, time = re.search(_DATE_FMT, date_str).groups()
        if time is not None:
            date_fmt = '%d/%m/%Y %H:%M'
        else:
            date_fmt = '%d/%m/%Y'
        return datetime.strptime(date_str, date_fmt)


def _convert_date_to_str(date):
    """ Convert datetime or float/int to str, according to expected format
    for Marthe timesteps file (pastp): float/int: >10, date: ^12, datetime: ^18
    """
    if isinstance(date, (int, float)):
        return '{:>10g}'.format(date)
    elif isinstance(date, (datetime, pd.Timestamp)):
        # get time to set fmt
        if date.hour == 0 and date.minute == 0:
            return '{:^12}'.format(date.strftime("%d/%m/%Y"))
        return '{:^18}'.format(date.strftime("%d/%m/%Y %H:%M"))


def _convert_date_to_str_iso(date):
    """ Convert datetime to str, leave int/float unchanged.
    used for to create/match key in actions dictionnary
    """
    if isinstance(date, (int, float)):
        return date
    elif isinstance(date, (datetime, pd.Timestamp)):
        # get time to set fmt
        if date.hour == 0 and date.minute == 0:
            return date.strftime("%Y-%m-%d")
        return date.strftime("%Y-%m-%dT%H:%M")


def read_mart_timesteps(file_pastp, encoding='ISO-8859-1'):
    """ Read a Marthe TimeStep file (`.pastp`)

    This function read and parse (istep, date [float or datetime]
    and actions in timestep) timesteps of Marthe project.

    Parameters
    ----------
    file_pastp : str or Path
        path to the timestep file (`*.pastp`)
    encoding : str, optional
        encoding used to read the file, by default 'ISO-8859-1'
    
    Returns
    -------
    MartTimeStep
    """
    
    with open(file_pastp, mode='r', encoding=encoding) as f:
        text_pastp = f.read()
    
    timesteps = re.split(PATTERN_END_STEP, text_pastp, flags=re.MULTILINE|re.DOTALL)
    dtime = []
    actions = {}
    for i, pastp in enumerate(timesteps):
        pastp = pastp.strip()
        
        if len(pastp) == 0 or re.match(PATTERN_END_SIM, pastp, re.I):
            continue
        
        if i == 0:
            _match = re.search(PATTERN_STEADY_STEP, pastp)
        else:
            _match = re.search(PATTERN_TRANSIENT_STEP, pastp)
        
        if _match:
            _pastp_dict = _match.groupdict()
            # at steady step, istep is not in pattern, add it
            _pastp_dict['step'] = int(_pastp_dict.get('step', i))
            _pastp_dict['time'] = _parse_date_pastp(_pastp_dict.get('time'))
            
            # split lines to parse action in timestep
            # only parse after the time, otherwise it's not action
            # and after 1-index -> cause pattern leave '***\n' after time
            block = pastp[_match.end():].splitlines()[1:]
            
            _actions = _parse_parameter_block(block)
            # _actions = []
            # for line in block:
            #     _actions.append(_parse_parameter_line(line))
            
            if len(_actions) > 0:
                actions[_convert_date_to_str_iso(_pastp_dict['time'])] = _actions
                _pastp_dict['has_action'] = True
            else:
                _pastp_dict['has_action'] = False
            
            dtime.append(_pastp_dict)
    
    dtime = pd.DataFrame(dtime)  # more efficient than append a DataFrame then concat...
    return MartheTimeSteps(dtime, actions)


def _build_timestep(istep, date, dactions):
    """ Build the lines for one time step of MARTHE pastp file.

    Parameters
    ----------
    istep: int
        index of time step. 0-based. The 0 step is steady state.
    date : datetime object or pd.Timestamp
        corresponding date for current timestep.
    dactions : dict
        dictionnary containing actions for current timestep.
        Keys are string dates in iso format (YYYY-MM-DDTHH:MM:SS)

    Returns
    -------
    lines : list of str
    """
    date_str = _convert_date_to_str(date)
    date_key_fmt = _convert_date_to_str_iso(date)
    
    if istep == 0:
        _start_step_str = FMT_START_SIM.format(init_time=date_str)
    else:
        _start_step_str = FMT_START_TIMESTEP.format(istep=istep, time_step=date_str)
    
    lines = [_start_step_str]
    actions_step = dactions.get(date_key_fmt, {})
    for variable, actions in actions_step.items():
        for action in actions:
            mode = action.pop('mode')
            action_str = _build_parameter_line(variable, mode, **action)
            lines.append(action_str)
    lines.append(FMT_END_TIMESTEP)
    return lines


def _build_pastp(dates, dactions):
    """ Build all lines of a pastp file

    Parameters
    ----------
    dates : list of datetime or pd.Series
        Dates of Marthe time steps.
    dactions : dict
        dictionnary containing actions for all timesteps.
        Keys are string dates in iso format (YYYY-MM-DDTHH:MM:SS)

    Return
    ------
    list of str
        list of lines to write in pastp file. One line per parameter per timestep.
        Lines are ordered by timestep and then by parameter.
        It Does NOT contains header/footer for pastp file 
        (see `MartheTimeStep.write_file` method to write a full pastp file)
    """
    lines = []
    for i, date in enumerate(dates):
        lines.extend(
            _build_timestep(i, date, dactions)
        )
    return lines


# TODO: def get_hdynam():
# from parsed pastp or parsed mart detect if external file, 
# if not detect step with HDYNAM (deal with 1,0,2,-1)
#  1 : activation (et pour les pas suivants),
#  2 : activation à ce pas de temps,
# -1 : désactivation à partir de ce pas;
#  0 : défaut, pas d'action (calcul à chaque pas de temps par défaut, si désactivé précédemment poursuite sans calcul)
# check for frequency in .mart
# for perman: check if 0 iter in mart


def write_evolution_file(df, filename):
    """ Write an external evolution file for Marthe HDYNAM computation
    or editions during simulation.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with date as index, value in column.
        e.g:
          - 0, 1, 2, -1 for HDYNAM computation. See Marthe documentation
          for details.
          - 0/1 for editions

    filename : str
        name of the file to write
    """
    df = pd.DataFrame(df.copy())  # force dataframe type
    col_date = df.index.name
    cols = list(df.columns)
    df_tmp = df.reset_index()
    df_tmp = df_tmp.assign(num_step=df_tmp.index+1)
    df[cols + ['num_step', col_date]].to_csv(
        filename,
        sep='\t',
        index=None,
        header=False
    )
