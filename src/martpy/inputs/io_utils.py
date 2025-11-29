#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from pathlib import Path

from martpy.utils.config import (
    ACTIONS_FMT, _ACTION_PARSER, EDITIONS_FMT,
    LIST_MAIL_OPT, _OPT_MAIL_PARSER,
    MART_VERSION
)
from martpy.utils.helper import _check_mart_key


# English header (Future implementation)
#  #<V7.8.4># --- End of Header lines --- ; Do not modify/delete this line
def _build_header(title):
    lines = [title]
    lines.append(
        f' #<V{MART_VERSION}># --- Fin du texte libre --- ;'
        ' Ne pas modifier/retirer cette ligne '
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
    return re.findall(_OPT_MAIL_PARSER, line)


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
                    _type = _infer_variable_dtype(k, v)
                    _param_values[k] = _parse_param_value(v, _type)
                if mode == 'LIST_MAIL':
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
        it is useful to store path of file if needed (add it to file referenced in params)
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
            iparam[k] = iparam[k] + list_vals  # combine previous lines with current
            params = {**params, **iparam}  # combine dict results
    
    return params


def _format_params_for_writer(dict_args):
    clean_dict = {}
    for k, v in dict_args.items():
        if k in ['as_external_file', 'opt_list_mail']:
            # do not change these parameters
            continue
        if isinstance(v, (list, tuple)) and len(v) > 0:
            # WARNING: not perfect... but if range, take only min/max
            _val = '{}:{}'.format(min(v), max(v))
        elif isinstance(v, bool):
            _val = int(v)
        else:
            _val = v
        clean_dict[k] = _val
    return clean_dict


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
        # TODO: complete options for EDITION
        opts = ['star', 'V', 'L', 'S', 'Z', 'I', 'F', 'B', 'C', 'P', 'Gig']
        dtemp = {opt: kwargs.get(opt, ' ') for opt in opts}
        if variable in EDITIONS_FMT.keys():
            dopt = EDITIONS_FMT[variable]
        else:
            dopt =  "I= 1;"  # old: ACTIONS_FMT[action]
        option_str = dopt.format(**dtemp)
        option_str = '{0}{1}'.format(option_str, filename)
    
    else:
        if action == 'GRILLE' and isinstance(kwargs.get('grid'), (int, float)):
            # special case for grid uniform value
            kwargs['grid'] = '={0}'.format(kwargs['grid'])
        
        option_str = ACTIONS_FMT[action].format(**kwargs)
        
        if action == 'LIST_MAIL':
            opts = kwargs.get('opt_list_mail', [])
            available_opts = [re.sub('[<|>]', '', x) for x in LIST_MAIL_OPT]
            opts = [f'<{opt}>' for opt in opts if opt in available_opts]
            option_str = '{0} {1}'.format(option_str, ' '.join(opts))
        elif action in ['COUCHE', 'ZONE_GEO', 'ZONEP', 'ZONE_METEO', 'ZONE_SOL', 'MAILLE', 'TRONCON']:
            option_str = '{0}{1}{2}'.format(option_str, filename, file_col)
    
    return '  {0:25}{1}'.format(var_type, option_str)
