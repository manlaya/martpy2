import pytest
from martpy import get_mart_variables  


def test_get_mart_variables_all():
    """Test returning all variables."""
    df = get_mart_variables()
    assert not df.empty


def test_get_mart_variables_valid_type():
    """Test filtering with valid variable type."""
    df = get_mart_variables(variable_type="soil")
    assert not df.empty


def test_get_mart_variables_invalid_type():
    """Test error on invalid variable type."""
    with pytest.raises(ValueError, match="Invalid variable type"):
        get_mart_variables(variable_type="invalid")