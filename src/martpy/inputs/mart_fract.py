#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

import pandas as pd

from martpy.inputs._io_utils import _build_header


# ---------------------------------------------------------------------------
# Types de fractures
# ---------------------------------------------------------------------------
# Le format .fract documente trois types de fractures verticales (doc MARTHE
# v7.8.4, pp. 197-201). Chaque type possède plusieurs mots-clés équivalents
# (synonymes français + alias anglais). On normalise tout vers un identifiant
# interne : 'semi_perm', 'imperm' ou 'conduct'.
#
# La lecture accepte tous ces mots-clés (insensible à la casse) ; l'écriture
# émet toujours la forme française canonique, comme le fait WinMarthe.
_FRACTURE_TYPE_KEYWORDS = {
    # semi-perméable
    '[fracture semi-perméable]': 'semi_perm',
    '[semi-pervious fracture]': 'semi_perm',
    # imperméable (= étanche = isolante)
    '[fracture imperméable]': 'imperm',
    '[fracture étanche]': 'imperm',
    '[fracture isolante]': 'imperm',
    '[impervious fracture]': 'imperm',
    '[insulating fracture]': 'imperm',
    # conductrice
    '[fracture conductrice]': 'conduct',
    '[conductive fracture]': 'conduct',
}

_TYPE_TO_FRACTURE_KEYWORD_FR = {
    'semi_perm': '[Fracture Semi-Perméable]',
    'imperm': '[Fracture Imperméable]',
    'conduct': '[Fracture Conductrice]',
}

# ---------------------------------------------------------------------------
# Modes de coordonnées
# ---------------------------------------------------------------------------
# Le tracé d'une fracture est donné soit en clair dans le fichier .fract
# ([Liste coordonnées]), soit délégué à un fichier .bln externe
# ([Fichier coordonnées]).
_COORDS_MODE_KEYWORDS = {
    '[liste coordonnées]': 'inline',
    '[list fracture coordinates]': 'inline',
    '[fichier coordonnées]': 'file',
    '[file fracture coordinates]': 'file',
}

_MODE_TO_COORDS_KEYWORD_FR = {
    'inline': '[Liste coordonnées]',
    'file': '[Fichier coordonnées]',
}

# Drapeau (optionnel) qui suit un nom de fichier .bln : il indique de lire
# *toutes* les fractures du fichier (chacune avec le même type et les mêmes
# paramètres que le bloc courant).
_ALL_FRACTURES_FLAGS = {
    '<toutes les fractures du fichier>',
    '<all_fractures_from_file>',
}
_ALL_FRACTURES_FLAG_FR = '<Toutes les Fractures du Fichier>'

# Noms de fichier spéciaux signifiant « réutiliser le .bln déjà nommé
# précédemment et passer à la fracture suivante ».
_CONTINUE_KEYWORDS = {'suite', 'continue'}
_CONTINUE_KEYWORD_FR = 'Suite'

# ---------------------------------------------------------------------------
# Paramètres
# ---------------------------------------------------------------------------
# Les paramètres possibles dépendent du type de fracture et ne sont pas tous
# toujours présents (doc MARTHE) :
#   - semi-perméable : Perméabilité, Pourcentage_Contact
#   - conductrice    : Transmissivité (ou Conductance)
#   - imperméable    : aucun paramètre spécifique
# Les couches (Couche_Haut / Couche_Bas) sont communes aux trois types et
# elles aussi optionnelles (valeurs par défaut documentées).
#
# On stocke les paramètres rencontrés dans un dictionnaire « ouvert » : seules
# les clés réellement présentes dans le fichier y figurent. Les clés connues
# sont normalisées ; une clé inconnue est conservée telle quelle pour ne rien
# perdre au passage lecture -> écriture.
_PARAM_KEY_TO_ATTR = {
    'perméabilité': 'permeability',
    'permeabilite': 'permeability',
    'permeability': 'permeability',
    'transmissivité': 'transmissivity',
    'transmissivite': 'transmissivity',
    'transmissivity': 'transmissivity',
    'conductance': 'transmissivity',
    'pourcentage_contact': 'contact_percentage',
    'contact_percentage': 'contact_percentage',
    'couche_haut': 'top_layer',
    'higher_layer': 'top_layer',
    'couche_bas': 'bottom_layer',
    'lower_layer': 'bottom_layer',
}

_ATTR_TO_PARAM_KEY_FR = {
    'permeability': 'Perméabilité',
    'transmissivity': 'Transmissivité',
    'contact_percentage': 'Pourcentage_Contact',
    'top_layer': 'Couche_Haut',
    'bottom_layer': 'Couche_Bas',
}

# Paramètres dont la valeur est un numéro de couche (entier).
_INT_PARAMS = {'top_layer', 'bottom_layer'}

# End-of-free-text marker (the V7.8 line); we detect it case-insensitively
# with a simple substring check.
_END_OF_HEADER_MARKER = '--- Fin du texte libre ---'

_PARAM_LINE_RE = re.compile(r'^\s*(\w+)\s*=\s*(\S+)\s*$')
_COMMENT_PREFIXES = ('#', '!', '*', '<<')


class MartFract:
    """ MARTHE vertical fractures (`.fract` file).

    Attributes
    ----------
    title : str
        free-text title (first line of the file)
    fractures : list of dict
        each fracture is a dict with the following keys:

        - ``type`` : str
            fracture type, one of ``'semi_perm'`` (semi-permeable),
            ``'imperm'`` (impermeable/sealing) or ``'conduct'`` (conductive).
        - ``params`` : dict
            parameters actually present for this fracture, with normalised
            keys among ``'permeability'``, ``'transmissivity'``,
            ``'contact_percentage'``, ``'top_layer'`` and ``'bottom_layer'``.
            Only the keys found in the file are present (they are optional and
            type-dependent). An unknown key is kept verbatim.
        - ``coord_mode`` : str
            ``'inline'`` if coordinates are listed in the file, ``'file'`` if
            they are delegated to an external `.bln` file.
        - ``coordinates`` : ``pd.DataFrame``
            ``x`` / ``y`` points (empty when ``coord_mode == 'file'``).
        - ``coord_file`` : str or None
            name of the external `.bln` file (or ``'Suite'`` to reuse the
            previously named one) when ``coord_mode == 'file'``.
        - ``all_fractures_from_file`` : bool
            whether the ``<Toutes les Fractures du Fichier>`` flag was set,
            i.e. read every fracture of the external `.bln` file.

    Notes
    -----
    When coordinates are delegated to a `.bln` file (``coord_mode == 'file'``),
    martpy only keeps the *reference* to that file: it does not read the
    `.bln` content, so ``coordinates`` stays empty. The reference is preserved
    faithfully on write.

    Examples
    --------
    >>> mf = MartFract.from_file('model.fract')
    >>> mf.fractures[0]['type']
    'semi_perm'
    >>> mf.fractures[0]['params']['permeability']
    0.009278
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

        Section keywords and parameter names are always written in their
        French canonical form (to match WinMarthe output); ``lang`` only
        controls the end-of-free-text header marker.

        Parameters
        ----------
        filename : str
            path to the output `.fract` file
        encoding : str, optional
            file encoding, by default ``'cp1252'``
        lang : str, optional
            language for the end-of-header marker, by default ``'fr'``.
        """
        lines = _build_header(self.title, lang=lang)
        for fracture in self.fractures:
            lines.extend(_build_fracture_block(fracture))
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


def _match_fracture_type(line):
    """ Return the normalised fracture type for a header line, or ``None``
    if the line is not a fracture header.
    """
    return _FRACTURE_TYPE_KEYWORDS.get(line.strip().lower())


def _match_coords_mode(line):
    """ Return the coordinates mode (``'inline'`` or ``'file'``) for a header
    line, or ``None`` if the line is not a coordinates header.
    """
    return _COORDS_MODE_KEYWORDS.get(line.strip().lower())


def _is_all_fractures_flag(line):
    return line.strip().lower() in _ALL_FRACTURES_FLAGS


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

    Known keys are normalised to their internal attribute name; an unknown
    key is returned verbatim so that nothing is lost on round-trip.
    """
    match = _PARAM_LINE_RE.match(line)
    if not match:
        return None
    raw_key, raw_value = match.group(1), match.group(2)
    attr = _PARAM_KEY_TO_ATTR.get(raw_key.lower(), raw_key)
    return attr, raw_value


def _new_raw_fracture(fracture_type):
    """ Build the mutable accumulator used while parsing one fracture block.
    """
    return {
        'type': fracture_type,
        '_params': {},
        'coord_mode': 'inline',
        '_coords': [],
        'coord_file': None,
        'all_fractures_from_file': False,
    }


def _parse_fracture_blocks(body_lines):
    """ Parse the body of a .fract file (after the end-of-header marker).

    Walks through the lines collecting one fracture per type header
    (``[Fracture Semi-Perméable]``, ``[Fracture Imperméable]`` or
    ``[Fracture Conductrice]``, and their synonyms/aliases). Comments and
    blank lines outside of a coordinates list are skipped.
    """
    fractures = []
    current = None
    in_coords = False

    for line in body_lines:
        fracture_type = _match_fracture_type(line)
        if fracture_type is not None:
            if current is not None:
                fractures.append(_finalise_fracture(current))
            current = _new_raw_fracture(fracture_type)
            in_coords = False
            continue

        if current is None:
            # Skip until we hit the first fracture block
            continue

        coords_mode = _match_coords_mode(line)
        if coords_mode is not None:
            current['coord_mode'] = coords_mode
            in_coords = True
            continue

        if _is_comment(line):
            continue

        if in_coords:
            if current['coord_mode'] == 'file':
                _consume_file_coords_line(current, line)
            else:
                xy = _parse_coord_line(line)
                if xy is not None:
                    current['_coords'].append(xy)
        else:
            parsed = _parse_param_line(line)
            if parsed is not None:
                attr, value = parsed
                current['_params'][attr] = value

    if current is not None:
        fractures.append(_finalise_fracture(current))

    return fractures


def _consume_file_coords_line(current, line):
    """ Handle a line inside a ``[Fichier coordonnées]`` block: either the
    name of the external `.bln` file (or ``Suite``/``Continue``), or the
    ``<Toutes les Fractures du Fichier>`` flag.
    """
    stripped = line.strip()
    if _is_all_fractures_flag(stripped):
        current['all_fractures_from_file'] = True
    elif current['coord_file'] is None:
        current['coord_file'] = _normalise_coord_file(stripped)
    # Any further line is ignored (a single file name is expected).


def _normalise_coord_file(name):
    """ Normalise the external coordinates file name: the ``Suite`` /
    ``Continue`` keyword is written back in its French form.
    """
    if name.lower() in _CONTINUE_KEYWORDS:
        return _CONTINUE_KEYWORD_FR
    return name


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
    """ Convert the raw parsed values into the final fracture dict, with
    proper Python types and a coordinates ``pd.DataFrame``.
    """
    params = {}
    for key, value in raw['_params'].items():
        params[key] = _convert_param_value(key, value)

    fracture = {
        'type': raw['type'],
        'params': params,
        'coord_mode': raw['coord_mode'],
        'coordinates': pd.DataFrame(raw['_coords'], columns=['x', 'y']),
        'coord_file': raw['coord_file'],
        'all_fractures_from_file': raw['all_fractures_from_file'],
    }
    return fracture


def _convert_param_value(key, value):
    """ Convert a parameter value string to the right Python type: layer
    numbers are integers, other known parameters are floats. An unknown key
    falls back to float, then to the raw string.
    """
    if key in _INT_PARAMS:
        return int(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def _build_fracture_block(fracture):
    """ Build the list of lines for a single fracture block in MARTHE format
    (French canonical keywords).
    """
    fracture_type = fracture.get('type', 'semi_perm')
    type_keyword = _TYPE_TO_FRACTURE_KEYWORD_FR.get(
        fracture_type, _TYPE_TO_FRACTURE_KEYWORD_FR['semi_perm']
    )
    lines = [type_keyword]

    for key, value in fracture.get('params', {}).items():
        param_key = _ATTR_TO_PARAM_KEY_FR.get(key, key)
        lines.append(f'{param_key} = {_format_value(value)}')

    coord_mode = fracture.get('coord_mode', 'inline')
    lines.append(_MODE_TO_COORDS_KEYWORD_FR[coord_mode])

    if coord_mode == 'file':
        coord_file = fracture.get('coord_file')
        if coord_file:
            lines.append(coord_file)
        if fracture.get('all_fractures_from_file'):
            lines.append(_ALL_FRACTURES_FLAG_FR)
    else:
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
