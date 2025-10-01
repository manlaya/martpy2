#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
from martpy.utils import MART_VARIABLES


PARSER = {
    row['ext']: (
        # here we capture either '=VALUE' or 'FILE.ext' at beggining of line,
        # before the '= DESCR' part, separated by space characters
        r'^=*(.*?)\s*=\s+{}.*$'.format(
            re.sub(
                r'[é|è|\'|\[|\]|\(|\)]',  # remove accents and special chars
                '.',
                row['descr'].strip(),
                flags=re.IGNORECASE
            ).strip()
        )
    ) for row in MART_VARIABLES.loc[
        MART_VARIABLES['is_file'].astype(int) == 1, ['ext', 'descr']
    ].to_dict('records')
}

WRITE_FMT = '{0:<70}={1}\n'


def _parse_marthe_project(file_rma, encoding='ISO-8859-1'):
    # read raw content
    with open(file_rma, 'r', encoding=encoding) as f:
        content = f.readlines()
    
    # parse files in marthe project
    rma = {k: None for k in PARSER.keys()}  # init with None
    # rma = OrderedDict({k: None for k in PARSER.keys()})  # init with None
    for k, v in PARSER.items():
        pattern = re.compile(v, re.I)  # simplier than read() and multiline
        for i, line in enumerate(content):
            _match = re.search(pattern, line)
            if _match is not None:
                _ = content.pop(i)  # remove line for next iteration
                res = _match.group(1).strip()
                if re.match(r'^\d+\.*\d*', res):
                    # if result is '=[0-9]' it is a constant value
                    rma[k] = float(res)
                else:
                    # otherwise it is a file
                    rma[k] = res if res != '' else None
                break
            else:
                continue
    return rma


def _write_rma_file(dict_rma, file_rma, title='MARTHE Project'):
    # dict_rma = rma, file_rma = 'toto.rma'
    descr = MART_VARIABLES[['ext', 'descr']].set_index('ext').to_dict()['descr']
    lines = ['Marthe project']
    for k, v in dict_rma.items():
        _descr = descr.get(k)
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
    return

