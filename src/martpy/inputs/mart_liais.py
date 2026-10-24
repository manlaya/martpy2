#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

import pandas as pd


# HBNESW directions: H=Haut, B=Bas, N=Nord, E=Est, S=Sud, W=Ouest (Ouest)
_HBNESW_DIRECTIONS = ['H', 'B', 'N', 'E', 'S', 'W']

# Header line written at the top of a .liais file
_LIAIS_HEADER = ' Col Lig Cou;HBNESW  #'

# Regex to parse a data line of a .liais file.
# Layout: <col> <row> <layer> <1 space separator> <HBNESW: 6 chars positional>
# <spaces> <igrid>
# The HBNESW field has fixed length 6 and may contain spaces, so we capture
# exactly 6 characters with `.{6}` instead of relying on whitespace splitting.
_LIAIS_PARSER = re.compile(
    r'^\s*(?P<col>\d+)\s+(?P<row>\d+)\s+(?P<layer>\d+)\s'
    r'(?P<hbnesw>.{6})'
    r'\s*(?P<igrid>\d+)\s*$'
)


class MartLiais(pd.DataFrame):
    """ Liaisons étanches MARTHE (`.liais` file).

    A DataFrame with one row per declared impermeable face on a MARTHE
    cell. Columns:

    - ``col``, ``row``, ``layer`` : 1-based MARTHE cell indices
    - ``H``, ``B``, ``N``, ``E``, ``S``, ``W`` : booleans, one per direction
      (Haut, Bas, Nord, Est, Sud, Ouest). ``True`` indicates that the
      corresponding face is impermeable.
    - ``igrid`` : nested grid index (0 = global grid, 1 = first nested grid,
      etc.)

    Examples
    --------
    >>> liais = MartLiais.from_file('model.liais')
    >>> liais.write_file('out.liais')
    """

    def __init__(self, df):
        super().__init__(df)

    def __repr__(self):
        return f'{self.__class__.__name__}\n{super().__repr__()}'

    def __str__(self):
        return self.__repr__()

    @property
    def _constructor(self):
        return MartLiais

    @classmethod
    def from_file(cls, filename, encoding='cp1252'):
        """ Read a `.liais` MARTHE file.

        Parameters
        ----------
        filename : str
            path to the `.liais` file
        encoding : str, optional
            file encoding, by default ``'cp1252'`` (MARTHE convention)

        Returns
        -------
        MartLiais
        """
        return read_liais_file(filename, encoding=encoding)

    def write_file(self, filename, encoding='cp1252'):
        """ Write a `.liais` file from a MartLiais object.

        Note
        ----
        Reciprocal seals are not written: per MARTHE documentation,
        WinMarthe automatically generates them at runtime, so each face
        is declared only once.

        Parameters
        ----------
        filename : str
            path to the output `.liais` file
        encoding : str, optional
            file encoding, by default ``'cp1252'``
        """
        lines = [_LIAIS_HEADER]
        for record in self.to_dict('records'):
            lines.append(_build_liais_line(**record))
        with open(filename, mode='w', encoding=encoding) as f:
            f.write('\n'.join(lines) + '\n')


def read_liais_file(filename, encoding='cp1252'):
    """ Read a MARTHE `.liais` file (liaisons étanches).

    Parameters
    ----------
    filename : str
        path to the `.liais` file
    encoding : str, optional
        file encoding, by default ``'cp1252'``

    Returns
    -------
    MartLiais
        DataFrame with columns: ``col``, ``row``, ``layer``, ``H``, ``B``,
        ``N``, ``E``, ``S``, ``W``, ``igrid``.
    """
    with open(filename, encoding=encoding) as f:
        lines = [line.rstrip('\r\n') for line in f.readlines()]

    records = []
    # Skip the header line (first line)
    for line in lines[1:]:
        if line.strip() == '':
            continue
        match = _LIAIS_PARSER.match(line)
        if not match:
            raise ValueError(f'Cannot parse .liais line: {line!r}')
        parsed = match.groupdict()
        hbnesw = parsed['hbnesw']
        record = {
            'col': int(parsed['col']),
            'row': int(parsed['row']),
            'layer': int(parsed['layer']),
        }
        for i, direction in enumerate(_HBNESW_DIRECTIONS):
            record[direction] = hbnesw[i] == '1'
        record['igrid'] = int(parsed['igrid'])
        records.append(record)

    columns = ['col', 'row', 'layer'] + _HBNESW_DIRECTIONS + ['igrid']
    df = pd.DataFrame(records, columns=columns)
    df = df.astype({
        'col': int,
        'row': int,
        'layer': int,
        'igrid': int,
        **dict.fromkeys(_HBNESW_DIRECTIONS, bool),
    })
    return MartLiais(df)


def _build_liais_line(col, row, layer, H, B, N, E, S, W, igrid):
    """ Build a single data line of a `.liais` file.

    The HBNESW field is built as a 6-character positional string with
    ``'1'`` for an impermeable face and a space otherwise.
    """
    hbnesw = ''.join('1' if flag else ' ' for flag in (H, B, N, E, S, W))
    return f' {col:>3d} {row:>3d} {layer:>3d} {hbnesw}{igrid:>3d}'
