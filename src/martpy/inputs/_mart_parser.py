#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import builtins
# from collections import OrderedDict  # not necessary after py37
import pandas as pd

from martpy.inputs.io_utils import (
    _build_header,
    _parse_parameter_block,
    _build_parameter_line,
    _parse_param_value
)
from martpy.utils.config import _get_resource_file


BLOCK_MART = {
    'Sauvegardes et contrôles' : 'outputs',
    'Pas de Temps et sous-pas de temps' : 'timesteps',
    'Contrôle de la Résolution Hydrodynamique de Nappe' : 'solver',
    'Unités des données' : 'units',
    'Options de Géométrie, États de Référence, Processeurs' : 'geometry_process',
    'Couplage et Transport : Concentration, Chaleur, Salinité' : 'transport',
    'Salinité, Densité' : 'density',
    'Température , effets Thermiques': 'thermal',
    'Concentration et Trajectoires' : 'trajectory_concentr',
    'Zone Non-Saturée et Multiphasique': 'unsat_multiphas',
    'Eau, Gaz, Huile, Eau Salée': 'gaz_oil_salt',
    'Écoulement d\'Huile, Eau Salée, NAQ': 'oil_naq_flow',
    'Écoulement de Gaz' : 'gaz_flow',
    'Géochimie' : 'geochemistry',
    'Calibration automatique / Analyse de sensibilité / Optimisation' : 'optim',
    'Réseau de Rivières, Drains, Lacs': 'river',
    'Hydroclimatologie': 'climatology',
    'Contrôles sur écran en cours de calcul': 'controls',
    'Allégements des écritures du fichier bilandeb': 'log',
    'Cultures, Nitrate' : 'agriculture',
    'Fin des paragraphes': 'dummy',
    'Initialisation avant calcul' : 'init_parameters',
    'Fin d\'Initialisation': 'dummy',
    'Fin du fichier des Paramètres Généraux': 'dummy',
}

WRITE_FMT_MART = '{0:>10}={1}\n'

MART_TEMPLATE = pd.read_table(_get_resource_file('parameters_template.csv'), encoding='ISO-8859-1', sep='\t')

# _type_mapping = {
#     'int': int,
#     'float': float,
#     'str': str,
#     'bool': lambda x: bool(int(x)),  # marthe uses 0/1 for boolean
# }
# MART_TEMPLATE['type'] = MART_TEMPLATE['type'].map(type_mapping)

# type are read as string, convert to actual python type
MART_TEMPLATE['type'] = MART_TEMPLATE['type'].apply(
    lambda x: getattr(builtins, x) if pd.notna(x) else str
    # remove __builtins__ and import builtins // AttributeError dict has not attr int(?)
)


def _parse_mart_file(mart_file, encoding='ISO-8859-1', verbose=False):
    """ Parse mart file into nested dictionnary
    
    Parameters
    ----------
    mart_file : str
        path to mart file
    encoding : str, optional
        encoding of the file

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
            'restart': {'value': 0, 'descr': '...'}
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
    with open(mart_file, mode='r', encoding=encoding) as f:
        content = f.read()
    
    blocks = re.split(r'\*\*\* (.*?)\*\*\*', content)
    header = blocks[0]
    blocks = blocks[1:]
    
    parsed_data = {}
    for i in range(0, len(blocks), 2):
        title = blocks[i].strip()
        params_content = blocks[i+1].strip()

        key_block = BLOCK_MART.get(title)
        if key_block is None or key_block == 'dummy':
            continue
        
        lines = params_content.splitlines()
        
        # dict for current block parsing
        params = {}
        
        if key_block == 'init_parameters':
            params = _parse_parameter_block(lines, verbose)
        else:
            
            tpl = MART_TEMPLATE[MART_TEMPLATE['group'] == key_block]
            
            for i, line in enumerate(lines):
                # look for value=description
                match = re.match(r'(\S+)=([^\[]+)', line.strip())
                
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
                    
                    # format parameter value
                    #_type = key['type'].values[0]
                    # add results to block
                    params[key] = {'value': value, 'description': description}
        
        # add to global dict
        parsed_data[key_block] = params
    
    return parsed_data


def _build_init_parameters(dict_param):
    str_init = ''
    for k, v in dict_param.items():
        for param in v:
            var, typ = v.pop('variable'), v.pop('mode')
            line = _build_parameter_line(var, typ, **v)
            str_init += f"{line}\n"
    return str_init


def _write_mart_file(dict_mart, mart_file, encoding='ISO-8859-1', title='mart parameter file'):
    """ Write a marthe parameter file from a dictionnary of parameters

    Notes
    -----
    - dict_mart should follow the structure returned by _parse_mart_file
    - This function currently only works for French version of Marthe (need internationalization)

    Parameters
    ----------
    dict_mart : dict
        Dictionnary of parameters
    mart_file : str
        Path to the marthe parameter file
    encoding : str, optional
        Encoding of the file, by default 'ISO-8859-1'
    title : str, optional
        Title of the file, by default 'mart parameter file'
    """

    block_names = { v: k for k,v in BLOCK_MART.items()}  # reversed dict
    
    mart_str = '\n'.join(_build_header(title)) + '\n'
    
    grp = MART_TEMPLATE.groupby('group', sort=False)

    for gr, df_tpl in grp:
        block_name = block_names.get(gr)
        mart_str += ' *** {:<48}***\n'.format(block_name)
        params_block = dict_mart.get(gr, {})
        for row in df_tpl.to_dict('records'):
            param_key = row['key']
            if param_key == '' or pd.isna(param_key) or param_key is None:
                continue
            actual_param = params_block.get(param_key, {})
            value = actual_param.get('value', row['default'])
            descr = actual_param.get('description', row['descr'])
            
            # format value according to type
            value = _parse_param_value(value, row['type'])
            
            # format line
            fmt = row.get('fmt')
            if pd.isna(fmt) or fmt is None:
                fmt = WRITE_FMT_MART
            else:
                fmt = f"{{0:{fmt}}}={{{1}}}\n"  # triple brackets to escape
            text = fmt.format(value, descr)
            mart_str += text
    
    mart_str += ' *** Fin des paragraphes                             $$$\n'
    mart_str += (
        ' *** Options supplémentaires (3) (pour accessoires)  ***\n'
        '         0=[Option supplémentaire 1]\n'
        '         0=[Option supplémentaire 2]\n'
        '         0=[Option supplémentaire 3]\n'
    )
    mart_str += ' *** Initialisation avant calcul                     ***\n'
    mart_str += _build_init_parameters(dict_mart.get('init_parameters'))
    mart_str += (
        '  /*****/***** Fin d\'Initialisation\n'
        ' *** Fin du fichier des Paramètres Généraux          ***\n'
    )

    with open(mart_file, 'w', encoding=encoding) as f:
        f.write(mart_str)
    
    return None
