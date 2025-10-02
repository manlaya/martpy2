#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
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
    r'(?P<date>\d+\.\d+|\d{2}/\d{2}/\d{4}( \d{2}:\d{2})?)\s*;'
)
PATTERN_TRANSIENT_STEP = (
    r"Le pas\s*:\s*(?P<step>\d+):\s*se termine.*la date\s*:\s*"
    r"(?P<date>\d+\.\d+|\d{2}/\d{2}/\d{4}(\s\d{2}:\d{2})?)\s*;"
)
PATTERN_END_STEP = r'\s{2}/\*{5}/\*{5} Fin de ce pas'
PATTERN_END_SIM = r'.*Fin de la simulation.*'

#  ---- Writer format ---- #
FMT_START_SIM  = ' *** Début de la simulation    à la date :{init_date}; ***'
FMT_START_TIMESTEP = ' *** Le pas :{istep:5d}: se termine à la date :{date_step}; ***'
FMT_END_TIMESTEP = '  /*****/***** Fin de ce pas'
FMT_END_SIM = ' ***        :     : Fin de la simulation :            ; ***'


class MartheTimeSteps:
    """ Object to create/edit Marthe timesteps

    Parameters
    ----------
    times: pd.DataFrame
        DataFrame with columns ['step', 'date', 'has_action']
    actions: dict, optional
        keys are dates in 'YYYY-MM-DD' format, values are list of actions (dicts)
    """

    def __init__(self, times, actions={}):
        self.times = times
        self.actions = actions

        min_date = self.times['date'].min()
        max_date = self.times['date'].max()
        self.time_window = (min_date, max_date)

    def add_action(
        self,
        times=None,
        steps=None,
        freq=None,
        variable=None,
        action=None,
        **kwargs
    ):
        pass

    def remove_action(
        self,
        times=None,
        steps=None,
        freq=None,
        variable=None,
        action=None,
        **kwargs
    ):
        pass

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
        lines.extend(_build_pastp(self.times['date'].to_list(), self.actions))
        lines.append(FMT_END_SIM)
        with open(filename, 'w', encoding=encoding) as f:
            f.write('\n'.join(lines))

    @staticmethod
    def from_file(file_pastp, encoding='ISO-8859-1'):
        return read_mart_timesteps(file_pastp, encoding)
    
    def set_hdynam_computation(
        self,
        freq=None,
        times=None,
        itimes=None,
        as_ext_file=False,
        as_freq_param=False,
    ):
        # TODO this exists in pymarthe
        return


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
            _pastp_dict['date'] = _parse_date_pastp(_pastp_dict.get('date'))
            
            # split lines to parse action in timestep
            # only parse after the time, otherwise it's not action
            # and after 1-index -> cause pattern leave '***\n' after time
            block = pastp[_match.end():].splitlines()[1:]
            
            _actions = _parse_parameter_block(block)
            # _actions = []
            # for line in block:
            #     _actions.append(_parse_parameter_line(line))
            
            if len(_actions) > 0:
                actions[_convert_date_to_str_iso(_pastp_dict['date'])] = _actions
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
        _start_step_str = FMT_START_SIM.format(init_date=date_str)
    else:
        _start_step_str = FMT_START_TIMESTEP.format(istep=istep, date_step=date_str)
    
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
