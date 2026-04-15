import pytest
from martpy import get_mart_variables


def test_get_mart_variables_all():
    """Test returning all variables."""
    df = get_mart_variables()
    var = df['code_var_fr'].to_numpy()
    assert not df.empty
    assert 'PERMEAB' in var
    assert 'DEBIT' in var
    assert 'CHARGE' in var
    assert len(df) == 332
    assert len(df.columns) == 10



def test_get_mart_variables_valid_type():
    """Test filtering with valid variable type."""
    df = get_mart_variables(variable_type="soil")
    var = df['code_var_fr'].to_numpy()
    assert not df.empty
    assert 'RUMAX' in var
    assert 'T_DEMI_PERCOL' in var
    assert 'PERMEAB' not in var


def test_get_mart_variables_invalid_type():
    """Test error on invalid variable type."""
    with pytest.raises(ValueError, match="Invalid variable type"):
        get_mart_variables(variable_type="invalid")
