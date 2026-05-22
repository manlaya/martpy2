#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

import pandas as pd

from martpy.inputs._io_utils import _build_header


# Section headers recognised inside a fracture block. The reader accepts both
# the original French keys and an English alias for robustness; the writer
# always emits the French form to match the MARTHE convention.
_FRACTURE_BLOCK_HEADERS = {
    'fr': '[Fracture Semi-Perméable]',
    'en': '[Semi-Permeable Fracture]',
}
_COORDS_BLOCK_HEADERS = {
    'fr': '[Liste coordonnées]',
    'en': '[Coordinates list]',
}

# End-of-free-text marker (the V7.8 line); we detect it case-insensitively
# with a simple substring check.
_END_OF_HEADER_MARKER = '--- Fin du texte libre ---'

# Mapping from MARTHE key (as appears in file) to attribute name used in the
# returned dict. The reader accepts both the French and an English alias.
_PARAM_KEY_TO_ATTR = {
    'transmissivité': 'transmissivity',
    'transmissivite': 'transmissivity',
    'transmissivity': 'transmissivity',
    'pourcentage_contact': 'contact_percentage',
    'contact_percentage': 'contact_percentage',
    'couche_haut': 'top_layer',
    'top_layer': 'top_layer',
    'couche_bas': 'bottom_layer',
    'bottom_layer': 'bottom_layer',
}

# Reverse mapping (attribute -> MARTHE key used on write) for the French
# output convention.
_ATTR_TO_PARAM_KEY_FR = {
    'transmissivity': 'Transmissivité',
    'contact_percentage': 'Pourcentage_Contact',
    'top_layer': 'Couche_Haut',
    'bottom_layer': 'Couche_Bas',
}

_PARAM_LINE_RE = re.compile(r'^\s*(\w+)\s*=\s*(\S+)\s*$')
_COMMENT_PREFIXES = ('#', '!', '*', '<<')


class MartFract:
    """ MARTHE Fractures Semi-Perméables (`.fract` file).

    Attributes
    ----------
    title : str
        free-text title (first line of the file)
    fractures : list of dict
        each fracture is a dict with the following keys:

        - ``transmissivity`` : float
        - ``contact_percentage`` : float
        - ``top_layer`` : int (``Couche_Haut``)
        - ``bottom_layer`` : int (``Couche_Bas``)
        - ``coordinates`` : ``pd.DataFrame`` with columns ``x`` and ``y``

    Examples
    --------
    >>> mf = MartFract.from_file('model.fract')
    >>> mf.fractures[0]['transmissivity']
    0.0
    >>> mf.write_file('out.fract')
    """

    def __init__(self, title='Marthe fractures', fractures=None):
        self.title = title
        self.fractures = list(fractures) if fractures is not None else []

    def __len__(self):
        return len(self.fractures)

    def __repr__(self):
        return (
            f'MartFract(title={self.title!r}, '
            f'fractures={len(self.fractures)})'
        )

    @classmethod
    def from_file(cls, filename, encoding='cp1252'):
        """ Read a `.fract` MARTHE file.

        Parameters
        ----------
        filename : str
            path to the `.fract` file
        encoding : str, optional
            file encoding, by default ``'cp1252'``

        Returns
        -------
        MartFract
        """
        return read_fract_file(filename, encoding=encoding)

    def write_file(self, filename, encoding='cp1252', lang='fr'):
        """ Write the fractures to a `.fract` file.

        Parameters
        ----------
        filename : str
            path to the output `.fract` file
        encoding : str, optional
            file encoding, by default ``'cp1252'``
        lang : str, optional
            language for section headers and end-of-header marker, by
            default ``'fr'``.
        """
        lines = _build_header(self.title, lang=lang)
        for fracture in self.fractures:
            lines.extend(_build_fracture_block(fracture, lang=lang))
        with open(filename, mode='w', encoding=encoding) as f:
            f.write('\n'.join(lines) + '\n')


def read_fract_file(filename, encoding='cp1252'):
    """ Read a MARTHE `.fract` file.

    Parameters
    ----------
    filename : str
        path to the `.fract` file
    encoding : str, optional
        file encoding, by default ``'cp1252'``

    Returns
    -------
    MartFract
    """
    with open(filename, encoding=encoding) as f:
        lines = [line.rstrip('\r\n') for line in f.readlines()]

    title, body = _split_title_and_body(lines)
    fractures = _parse_fracture_blocks(body)
    return MartFract(title=title, fractures=fractures)


def _is_comment(line):
    stripped = line.strip()
    return stripped == '' or stripped.startswith(_COMMENT_PREFIXES)


def _is_fracture_header(line):
    return line.strip().lower() in (
        h.lower() for h in _FRACTURE_BLOCK_HEADERS.values()
    )


def _is_coords_header(line):
    return line.strip().lower() in (
        h.lower() for h in _COORDS_BLOCK_HEADERS.values()
    )


def _split_title_and_body(lines):
    """ Split lines into the title (free-text header) and the body.

    The title is taken as the first non-empty, non-comment line. The body
    starts at the line following the end-of-free-text marker.
    """
    title = ''
    body_start = 0
    for i, line in enumerate(lines):
        if _END_OF_HEADER_MARKER in line:
            body_start = i + 1
            break
    else:
        # No marker found: assume whole file is body and title is line 0
        body_start = 1 if lines else 0

    for line in lines[:body_start]:
        if line.strip() and not line.strip().startswith(_COMMENT_PREFIXES) \
                and _END_OF_HEADER_MARKER not in line:
            title = line
            break

    return title, lines[body_start:]


def _parse_param_line(line):
    """ Parse a ``Key = value`` line. Returns ``(attr_name, value_str)`` or
    ``None`` if the line is not a parameter line.
    """
    match = _PARAM_LINE_RE.match(line)
    if not match:
        return None
    raw_key, raw_value = match.group(1), match.group(2)
    attr = _PARAM_KEY_TO_ATTR.get(raw_key.lower())
    if attr is None:
        return None
    return attr, raw_value


def _parse_fracture_blocks(body_lines):
    """ Parse the body of a .fract file (after the end-of-header marker).

    Walks through the lines collecting one fracture per
    ``[Fracture Semi-Perméable]`` block. Comments and blank lines outside
    of a block are skipped.
    """
    fractures = []
    current = None
    in_coords = False

    for line in body_lines:
        if _is_fracture_header(line):
            if current is not None:
                fractures.append(_finalise_fracture(current))
            current = {
                'transmissivity': None,
                'contact_percentage': None,
                'top_layer': None,
                'bottom_layer': None,
                '_coords': [],
            }
            in_coords = False
            continue

        if current is None:
            # Skip until we hit the first fracture block
            continue

        if _is_coords_header(line):
            in_coords = True
            continue

        if _is_comment(line):
            continue

        if in_coords:
            xy = _parse_coord_line(line)
            if xy is not None:
                current['_coords'].append(xy)
        else:
            parsed = _parse_param_line(line)
            if parsed is not None:
                attr, value = parsed
                current[attr] = value

    if current is not None:
        fractures.append(_finalise_fracture(current))

    return fractures


def _parse_coord_line(line):
    """ Parse a ``"x y"`` coordinate line. Returns ``(x, y)`` floats or
    ``None`` if parsing fails.
    """
    parts = line.split()
    if len(parts) < 2:
        return None
    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        return None


def _finalise_fracture(raw):
    """ Convert raw parsed values into the final fracture dict, with proper
    Python types and a coordinates ``pd.DataFrame``.
    """
    coords = pd.DataFrame(raw.pop('_coords'), columns=['x', 'y'])
    fracture = {
        'transmissivity': _to_float(raw['transmissivity']),
        'contact_percentage': _to_float(raw['contact_percentage']),
        'top_layer': _to_int(raw['top_layer']),
        'bottom_layer': _to_int(raw['bottom_layer']),
        'coordinates': coords,
    }
    return fracture


def _to_float(value):
    if value is None:
        return None
    return float(value)


def _to_int(value):
    if value is None:
        return None
    return int(value)


def _build_fracture_block(fracture, lang='fr'):
    """ Build the list of lines for a single fracture block in MARTHE format.
    """
    key_lang = lang.lower() if lang.lower() in _FRACTURE_BLOCK_HEADERS else 'fr'
    lines = [_FRACTURE_BLOCK_HEADERS[key_lang]]
    for attr in ['transmissivity', 'contact_percentage', 'top_layer', 'bottom_layer']:
        value = fracture.get(attr)
        if value is None:
            continue
        lines.append(f'{_ATTR_TO_PARAM_KEY_FR[attr]} = {_format_value(value)}')
    lines.append(_COORDS_BLOCK_HEADERS[key_lang])
    coords = fracture.get('coordinates')
    if coords is not None:
        for _, row in coords.iterrows():
            lines.append(f'{row["x"]} {row["y"]}')
    return lines


def _format_value(value):
    """ Format a numeric value, preserving integer display when possible.
    """
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)
