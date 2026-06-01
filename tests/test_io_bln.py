# -*- coding: utf-8 -*-
"""Test module for bln_io.py"""

import os
import tempfile
import pytest

try:
    import geopandas as gpd
    from shapely.geometry import LineString, Polygon
    from martpy.utils.bln_io import read_bln, write_bln
except (ImportError, ModuleNotFoundError):
    pytest.skip("geopandas not installed, skipping tests", allow_module_level=True)


def test_read_bln():
    """Test reading a .bln file."""
    bln_file = "tests/data/bln/Fracture_Verticale.bln"
    gdf = read_bln(bln_file)

    # Check if the GeoDataFrame is not empty
    assert not gdf.empty, "GeoDataFrame should not be empty"

    # Check if the required columns exist
    assert 'geometry' in gdf.columns, "'geometry' column should exist"
    assert 'filter_flag' in gdf.columns, "'filter_flag' column should exist"
    assert 'label' in gdf.columns, "'label' column should exist"

    # Check the number of features
    assert len(gdf) == 2, "Expected 2 features in the GeoDataFrame"

    # Check the geometry types
    assert isinstance(gdf.iloc[0].geometry, LineString), "feature should be a Linestring"
    assert isinstance(gdf.iloc[1].geometry, LineString), "feature should be a Linestring"

    # Check the filter_flag values
    assert gdf.iloc[0]['filter_flag'] == 0, "First feature's filter_flag should be 0"
    assert gdf.iloc[1]['filter_flag'] == 0, "Second feature's filter_flag should be 0"

    # Check the label values
    assert gdf.iloc[0]['label'] == 'Longue_Fract', "First feature's label should be 'Longue_Fract'"
    assert gdf.iloc[1]['label'] == 'Fract_Oblique', "Second feature's label should be 'Fract_Oblique'"


def test_read_bln_polyg():
    bln_file = 'tests/data/bln/Secteur_CALL2.bln'
    gdf = read_bln(bln_file)
    assert isinstance(gdf, gpd.GeoDataFrame), "Output should be a GeoDataFrame"
    assert len(gdf) == 2, "There should be 2 features in the GeoDataFrame"
    assert gdf.geometry.iloc[0].geom_type == 'Polygon', "First feature should be a Polygon"


def test_write_bln():
    """Test writing a .bln file."""
    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(mode='w', suffix='.bln', delete=False) as tmp_file:
        tmp_bln_path = tmp_file.name

    try:
        # Create a sample GeoDataFrame
        features = [
            {'geometry': Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]), 'filter_flag': 0, 'label': 'Test_Polygon'},
            {'geometry': LineString([(0, 0), (1, 1)]), 'filter_flag': 1, 'label': 'Test_Line'},
        ]
        gdf = gpd.GeoDataFrame(features, crs='EPSG:2154')

        # Write the GeoDataFrame to a .bln file
        write_bln(gdf, tmp_bln_path)

        # Read the written file back
        gdf_read = read_bln(tmp_bln_path, epsg=2154)

        # Check if the read GeoDataFrame matches the original
        assert len(gdf_read) == len(gdf), "Number of features should match"
        assert gdf_read.iloc[0]['label'] == 'Test_Polygon', "First feature's label should match"
        assert gdf_read.iloc[1]['label'] == 'Test_Line', "Second feature's label should match"

    finally:
        # Clean up the temporary file
        if os.path.exists(tmp_bln_path):
            os.remove(tmp_bln_path)


def test_read_bln_with_unit():
    """Test reading a .bln file with a unit conversion factor."""
    bln_file = "tests/data/bln/Fracture_Verticale.bln"
    gdf = read_bln(bln_file, epsg=2154, unit=1000)

    # Check if the coordinates are scaled by the unit factor
    first_feature_coords = list(gdf.iloc[0].geometry.coords)
    assert first_feature_coords[0][0] == 111916.937, "X coordinate should be scaled by 1000"
    assert first_feature_coords[0][1] == 511236.544, "Y coordinate should be scaled by 1000"
