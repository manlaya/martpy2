#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

from martpy.utils import MART_VARIABLES
from martpy.utils.config import get_lang, _get_descr_field


WRITE_FMT = '{0:<70}={1}\n'


def _parse_marthe_project(file_rma, encoding='ISO-8859-1', lang=None):
    if lang is None:
        lang = get_lang()

    _descr_field = _get_descr_field(lang)
    _parser = MART_VARIABLES.loc[
            MART_VARIABLES['is_file'] == 1, [_descr_field, 'ext']
    ]
    _descr_784 = _parser[_descr_field].str.strip().values
    
    # read raw content
    with open(file_rma, 'r', encoding=encoding) as f:
        content = f.readlines()
    
    # parse title
    title = content.pop(0).strip()

    # parse files in marthe project
    rma = dict.fromkeys(_parser['ext'])  # init with None

    for i, line in enumerate(content):
        # extract value and descr
        _match = re.search(r'^=?(\S+)\s*=\s+(.*)$', line)

        if _match:
            value, descr = _match.groups()
            # rma is ordered, regardless version (only new lines), so use order of descr
            _valid_descr = _descr_784[i]

            k = MART_VARIABLES.loc[
                MART_VARIABLES[_descr_field].str.strip() == _valid_descr, 'ext'
            ].values[0]

            # parse uniform value as float
            # (positive or negative with or without decimals,
            # scientific notation allowed)
            if re.match(r'[+-]?\d+(?:\.\d+)?(?:e[+-]\d+)?', value):
                # if result is '=[0-9]' it is a constant value
                value = float(value)

            rma[k] = value

    rma['title'] = title
    return rma


def _write_rma_file(dict_rma, file_rma, title=None, lang=None):

    """ Write a rma file from a dict of files

    Parameters
    ----------
    dict_rma : dict
        dict of files in RMA, as parsed by _parse_marthe_project
    file_rma : str
        file to write
    title : str, optional
        title to use, by default None (use existing one or 'Marthe Project' if
        none)
    lang : str, optional
        locale to use to write file, by default None (use user config).
        Accepted values 'fr','en'
    
    Returns
    -------
    int
        status (0 if ok)
    """
    if lang is None:
        lang = get_lang()
        
    _descr_field = _get_descr_field(lang)
    tpl = MART_VARIABLES.loc[
        MART_VARIABLES['is_file'] == 1, ['ext', _descr_field]
    ].set_index('ext').squeeze().to_dict()  # squeeze to make Series and dict fmt

    # remove title from files to write if present
    _local_title = dict_rma.pop('title', 'Marthe Project')
    if title is None:
        # title would overwrite _local_title if present
        title = _local_title

    lines = []
    # loop over template for security: assert to write all lines
    for k, _descr in tpl.items():
        v = dict_rma.get(k)
        if isinstance(v, float):
            value = '={}'.format(v)
        elif isinstance(v, str):
            value = v
        elif v is None:
            value = ''
        lines.append(WRITE_FMT.format(value, _descr))

    with open(file_rma, mode='w', encoding='ISO-8859-1') as f:
        f.write(f"{title}\n")
        f.writelines(lines)
    return 0
