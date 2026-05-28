import pytest
from martpy import get_mart_variables
from martpy.utils.constant import (
    HISTO_TO_GENERIC_FR,
    HISTO_TO_GENERIC_EN,
    GENERIC_TO_HISTO_FR,
    GENERIC_TO_HISTO_EN,
)
from martpy.utils.helper import to_histo_varname, from_histo_varname


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


# ----------------------------- histo/generic mapping -----------------------------


def test_to_histo_varname_canonical():
    """Canonical generic names roundtrip to their native histo form."""
    assert to_histo_varname('charge') == 'Charge'
    assert to_histo_varname('debit_rivi') == 'Débit_Rivi'
    assert to_histo_varname('flux_ruiss') == 'Flux_Ruiss'
    assert to_histo_varname('perc_satur_nappe') == '%Satur_Nappe'


def test_to_histo_varname_accepts_aliases():
    """Generic codes from marthe_variables.csv are accepted as input aliases."""
    assert to_histo_varname('CHARGE') == 'Charge'
    assert to_histo_varname('PERMEAB') == 'Perméab'
    assert to_histo_varname('DEFIC_SOL') == 'Déficit_Sol'


def test_to_histo_varname_english():
    """Lang='en' returns English histo names."""
    assert to_histo_varname('h_head', lang='en') == 'H_Head'
    assert to_histo_varname('HYDR_HEAD', lang='en') == 'H_Head'
    assert to_histo_varname('river_flow', lang='en') == 'River_Flow'


def test_to_histo_varname_passthrough_unknown():
    """Unknown names are returned unchanged."""
    assert to_histo_varname('not_a_marthe_var') == 'not_a_marthe_var'


def test_from_histo_varname_canonical():
    """Histo names normalize to lowercase accent-free generic names."""
    assert from_histo_varname('Charge') == 'charge'
    assert from_histo_varname('Débit_Rivi') == 'debit_rivi'
    assert from_histo_varname('Flux_Ruiss') == 'flux_ruiss'
    assert from_histo_varname('%Satur_Nappe') == 'perc_satur_nappe'


def test_from_histo_varname_english():
    """Lang='en' normalizes English histo names."""
    assert from_histo_varname('H_Head', lang='en') == 'h_head'
    assert from_histo_varname('River_Flow', lang='en') == 'river_flow'


def test_from_histo_varname_fallback_canonicalization():
    """Unknown histo names fall back to deterministic canonicalization."""
    assert from_histo_varname('Some_New_Header') == 'some_new_header'


def test_from_histo_varname_idempotent():
    """Calling from_histo_varname on an already-canonical name is a no-op."""
    canonical = from_histo_varname('Charge')
    assert from_histo_varname(canonical) == canonical
    assert from_histo_varname('flux_ruiss') == 'flux_ruiss'


def test_to_histo_varname_idempotent():
    """Calling to_histo_varname on an already-histo name is a no-op."""
    histo = to_histo_varname('charge')
    assert to_histo_varname(histo) == histo
    assert to_histo_varname('Débit_Rivi') == 'Débit_Rivi'


def test_roundtrip_all_histo_variables_fr():
    """Round-trip to(from(x)) == x must hold for the 149 French histo names."""
    for histo_name in HISTO_TO_GENERIC_FR:
        generic = from_histo_varname(histo_name, lang='fr')
        assert to_histo_varname(generic, lang='fr') == histo_name


def test_roundtrip_all_histo_variables_en():
    """Round-trip to(from(x)) == x must hold for the 149 English histo names."""
    for histo_name in HISTO_TO_GENERIC_EN:
        generic = from_histo_varname(histo_name, lang='en')
        assert to_histo_varname(generic, lang='en') == histo_name


def test_mappings_cover_all_histo_variables():
    """Sanity check: all 149 histo variables are covered in both directions."""
    assert len(HISTO_TO_GENERIC_FR) == 149
    assert len(HISTO_TO_GENERIC_EN) == 149
    # GENERIC_TO_HISTO may have more entries due to marthe_variables.csv aliases
    assert len(GENERIC_TO_HISTO_FR) >= 149
    assert len(GENERIC_TO_HISTO_EN) >= 149
