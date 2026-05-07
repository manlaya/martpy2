#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# copy from aquida lib (python lib for data assimilation in Aqui-FR modelling platform)
# released under GPLv3 licence (and from one of the same author as this lib)
def getattr_nested(some_dict, key, key2=None):
    """ Extension of get method (or getattr function) for nested dict

    Parameters
    ----------
    some_dict : dict
        a nested dictionnary to query
    key : str or list
        the key(s) to get :
        - if it is a string, it can be a nested key separated by '/' or '.'
        - if it is a list, it is a list of keys in the order of nested keys
    key2 : str, optional
        the second level key to get, by default None
    
    Returns
    -------
        the value of the nested key
    
    Raises
    ------
    KeyError
        if key does not contains a separator
    
    ValueError
        if one key or subkey does not return a dictionary
        (eg if first key return a list)
    
    Example
    -------
    >>> getattr_nested({'a': {'b': 1}}, 'a/b')
    1
    >>> getattr_nested({'a': {'b': 1}}, ['a', 'b'])
    1
    >>> getattr_nested({'a': {'b': 1}}, 'a', 'b')
    1
    >>> getattr_nested({'a': {'b': 1}}, 'a', 'c')
    None
    >>> getattr_nested({'a': {'b': {'c': 2}}}, 'a/b/c')
    2
    """
    from copy import deepcopy
    
    # set list of nested keys
    if '/' in key:
        _key = key.split('/')
    elif '.' in key:
        _key = key.split('.')
    elif isinstance(key, list):
        _key = key
    elif key2 is not None:
        _key = [key, key2]
    else:
        raise KeyError(
            'key must be a string or a list of strings; '
            'or key and key2 must be strings'
        )
    
    _dict = deepcopy(some_dict)  # ensure that the original dict is untouched

    for k in _key[:-1]:
        _dict = _dict.get(k, {})
        if not isinstance(_dict, dict):
            raise ValueError(
                f'Value for key {k} is not a nested dict. Cannot continue. ',
                'value type: {}. '.format(type(_dict)),
                'value: {}'.format(_dict)
            )
    return _dict.get(_key[-1], None)


# def _combine_dict(d1, d2, key=None):
#     """ combine two dicts with same keys"""
#     if key is None:
#         key = list(d1.keys())
#     if isinstance(key, str):
#         key = [key]
#     return {k: {**d1[k], **d2[k]} for k in key}

def remove_accents(input_str):
    import unicodedata
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    only_ascii = nfkd_form.encode('ASCII', 'ignore')
    return only_ascii.decode('utf-8')
