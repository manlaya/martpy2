#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import builtins
import re
from pathlib import Path

import pandas as pd

from martpy.inputs.io_utils import (
    _build_header,
    _build_parameter_block,
    _parse_parameter_block,
)
from martpy.utils.config import get_lang
from martpy.utils.constant import (
    _FLOAT_PATTERN,
    BLOCK_MART,
    BLOCK_MART_EN,
)
from ..utils.config import _get_resource_file
from martpy.utils.helper import _get_closest_suggestion


WRITE_FMT_MART = '{0:>10}={1}\n'

MART_TEMPLATE = pd.read_table(
    _get_resource_file('parameters_template.csv'), encoding='ISO-8859-1', sep='\t'
)

# type are read as string, convert to actual python type
MART_TEMPLATE['type'] = MART_TEMPLATE['type'].apply(
    lambda x: getattr(builtins, x) if pd.notna(x) else str
    # remove __builtins__ and import builtins // AttributeError dict has not attr int(?)
)


def _parse_mart_file(mart_file, encoding='ISO-8859-1', verbose=False, lang=None):
    """ Parse mart file into nested dictionnary

    Parameters
    ----------
    mart_file : str
        path to mart file
    encoding : str, optional
        encoding of the file
    verbose : bool, optional
        verbose mode
    lang : str, optional
        language of the file

    Returns
    -------
    dict:
        nested dict storing mart file parameters by block
        initial parameters value are stored as a list of dict

    Example
    -------

    >>> _parse_mart('some_file.mart')
    {
        'outputs': {
            'restart': 0
            ...
        },
        ...
        'initial_parameters': {
            'VARIABLE1': [
                {'mode': 'ZONE', 'grid_id': 0, 'value': 1e2, 'zone': 2},
                {'mode': 'ZONE', 'grid_id': 0, 'value': 1e2, 'zone': 3},
            ],
            ...
        }
    }
    """
    lang = get_lang() if lang is None else lang
    _BLOCK_MART = BLOCK_MART if lang == 'fr' else BLOCK_MART_EN
    with open(mart_file, mode='r', encoding=encoding) as f:
        content = f.read()

    blocks = re.split(r'\*\*\* (.*?)\*\*\*', content)
    # header = blocks[0]  # unused
    blocks = blocks[1:]

    parsed_data = {}
    for i in range(0, len(blocks), 2):
        title = re.sub(r'\[.*\]', '', blocks[i]).strip()  # memo: old version have [Param MARTHE 7.X] in 1st block title
        params_content = blocks[i+1].strip()

        # allow slightly different titles (eg 'calculs' vs 'calcul', diff V7.7 et 7.8)
        title2 = _get_closest_suggestion(title, list(_BLOCK_MART.keys()), n=1)
        key_block = _BLOCK_MART.get(title2[0] if title2 is not None else title)
        if key_block is None or key_block == 'dummy':
            continue

        lines = params_content.splitlines()

        # dict for current block parsing
        params = {}

        if key_block == 'init_parameters':
            params = _parse_parameter_block(
                lines,
                path=Path(mart_file).parent,
                verbose=verbose
            )
        else:

            tpl = MART_TEMPLATE[MART_TEMPLATE['group'] == key_block]

            for i, line in enumerate(lines):
                # look for value=description
                match = re.match(r'(\S+|\s*)=([^\[]+)', line.strip())

                if match:
                    value = match.group(1).strip()
                    description = match.group(2).strip()

                    # find corresponding key in template
                    i_tpl = tpl.iloc[i]
                    # i_tpl = tpl[tpl['descr'].str.contains(re.escape(description), case=False, na=False)]
                    key = i_tpl['key']

                    if key == '' or pd.isna(key) or key is None:
                        if verbose:
                            print(
                                f"Warning: description '{description}' "
                                f"not found in template for block '{key_block}'"
                            )
                        key = '_'.join(re.findall(r'[a-zA-Z0-9]+', description)).lower()
                        continue

                    if key == 'dummy':
                        continue

                    # apply type conversion, according to template
                    _type = i_tpl.get('type')
                    value = _set_type_general_parameter(value, _type)

                    # add results to block
                    params[key] = value

        # add to global dict
        parsed_data[key_block] = params

    return parsed_data


def _set_type_general_parameter(value, _type=None):
    """ Convert general mart parameter value to given type

    Parameters
    ----------
    value : str
        parameter value as string
    _type : type
        target python type

    Returns
    -------
    any
        parameter value converted to target type
    """

    if re.match(r'^\d+$', value):
        # force int conversion if value looks like an integer
        # in some cases (state for example: 0,1 or transi/perman)
        # but default is string
        _type = int if _type == str or _type is None else _type
    elif re.match(_FLOAT_PATTERN, value):
        # force float conversion if value looks like a number
        # in some cases (units for example) default is string
        # because value can be non numeric (m/s for example)
        # but we want to convert to float if it is a number
        _type = float if _type == str or _type is None else _type

    if _type is not None:
        if _type == bool:
            return bool(int(value))
        else:
            try:
                convert = _type(value)
            except ValueError:
                return value  # return as is if conversion fails / eg for str
            else:
                return convert
    else:
        return value


def _set_valid_value(value, valid_value):
    """ Set value to be valid according to valid_value specification from template

    Parameters
    ----------
    value : any
        parameter value
    valid_value : str
        valid value specification from template

    Returns
    -------
    value if valid

    Raises
    ------
    ValueError
        if value is not valid
    """
    if pd.isna(valid_value) or valid_value is None or valid_value == '':
        return value  # no restriction

    # parse valid_value specification
    valid_values = [part.strip() for part in valid_value.split(',')] + [' ', '']  # add empty str
    str_val = str(value) if not pd.isna(value) else ' '
    if str_val.lower() in valid_values:
        return value
    else:
        raise ValueError(f"Value {value} not in valid values: {valid_value}")


def _write_mart_file(
    dict_mart,
    mart_file,
    write_ext_files=False,
    encoding='ISO-8859-1',
    title='mart parameter file',
    lang=None
):
    """ Write a marthe parameter file from a dictionnary of parameters

    Notes
    -----
    - dict_mart should follow the structure returned by _parse_mart_file
    - This function currently only works for French version of Marthe
    (need internationalization)

    Parameters
    ----------
    dict_mart : dict
        Dictionnary of parameters
    mart_file : str
        Path to the marthe parameter file
    write_ext_files : bool, optional
        Write external files (modin), by default False
        If True, the modin parameters will be written in the *.mart file
    encoding : str, optional
        Encoding of the file, by default 'ISO-8859-1'
    title : str, optional
        Title of the file, by default 'mart parameter file'
    lang : str, optional
        Language of the file, by default None (user config)
    """

    lang = get_lang() if lang is None else lang
    _BLOCK_MART = BLOCK_MART if lang == 'fr' else BLOCK_MART_EN
    block_names = {v: k for k,v in _BLOCK_MART.items()}  # reversed dict

    mart_str = '\n'.join(_build_header(title)) + '\n'

    # write based on full template, not only present parameters
    grp = MART_TEMPLATE.groupby('group', sort=False)

    for gr, df_tpl in grp:

        # write block title
        block_name = block_names.get(gr)
        mart_str += ' *** {:<47} ***\n'.format(block_name)
        params_block = dict_mart.get(gr, {})

        # then write parameters for this block
        for row in df_tpl.to_dict('records'):
            param_key = row['key']
            if param_key == '' or pd.isna(param_key) or param_key is None:
                continue

            # default value if not present in dict_mart - TODO parse full dict
            value = params_block.get(param_key, row['default'])
            descr = row['descr'] if lang == 'fr' else row['descr_en']

            # Check for range validity in general parameters
            value = _set_valid_value(value, row['valid_value'])

            # format line
            fmt = row.get('fmt')
            if pd.isna(fmt) or fmt is None or value == '':
                fmt = WRITE_FMT_MART
            else:
                fmt = f"{{0:{fmt}}}={{{1}}}\n"  # triple brackets to escape
            if pd.isna(value) or value is None:
                value = ''
            text = fmt.format(value, descr)
            mart_str += text

    if lang == 'fr':
        mart_str += ' *** Fin des paragraphes                             $$$\n'
        mart_str += (
            ' *** Options supplémentaires (3) (pour accessoires)  ***\n'
            '         0=[Option supplémentaire 1]\n'
            '         0=[Option supplémentaire 2]\n'
            '         0=[Option supplémentaire 3]\n'
        )
        mart_str += ' *** Initialisation avant calcul                     ***\n'
    else:
        mart_str += ' *** End of paragraphs                               $$$\n'
        mart_str += (
            ' *** Extra options (3) for future use  (not used)    ***\n'
            '         0=[Complementary Option  1]\n'
            '         0=[Complementary Option  2]\n'
            '         0=[Complementary Option  3]\n'
        )
        mart_str += ' *** Initialization before simulation                ***\n'

    # build init parameters block
    mart_str += _build_parameter_block(
        dict_mart.get('init_parameters'), write_ext_files, mode='str',
        path=Path(mart_file).parent
    )

    if lang == 'fr':
        mart_str += (
            '  /*****/***** Fin d\'Initialisation\n'
            ' *** Fin du fichier des Paramètres Généraux          ***\n'
        )
    else:
        mart_str += (
            '  /*****/***** End of Initialization\n'
            ' *** End General Parameters file                     ***\n'
        )

    with open(mart_file, 'w', encoding=encoding) as f:
        f.write(mart_str)

    return None
