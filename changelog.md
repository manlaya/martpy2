Changelog
=========

<!-- martpy changelog
Use : https://keepachangelog.com/en/1.0.0/ for syntax
Use : https://semver.org/ for versioning strategy
-->

<!-- ## [unreleased] -->

## [0.1.0] - 2026-05-06

### Added

- first release as a (beta) stand alone package.
- refactoring BRGM internal codes (mainly: pymarthe-jpv from JPV 20X? ; martpy(1) from AM - 2022-2024)
- Add support for reading/writing input files:
    + `*.rma` (Marthe project),
    + `*.mart` (Marthe general parameters),
    + `*.pastp` (Marthe timesteps),
    + `*.modin` (Init modifications of parameters - READER only, write is in the mart/pastp file)
    + `*.histo` (Marthe timeseries config),
    + `*.layer`, implementation step (modified) from pymarthe project:
        https://github.com/pymartheproject/pymarthe
- Add support for reading output files:
    + `histobil_*.prn` (Marthe output balance file),
    + `histoclim.prn` (Marthe hydroclimatic balance file)
    + `histomas.prn` (Marthe mass balance file)
    + `historiq.prn` (Marthe output time series),
- Add wrapper for grid management (based on `gridmarthe` library)
- Add method to fill value from zone in grid wrapper
- Add class and methods for:
    + `MartTimestep`:
        * add timesteps,
        * add actions,
        * slice times,
        * remove actions
        * add forcings yearly (wrapper of add actions)
        * add pumping monthly (wrapper of add actions)
    + `MartParams`:
        * create from file/ from template
    + `MartHisto`:
        * create from file/ from template,
        * inherit pandas dataframe for easy interop,
        * export as shapefile,
        * from shapefile,
        * fill coordinates from grid
    + `MartProject`:
        * create from file/ from template,
        * getter/setter for project files
    * `MartModel`:
        * create object to control a model, inherit from projet file
        * add getter for outputs,
        * add setter for batch file,
        * add run method (requires and installation of marthe)
- Add tests for most of the features
- Add user config, resources to get all marthe variables, constants to store
  marthe constants, formatter, etc.
- Add helper function to retrieve help for marthe variable, actions
- Doc: 1st notebook

### Fixed

- fix rma writer : fix title editing, see ([#1](https://gitlab.com/brgm/hydrogeological-modelling/marthe-tools/martpy/-/work_items/1))
- fix rma parser : rewrite to take advandage of file order -> allow legacy reader
- Fix bad fmt/parser type in ACTION + add support for lake
- Numeric type was forced in zone/cell actions ; this is removed for cases with '*' and ':' (special char in Marthe)
- Fix writing opt_list_mail in pastp/mart; add drop dups in add times
- fix: #2 cell coordinate not filled with grids if xy is not a cell center ([#2](https://gitlab.com/brgm/hydrogeological-modelling/marthe-tools/martpy/-/work_items/2))
- Fix: histo bad writer lenght for coordinates + error reading scientific notation
- add parsing of empty value in mart file (should be set to default ?)
- Fix: add parsing parameter with special char, and multiphase par + misc
- add: parsing of special char in variable for parameters line
(e.g. T_1/2_), fix ([#12](https://gitlab.com/brgm/hydrogeological-modelling/marthe-tools/martpy/-/work_items/12))
- add: parsing of multiphase parameters ('FIX=...'), fix ([#13](https://gitlab.com/brgm/hydrogeological-modelling/marthe-tools/martpy/-/work_items/13))
- add: constructor to MartHisto, should fix ([#9](https://gitlab.com/brgm/hydrogeological-modelling/marthe-tools/martpy/-/work_items/9))
- Fix: timestep rewrite error ([#11](https://gitlab.com/brgm/hydrogeological-modelling/marthe-tools/martpy/-/work_items/11))
- Fix: modin file recursive parsing. See ([#16](https://gitlab.com/brgm/hydrogeological-modelling/marthe-tools/martpy/-/work_items/16))
- Fix: prn reader for zone budget + mart reader type value
- Fix: output reader now capture volume in riv_dra_lac, ([#18](https://gitlab.com/brgm/hydrogeological-modelling/marthe-tools/martpy/-/work_items/18))
- Fix: reader prn for historiq with less than 6 lines
