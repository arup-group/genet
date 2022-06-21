import rioxarray


def get_elevation_image(elevation_tif):
    xarr_file = rioxarray.open_rasterio(elevation_tif)

    return xarr_file[0, :, :]


def get_elevation_data(img, lat, lon):
    output = img.sel(x=lon, y=lat, method="nearest")
    mt = output.values
    elevation_meters = mt.item()

    return elevation_meters
