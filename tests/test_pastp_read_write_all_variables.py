#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import io
from unittest.mock import patch

from martpy.inputs.timesteps import MartTimeSteps
from martpy.utils.helper import get_mart_variables

NOT_ACTIONABLE = {
    '!!!!!',    # comment variable: lines with '!' are skipped by the parser
    'MODIFIC',  # reads an external modin file
}


def _build_fake_pastp():
    """ Build a fake pastp string with one EDITION action per variable
    of ``marthe_variables.csv`` """
    lines = [
        'Fake pastp file',
        ' #<V7.8a># --- Fin du texte libre --- ; Ne pas modifier/retirer cette ligne',
        ' *** Début de la simulation    à la date : 31/12/1979 ; ***',
    ]
    for variable in sorted(set(get_mart_variables()['code_var_fr'].to_list())):
        if variable in NOT_ACTIONABLE:
            continue
        lines.append('  /{0}/EDITION        I= 1;'.format(variable))
    lines.append(' *** Le pas :    1: se termine à la date : 01/01/1980 ; ***')
    lines.append('  /*****/***** Fin de ce pas')
    return '\n'.join(lines) + '\n'


def test_read_write_all_variables():
    """
    test reading/writing a fake pastp with every variable of
    marthe_variables.csv (see test_read_write_satur)
    """
    pastp = _build_fake_pastp()

    with patch('builtins.open', return_value=io.StringIO(pastp)):
        times = MartTimeSteps.from_file(pastp)

    variables = set(get_mart_variables()['code_var_fr'].to_list()) - NOT_ACTIONABLE
    actions = times.get_actions()['1979-12-31']
    assert set(actions) == variables, 'not all variables were read from the pastp file'
    assert '%SATURAT' in actions, 'variable starting with % not read'
    assert 'T_1/2_TARIS_1' in actions, 'variable with \'/\' in name not read'
    assert 'TEMPER_RE-INJ' in actions, 'variable with \'-\' in name not read'

    times.write_file('tests/data/tmp_outputs/all_variables_roundtrip.pastp')
    times_rewrite = MartTimeSteps.from_file(
        'tests/data/tmp_outputs/all_variables_roundtrip.pastp'
    )
    actions_rewrite = times_rewrite.get_actions()['1979-12-31']
    msg = 'not all variables were kept after write/re-read'
    assert set(actions_rewrite) == variables, msg


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, '-v', '--no-cov'])
