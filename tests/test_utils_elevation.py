import pytest
import genet.utils.elevation as elevation
import xarray as xr
import os


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
