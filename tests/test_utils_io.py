import os

import genet.utils.io
import pytest
from geopandas import GeoDataFrame
from shapely import Point


def test_throws_error_when_filetype_is_not_supported():
    with pytest.raises(RuntimeError) as e:
        genet.utils.io.check_file_type_is_supported("hello")

    assert "is not a supported file type" in str(e.value)


def test_saving_geodataframe_with_missing_geometry_produces_file(tmpdir):
    expected_file_name = "tmp"
    expected_output_path = tmpdir / expected_file_name + ".parquet"
    assert not os.path.exists(expected_output_path)

    data = {"id": ["1", "2"], "geometry": [float("nan"), Point(2, 1)]}
    gdf = GeoDataFrame(data, crs="EPSG:4326")
    genet.utils.io.save_geodataframe(gdf, filename=expected_file_name, output_dir=tmpdir)

    assert os.path.exists(expected_output_path)


def test_saving_geodataframe_with_missing_data_in_string_column_produces_file(tmpdir):
    expected_file_name = "tmp"
    expected_output_path = tmpdir / expected_file_name + ".parquet"
    assert not os.path.exists(expected_output_path)

    data = {"id": ["1", float("nan")], "geometry": [Point(2, 1), Point(2, 1)]}
    gdf = GeoDataFrame(data, crs="EPSG:4326")
    genet.utils.io.save_geodataframe(gdf, filename=expected_file_name, output_dir=tmpdir)

    assert os.path.exists(expected_output_path)
