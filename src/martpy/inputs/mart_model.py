#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# import os, subprocess

# from martpy.utils.config import MARTBIN
from martpy.inputs._rma_parser import (
    _parse_marthe_project,
    _write_rma_file
) 


def read_rma_file(file_rma):
    """
    Docstring for read_rma_file
    
    Parameters
    ----------
    file_rma: str
        Path to the rma project to read
    """
    return MartProject.from_rma_file(file_rma)


class MartProject:
    def __init__(self, rma, files={}):
        self.rma   = rma
        self.files = files
    
    def get_files(self, only_active=True):
        """ Get a dictionnary of files in RMA project

        Parameters
        ----------
        only_active : bool, optional
            filter files to get only the current activated files,
            by default True

        Returns
        -------
        dict
            dict with files stored in RMA project
        """
        if only_active:
            return {k: v for k, v in self.files.items() if v}
        else:
            return self.files

    @classmethod
    def from_rma_file(cls, rma_file):
        files = _parse_marthe_project(rma_file)
        return MartProject(rma_file, files)
    
    def write_file(self, file_rma=None, title='MARTHE Project'):
        if file_rma is None:
            file_rma = self.file_rma
        _write_rma_file(self.rma, file_rma, title=title)


# class for RMA/ MartModel
# MartModel (storing MartProject + grid + histo + forcings + timesteps, methods to run,
# postprocess, etc).
# read rma file, check for defrma, optionaly read permh with gridmarthe and get
# dimensions
class MartModel:
    def __init__(self, file_rma=None):
        self.file_rma = file_rma
        raise NotImplementedError('MartModel class is not yet constructed')

    def run(self):
        raise NotImplementedError()
    