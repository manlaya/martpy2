#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pandas import read_csv
from .config import _get_resource_file
from .misc import _canonicalize_name


def _build_mart_variables():
    """ Build the MART_VARIABLES DataFrame from the resource file
    """
    return read_csv(
        _get_resource_file('marthe_variables.csv'),
        sep='\t',
        encoding='ISO-8859-1'
    )


MART_VERSION = '7.8.4'
NAN_VALUES = [9999., -9999., 8888.]  # Example NaN values, can be modified as needed

MART_VARIABLES = _build_mart_variables()
MART_HISTO_VAR = read_csv(_get_resource_file('marthe_histo.csv'))


def _build_histo_mappings():
    """Build bidirectional dicts between histo variable names and generic ones.

    A "histo" name is the one written in .histo files and .prn headers
    (e.g. ``'Charge'``, ``'Débit_Rivi'``). A "generic" name is the
    user-facing canonical form, accent-free and lowercase (e.g. ``'charge'``,
    ``'debit_rivi'``).

    The canonical generic name is derived deterministically from the histo
    name via :func:`_canonicalize_name`. This gives full coverage of all
    149 histo variables, independent of whether ``marthe_variables.csv``
    holds a matching entry.

    On top of that, aliases from ``marthe_variables.csv`` are accepted as
    input to :func:`~martpy.utils.helper.to_histo_varname` (so a user can
    write ``DEFIC_SOL`` or ``HYDR_HEAD`` as well as ``deficit_sol`` or
    ``charge``). Aliases never override the canonical mapping, so reading
    a histo file always yields the canonical generic name.

    Returns
    -------
    tuple of 4 dicts
        ``HISTO_TO_GENERIC_FR``, ``HISTO_TO_GENERIC_EN``,
        ``GENERIC_TO_HISTO_FR``, ``GENERIC_TO_HISTO_EN``.
    """
    # 1. Canonical mapping derived from each histo entry.
    # Columns are normalized in a single vectorized pass instead of looping
    # row by row (dict(zip(...)) keeps the last value on duplicate keys, which
    # matches the original per-row assignment).
    histo_fr = MART_HISTO_VAR['code_histo'].astype(str).str.strip()
    histo_en = MART_HISTO_VAR['code_histo_en'].astype(str).str.strip()
    canon_fr = histo_fr.map(_canonicalize_name)
    canon_en = histo_en.map(_canonicalize_name)

    histo_to_generic_fr = dict(zip(histo_fr, canon_fr, strict=True))
    histo_to_generic_en = dict(zip(histo_en, canon_en, strict=True))
    generic_to_histo_fr = dict(zip(canon_fr, histo_fr, strict=True))
    generic_to_histo_en = dict(zip(canon_en, histo_en, strict=True))

    # 2. Aliases from marthe_variables.csv (do not override canonical mapping).
    ext = MART_HISTO_VAR['ext'].astype(str).str.strip().str.upper()
    ext_to_histo_fr = dict(zip(ext, histo_fr, strict=True))
    ext_to_histo_en = dict(zip(ext, histo_en, strict=True))

    # Keep only rows whose code_abb points to a known histo extension.
    code_abb = MART_VARIABLES['code_abb']
    key = code_abb.astype(str).str.strip().str.upper()
    valid = (
        code_abb.notna()
        & ~key.isin(['', 'KKKKK'])
        & key.isin(set(ext_to_histo_fr))
    )

    alias_fr = MART_VARIABLES.loc[valid, 'code_var_fr'].map(_canonicalize_name)
    alias_en = MART_VARIABLES.loc[valid, 'code_var_en'].map(_canonicalize_name)
    valid_key = key[valid]

    # The original loop used setdefault (first alias wins on duplicate keys).
    # Reversing before dict(zip(...)) reproduces that: the last write wins, so
    # the first row in document order ends up kept.
    alias_to_histo_fr = dict(zip(
        alias_fr[::-1], valid_key.map(ext_to_histo_fr)[::-1], strict=True
    ))
    alias_to_histo_en = dict(zip(
        alias_en[::-1], valid_key.map(ext_to_histo_en)[::-1], strict=True
    ))

    # Canonical mapping always wins over aliases.
    generic_to_histo_fr = {**alias_to_histo_fr, **generic_to_histo_fr}
    generic_to_histo_en = {**alias_to_histo_en, **generic_to_histo_en}

    return (
        histo_to_generic_fr,
        histo_to_generic_en,
        generic_to_histo_fr,
        generic_to_histo_en,
    )


(
    HISTO_TO_GENERIC_FR,
    HISTO_TO_GENERIC_EN,
    GENERIC_TO_HISTO_FR,
    GENERIC_TO_HISTO_EN,
) = _build_histo_mappings()

COMMENT_BLOCK = '/!!!!!/!!!!!'
COMMENTS = ['!', '#']

MART_OUTPUTS = [
    "chasim.out",
    "debsim.out",
    "veloci.out",
    "trajmar.out",
    "grill_crit_ecarts.out",
    "ecarpara.out",
    'converg.txt',
    "bilandeb.txt",
    "chasimsq.prn",
    "histobil_debit.prn",
    "histobil_nap_cumu.prn",
    "histobil_nap_pastp.prn",
    "histobil_riv_dra_lac.prn",
    "historiq.prn",
    "histoclim.prn",
    "histomas.prn",
    "histomas_pastp.prn",
    "histomas_cumul.prn",
    "rivsim.prn",
    "crit_ecart_simul.prn",
    "historiq_sim_obs.prn",
    "histodif.prn",
    "histobil_dif_debit.prn",
    "mart_ver.txt",
    "marthe.txt",
    "reseau_riv_drains_lacs.txt",
]

# memo: look into modumar_marlibfi.f90:L86 for list of actions
# TODO english version ? (modumar_marlibfi.f90:L92)
# memo: when sequence (eg 1:2), mart align to center but right align
# is still ok (parsed by marthe)
ACTIONS_FMT = {
    'ACTION'    : 'I={value:>2};',
    'FICHIER'   : 'N: {file_path}',
    'GRILLE'    : 'N: {grid}',
    'LIST_MAIL' : 'N: {file_path}',
    'COUCHE'    : 'C={layer:>7}V={value:>10};',
    'MAILLE'    : 'C={col:>7}L={row:>7}P={layer:>7}V={value:>10};',
    'MAILL'     : 'C={col:>7}L={row:>7}P={layer:>7}V={value:>10};',  # old version
    'FICH_METE' : 'N={step:>7}',
    'ZONEP'     : 'Z={zone:>7}V={value:>10};',
    'ZONE_SOL'  : 'Z={zone:>7}V={value:>10};',
    'ZONE_CLIM' : 'Z={zone:>7}V={value:>10};',
    'ZONE_IRRI' : 'Z={zone:>7}V={value:>10};',
    'ZONE_GEO'  : 'Z={zone:>7}V={value:>10};',
    'ZONE_GEO2' : 'Z={zone:>7}V={value:>10};',
    'ZONE_GEO3' : 'Z={zone:>7}V={value:>10};',
    'EDITION'   : 'I={edit:>2};',
    'TRONCON'   : 'A={afluent:>7}T={tronc:>7}V={value:>10};',
    'LAC_GLOB'  : 'L={lake:>7}V={value:>10};',
    'LAC_EXUT'  : 'L={lake:>7}A={afluent:>7}V={value:>10};',
}

_FLOAT_PATTERN = r'[+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)?'

# MEMO: regexp for parsing
# - '*' or ':' in value, \S then if in parsing func, '?' for optional group
# - transient/evolution file are not parsed in every parser string as it may
#   be common to different actions. A dedicated func is in _io_utils.py
#   (_parse_param_file_and_col) and called after main parser in _parse_parameter_line
_ACTION_PARSER = {
    'ACTION'    : r'I=\s*(?P<value>(-)?\d+);',
    'GRILLE'    : r'N:\s*(?P<grid>\S+?)\s*$',
    'LIST_MAIL' : r'N:\s+(?P<file_path>.*?)(?:\s+<[^>]+>|$)',   # file - opt
    'COUCHE'    : r'C=\s*(?P<layer>\S+)\s*V=\s*(?P<value>\S+)\s*;\s*$',  # possible '*' or ':' in value, \S then if in parsing func
    'MAILLE'    : r'C=\s*(?P<col>\S+)\s*L=\s*(?P<row>\S+)\s*P=\s*(?P<layer>\S+)\s*V=\s*(?P<value>\S+)\s*;',  # \d+\.*\d ?
    'FICH_METE' : r'N=\s*(?P<step>\S*)',
    'ZONEP'     : r'Z=\s*(?P<zone>\S+)\s*V=\s*(?P<value>\S+)\s*;\s*$',
    'ZONE_SOL'  : r'Z=\s*(?P<zone>\S+)\s*V=\s*(?P<value>\S+)\s*;\s*$',
    'ZONE_CLIM' : r'Z=\s*(?P<zone>\S+)\s*V=\s*(?P<value>\S+)\s*;\s*$',
    'ZONE_IRRI' : r'Z=\s*(?P<zone>\S+)\s*V=\s*(?P<value>\S+)\s*;\s*$',
    'ZONE_GEO'  : r'Z=\s*(?P<zone>\S+)\s*V=\s*(?P<value>\S+)\s*;\s*$',
    'ZONE_GEO2' : r'Z=\s*(?P<zone>\S+)\s*V=\s*(?P<value>\S+)\s*;\s*$',
    'ZONE_GEO3' : r'Z=\s*(?P<zone>\S+)\s*V=\s*(?P<value>\S+)\s*;\s*$',
    'EDITION'   : r'[I|\*]=\s*(?P<edit>\d+)\s*;',  # TODO complete edition parsing dict
    'FICHIER'   : r'N:\s*(?P<file_path>\S+)',
    'TRONCON'   : r'A=\s*(?P<afluent>\S+)\s*T=\s*(?P<tronc>\S+)\s*V=\s*(?P<value>\S+)\s*;',
    'LAC_GLOB'  : r'L=\s*(?P<lake>\S+)\s*V=\s*(?P<value>\S+)\s*;\s*$',
    'LAC_EXUT'  : r'L=\s*(?P<lake>\S+)\s*A=\s*(?P<afluent>\S+)\s*V=\s*(?P<value>\S+)\s*;',
}

# LIB_ACTION_9_UK = [
#     "GRID     " , "LAYER    " , "GEO_ZONE " , "CELL     " , "OUTPUT   ",
#     "SOIL_ZONE" , "IRRI_ZONE" , "UNS_ZONE " , "TRIBUTAR " , "METE_FILE",
#     "LIST_CELL" , "CLIM_ZONE" , "LAKE_GLOB" , "LAKE_OUTL" , "FILE     ",
# ]

# 1=NAQ ; 2=AQU ; 3=Sat ; 4=S_Liq ; 5=S_NAQ ; 99=Rien
# cf. modumar_Objets_Marth.f90
# pour les histo, modumar_Histor_et_Optimis.f90
# (pour les historiq et nom des champs: modumar_Marlibfi.f90/L3894
EDITIONS_FMT = {
    'CHARGE'      : 'I={edit:>2};',
    'VITESSE'     : 'I={edit:>2} [C={C:>7};L={L:>7};P={P:>7};Gig={Gig:>2}]',
    'FLUX_INFILTR': 'I={edit:>2};Z={Z:>2};C={C:>2};',
    'DEBIT'       : '*={edit:>2};V={V:>2};L={L:2};S={F:>2};Z={Z:>2};',
    'DEBIT_RIVI'  : 'I={edit:>2};L={L:>2};F={F:>2};B={B:>2};',
    'RUISSEL'     : 'I={edit:>2};Z={Z:>2};C={C:>2};',
    'RECHARGE'    : 'I={edit:>2};Z={Z:>2};C={C:>2};',
    'FLUX_PLUV'   : 'I={edit:>2};Z={Z:>2};C={C:>2};',
    'PROFOND_NAPP': 'I={edit:>2};Z={S:>2};',
    'HAUTEU_RIVI' : 'I={edit:>2};P={P:>2};',
    'SATUR_NAQ'   : 'I={edit:>2};R={P:>2};',
    # '%SATURAT':
    # 'ETAT_HYD_CLIM'  # en lecture = que fichier
}


OPT_LIST_MAIL = {
    'sum': '<Somm_Mail>',
    'keep_9999': '<Keep_9999>',
    'mean': '<Moyenne>',
    'init_zero': '<Init_a_Zero>',
    'xyv': '<X_Y_V>',
    'xyc': '<X_Y_C>',
    'xyz': '<X_Y_Z>'
}

_OPT_MAIL_PARSER = r'<([^>]+)>'  # to use with re.findall()

# from modumar_Marlibfi.f90 l 3898 à 3928 // len=15
HISTO_BIL_HEAD = [
       "Entr_Limit     "  , "Sort_Limit     ", "Entr_Inject_fix", "Sort_Pompag_fix" ,
       "Réduct_Pompage ", "Désaturation   ", "Débord/Suintem ", "Recharge_Maill " ,
       "Évaporat_Maill ", "Excès_Irrigat  ", "Stockage_Posit ", "Stockage_Négat " ,
       "Rivière->Nappe ", "Nappe->Rivière ", "Éch_Phas_Posit ", "Éch_Phas_Négat"  ,
       "Drains->Nappe  ", "Nappe->Drains  ", "Lacs->Nappe    ", "Nappe->Lacs    " ,
       "Transpir_Racin " ,
       "Glob_Limites   ", "Glob_Intern_fix", "Glob_Stock     " ,
       "Glob_Riv_Nappe ", "Abs_Déb_Résid  ", "Déb_Résid_Maxi " ,
       "%_Non_Converg  ", "d_BilQ_Global  ", "d_BilQ<->QFixé " ,
       "Glob_Drain_Napp", "Glob_Lacs_Nappe", "d_BilanVol_Pas " ,
       "%_Non_CV_Gl_Pas", "Nombre_Désatur ", "Nombre_Suintem ", "Nombre_Itérat  " ,
       "Nombre_Sous-pas", "Nbre_Réduc_Pomp"
]

# TODO: change in modumar !
# for now, only rename in postproc, in order to avoid breaking
# existing scripts
HISTO_BIL_ZONE_HEAD = [
       "Entr_Limit_ext ", "Sort_Limit_ext ", "Glob_Limit_ext " ,
       "Entr_Limit_Zon ", "Sort_Limit_Zon ", "Glob_Limit_Zon " ,
       "Entr_Inject_fix", "Sort_Pompag_fix", "Glob_Intern_fix" ,
       "Réduct_Pompage " , "Désaturation   " ,
       "Recharge_Maill ", "Évaporat_Maill ", "Excès_Irrigat  " ,
       "Transpir_Racin " ,
       "Entr_Résiduel  ", "Sort_résiduel  ", "Glob_Résiduel  " ,
       "Débord/Suintem ", "Déb._de_Transit" ,
       "Rivière->Napp  ", "Napp->Rivière  ", "Glob_Riv-Nappe " ,
       "Drains->Napp   ", "Napp->Drains   ", "Glob_Drain-Napp" ,
       "Lacs->Nappe    ", "Nappe->Lacs    ", "Glob_Lacs-Napp " ,
       "Éch_Phas_Posit ", "Éch_Phas_Négat ",
       "Glob_Éch_Phase " , "Stockage       " , "Somme=Bil_Glob." ,
       "Entr_Lim_Z_Hau ", "Sort_Lim_Z_Hau ", "Glob_Lim_Z_Hau " ,
       "Entr_Lim_Z_Bas ", "Sort_Lim_Z_Bas ", "Glob_Lim_Z_Bas " ,
]

RENAME_HISTOBIL_HEAD_ZONE = {
    # k=BILZONE_KEY, v='BIL_KEY' (stripped)
    "Stockage": "Glob_Stock",
    "Glob_Lacs-Napp" : "Glob_Lacs-Nappe",
    "Rivière->Napp"  : "Rivière->Nappe",
    "Napp->Rivière"  : "Nappe->Rivière",
    "Glob_Riv-Nappe" : "Glob_Riv_Nappe",
    "Drains->Napp"   : "Drains->Nappe",
    "Napp->Drains"   : "Nappe->Drains",
    "Glob_Drain-Napp": "Glob_Drain_Napp",
}
BLOCK_MART = {
    'Sauvegardes et contrôles' : 'outputs',
    'Pas de Temps et sous-pas de temps' : 'timesteps',
    'Contrôle de la Résolution Hydrodynamique de Nappe' : 'solver',
    'Unités des données' : 'units',
    'Options de Géométrie, États de Référence, Processeurs' : 'geometry_process',
    'Couplage et Transport : Concentration, Chaleur, Salinité' : 'transport',
    'Salinité, Densité' : 'density',
    'Température , effets Thermiques': 'thermal',
    'Concentration et Trajectoires' : 'trajectory_concentr',
    'Zone Non-Saturée et Multiphasique': 'unsat_multiphas',
    'Eau, Gaz, Huile, Eau Salée': 'gaz_oil_salt',
    'Écoulement d\'Huile, Eau Salée, NAQ': 'oil_naq_flow',
    'Écoulement de Gaz' : 'gaz_flow',
    'Géochimie' : 'geochemistry',
    'Calibration automatique / Analyse de sensibilité / Optimisation' : 'optim',
    'Réseau de Rivières, Drains, Lacs': 'river',
    'Hydroclimatologie': 'climatology',
    'Contrôles sur écran en cours de calcul': 'stdout',
    'Allégements des écritures du fichier bilandeb': 'log_level',
    'Cultures, Nitrate' : 'agriculture',
    'Fin des paragraphes': 'dummy',
    'Initialisation avant calcul' : 'init_parameters',
    'Fin d\'Initialisation': 'dummy',
    'Fin du fichier des Paramètres Généraux': 'dummy',
}
BLOCK_MART_EN = {
    'Outputs and controls' : 'outputs',
    'Time Steps and sub-steps' : 'timesteps',
    'Control of Aquifer Hydraulic solving process' : 'solver',
    'Data units' : 'units',
    'Geometric options, Data reference, Processors' : 'geometry_process',
    'Transport/Coupling: Concentration, Heat, Salinity' : 'transport',
    'Salinity, Density' : 'density',
    'Temperature , Thermal effects' : 'thermal',
    'Concentration and Pathlines' : 'trajectory_concentr',
    'Unsaturated Zone and Multiphase flow' : 'unsat_multiphas',
    'Water, Gas, Oil, Salt Water' : 'gaz_oil_salt',
    'Oil Flow (Oil, Salt Water, NAQ)' : 'oil_naq_flow',
    'Gas Flow' : 'gaz_flow',
    'Geochemistry' : 'geochemistry',
    'Automatic Calibration / Sensitivity analysis / Optimization' : 'optim',
    'River Network, Drains, Lakes' : 'river',
    'Hydroclimatology' : 'climatology',
    'Screen display during the run' : 'stdout',
    'Shorter version of the flowbalance file' : 'log_level',
    'Crops, Nitrate' : 'agriculture',
    'End of paragraphs' : 'dummy',
    'Initialization before simulation' : 'init_parameters',
    'End of Initialization' : 'dummy',
    'End General Parameters file' : 'dummy',
}

SOIL_VARIABLES = {
    "CAP_SOL_PROGR",
    "RUMAX",
    "EQU_RUIS_PERC",
    "T_DEMI_PERCOL",
    "DEF_SOL_PROGR",
    "DEFIC_SOL",
    "NIV_RESERV_H",
    "CORREC_PLUIE",
    "CORR_ETP",
    "T_RUISS",
    "NIV_RUI",
    "TEMPER_AIR",
    "CORR_TEMP_AIR",
    "RETEN_NEIGE",
    "EVAP_NEIGE",
    "COEF_FONTE_PLU",
    "TEMPER_FONTE",
    "DEGR_JOUR_NEI",
    "FONT_SOL_NEIG",
    "STOCK_NEIGE",
    # external basin parameters:
    # "TEMPERAT_SOL"
    # "T_1/2_TARIS_1"
    # "T_1/2_PERC_G2"
    # "T_1/2_TARIS_2"
    # "FACT_ECH_SOUT"
    # "NIV_RESERV_G1"
    # "NIV_RESERV_G2"
    # "RET_INI_NEIGE"
}

# TODO: add more variable types and their corresponding variables in the future
# TODO: is VALID_VARIABLE_TYPES the right name ? is TYPES may be better ?
VALID_VARIABLE_TYPES = [
    'soil',
]
