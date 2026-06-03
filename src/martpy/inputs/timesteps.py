#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from martpy.inputs._io_utils import (
    _build_header,
    _build_parameter_block,
    _filter_valid_opt_list_mail,
    _parse_parameter_block,
)
from martpy.utils.helper import _check_mart_key
from martpy.utils.config import get_lang


# Memo: check fmt here in MARTHE src/edi_pastp_prepro.f90:L752
# TODO add parsing for timestep (optional) names? useful? eg: *** thename // or ***; Nom=thename
# --- Parser pattern --- #
# more regex hell
_FLOAT_FMT = r'\d+\.\d+'
_DATE_FMT = r'(\d{2}/\d{2}/\d{4})( \d{2}:\d{2})?'

PATTERN_STEADY_STEP = (
    r' \*\*\* (?:D.*but de la simulation|Beginning of simulation).*:\s*'
    r'(?P<time>\d+\.\d+|\d{2}/\d{2}/\d{4}( \d{2}:\d{2})?)\s*;'
)
PATTERN_TRANSIENT_STEP = (
    r"(?:Le pas|Step)\s*:\s*(?P<step>\d+):\s*(?:se termine.*la date|Ends at date)\s*:\s*"
    r"(?P<time>\d+\.\d+|\d{2}/\d{2}/\d{4}(\s\d{2}:\d{2})?)\s*;"
)
PATTERN_END_STEP = r'\s{2}/\*{5}/\*{5} (?:Fin de ce pas|End of this Time Step)'
PATTERN_END_SIM = r'.*(?:Fin de la simulation|End of simulation).*'

#  ---- Writer format ---- #
FMT_START_SIM  = {
    'fr': ' *** Début de la simulation    à la date :{init_time}; ***',
    'en': ' *** Beginning of simulation  at date    :{init_time}; ***'
}
FMT_START_TIMESTEP = {
    'fr': ' *** Le pas :{istep:5d}: se termine à la date :{time_step}; ***',
    'en': ' *** Step   :{istep:5d}:      Ends at date    :{time_step}; ***'
}
FMT_END_TIMESTEP = {
    'fr': '  /*****/***** Fin de ce pas',
    'en': '  /*****/***** End of this Time Step'
}
FMT_END_SIM = {
    'fr': ' ***        :     : Fin de la simulation :            ; ***',
    'en': ' ***        :     : End of simulation    :            ; ***'
}


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


def _subset_times(times, step=1, freq='Y', day=1, month=8):
    """ subset times with options

    Parameters
    ----------
    times: pd.Serie
        serie with timestamp
    step: int (istep) or datetime
        when to start subset
    freq: str
    day : int
        (used if freq=M or freq=Y)
    month: int
        (used if freq=Y)
    """
    times = times.copy()
    if isinstance(step, int):
        times = times.iloc[step:]
    elif isinstance(step, datetime):
        times = times.loc[times >= step]
    else:
        raise TypeError('step argument must be int or datetime')

    # TODO: create a date_range with user freq and use to subset times?
    if freq is None:
        times = times.iloc[0]
    elif freq.upper() == 'Y':
        query = (times.dt.day == day) & (times.dt.month == month)
        times = times[query]
    elif freq.upper() == 'M':
        query = (times.dt.day == day)
        times = times[query]
    elif freq.upper() == 'W':
        times = times[times.day_of_week == 0]
    elif freq.upper() == 'D':
        query = (times.dt.hour == 0) & (times.dt.minute == 0)
        times = times[query]
    else:
        raise NotImplementedError(
            "Method not yet available. Use freq=None or freq='Y'"
        )
    return times


def _clean_steps_and_actions(times, actions):
    times['step'] = times['step'].rank(method='first').astype(int) - 1
    times = times.sort_values(by='step')
    valid_keys = {_convert_date_to_str_iso(t) for t in times['time']}
    actions = {
        k: v for k, v in actions.items() if k in valid_keys
    }
    return MartTimeSteps(times, actions)


class MartTimeSteps:
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
        # source file path, set by from_file()/read_mart_timesteps() after parsing
        self.pastp_file = None

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
        dates : pandas.DateTimeIndex, pandas.Series or list of str/datetime, optional
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
        times = pd.concat([self.times, dt], ignore_index=True)
        if not times[times.duplicated(subset='time')].empty:
            # security if user add existing times
            times = times.drop_duplicates(subset='time', keep='first')  # keep previous
            times['step'] = np.arange(1, len(times)+1)
        self.times = times
        self.time_window = (self.times['time'].min(), self.times['time'].max())

    def remove_times(self, time=None, step=None):
        """ Remove specific timesteps from the timesteps

        Parameters
        ----------
        time : str, datetime or sequence of these, optional
            timestep date(s) to remove. Accepts a single date (scalar) or a
            vector (list, pandas.DatetimeIndex, ...). To remove a date range, pass for instance
            `time=pd.date_range(start, end)`.
        step : int or list of int, optional
            timestep number(s) to remove.

        Returns
        -------
        MartTimeSteps
            A new instance without the removed timestep(s).

        Notes
        -----
        Use :py:meth:`slice_times` to keep a `[min_date, max_date]` range.
        """
        times = self.times.copy()
        if time is not None:
            time = _to_datetime(time)
            times = times.loc[~times['time'].isin(time)]
        elif step is not None:
            if isinstance(step, int):
                step = [step]
            times = times.loc[~times['step'].isin(step)]
        else:
            # nothing to remove, return a copy
            return MartTimeSteps(times, dict(self.actions))

        return _clean_steps_and_actions(times, self.actions)

    def slice_times(self, min_date=None, max_date=None):
        # TODO for slice: add keep_init bool (keep file read at timestep 0 for ex)
        """ Slice times from the timesteps

        Parameters
        ----------
        min_date : str or datetime, optional
            min date for slice. Strings are accepted and parsed by pandas.
        max_date : str or datetime, optional
            max date for slice. Strings are accepted and parsed by pandas.

        Returns
        -------
        MartTimeSteps
            A new marthe time step instance with the sliced the timestep(s)
        """
        times = self.times.copy()
        if min_date is not None:
            min_date = pd.to_datetime(min_date)
            times = times.loc[times['time'] >= min_date]
        if max_date is not None:
            max_date = pd.to_datetime(max_date)
            times = times.loc[times['time'] <= max_date]
        return _clean_steps_and_actions(times, self.actions)

    def get_actions(self, *, time=None, step=None, variable=None, as_dataframe=False):
        """ Get actions for all or selected timesteps/variables

        Only keywords argument accepted (key=value).

        Parameters
        ----------
        time : str, datetime or sequence of these, optional
            timestep date(s) to get actions for, by default None.
        step : int or list of int, optional
            timestep number(s) to get actions for, by default None
        variable : str, optional
            marthe variable to get actions for, by default None
        as_dataframe : bool, optional
            return actions as a dataframe, by default False

        Returns
        -------
        dict
            dictionnary of actions for the timestep(s) requested.

        Examples
        --------
        >>> pastp = read_mart_timesteps('hallue.pastp')
        >>> act = pastp.get_actions()  # get all actions
        >>> act = pastp.get_actions(time='2012-07-31')  # get actions for specific time
        >>> act = pastp.get_actions(step=[0,-1])  # get actions for specific step
        >>> act = pastp.get_actions(variable='CALCUL_HDYNAM')  # get actions for specific variable
        """

        if time is not None or step is not None:
            if time is not None:
                time_keys = self.times.set_index('time').loc[time, :]
                time_keys = time_keys.name if isinstance(time_keys, pd.Series) else time_keys.index
            elif step is not None:
                time_keys = self.times.iloc[step, :]['time']

            if isinstance(time_keys, (list, tuple, pd.Series, pd.DatetimeIndex)):
                time_keys = [_convert_date_to_str_iso(t) for t in time_keys]
            elif isinstance(time_keys, (datetime, pd.Timestamp)):
                time_keys = [_convert_date_to_str_iso(time_keys)]
            else:
                time_keys = [time_keys]

            filtered_actions = {
                k: v for k, v in self.actions.items() if k in time_keys
            }

        elif variable is not None:
            variable = variable.upper()
            _check_mart_key(variable)
            filtered_actions = {}
            for time_key, actions in self.actions.items():
                if variable in actions:
                    filtered_actions[time_key] = {
                        variable: actions[variable]
                    }

        else:
            filtered_actions = self.actions

        if not as_dataframe:
            return filtered_actions
        else:
            return self._get_actions_as_dataframe(filtered_actions)

    def _get_actions_as_dataframe(self, actions):
        # data = pd.DataFrame.from_dict(d, orient='index')
        df = []
        for date, values in actions.items():
            for variable, list_values in values.items():
                tmp = pd.DataFrame(
                    list_values,
                    index=pd.MultiIndex.from_tuples(
                        [(pd.to_datetime(date), variable) for x in list_values]
                    )
                )
                df.append(tmp)
        df = pd.concat(df)
        return df

    def add_action(
        self,
        times=None,
        steps=None,
        freq=None,
        variable=None,
        action=None,
        **kwargs
    ):
        """ Add actions to any timesteps

        Parameters
        ----------
        times : str, datetime, pandas.DateTimeIndex or pandas.Series, optional
            times to add actions, by default None. Strings are accepted and
            parsed by pandas (scalar or vector).
        steps : int or list, optional
            timesteps number if no times are provided, by default None.
        freq : str, optional
            A frequency string to create a DateTimeIndex if no times are provided.
            If provided, action will be added to every timestep matching this frequency.
            By default None (not used). See pandas.DateOffset for more details:
            https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#dateoffset-objects
        variable : str, optional
            marthe variable for the action, by default None
        action : str, optional
            action to do, by default None
        **kwargs
            parameters to the VARIABLE/ACTION to add.
            Available kwargs for each ACTION:
            - ACTION : `active` (`0,1,2,-1`),
            - FICHIER: `file`,
            - GRILLE : `grid`,
            - LIST_MAIL : `file`, `opt_list_mail` (see :py:func:`get_opt_list_cells`)
            - COUCHE : `layer`, `value`,
            - MAILLE : `col`, `row`, `layer`, `value`,
            - FICH_METE : `step`,
            - ZONEP     : `zone`, `value`,
            - ZONE_SOL  : `zone`, `value`,
            - ZONE_CLIM : `zone`, `value`,
            - ZONE_IRRI : `zone`, `value`,
            - ZONE_GEO  : `zone`, `value`,
            - ZONE_GEO2 : `zone`, `value`,
            - ZONE_GEO3 : `zone`, `value`,
            - EDITION   : `edit` (optional, if edition asked, edit will be set to 1),
            - TRONCON   : `afluent`, `tronc`, `value`,
            - LAC_GLOB  : `lake`, `value`,
            - LAC_EXUT  : `lake`, `afluent`, `value`,

            For available variable, please check
            :py:func:`martpy.get_mart_variables_list`
        """
        new_actions = {}
        _check_mart_key(variable)
        # TODO _check_mart_action(variable, action)
        if times is None:
            if steps is not None:
                # times = self.times.loc[self.times['step'].isin(steps), :]
                times = self.times.iloc[steps,:]['time']
            elif freq is not None:
                times = pd.date_range(
                    self.times['time'].min(), self.times['time'].max(), freq=freq
                )
            else:
                raise ValueError('Please provide times or steps')

        # accept scalar or vector, str or datetime (normalized via pandas)
        times = _to_datetime(times)

        for time in times:
            key = _convert_date_to_str_iso(time)
            if action.lower() == 'edition' and kwargs.get('edit') is None:
                kwargs['edit'] = 1
            new_action_list = self.actions.get(key, {}).get(variable.upper(), []) + [
                {'mode': action.upper(), **kwargs}
            ]
            new_actions[key] = {
                # keep previous actions if any, order matters
                **self.actions.get(key, {}),
                variable.upper(): _deduplicate_action_list(new_action_list),
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

    def set_met_forcings(
        self,
        tpl_name,
        path_data='./',
        mode=1,
        step=1,
        freq='Y',
        day=1,
        month=8
    ):
        """ Set meteorological forcings with sequential [yearly] files

        Parameters
        ----------
        tpl_name : list or tuple
            list or tuple of two template string for file names.
            Order matters: [precip, evap] if mode=1, or [infiltr, runoff] if mode
            is 2 or 4. See example below.
            Template will be filled with year and year+1
        path_data: str or Path, optional
            path to met data. By default current dir.
        mode: int, optional
            Hydroclimatic forcings mode. Depend of the hydroclimatic balance
            used in user's model. See MARTHE guide for more explanations.
            Accepted values:
                - 1: Gardenia coupled balance, use Rainfall and potential
                evaporatranspiration as forcings;
                - 2 or 4: Use infiltration and runoff fluxes.
        setp: int or datetime, optional
            Step to start adding forcings. If int is passed, it is used to find
            the step indice ; if datetime is passed, it used to find the date
            in timesteps.
        freq : str, optional
            frequency to add meteorological forcings, by default 'Y' for yearly
            (based on yearly files from Météo-France). If None, data are only
            added to the 0 timestep (steady state).

        Returns
        -------
        None
            Set new actions to current instance.

        Notes
        -----
        To add meteorological forcings only to the 1st timestep with constant
        files name use arguments `step=1` and `freq=None` together with tpl_name
        without format tags (eg `['File1', 'File2']`).

        Example
        -------
        >>> pastp.set_forcings(
        ...     [
        ...         'DRAIN_SURFEX_V8F_JOU_{}_{}_ASCII',
        ...         'RUNOFF_SURFEX_V8F_JOU_{}_{}_ASCII'
        ...     ],
        ...     '/gpfs/projets/poseidon/SAFRAN/',
        ...     mode=4,
        ... )
        """
        # from pandas.tseries.offsets import DateOffset
        lang = get_lang()
        if mode == 1:
            if lang == 'fr':
                var1, var2 = 'METEO_PLUIE', 'METEO_ETP'
                flux1, flux2 = 'FLUX_PLUV', 'FLUX_ETP'
            else:
                var1, var2 = 'METEO_RAIN', 'METEO_PET'
                flux1, flux2 = 'RAIN_FLUX', 'PET_FLUX'
        elif mode in [2,4]:
            if lang == 'fr':
                var1, var2 = 'METEO_RECHARG', 'METEO_RUISSEL'
                flux1, flux2 = 'RECHARGE', 'RUISSEL'
            else:
                var1, var2 = 'METEO_RECHARG', 'METEO_RUNOFF'
                flux1, flux2 = 'RECHARGE', 'RUNOFF'
        else:
            raise ValueError('Unknow mode. Accepted values: 1,2,4')

        times = self.get_times()
        times = _subset_times(times, step, freq, day, month)

        for t in times:
            self.add_action(
                times=t,
                variable=var1,
                action='FICHIER' if lang == 'fr' else 'FILE',
                file_path=Path(path_data, tpl_name[0].format(t.year, t.year+1))
            )
            self.add_action(
                times=t,
                variable=var2,
                action='FICHIER' if lang == 'fr' else 'FILE',
                file_path=Path(path_data, tpl_name[1].format(t.year, t.year+1))
            )
            self.add_action(
                times=t,
                variable=flux1,
                action='FICH_METE' if lang == 'fr' else 'METE_FILE',
                step='*'
            )
            self.add_action(
                times=t,
                variable=flux2,
                action='FICH_METE' if lang == 'fr' else 'METE_FILE',
                step='*'
            )
        return

    def set_pumping_data(self, file_tpl, step=1, freq='M', opt=None):
        """ Add pumping data to Marthe Timesteps, with XY format,
        based on frequency

        Parameters
        ----------
        file_tpl : str
            file name template to add data. Template will be filled with
            year, month [day].
        step : int, optional
            initial step when adding data, by default 1
        freq : str, optional
            frequency to add data, by default 'M' (monthly)
        opt : list, optional
            List of options to use when reading data, by default no options are used.
            Available options are:
                - sum (in Marthe files: Somm_Mail) : aggregate (sum) pumping by cell
                - mean (Moyenne) : aggregate in cell (average)
                - keep_9999 (Keep_9999) : keep special values (9999., ie do not
                overwrite with new data)
                - init_zero (Init_a_Zero): initialize values with 0.
                - xyv (X_Y_V) : fmt X,Y,Value
                - xyc (X_Y_C) : fmt X,Y,Layer
                - xyz (X_Y_Z) : fmt X,Y,Z
        """
        # use default opts ? <X_Y_C> <Somm_Mail> <Keep_9999>
        if opt is None:
            opt = []
        times = self.get_times()
        times = _subset_times(times, step, freq, day=1)
        lang = get_lang()
        opt = _filter_valid_opt_list_mail(opt, errors='raise')
        for t in times:
            self.add_action(
                times=t,
                variable='DEBIT' if lang == 'fr' else 'DISCHARGE',
                action='LIST_MAIL' if lang == 'fr' else 'LIST_CELL',
                file_path=file_tpl.format(t.year, t.month, t.day),
                opt_list_mail=opt
            )
        return

    def write_file(
        self,
        filename=None,
        write_ext_files=False,
        title='Marthe TimeSteps',
        encoding='ISO-8859-1',
        lang=None,
        **kwargs
    ):
        """ Build a Timestep (`*.pastp`) file

        Parameters
        ----------
        filename : str, Path, optional
            name of the pastp file. If None (default), fall back to the source
            file path stored in `self.pastp_file` (set when the instance was
            loaded via `from_file`). Raises a ValueError if both are None.
        write_ext_files : bool, optional
            Write external files (e.g. `.modin` file), by default False
            If True, external files are written in the .mart file
        title : str, optional.
            First line of file (description, title)
        encoding : str, optional.
            encoding for file to write. Default
        lang: str, optional
            language of pastp file. Default is
            the current language of the configuration. See :py:func:`get_lang`.
            and :py:func:`set_lang`.
        """
        if filename is None:
            filename = self.pastp_file
        if filename is None:
            raise ValueError(
                'No filename provided and no source file path available '
                '(self.pastp_file is None). Please provide a filename.'
            )
        lang = get_lang() if lang is None else lang
        kwargs['path'] = Path(filename).parent  # used if write_ext_files
        lines = []
        lines.extend(_build_header(title))
        lines.extend(_build_pastp(
            self.times['time'].to_list(), self.actions, write_ext_files, lang, **kwargs
        ))
        lines.append(FMT_END_SIM.get(lang))
        with open(filename, 'w', encoding=encoding) as f:
            f.write('\n'.join(lines))

    @staticmethod
    def from_file(file_pastp, encoding='ISO-8859-1'):
        return read_mart_timesteps(file_pastp, encoding)

    @classmethod
    def from_dates(cls, date_min=None, date_max=None, freq='D', dates=None,):
        """ Create a MartTimeSteps instance based on a list of dates or a frequency

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
        MartTimeSteps
            a time step instance with the dates provided
        """
        dt = _create_times(dates, date_min, date_max, freq)
        return cls(dt)

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
        msg = '\nMarthe timesteps\n'
        msg += '================\n'
        msg += 'Datetime From: {}, to: {}\n'.format(self.time_window[0], self.time_window[1])
        msg += 'Number of steps: {}\n'.format(len(self.times))
        msg += 'Number of steps with action: {}\n'.format(len(self.actions))
        return msg


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
        date_fmt = '%d/%m/%Y %H:%M' if time is not None else '%d/%m/%Y'
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


def _deduplicate_action_list(action_list):
    """Remove duplicate action dicts from a list, keeping the last occurrence.

    Uses repr() for comparison to handle unhashable values (lists, Path objects).
    """
    seen_keys = []
    unique_actions = []
    for action in reversed(action_list):
        canonical_key = repr(sorted(action.items(), key=lambda kv: kv[0]))
        if canonical_key not in seen_keys:
            seen_keys.append(canonical_key)
            unique_actions.insert(0, action)
    return unique_actions


def _to_datetime(dates):
    """ Normalize a date-like argument to pandas datetime.

    Accepts a scalar (str, datetime, pd.Timestamp) or a vector (list, tuple,
    pandas.Series, pandas.DatetimeIndex). Strings are parsed by pandas.
    Always returns a pandas.DatetimeIndex so callers can use it uniformly
    (iteration, `.isin`, ...).
    """
    if isinstance(dates, (str, datetime, pd.Timestamp)):
        dates = [dates]
    return pd.to_datetime(list(dates))


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

    timesteps = re.split(
        PATTERN_END_STEP, text_pastp, flags=re.MULTILINE|re.DOTALL|re.IGNORECASE
    )
    dtime = []
    actions = {}
    for i, pastp in enumerate(timesteps):
        pastp = pastp.strip()

        if len(pastp) == 0 or re.match(PATTERN_END_SIM, pastp, re.I):
            continue

        if i == 0:
            _match = re.search(PATTERN_STEADY_STEP, pastp, re.IGNORECASE)
        else:
            _match = re.search(PATTERN_TRANSIENT_STEP, pastp, re.IGNORECASE)

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
    timesteps = MartTimeSteps(dtime, actions)
    timesteps.pastp_file = Path(file_pastp)
    return timesteps


def _build_timestep(istep, date, dactions, write_ext_files=False, lang='fr', **kwargs):
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
    write_ext_files : bool, optional
        Option to write modin as external files. Default is False: modin instructions
        are melted in the .mart|.pastp file.
    lang: str, optional
        language to use (fr, en). Default is 'fr'

    Returns
    -------
    lines : list of str
    """
    lang = lang.lower()

    date_str = _convert_date_to_str(date)
    date_key_fmt = _convert_date_to_str_iso(date)

    if istep == 0:
        _start_step_str = FMT_START_SIM.get(lang).format(init_time=date_str)
    else:
        _start_step_str = FMT_START_TIMESTEP.get(lang).format(istep=istep, time_step=date_str)

    lines = [_start_step_str]
    actions_step = dactions.get(date_key_fmt, {})
    lines.extend(
        _build_parameter_block(actions_step, write_ext_files, mode='list', **kwargs)
    )
    lines.append(FMT_END_TIMESTEP.get(lang))
    return lines


def _build_pastp(dates, dactions, write_ext_files, lang='fr', **kwargs):
    """ Build all lines of a pastp file

    Parameters
    ----------
    dates : list of datetime or pd.Series
        Dates of Marthe time steps.
    dactions : dict
        dictionnary containing actions for all timesteps.
        Keys are string dates in iso format (YYYY-MM-DDTHH:MM:SS)
    write_ext_files : bool, optional
        Write external files (e.g. `.modin` file), by default False
        If True, external files are written in the .mart file
    lang : str, optional
        language of pastp file. Default is french ('fr').
        Other option is 'en' for english.

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
            _build_timestep(i, date, dactions, write_ext_files, lang, **kwargs)
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
          - 0, 1, 2, -1 for HDYNAM computation. See Marthe documentation for details.
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
