import pytest
import genet.utils.elevation as elevation
import xarray as xr
import os
from tests.fixtures import assert_semantically_equal

elevation_test_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_data", "elevation"))
tif_path = os.path.join(elevation_test_folder, 'hk_elevation_example.tif')
array_path = os.path.join(elevation_test_folder, 'elevation_image.nc')


def test_output_type_get_elevation_image():
    img = elevation.get_elevation_image(tif_path)
    assert isinstance(img, xr.DataArray)


def test_get_elevation_image():
    output = elevation.get_elevation_image(tif_path)
    image = xr.open_dataset(array_path)
    assert output == image


def test_get_elevation_data():
    # need to figure out how to load save and load in an xarray.DataArray - only managed xarray.Dataset
    image = elevation.get_elevation_image(tif_path)
    output = elevation.get_elevation_data(image, 22.268764, 114.159062)
    assert output == 446


@pytest.fixture()
def elevation_dictionary():
    # based on network4() fixture
    elevation_dictionary = {'101982': {'z': -51}, '101990': {'z': 100}}
    return elevation_dictionary


def test_validation_report_for_node_elevation_dictionary(elevation_dictionary):
    report = elevation.validation_report_for_node_elevation(elevation_dictionary)
    correct_report = {'summary': {'extremely_high_values_count': 0, 'extremely_low_values_count': 1, 'max_value': 100,
                                  'mean': 24, 'median': 24, 'min_value': -51, 'total_nodes': 2},
                      'values': {'extremely_high_values_dict': {}, 'extremely_low_values_dict': {'101982': -51}}}

    assert_semantically_equal(report, correct_report)
