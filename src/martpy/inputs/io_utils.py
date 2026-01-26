#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from pathlib import Path

from martpy.utils.constant import (
    _ACTION_PARSER,
    _OPT_MAIL_PARSER,
    ACTIONS_FMT,
    EDITIONS_FMT,
    MART_VERSION,
    OPT_LIST_MAIL,
)
from martpy.utils.helper import _check_mart_key
from martpy.utils.config import get_lang



def _build_header(title, lang=None):
    if lang is None:
        lang = get_lang()
    lines = [title]
    if lang.lower() == 'fr':
        lines.append(
            f' #<V{MART_VERSION}># --- Fin du texte libre --- ;'
            ' Ne pas modifier/retirer cette ligne '
        )
    else:
        lines.append(
            f' #<V{MART_VERSION}># --- End of Header lines --- ;'
            ' Do not modify/delete this line '
        )
    return lines


def _parse_param_value(val, typ):
    """ Parse value in a parameter line from mart or pastp file
    (fmt /VARIABLE/ACTION ...C=VALUE V=VALUE2)

    Value:
    - *   : unchanged
    - 1:2 : range from 1 to 2
    - =24 : uniform value (for a grid mode)
    - 1e2 : just a float value

    Parameters
    ----------
    val : str
        Value to parse
    typ : type
        Expected type of the value.

    Returns
    -------
    list or str
        Parsed value of type `typ`
    """
    if '*' in val:
        return val
    elif ':' in val:
        tmp = val.split(':')
        return list(range(int(tmp[0]), int(tmp[1])+1))
    elif '=' in val:
        tmp = val.split('=')[1]
        return typ(tmp)
    else:
        return typ(val)


def _infer_variable_dtype(var, value):
    """ Try to guess type for a value based on variable in
    an Action Parameter (in .mart or .pastp)

    all indices (column, row, grid, zone, etc.) should be integer
    a file should be a string,
    a fixed value is a float
    """
    if var == 'value':
        return float
    elif var == 'grid':
        if '=' in value:
            return float
        else:
            return str
    elif var == 'file':
        return str
    else:
        return int


def _parse_list_mail_opt(line: str):
    """ Parse successive options for a LIST_MAIL action
    """
    _keys = {re.sub(r'[<|>]', '', v): k for k, v in OPT_LIST_MAIL.items()}
    _opts = re.findall(_OPT_MAIL_PARSER, line)
    return [_keys.get(x) for x in _opts]


def _parse_units_time(unit_line):
    # objective: parse 'day', 'hour', 'min', 's', etc.
    # return a dict with base unit and multiplier if any
    raise NotImplementedError


def _parse_units_si(unit_line):
    # objective: parse 'm/s', 'm3/s', 'mm/day', '°C', 'W/m2', etc.
    # return a dict with base unit and multiplier if any
    raise NotImplementedError


def _parse_param_file_and_col(line):
    """ parse File= VALUE[; Col=INT] format
    """
    pattern = r'File=\s*(?P<file_evol>\S+);+\s*(?:Col=\s*(?P<file_column>\d+))?'
    match = re.search(pattern, line)
    if match:
        return match.groupdict()
    else:
        return {}


def _parse_parameter_line(line, verbose=False):
    """ Parse a parameter line in Marthe files (*.mart or  *.pastp)

    Parameters
    ----------
    line : str
        a parameter line from mart or pastp files.
    verbose : bool, optional
       Print debug information, by default False

    Returns
    -------
    dict
        Dictionnary containing variables and values of parameter line
    """
    parsed_params = {}

    if '!' in line or re.match(r'^\s*[#|!]', line):
        return None

    pattern = r'^\s*(\d?)?/(\w+)/(\w+)\s*.*$'
    # TODO match for syntax /VAR/MODE/[FIX=NAQ;]   N=...  ;
    # here [] design optional pattern
    # only (re) god knows what it does:
    # pattern = r'^\s*(\d?)?/(\w+)/(\w+)(?:\s*/FIX=(\w+);)?\s*.*$'
    # beside jokes:
    #   - `(?:...)` should exclude pattern,
    #   - then nested `(...?)` should return the pattern inside,
    #   - final `?` should make it optional
    _match = re.search(pattern, line)
    if _match:
        grid, variable, mode = _match.groups()
        # grid, variable, mode, fix = _match.groups()
        parsed_params[variable] = {
            'mode': mode,
            'grid_id': int(grid) if grid != '' else 0
        }
        _line_parser = _ACTION_PARSER.get(mode)
        if _line_parser is not None:
            pattern = re.compile(_line_parser)
            _submatch = re.search(pattern, line)
            if _submatch:
                _param_values = {}
                for k, v in _submatch.groupdict().items():
                    _type = _infer_variable_dtype(k, v) if mode != 'ACTION' else int
                    _param_values[k] = _parse_param_value(v, _type)
                if mode in ['LIST_MAIL', 'LIST_CELL']:
                    _param_values['opt_list_mail'] = _parse_list_mail_opt(line)
                file_evol_dict = _parse_param_file_and_col(line)
                parsed_params[variable] = {
                    **parsed_params[variable],
                    **_param_values,
                    **file_evol_dict
                }
        else:
            if verbose:
                print('line parser missing for:', mode)
    return parsed_params


def _parse_parameter_block(block_lines, path=None, verbose=False):
    """ Parse a params/actions block for .mart or .pastp

    This function loop over lines in block to call :py:func:`_parse_parameter_line`
    and merge results

    Parameters
    ----------
    block_lines : list of str
        lines in the block to parse
    path : str, optional
        path to the mart/pastp file, by default None
        it is useful to store path of file if needed (add it to file referenced in
        params).
        e.g. for MODIFIC key, to be able to read the '*.modin' file
    verbose : bool, optional
        whether to print debug information, by default False
    """
    params = {}
    for line in block_lines:

        iparam = _parse_parameter_line(line, verbose=verbose)
        if iparam is None or len(list(iparam.keys())) == 0:
            continue

        key = list(iparam.keys())[0]  # one line has always one key here
        iparam[key]['as_external_file'] = False

        if key == 'MODIFIC':
            # MODIFIC allow user to set more parameter in external file '*.modin'
            fmodin = iparam[key].get('file')
            with open(Path(path, fmodin), mode='r', encoding='ISO-8859-1') as f:
                fmodin_lines = f.readlines()
            # => recursive call to parse this file
            modin_params = _parse_parameter_block(fmodin_lines)
            # add external file flag for all values, for writers
            for k, v in modin_params.items():
                modin_params[k] = [
                    {**x, 'as_external_file': True, 'external_file': fmodin} for x in v
                ]
            iparam = modin_params  # replace parsed params

        # here we combine dict for all keys, if MODIFIC several keys, only one otherwise
        for k, v  in iparam.items():
            list_vals = params.get(k, [])
            if not isinstance(iparam[k], list):
                # make it a list if several option for same variable
                # but if modific was there, already a list
                iparam[k] = [iparam[k]]
            iparam[k] = list_vals + iparam[k]  # combine previous lines with current
            params = {**params, **iparam}  # combine dict results

    return params


def _format_params_for_writer(dict_args):
    clean_dict = {}
    for k, v in dict_args.items():
        if k in ['as_external_file', 'opt_list_mail']:
            # do not change these parameters
            _val = v
        else:
            if isinstance(v, (list, tuple)) and len(v) > 0:
                # WARNING: not perfect... but if range, take only min/max
                _val = '{}:{}'.format(min(v), max(v))
            elif isinstance(v, bool):
                _val = int(v)
            else:
                _val = v
        clean_dict[k] = _val
    return clean_dict


def _filter_valid_opt_list_mail(opts, errors='ignore'):
    # errors = ignore (default) or raise
    available_opts = OPT_LIST_MAIL.keys()
    _opts = [opt for opt in opts if opt.lower() in available_opts]
    if errors == 'raise':
        invalid = [f'<{opt}>' for opt in opts if opt.lower() not in available_opts]
        if len(invalid) != 0:
            raise ValueError(
                'Unknow option for `list_mail` action: {} '.format(', '.join(invalid)) +
                'Please use: {}'.format(', '.join(list(available_opts)))
            )
    return _opts


def _format_opt_list_mail(opts):
    return [OPT_LIST_MAIL.get(opt.lower()) for opt in opts]


def _build_parameter_line(variable, action, **kwargs):
    """ Edit a line of a Marthe time step file or mart file (general parameters)

    TODO (?) deal with external_file option, 'MODIFIC' key, and '*.modin' file

    Parameters
    ----------
    variable : str
        Variable to edit. Possible values are all the variable of MARTHE
    action : str
        Geometry. Possible values are in ACTIONS_FMT dictionnary keys.
    kwargs : dict
        Other options depending on the typ. See ACTIONS_FMT and EDITIONS dictionnaries.

    Returns
    -------
    line : str
        Line formatted for the MARTHE file
    """
    action, variable = action.upper(), variable.upper()  # force uppercase
    _check_mart_key(variable)  # assert is a valid marthe variable
    var_type = '/{0}/{1}'.format(variable, action)
    kwargs = _format_params_for_writer(kwargs)

    # Case we have a time serie file after a modification
    # this does not concern actions with file required
    filename = kwargs.get('file_evol', '')
    if filename and action not in ['FICH_METE', 'GRILLE', 'FICHIER', 'LIST_MAIL']:
        filename =' File= {0}'.format(filename)

    # Case we select a specific column in a tabular time serie file
    file_col = kwargs.get('file_column', '')
    if file_col and int(file_col) == 1:
        file_col = ''
    elif file_col and int(file_col) > 1:
        file_col = '; Col={0}'.format(file_col)

    if action == 'EDITION':
        # TODO: complete options for EDITION, edit config._ACTION_PARSER first
        opts = ['edit', 'V', 'L', 'S', 'Z', 'I', 'F', 'B', 'C', 'P', 'Gig']
        dtemp = {opt: kwargs.get(opt, ' ') for opt in opts}
        dopt = EDITIONS_FMT.get(variable, 'I= 1;')
        option_str = dopt.format(**dtemp)
        option_str = '{0}{1}'.format(option_str, filename)

    else:
        if action in ['GRILLE', 'GRID'] and isinstance(kwargs.get('grid'), (int, float)):
            # special case for grid uniform value
            kwargs['grid'] = '={0}'.format(kwargs['grid'])

        option_str = ACTIONS_FMT[action].format(**kwargs)

        if action in ['LIST_MAIL', 'LIST_CELL']:
            opts = _filter_valid_opt_list_mail(kwargs.get('opt_list_mail', []))
            opts = _format_opt_list_mail(opts)
            option_str = '{0} {1}'.format(option_str, ' '.join(opts))
        elif action in ['COUCHE', 'MAILLE', 'TRONCON', \
                        'ZONE_GEO', 'ZONE_METEO', 'ZONE_SOL', 'ZONEP']:
            option_str = '{0}{1}{2}'.format(option_str, filename, file_col)

    return '  {0:25}{1}'.format(var_type, option_str)


def _build_parameter_block(dict_param, mode='str'):
    """ Build a block of parameters for MARTHE general parameters, timesteps
    of initial modifications (modin)

    Parameters
    ----------

    dict_param: dict
        dictionnary of parameters to write as a block (init param, modin, timestep),
        as read with :py:func:`_parse_parameter_block`.
    mode: str, optional
        `str` (default) or `list` to return parameters as a multiline string
        or as a list of lines

    Returns
    -------
    str or list
        str or list of str containing the parameter to write in MARTHE fmt
    """

    if mode == 'str':
        params = ''
    elif mode == 'list':
        params = []
    else:
        raise ValueError('Unknown mode. Please use `str` or `list`')

    for variable, actions in dict_param.items():
        for action in actions:
            _mode = action.pop('mode')
            line = _build_parameter_line(variable, _mode, **action)
            if mode == 'str':
                params += f"{line}\n"
            elif mode == 'list':
                params.append(line)
    return params


def _write_modin(dict_action, fname, lang=None):
    if lang is None:
        lang = get_lang()

    lines = _build_parameter_block(dict_action)
    if lang.lower() == 'fr':
        lines += '  /*****/***** Fin d\'Initialisation\n'
    else:
        lines += '  /*****/***** End of Initialization\n'

    with open(fname, encoding='ISO-8859-1', mode='w') as f:
        f.write(lines)
    return 0


def _fmt_nchar(n, nchar=7):
    """ Force float format to X char
    """
    # s = "{:.7g}".format(n)
    # edit: compute max dec and use f by default
    # modified from https://stackoverflow.com/questions/57007807/format-display-of-a-floating-number-to-a-fixed-length
    mantissa_length = max(nchar - len(str(int(n))) - 1, 0)
    s = '{:{nchar}.{man}f}'.format(n, nchar=nchar, man=mantissa_length)
    # check and cut if necessary
    if len(s) > 7:
        s = "{:.1e}".format(n) if abs(n) >= 1e7 or abs(n) < 1e-4 else s[:7]
    return s.rjust(7)
