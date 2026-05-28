#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import difflib

from .constant import (
    _ACTION_PARSER,
    GENERIC_TO_HISTO_EN,
    GENERIC_TO_HISTO_FR,
    HISTO_TO_GENERIC_EN,
    HISTO_TO_GENERIC_FR,
    MART_VARIABLES,
    MART_HISTO_VAR,
    OPT_LIST_MAIL,
    VALID_VARIABLE_TYPES
)
from .misc import _canonicalize_name


def _get_closest_suggestion(key, valid_keys, n=3):
    """ Get suggestion for key error using difflib
    """
    # Use difflib from stdlib to get close matches if wrong user input
    # 'n=1' is number of suggestions
    suggestions = difflib.get_close_matches(key, valid_keys, n=n, cutoff=0.6)
    if suggestions:
        return suggestions[:n]  # n best suggestions
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
    def __init__(self, variable, valid_keys, mode='variable'):
        self.message = self._get_message(variable, valid_keys, mode.lower())
        super().__init__(self.message)
        self.variable = variable
        self.valid_keys = valid_keys
        self.mode = mode

    def _get_message(self, variable, valid_keys, mode):
        msg = f'{mode.title()} `{variable}` is not a Marthe variable. '
        closest = _get_closest_suggestion(variable.upper(), valid_keys)
        if closest is not None:
            msg += 'Possible closest value: {}. '.format(', '.join(closest))
        if mode == 'variable':
            msg += 'Check for all Marthe variables with `get_mart_variables()`'
        elif mode == 'action':
            msg += 'Check for all Marthe actions with `get_mart_actions()`'
        else:
            raise ValueError(f'Invalid mode: {mode}')
        return msg


def _check_mart_key(variable):
    valid_keys = MART_VARIABLES['code_var_fr'].to_list()
    valid_keys += MART_VARIABLES['code_var_en'].to_list()
    if variable.upper() not in valid_keys:
        raise MartKeyError(variable, valid_keys)


def _check_valid_action(action):
    _valid_actions = get_mart_actions()
    if action not in _valid_actions:
        raise MartKeyError(action, _valid_actions, mode='action')


def get_mart_variables(variable_type: str | None = None):
    """ Get information on all Marthe variables, or a subset of variables
    based on variable name

    Returns
    -------
    pd.DataFrame
        DataFrame with information on all Marthe variables
    variable_type : str | None, optional
        specific variable type to filter the DataFrame,
        if no argument is given, all variables are returned
    See Also
    --------
    get_variable_help : get information on a specific Marthe variable
    """
    if variable_type is not None:

        # Check for valid variable type
        _check_available_varname_type(variable_type)
        return _get_slice_variables(variable_type)

    return MART_VARIABLES


def get_variable_help(variable, locale='fr'):
    """ Help function to get informations on a specific Marthe variable

    Parameters
    ----------
    variable : str
        Marthe variable code
    locale : str, optional
        locale for the variable code, by default 'fr'
        accepted values are 'fr' and 'en'

    Returns
    -------
    dict
       dict with information on the variable

    See Also
    --------
    get_mart_variable : get information on all Marthe variables
    """
    _check_mart_key(variable)
    subset = MART_VARIABLES.loc[MART_VARIABLES[f'code_var_{locale}'] == variable.upper()]
    return subset.to_dict('records')[0]


def get_mart_histo_variables():
    """ Get all Marthe histo (time series) variant of variables
    
    Notes
    -----

    TODO: link (join) with get_mart_variable
    and make all this user transparent (i.e. martpy user
    should only deal with marthe variable, then the code write histo
    variant in histo file).

    Returns
    -------
    pandas.DataFrame
        Dataframe of all Marthe histo variables with columns:
        `ext` (extension of file, link with marthe full name variable, see
        :py:func:`get_mart_variables`), `code_var` (french histo code),
        `code_var_en` (english version).
    """
    return MART_HISTO_VAR


def get_mart_actions():
    """ Get all Marthe actions
    """
    return list(_ACTION_PARSER.keys())


def get_opt_list_cells():
    """ Get all Marthe options for list cells
    """
    return list(OPT_LIST_MAIL.keys())


def _get_slice_variables(varname_type: str):
    """Get subset of variables based on variable type."""
 
    from . import constant
    # Dynamically select the appropriate subset of variables
    subset_variables = getattr(constant, f"{varname_type.upper()}_VARIABLES", None)
    if subset_variables is None:
        raise NotImplementedError(f"Variable type not implemented: {varname_type}")

    mask = MART_VARIABLES['code_var_fr'].isin(subset_variables)
    return MART_VARIABLES.loc[mask]


def _check_available_varname_type(varname_type: str):
    """ Check if the provided variable name is valid"""

    if not isinstance(varname_type, str) or not varname_type.strip():
        raise ValueError("Variable type must be a non-empty string.")

    if varname_type.lower() not in VALID_VARIABLE_TYPES:
        raise ValueError(f'Invalid variable type: {varname_type},'
                         f'valid variable types are:\n{VALID_VARIABLE_TYPES}.')


def to_histo_varname(name, lang='fr'):
    """Convert a generic Marthe variable name to its histo file equivalent.

    Generic names are the user-facing canonical form (accent-free, lowercase,
    e.g. ``'charge'``, ``'debit_rivi'``). Histo names are written in
    .histo files and .prn output headers (e.g. ``'Charge'``, ``'Débit_Rivi'``).

    Input is canonicalized before lookup, so French or English generic codes
    from ``marthe_variables.csv`` (e.g. ``'CHARGE'``, ``'HYDR_HEAD'``) are
    accepted as aliases. The function is idempotent on histo names already
    in the target language.

    Parameters
    ----------
    name : str
        Generic variable name (case-insensitive, accents tolerated).
    lang : str, optional
        Target language of the histo name: ``'fr'`` (default) or ``'en'``.

    Returns
    -------
    str
        Histo variable name in the target language, or the input unchanged
        if no match is found.

    See Also
    --------
    from_histo_varname : reverse conversion (histo name to generic name).
    """
    mapping = GENERIC_TO_HISTO_FR if lang.lower() == 'fr' else GENERIC_TO_HISTO_EN
    return mapping.get(_canonicalize_name(name), name)


def from_histo_varname(name, lang='fr'):
    """Convert a histo variable name to its canonical generic Marthe name.

    The generic form is accent-free, lowercase, and uses underscores
    (e.g. ``'Charge'`` -> ``'charge'``, ``'Débit_Rivi'`` -> ``'debit_rivi'``).
    For names not present in the histo table (e.g. derived headers), the
    canonicalization is applied as a deterministic fallback. The function
    is idempotent on generic names.

    Parameters
    ----------
    name : str
        Variable name as found in .histo files or .prn output headers.
    lang : str, optional
        Language of the input histo name: ``'fr'`` (default) or ``'en'``.

    Returns
    -------
    str
        Canonical generic variable name (lowercase, no accents).

    See Also
    --------
    to_histo_varname : reverse conversion (generic name to histo name).
    """
    mapping = HISTO_TO_GENERIC_FR if lang.lower() == 'fr' else HISTO_TO_GENERIC_EN
    key = str(name).strip()
    if key in mapping:
        return mapping[key]
    return _canonicalize_name(name)
