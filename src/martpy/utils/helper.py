#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import difflib

from martpy.utils.config import MART_VARIABLES


def _get_suggested_key_error(key, valid_keys):
    """ Get suggestion for key error using difflib
    """
    # Use difflib from stdlib to get close matches if wrong user input
    # 'n=1' is number of suggestions
    suggestions = difflib.get_close_matches(key, valid_keys, n=3, cutoff=0.6) 
    if suggestions:
        return suggestions[:3]  # 3 best suggestions
    return None  # otherwise None


class MartKeyError(KeyError):
    """Exception raised for when a Marthe key is not valid

    Attributes
    ----------
    variable : str
        input variable that caused the error
    valid_keys : list
        list of valid keys
    message : str
        explanation of the error
    """
    def __init__(self, variable, valid_keys):
        self.message = self._get_message(variable, valid_keys)
        super().__init__(self.message)
        self.variable = variable
        self.valid_keys = valid_keys
    
    def _get_message(self, variable, valid_keys):
        msg = f'Variable `{variable}` is not a Marthe variable. '
        closest = _get_suggested_key_error(variable.upper(), valid_keys)
        if closest is not None:
            msg += 'Possible closest value: {}. '.format(', '.join(closest))
        msg += 'Check for all Marthe variables with `get_mart_variables()`'
        return msg


def _check_mart_key(variable):
    valid_keys = MART_VARIABLES['code_var_fr'].to_list()
    if variable.upper() not in valid_keys:
        raise MartKeyError(variable, valid_keys)


def get_mart_variable():
    """ Help function to get informations on all Marthe variables

    Returns
    -------
    pd.DataFrame
        DataFrame with information on all Marthe variables
    
    See Also
    --------
    get_variable_help : get information on a specific Marthe variable
    """
    return MART_VARIABLES


def get_variable_help(variable):
    """ Help function to get informations on a specific Marthe variable
    
    Parameters
    ----------
    variable : str
        Marthe variable code
    
    Returns
    -------
    pd.Series
       Series with information on the variable
    
    See Also
    --------
    get_mart_variable : get information on all Marthe variables
    """
    _check_mart_key(variable)
    return MART_VARIABLES.loc[MART_VARIABLES['code_var_fr'] == variable.upper()]

