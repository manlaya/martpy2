#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd

from martpy.inputs._mart_parser import (
    _parse_mart_file,
    _write_mart_file,
    BLOCK_MART,
    MART_TEMPLATE
)


class MartheParams:
    """ Object to create/edit Marthe parameters
    """

    def __init__(self,
        **params,
    ):
        """ Initialize MartheParams object

        Parameters
        ----------
        **params : dict
            nested dictionnary with marthe parameters by block
        
        Examples
        --------
        >>> mart_params = MartheParams.from_template()
        >>> mart_params.write_file('params.mart')
        >>> params = MartheParams.from_file('params.mart')
        >>> params['general_params']
        """
        for k, v in params.items():
            self[k] = v
        
        self.groups = {v: k for k,v in BLOCK_MART.items() if v != 'dummy'}.keys()
    
    def __getitem__(self, key):
        return getattr(self, key)
   
    def __setitem__(self, key, value):
        setattr(self, key, value)
    
    def get_param_groups(self):
        return list(self.groups)
    
    def get_param_keys(self, nested=False):
        """ Get parameters keys

        Parameters
        ----------
        nested : bool, optional
            if true return a list of string with nested group/keys, by default False
            (will only return keys)
        """
        all_keys = []
        for g in self.keys:
            for k in self[g].keys():
                if nested:
                    _tmp = f'{g}/{k}'
                else:
                    _tmp = k
                all_keys.append(_tmp)
        return all_keys
    
    def get_param_help(self, group=None, key=None, locale='fr'):
        """ Get help information on marthe parameters
        # TODO use get_parameter_help function ?

        Parameters
        ----------
        group : str, optional
            marthe parameter group, by default None
        key : str, optional
            marthe parameter key, by default None
        locale : str, optional
            language for the parameter description, by default 'fr'
            accepted values are 'fr' and 'en'
        
        Returns
        -------
        dict
            dict with help information on the parameter(s)
        """
        df = MART_TEMPLATE
        if group is not None:
            if group not in self.get_param_groups():
                msg = f'Group `{group}` not found in Marthe parameters'
                msg += f' - possible groups: {", ".join(self.get_param_groups())}'
                raise ValueError(msg)
            df = df.loc[df['group'] == group]
        if key is not None:
            df = df.loc[df['key'] == key]
        
        _descr = 'descr'
        if locale == 'en':
            _descr += '_en'
        
        help_dict = {}
        for _, row in df.iterrows():
            g = row['group']
            k = row['key']
            help_dict.setdefault(g, {})
            help_dict[g][k] = {
                'default': row['default'],
                'type': row['type'],
                'description': row[_descr],
            }
        return help_dict
    
    def to_dict(self):
        d = {}
        for k in self.keys:
            d[k] = self[k]
        return d

    @classmethod
    def from_file(cls, mart_file):
        return read_general_parameters(mart_file)
    
    @staticmethod
    def from_template():
        tmp = MART_TEMPLATE[['group', 'key', 'default', 'type']]
        tmp = tmp.loc[tmp['key'] != 'dummy']
        params = {}
        groups = tmp.groupby('group')
        for g, df in groups:
            params[g] = {}
            for _, row in df.iterrows():
                value = row['default'] if not pd.isna(row['default']) else ''
                if row['type'] is not None and not pd.isna(row['type']) and value != '':
                    value = row['type'](value)
                params[g][row['key']] = value
        return MartheParams(**params)

    def write_file(self, mart_file, title='marthe parameters'):
        _write_mart_file(self.to_dict(), mart_file, title=title)


def read_general_parameters(mart_file):
    """ Read a marthe general parameter file

    Parameters
    ----------
    mart_file : str, Path.
        path to marthe general parameter file (`.mart`)
    
    Returns
    -------
    dict:
        nested dictionnary with general parameters by block
    
    Example
    -------
    >>> mpar = read_general_parameters('toto.mart')
    """
    parsed_params = _parse_mart_file(mart_file)
    return MartheParams(**parsed_params)


def read_relax(file_relax, encoding='ISO-8859-1'):
    # TODO better: not always 1 row to skip ?
    return pd.read_csv(
        file_relax,
        sep=r'\s+',
        header=None,
        names=['iteration', 'relax'],
        encoding=encoding,
        skiprows=1,
    )


def _set_restart(dict_param):
    current = dict_param.get('general_params', {}).get('edit_restart')
    if current is not None:
        dict_param['general_params']['edit_restart'] = 1
    return dict_param

