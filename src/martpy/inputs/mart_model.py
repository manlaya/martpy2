#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, subprocess
from pathlib import Path

# from martpy.utils.config import MARTBIN
from martpy.inputs._rma_parser import (
    _parse_marthe_project,
    _write_rma_file
) 
from martpy.utils.os_utils import mv_res


def read_rma_file(rma_file):
    """Shortcut function to create a MARTHE project.
    
    Parameters
    ----------
    rma_file: `str`
        Path to the RMA file to read.
    """
    return MartProject.from_rma_file(rma_file)


class MartProject:
    """Object to store MARTHE project information from *.rma file."""

    def __init__(self, rma_file, files=None, title='MARTHE Project'):
        """Instantiation.

        Parameters
        ----------
        rma_file: `str`
            Path to the RMA file to write.

        files: `dict`
            Dictionary containing the files the RMA project points to.

        title: `str`
            Title of the MARTHE project to insert in the RMA file.
        """
        self._rma_file = rma_file
        self._files = files if files else {}
        self.title = title
    
    def get_files(self, only_active=True):
        """Get a dictionary of the files in the RMA project.

        Parameters
        ----------
        only_active: `bool`, optional
            Whether to filter files to get only the current activated
            files. By default, it does.

        Returns
        -------
        `dict`
            Dictionary containing the files the RMA project points to.
        """
        if only_active:
            return {k: v for k, v in self._files.items() if v}
        else:
            return self._files.copy()

    @classmethod
    def from_rma_file(cls, rma_file):
        """Instantiate a MARTHE project from an RMA file.

        Parameters
        ----------
        rma_file: `str`
            Path to the RMA file to read.
        """
        files = _parse_marthe_project(rma_file)
        title = files.pop('title', 'MARTHE Project')
        return MartProject(rma_file, files, title)
    
    def to_rma_file(self, rma_file=None, title='MARTHE Project'):
        """Write a MARTHE project into an RMA file.

        Parameters
        ----------
        rma_file: `str`
            Path to the RMA file to write.

        title: `str`
            Title of the MARTHE project to insert in the RMA file.
        """
        if rma_file is None:
            rma_file = self._rma_file
        _write_rma_file(self._rma_file, rma_file, title=title)


class MartModel:

    # Object to store MARTHE model information and run the model
    # using rma, mart, permh, pastp, layer files/informations
    # One class to bring them all, and in the darkness bind them

    def __init__(self, name):
        """ Constructor for MartModel class

        Parameters
        ----------
        name : str
            The name of current model. It should correspond to the `.rma` file
            if existing.
            If the file does not exist, only the model name is stored. You can
            create a MartProject object later and assign it to the model.
        """
        self.model_name = name.replace('.rma', '')
        self.file_rma = f"{self.model_name}.rma"
        if os.path.exists(self.file_rma):
            self.model_path = os.path.dirname(self.model_name)
            self.model_name = os.path.basename(self.model_name)
            self.project = MartProject.from_rma_file(self.file_rma)
        else:
            self.model_path = os.getcwd()
            self.project = None
    
    def load_model(self,):
        # load .mart, .pastp, .layer, .permh
        raise NotImplementedError
    
    def get_outputs(self,):
        # load historiq, histobil*.prn
        raise NotImplementedError
    
    def set_batch_file(self, restart='restart.rma', overwrite=False):
        """ Set the batch file path (nom_proj_marthe.defrma) for the model run

        Parameters
        ----------
        restart : str, optional
            name of the restart file to create, by default 'restart.rma'
        overwrite : bool, optional
            If True, overwrite existing batch file, by default False
        
        Returns
        -------
        None
            Write the batch file path to run marthe without arguments
            and automatically set restarts.
        """
        if not hasattr(self, 'project') or self.project is None:
            raise ValueError("No MartProject associated with this MartModel.")
        batch_file = 'nom_proj_marthe.defrma'
        if not os.path.exists(Path(self.model_path, batch_file)) or overwrite:
            with open(Path(self.model_path, batch_file), 'w') as bf:
                bf.write(f"{self.file_rma}\n")
                bf.write(f"{restart}\n")  # automatic restart
        else:
            print(f"Batch file {batch_file} already exists.")
        return None

    def run(self, output_dir=None, martbin='marthe', mute=False, debug=False):
        """ Run the MARTHE model using the RMA project file

        Parameters
        ----------
        output_dir : str, optional
            Path to the output directory where results will be stored,
            by default None (model directory)
        martbin : str, optional
            Path to the MARTHE binary executable, by default 'marthe'
        mute : bool, optional
            If True, suppress the output of the MARTHE run, by default False
        debug : bool, optional
            If True, print debug information, by default False
        """
        
        if not hasattr(self, 'project') or self.project is None:
            raise ValueError("No MartProject associated with this MartModel.")
        
        cmd = [martbin]
        cmd_kwargs = {}

        if os.path.exists(Path(self.model_path, 'nom_proj_marthe.defrma')):
            # batch mode, cd $MODELDIR;marthe
            # the `nom_proj_marthe.defrma` is a special file for CLI
            cmd_kwargs['cwd'] = self.model_path
        else:
            cmd += [self.file_rma]
        
        if mute:
            # TODO: better use of mute options in marthe parameters ?
            # for now, just do #$ cmd > /dev/null 2>&1
            cmd_kwargs['stdout'] = subprocess.DEVNULL
            cmd_kwargs['stderr'] = subprocess.DEVNULL
        
        if debug:
            print(f"Running command: {' '.join(map(str, cmd))}")
            print(cmd_kwargs)
        
        status = subprocess.run(cmd, **cmd_kwargs).returncode  # returncode to mimic .call() return status
        
        if status != 0:
            print(f"Error: MARTHE run failed with status code {status}.")
        
        if output_dir is not None:
            # move output files to output_dir
            mv_res(dst=output_dir)
        
        return status
    
    def __repr__(self):
        _str = f"MartModel: {self.model_name}\n"
        _str += f"    Path: {self.model_path}\n"
        if self.project is not None:
            _str += f"    Title: {self.project.title}\n"
            _str +=  "    Files:\n"
            for k, v in self.project.get_files(only_active=True).items():
                _str += f"        {k}: {v}\n"
        else:
            _str += "    No MartProject associated.\n"
        return _str
