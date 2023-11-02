import os

import pytest
import xarray as xr

import genet.utils.elevation as elevation

elevation_test_folder = pytest.test_data_dir / "elevation"
tif_path = elevation_test_folder / "hk_elevation_example.tif"
tif_path_crs_not_4326 = elevation_test_folder / "hk_elevation_example_crs_2326.tif"
array_path = elevation_test_folder / "elevation_image.nc"


def test_output_type_get_elevation_image():
    img = elevation.get_elevation_image(tif_path)
    assert isinstance(img, xr.DataArray)


def test_get_elevation_image():
    output = elevation.get_elevation_image(tif_path)
    image = xr.open_dataset(array_path)
    assert output == image


def test_get_elevation_image_with_crs_not_4326():
    output = elevation.get_elevation_image(tif_path_crs_not_4326)
    image = xr.open_dataset(array_path)
    assert output == image


def test_get_elevation_data():
    # need to figure out how to load save and load in an xarray.DataArray - only managed xarray.Dataset
    image = elevation.get_elevation_image(tif_path)
    output = elevation.get_elevation_data(image, 22.268764, 114.159062)
    assert output == 446


def test_validation_report_for_node_elevation_dictionary(assert_semantically_equal):
    # based on network4() fixture
    elevation_dictionary = {"101982": {"z": -51}, "101990": {"z": 100}}
    report = elevation.validation_report_for_node_elevation(elevation_dictionary)
    correct_report = {
        "summary": {
            "extremely_high_values_count": 0,
            "extremely_low_values_count": 1,
            "max_value": 100,
            "mean": 24,
            "median": 24,
            "min_value": -51,
            "total_nodes": 2,
        },
        "values": {"extremely_high_values_dict": {}, "extremely_low_values_dict": {"101982": -51}},
    }

    assert_semantically_equal(report, correct_report)


def test_writing_slope_saves_data_to_xml(assert_xml_semantically_equal, tmpdir):
    slope_xml_file = pytest.test_data_dir / "elevation" / "link_slopes.xml"
    slope_dictionary = {"0": {"slope": 2.861737280890912}, "1": {"slope": -0.1}}
    elevation.write_slope_xml(slope_dictionary, tmpdir)

    generated_elevation_file_path = os.path.join(tmpdir, "link_slopes.xml")
    assert_xml_semantically_equal(generated_elevation_file_path, slope_xml_file)
