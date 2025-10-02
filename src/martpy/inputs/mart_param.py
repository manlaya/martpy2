#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from martpy.inputs._mart_parser import (
    _parse_mart_file,
    _write_mart_file
)


class MartheParams:
    """ Object to create/edit Marthe parameters
    """

    def __init__(self,
        controls={},
        init_parameters={}
    ):
        
        self.init_parameters = init_parameters
        pass
    
    def __getitem__(self, key):
        return getattr(self, key)
   
    def __setitem__(self, key, value):
        setattr(self, key, value)
    
    def to_dict(self,):
        return 

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
    >>> print(mpar)
    ...
    """
    parsed_params = _parse_mart_file(mart_file)
    return MartheParams(**parsed_params)


def _set_restart(dict_param):
    current = dict_param.get('general_params', {}).get('edit_restart')
    if current is not None:
        dict_param['general_params']['edit_restart'] = 1
    return dict_param

