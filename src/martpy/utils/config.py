#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, shutil
from platform import uname
from pandas import read_csv


def _get_martbin(bin='marthe'):
    """
    Function to retrieve the path to the MART binary.
    This function can be modified to change the path as needed.
    """
    if uname().system == 'Windows':
        martbin = os.path.join(os.environ.get('Bin_Marthe'), '{}.exe'.format(bin))
        if martbin is None or not os.path.exists(martbin):
            raise FileNotFoundError(f"MART binary not found at {martbin}")
    else:
        martbin = shutil.which(bin)
        if not martbin:
            raise FileNotFoundError("MART binary not found in PATH")
    return martbin


def _get_resource_file(filename):
    """ Get resource file path from package
    syntax: python >= 3.7
    """
    import importlib.resources as impresources
    return (impresources.files('martpy.resources') / filename)


# cf. modumar_Objets_Marth.f90
# pour les histo, modumar_Histor_et_Optimis.f90 (pour les historiq et nom des champs: modumar_Marlibfi.f90/L3894

MART_VERSION = '7.8.4'
LC_ALL  = 'fr'  # TODO guess lang install marthe + trad outputs/keys
NAN_VALUES = [9999., -9999., 8888.]  # Example NaN values, can be modified as needed
MART_VARIABLES = read_csv(_get_resource_file('marthe_variables.csv'), sep='\t', encoding='ISO-8859-1')

# MARTBIN = _get_martbin()
MARTBIN = None

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

ACTIONS_FMT = {
    'ACTION'    : 'I= {active};',
    'FICHIER'   : 'N: {file}',
    'GRILLE'    : 'N: {grid}',
    'LIST_MAIL' : 'N: {file}',
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

_ACTION_PARSER = {
    'ACTION'    : r'I=\s*(?P<active>\d+);',
    'GRILLE'    : r'N:\s*(?P<grid>\S+?)\s*$',  # value or file todo gérer le cas avec '=' est-ce qu'on force la regex à ne pas le prendre ou est qu'on garde et met un if pour typer le res ?
    'LIST_MAIL' : r'N:\s+(?P<file>.*?)(?:\s+<[^>]+>|$)',   # file - opt
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
    'FICHIER'   : r'N:\s*(?P<file>\S+)',
    'TRONCON'   : r'A=\s*(?P<afluent>\S+)\s*T=\s*(?P<tronc>\S+)\s*V=\s*(?P<value>\S+)\s*;',
    'LAC_GLOB'  : r'L=\s*(?P<lake>\S+)\s*V=\s*(?P<value>\S+)\s*;\s*$',
    'LAC_EXUT'  : r'L=\s*(?P<lake>\S+)\s*A=\s*(?P<afluent>\S+)\s*V=\s*(?P<value>\S+)\s*;',
}


# 1=NAQ ; 2=AQU ; 3=Sat ; 4=S_Liq ; 5=S_NAQ ; 99=Rien

EDITIONS_FMT = {
    'CHARGE'      : 'I={edit:>2};',
    'VITESSE'     : 'I={edit:>2} [C={C:>7d};L={L:>7d};P={P:>7d};Gig={Gig:>2d}]',
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


LIST_MAIL_OPT = [
    '<Somm_Mail>',
    '<Keep_9999>',
    '<Moyenne>',
    '<Init_a_Zero>',
    '<X_Y_V>',
    '<X_Y_C>',
    '<X_Y_Z>'
]

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
       "Entr_Inject_fix", "Sort_Pompag_fix", "Glob_Intern_fix" ,  # ok
       "Réduct_Pompage " , "Désaturation   " , #ok
       "Recharge_Maill ", "Évaporat_Maill ", "Excès_Irrigat  " , # ok
       "Transpir_Racin " , # ok
       "Entr_Résiduel  ", "Sort_résiduel  ", "Glob_Résiduel  " ,
       "Débord/Suintem ", # ok
       "Déb._de_Transit" ,
       "Rivière->Napp  ", "Napp->Rivière  ", "Glob_Riv-Nappe " , # e manquant ou _ devient - ...
       "Drains->Napp   ", "Napp->Drains   ", "Glob_Drain-Napp" , # idem
       "Lacs->Nappe    ", "Nappe->Lacs    ", # ok!
       "Glob_Lacs-Napp " , # ko !!!!
       "Éch_Phas_Posit ", "Éch_Phas_Négat ", # ok 
       "Glob_Éch_Phase " ,
       "Stockage       " ,  # Glob_Stock
       "Somme=Bil_Glob." ,
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
