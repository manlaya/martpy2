# -*- coding: utf-8 -*-
"""
Created on Thu Mar 17 11:38:56 2022

@author: manlay

"""

import os, re
import pandas as pd
import numpy as np


def clean_inputs(obs, sim):
    obs, sim = np.array(obs).flatten(), np.array(sim).flatten()
    return obs, sim

def normalize(x, digit=3):
    """ z_score or normalize """
    return np.round(( x - np.mean(x) ) / np.std(x), digit)

def ratio(obs, sim, digit=3):
    obs, sim = clean_inputs(obs, sim)
    rd = np.nanmean(sim) / np.nanmean(obs)
    return np.round(rd, digit)

def pearsonr(obs, sim, digit=3):
    obs, sim = clean_inputs(obs, sim)
    sim = sim - np.nanmean(sim)
    obs = obs - np.nanmean(obs)
    r = np.sum(sim * obs) / (np.sqrt(np.sum(sim ** 2)) * np.sqrt(np.sum(obs ** 2)))
    return np.round(r, digit)

# def coeffcorr(obs, sim, digit=3):
    # obs, sim = np.array(obs), np.array(sim)
    # return np.round(np.corrcoef(obs, sim)[0, 1], digit)

# def rsquared(obs, sim, digit=3):
    # return np.round(coeffcorr(obs, sim) ** 2, digit)

def mae(obs, sim, digit=3):
    """ Mean Absolute Error
    Smaller is better(Best value is 0)
    """
    obs, sim = clean_inputs(obs, sim)
    return np.round(np.nanmean(np.abs(sim - obs)), digit)

def bias(obs, sim, abs=False, percent=False, digit=3):
    obs, sim = clean_inputs(obs, sim)
    # return np.round((1/np.size(obs)) * np.sum(obs - sim), digit)
    if not abs:
        biais = np.round(np.nanmean(sim - obs), digit)
    else:
        biais = mae(obs, sim, digit)
    
    if percent:
        return np.round(100 * (biais / np.nanmean(obs)), digit)
    else:
        return biais

# def mape(obs, sim, digit=4):
    # """ MAPE (Mean Absolute Percentage Error) """
    # return np.round( 100 * np.nanmean( (obs-sim) / obs ), digit)

def mse(obs, sim, bias_excluded=False, digit=3):
    """ Mean Squared Error
    Smaller is better(Best value is 0)
    """
    obs, sim = clean_inputs(obs, sim)
    if bias_excluded :
        sim = sim - bias(obs, sim)
    return np.round(np.nanmean(( sim - obs)**2), digit)

def rmse(obs, sim, bias_excluded=False, norm=False, digit=3):
    """Root Mean Squared Error
    Smaller is better(Best value is 0)
    """
    rmserr = np.round(np.sqrt(mse(obs, sim, bias_excluded)), digit)
    if norm:
        return np.round(rmserr / np.nanmean(obs), digit)
    else:
        return rmserr

def nrms_be(obs, sim, digit=3):
    """ Normed root mean square error bias-excluded, used in vergnes et al. 2020 aqui-FR
    0 for perfect score, <0.8 acceptable
    https://doi.org/10.5194/hess-24-633-2020
    """
    obs, sim = clean_inputs(obs, sim)
    err = ( sim - np.nanmean(sim)) - (obs - np.nanmean(obs))
    rmse = np.sqrt(np.nansum(err**2) / np.size(obs) )
    return np.round(rmse / np.std(obs), digit)

def nse(obs, sim, bias_excluded=False, digit=3):
    """ Nash-Shutcliffe efficiency computation
    https://doi.org/10.1016/0022-1694(70)90255-6
    """
    obs, sim = clean_inputs(obs, sim)
    if bias_excluded:
        sim = sim - bias(obs, sim)
    return np.round((1 - ( np.nansum((obs-sim)**2) / np.nansum((obs-np.nanmean(obs))**2) ) ), digit)
    # nash_garden = 1 - ( np.mean((obs - sim)**2) / (np.std(obs)**2) )

def nnse(obs, sim, digit=3):
    """ Normalize nse """
    return 1 / (2 - nse(obs, sim, digit))

def kge(obs, sim, digit=3):
    """ Kling-Gupta Efficiency 
    inputs array must be nan-free !
    refs.
    Gupta et al. (2009) : https://doi.org/10.1016/j.jhydrol.2009.08.003
    Kling et al. (2012) : https://doi.org/10.1016/j.jhydrol.2012.01.011
    """
    obs, sim = clean_inputs(obs, sim)
    r = np.corrcoef(obs, sim)[0, 1] # pearson r
    
    sim_std = np.std(sim)
    obs_std = np.std(obs)
    obs_mean = np.mean(obs)
    sim_mean = np.mean(sim)
    
    kge = 1 - np.sqrt( ((r - 1)**2) + (((sim_mean / obs_mean)-1)**2) + (((sim_std / obs_std) - 1)**2) )
    return np.round(kge, digit)

def bier_skill_score(previ):
    """ Brier skill score opération assim... :) """
    print('not yet implemented')
    

def rpss():
    """ Ranking Probability Skill Score 
    opération assim... :) """
    print('not yet implemented')

class MartheMetrics:
    
    def __init__(self, obs, sim):
        
        self.corr = pearsonr(obs, sim)
        self.ratio= ratio(obs, sim)
        self.bias = bias(obs, sim)
        self.mae  = mae(obs, sim)
        self.rmse = rmse(obs, sim)
        self.rmse_bias_excluded = rmse(obs, sim, bias_excluded=True)
        self.rmse_norm = rmse(obs, sim, norm=True)
        self.nse  = nse(obs, sim)
        self.nse_bias_excluded = nse(obs, sim, bias_excluded=True)
        self.kge = kge(obs, sim)
        self.nrms_be = nrms_be(obs, sim)
        
        self.abb = {
            'corr'              : f'{self.corr:<6} Pearson correlation coefficient',
            'ratio'             : f'{self.ratio:<6} Rd, Ratio criterion',
            'bias'              : f'{self.bias:<6} Bias',
            'mae'               : f'{self.mae:<6} Mean absolute error (absolute bias)',
            'rmse'              : f'{self.rmse:<6} Root Mean Squared Error',
            'rmse_bias_excluded': f'{self.rmse:<6} Root Mean Squared Error Bias excluded',
            'rmse_norm'         : f'{self.rmse:<6} Normed Root Mean Squared Error',
            'nse'               : f'{self.nse:<6} Nash Shutcliffe Efficiency',
            'nse_bias_excluded' : f'{self.nse_bias_excluded:<6} NSE without bias',
            'kge'               : f'{self.kge:<6} Kling-Gupta efficiency',
            'nrms_be'           : f'{self.nrms_be:<6} Normed root mean square error bias-excluded, Vergnes et al. 2020',
        }
    
    def __repr__(self):
        msg = "Compute differents metrics for simulations\n"
        msg += self.dict_as_str(self.abb)
        return msg
    
    def to_dic(self):
        return {
            'corr'               : self.corr,
            'ratio'              : self.ratio,
            'bias'               : self.bias,
            'mae'                : self.mae ,
            'rmse'               : self.rmse,
            'rmse_bias_excluded' : self.rmse_bias_excluded,
            'rmse_norm'          : self.rmse_norm,
            'nse'                : self.nse ,
            'nse_bias_excluded'  : self.nse_bias_excluded,
            'kge'                : self.kge,
            'nrms_be'            : self.nrms_be,
        }
    
    def dict_as_str(self, dic):
        text = ""
        for k, v in dic.items():
            text += "{:<12}: {:<6}\n".format(k, v)
        return text

    def to_dataframe(self, index=[0]):
        return pd.DataFrame(self.to_dic(), index=index)

