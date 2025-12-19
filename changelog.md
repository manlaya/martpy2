<!-- martpy changelog -->

Version 0.1
-----------

Released on XXXX-XX-XX.

- first release as a (beta) stand alone package.
- Add support for reading/writing input files:
    + `*.rma` (Marthe project),
    + `*.mart` (Marthe general parameters),
    + `*.pastp` (Marthe timesteps),
    + `*.histo` (Marthe timeseries config),
- Add support for reading output files:
    + `histobil_*.prn` (Marthe output balance file),
    + `historiq.prn` (Marthe output time series),
- Add wrapper for grid management (based on `gridmarthe` library)
- Add methods to run marthe from python
