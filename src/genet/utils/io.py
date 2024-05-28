import os
from typing import Optional

import geopandas as gpd
from pandas.core.dtypes.common import is_datetime64_any_dtype as is_datetime

from genet.output import sanitiser as sanitiser
from genet.utils import persistence as persistence

SUPPORTED_FILE_FORMATS = ["parquet", "geoparquet", "geojson", "shp", "shapefile"]


def check_file_type_is_supported(filetype: str):
    """Checks there is support for the given file type

    Args:
        filetype (str, optional): The file type to save a spatial object to.

    Raises:
        RuntimeError: `filetype` is not a supported file type
    """
    if filetype.lower() not in SUPPORTED_FILE_FORMATS:
        raise RuntimeError(
            f"{filetype} is not a supported file type: {', '.join(SUPPORTED_FILE_FORMATS)}"
        )


def save_geodataframe(
    gdf: gpd.GeoDataFrame, filename: str, output_dir: str, filetype: Optional[str] = "parquet"
):
    """Saves geopandas.GeoDataFrame to the requested file format

    Args:
        gdf (gpd.GeoDataFrame): GeoDataFrame to save to disk.
        filename (str): Name of the file, without extension.
        output_dir (str): Path to folder where to save the file.
        filetype (str, optional):
            The file type to save the GeoDataFrame to: geojson, geoparquet or shp are supported.
            Defaults to parquet format.
    """
    if not gdf.empty:
        check_file_type_is_supported(filetype)

        _gdf = sanitiser.sanitise_geodataframe(gdf.copy())
        persistence.ensure_dir(output_dir)

        if filetype.lower() in ["parquet", "geoparquet"]:
            _gdf.to_parquet(os.path.join(output_dir, f"{filename}.parquet"))
        elif filetype.lower() == "geojson":
            _gdf.to_file(
                os.path.join(output_dir, f"{filename}.geojson"), driver="GeoJSON", engine="pyogrio"
            )
        elif filetype.lower() in ["shp", "shapefile"]:
            for col in [col for col in _gdf.columns if is_datetime(_gdf[col])]:
                _gdf[col] = _gdf[col].astype(str)
            _gdf.to_file(os.path.join(output_dir, f"{filename}.shp"))
