#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, subprocess
from glob import glob
import xarray as xr
from pathlib import Path
import shutil

from martpy.inputs._rma_parser import (
    MART_VARIABLES,
    _parse_marthe_project,
    _write_rma_file,
)
from martpy.utils.os_utils import mv_res
from martpy.utils.helper import get_mart_variables
from martpy.outputs import read_prn

from martpy.inputs import (
    mart_histo,
    mart_param,
    mart_layer
)
from martpy.inputs.mart_histo import read_histo_file

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
        self.rma_file = rma_file
        self.project_files = files if files else {}
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
            return {k: v for k, v in self.project_files.items() if v}
        else:
            return self.project_files.copy()

    def set_files(self, dict_files=None, **files):
        """Set the files in the RMA project.

        Parameters
        ----------
        dict_files: `dict`, optional
            Dictionary containing the files the RMA project points to.
            The keys are the file extensions and the values are the paths.
            The keys must be in the list of valid extensions.
            See :py:func:`martpy.get_mart_variables`.

        **files: `dict`
           Dictionary containing the files the RMA project points to, passed
           as keywords arguments instead of dict.

        Raises
        ------
        ValueError
           If the keys are not in the list of valid extensions.

        Example
        -------
        >>> project = MartProject.from_template()
        >>> project.set_files(permh='model.permh', pastp='times.pastp')
        >>> project.set_files({'permh': 'model.permh', 'pastp': 'times.pastp'})
        """
        if dict_files is None:
            dict_files = {}
        inputs = {**dict_files, **files}
        for k, v in inputs.items():
            if k not in MART_VARIABLES['ext'].values:
                raise ValueError(
                    'Invalid file extension {}. '
                    'Please check with `martpy.get_mart_variables()`.'
                )
            self.project_files[k] = v
        return None

    @classmethod
    def from_template(cls, rma_file='new_project.rma', title='Marthe Project'):
        """ Create a Marthe Project from scratch

        Parameters
        ----------
        rma_file : str, optional
            the name that will be used for storage, by default 'new_project.rma'

        Returns
        -------
        MartProject
        """
        _tpl_vars = MART_VARIABLES.loc[
            MART_VARIABLES['is_file'] == 1, 'ext'
        ].values
        tpl_files = dict.fromkeys(_tpl_vars)  # init with None
        return cls(rma_file, tpl_files, title)

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
        return cls(rma_file, files, title)

    def to_rma_file(self, rma_file=None, title=None):
        """Write a MARTHE project into an RMA file.

        Parameters
        ----------
        rma_file: `str`
            Path to the RMA file to write. Default is the rma file of
            the class instance (i.e overwrite!)

        title: `str`
            Title of the MARTHE project to insert in the RMA file.
            default is None (i.e use existing title)
        """
        if rma_file is None:
            rma_file = self.rma_file
        if title is None:
            title = self.title
        _write_rma_file(self.project_files, rma_file, title=title)

    def __repr__(self):
        msg = f'{self.__class__.__name__}({self.rma_file})\n'
        msg += f'Title: {self.title}\n'
        msg += f'Files: {self.project_files}'
        return msg


class MartModel(MartProject):

    # Object to store MARTHE model information and run the model
    # using rma, mart, permh, pastp, layer files/informations
    # One class to bring them all, and in the darkness bind them

    def __init__(self, name):
        """ Constructor for MartModel class

        Parameters
        ----------
        name : str, Path
            The name/path of current model. It should correspond to the `.rma` file,
            if existing. If the file does not exist, an empty one is created.
            You can later set any variable.
        """
        _model_name = str(name).replace('.rma', '')
        _rma_file = f"{_model_name}.rma"

        if os.path.exists(_rma_file):
            # factory... TODO switch back to super().__init__() ? Changes needed
            obj = MartProject.from_rma_file(_rma_file)
            self.__dict__ = obj.__dict__
        else:
            obj = MartProject.from_template()
            self.__dict__ = obj.__dict__

        self.model_path = os.path.dirname(_model_name)
        if self.model_path == '':
            self.model_path = '.'
        self.model_name = os.path.basename(_model_name)
        os.makedirs(self.model_path, exist_ok=True)

        self.mart_histo = None
        self.mart_layer = (None, None)
        self.mart_params = None
        self.outputs = {}
        self.grid = None

    def _load_var(self, varname, file):
        """Loads a variable
                
        Parameters
        ----------
        varname : str
            Variable name
        file : str | Path
            variable file
        """
        # TODO : add other variable
        absolute_path = Path(self.model_path) / file
        if varname == 'HISTORIQ':
            self.mart_histo = mart_histo.MartHisto.from_histo_file(
                filename=str(absolute_path))
        elif varname == 'PARAM':
            self.mart_params = mart_param.MartParams.from_file(
                mart_file=str(absolute_path))
        elif varname == 'COUCHE':
            self.mart_layer = mart_layer.read_layer(
                file_layer=str(absolute_path))

    def _load_grid(self, varname, file, **kwargs):
        """Loads a single grid
        
        Parameters
        ----------
        varname : str
            Variable name
        file : str | Path
            grid file

        """
        if isinstance(file, float):
            zone_coord = self.grid['zone']
            # create a new dataset where all values are the given value
            ds = xr.Dataset.gm.from_float(zone_coord, file, varname)
            
        elif self.grid is None or varname not in self.grid.data_vars:
            absolute_path = Path(self.model_path) / file
            ds = xr.Dataset.gm.load_marthe_grid(filename=str(absolute_path), **kwargs)
            if varname == 'PERMEAB':
                ds = ds.gm.get_active_mask(
                    varname.lower(),
                    as_array=True,)
        else:
            return

        self.grid = ds.gm.merge(self.grid, varname.lower())

    def load_model(self,):
        """Load .mart, .pastp, .layer files
                
        Returns
        -------
        None
            Set internal properties (_mart_histo, _mart_layer etc.)
        
        """
        # load .mart (mart_param from file), .pastp, .layer, .permh
        mart_variables = get_mart_variables()
        files = self.get_files()
        for var, file in files.items():
            serie = mart_variables.loc[mart_variables['ext'] == var, :]
            if isinstance(file, str):
                if serie['is_grid'].item():
                    continue
                self._load_var(serie['code_var_fr'].item(), file)
            elif isinstance(file, float):
                continue

    def load_all_grid(self, **kwargs):
        """Load grid files from gridmarthe and set their dataset into grid

        Returns
        -------
        None
            Set internal property (grid)
                
        """
        mart_variables = get_mart_variables()
        files = self.get_files()
        for varname, file in files.items():
            serie = mart_variables.loc[mart_variables['ext'] == varname, :]
            code_var = serie['code_var_fr'].item()
            if not serie['is_grid'].item() :
                continue
            self._load_grid(code_var, file, **kwargs)

    def load_outputs(self, path=None, loading='all'):
        if path is None:
            self.outputs = self.get_outputs(loading=loading)
        else:
            dir_path = Path(path)
            self.outputs = self.get_outputs(str(dir_path.parent), loading)

    def get_da(self, varname):
        """Get DataArray from var

        Parameters
        ----------
        varname : str
            Variable name to get from grid

        Returns
        -------
        xr.DataArray
            Returns a xarray Dataarray from var
                
        """
        if self.grid is None:
            return
        elif varname.lower() in self.grid.data_vars:
            return self.grid[varname.lower()]
        return
        
    def set_value(self, zone, value, varname):
        """Set a value in the dataset
                        
        Parameters
        ----------
        zone : int | None
            zone number
        value : float | np.ndarray
            value to be set in the zone
        varname : str
            variable name
                
        Returns
        -------
        bool
            True if modified, otherwise False
        """
        if self.grid is None:
            return False
        
        elif varname.lower() in self.grid.data_vars:
            result = self.grid.gm.set_value(zone, value, varname.lower())
            if result and varname == 'permeab':
                # case when permeab is modified, set ibound
                self.grid = self.grid.gm.get_active_mask(
                                    varname.lower(),
                                    as_array=True,)
            return result
        return False

    def to_marthe_grid(self, fileout, varname, from_z=0.0):
        """Save the MartModel object to a marthe grid
                        
        Parameters
        ----------
        fileout : str
            absolute path to save the file
        varname : str
            variable name
        from_z : float
            z dim
                
        Returns
        -------
        int
            status
        """
        file_permh = self.model_path + "/" + self.get_files()['permh']
        if not os.path.exists(file_permh):
            raise FileNotFoundError(f"{file_permh} does not exists")
        ds = self.grid
        if 'z' in ds.data_vars and from_z in ds['z']:
            ds.where(ds['z'] == from_z, drop=True)
        # avoid errors from key
        if varname.lower() not in ds.data_vars:
            if varname.upper() not in ds.data_vars:
                # raise Exception(f"{varname} not in Dataset")
                print(f"{varname} not found")
                return
            else:
                varname = varname.upper()
        else:
            varname = varname.lower()
        return ds.gm.write_marthe_grid(fileout=fileout,
                                       varname=varname,
                                       file_permh=file_permh)

    def to_config(self, fileout, varname):
        if varname == 'HISTORIQ':
            return self.mart_histo.write_file(fileout)
        if varname == "PARAM":
            return self.mart_params.write_file(fileout)
        if varname == "COUCHE":
            return shutil.copy(self.model_path+"/"+self.get_files()['layer'],
                               str(fileout))

    def to_rma(self, fileout, from_z=0.0):
        """Save the MartModel object to a .rma
                        
        Parameters
        ----------
        fileout : str
            absolute path to save the file
        from_z : float
            z dim, if 0.0 no z dim selected
                
        Returns
        -------
        bool
            True if saved otherwise False
        """
        mart_variables = get_mart_variables()
        self.write_rma_file(fileout=fileout)
        path = Path(fileout).parent

        for ext, file in self.get_files().items():
            serie = mart_variables.loc[mart_variables['ext'] == ext, :]
            varname = serie['code_var_fr'].item()

            if serie['is_grid'].item() and isinstance(file, str):
                current_file = str(path / file)
                if self.to_marthe_grid(fileout=current_file,
                                    varname=varname,
                                    from_z=from_z):
                    raise Exception("Exception has occurred")

            else:
                current_file = str(path / file) if isinstance(file, str) else file
                self.to_config(fileout=current_file,
                               varname=varname,)

        return True

    def write_rma_file(self, fileout):
        try:
            path = Path(fileout).with_suffix('.rma')
            shutil.copy(self.rma_file, str(path))
        except shutil.SameFileError:
            raise Exception(f"{fileout} and {self.rma_file} are the same, can not override current used file")
        except:
            raise Exception

    def get_outputs(self, output_dir=None, loading='all'):
        """ Load standard outputs from the model run

        Parameters
        ----------
        output_dir : str, optional
            Directory where outputs are stored. If None, use model directory.
        loading : str
            Method should load 'all' outputs or only 'histo', 'out'

        Returns
        -------
        dict
            Dictionary containing loaded outputs (historiq, etc.)
        """ # TODO : check loading value
        out_dir = output_dir if output_dir else self.model_path
        outputs = {}

        if loading == 'all' or loading == 'histo':
            # get time series
            f_hist = os.path.join(out_dir, 'historiq.prn')
            if os.path.exists(f_hist):
                outputs['historiq'] = read_prn(f_hist)

            # get balance files
            histobils = glob(os.path.join(out_dir, 'histo[bil|clim]*.prn'))
            for f in histobils:
                key = os.path.basename(f).replace('.prn', '')
                outputs[key] = read_prn(f)

        if loading == 'all' or loading == 'out':
            out_files = glob(os.path.join(out_dir, '*.out'))
            for f in out_files:
                fpastp = self.model_path+"/"+self.get_files()['pastp']
                ds = xr.Dataset.gm.load_marthe_grid(filename=f, fpastp=fpastp,
                                                    add_id_grid=True)
                key = list(ds.data_vars.keys())[0]
                outputs[key] = ds

        return outputs

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
        batch_file = 'nom_proj_marthe.defrma'
        if not os.path.exists(Path(self.model_path, batch_file)) or overwrite:
            with open(Path(self.model_path, batch_file), 'w') as bf:
                bf.write(f"{self.rma_file}\n")
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
            Path to the MARTHE binary executable, by default 'marthe'. This
            means the program called 'marthe' needs to be in your `$PATH`
        mute : bool, optional
            If True, suppress the output of the MARTHE run, by default False
        debug : bool, optional
            If True, print debug information, by default False
        """

        cmd = [martbin]
        cmd_kwargs = {}

        if os.path.exists(Path(self.model_path, 'nom_proj_marthe.defrma')):
            # batch mode, cd $MODELDIR;marthe
            # the `nom_proj_marthe.defrma` is a special file for CLI
            cmd_kwargs['cwd'] = self.model_path
        else:
            cmd += [self.rma_file]

        if mute:
            # TODO: better use of mute options in marthe parameters ?
            # for now, just do #$ cmd > /dev/null 2>&1
            cmd_kwargs['stdout'] = subprocess.DEVNULL
            cmd_kwargs['stderr'] = subprocess.DEVNULL

        if debug:
            print(f"Running command: {' '.join(map(str, cmd))}")
            print(cmd_kwargs)

        status = subprocess.run(cmd, **cmd_kwargs).returncode  # memo: returncode to mimic .call() return status

        if status != 0:
            print(f"Error: MARTHE run failed with status code {status}.")

        if output_dir is not None:
            # move output files to output_dir
            mv_res(src_dir=self.model_path, dst_dir=output_dir)

        return status

    def __repr__(self):
        _str = f"MartModel: {self.model_name}\n"
        _str += f"    Path: {self.model_path}\n"
        _str += f"    Title: {self.title}\n"
        _str +=  "    Files:\n"
        for k, v in self.get_files(only_active=True).items():
            _str += f"        {k}: {v}\n"
        return _str
