#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, subprocess

from martpy.utils.config import MARTBIN
from martpy.inputs._mart_parser import (
    _parse_rma_file,
    _write_rma_file
) 

# class for RMA/ MartModel
# read rma file, check for defrma, optionaly read permh with gridmarthe and get dimensions

class MartModel:
    def __init__(self, file_rma=None):
        self.file_rma = file_rma
        self.rma = _parse_rma_file(file_rma) if file_rma is not None else {}

    def write_file(self, file_rma=None, title='MARTHE Project'):
        if file_rma is None:
            file_rma = self.file_rma
        _write_rma_file(self.rma, file_rma, title=title)

    def __getitem__(self, key):
        return getattr(self, key)
   
    def __setitem__(self, key, value):
        setattr(self, key, value)
    
    def __repr__(self):
        pass

    def run(self, martbin=None, workdir=None, wait=True):
        """ Run marthe model with current rma file

        Parameters
        ----------
        martbin : str, Path, optional
            path to marthe binary (default is from config)
        workdir : str, Path, optional
            working directory where to run marthe (default is current directory)
        wait : bool, optional
            if True (default) wait for process to end before returning

        Returns
        -------
        subprocess.Popen:
            the process object from subprocess.Popen

        Example
        -------

        >>> m = MartModel()
        >>> m.run(martbin='/path/to/marthe/bin/marthe', workdir='/path/to/workdir')
        <subprocess.Popen object at 0x7f8c9b0c1d90>
        """
        if martbin is None:
            martbin = MARTBIN
        if workdir is None:
            workdir = os.getcwd()
        
        process = subprocess.Popen(
            [martbin, self.file_rma],
            cwd=workdir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        if wait:
            process.wait()
        
        return process
