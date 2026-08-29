#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse

from martpy.outputs.bilandeb import extract_layer_transfers


def main():
    parser = argparse.ArgumentParser(
        description='Extract layer transfers from MARTHE "bilandeb.txt" file'
                    'to a netCDF file'
    )

    parser.add_argument(
        'marthe_file', type=str,
        help='MARTHE "bilandeb.txt" file to parse'
    )

    parser.add_argument(
        'netcdf_file', type=str,
        help='netCDF file to generate'
    )

    args = parser.parse_args()

    extract_layer_transfers(args.marthe_file, args.netcdf_file)


if __name__ == '__main__':
    main()
