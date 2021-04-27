import sys
from numpy import number
from geopandas import GeoDataFrame, GeoSeries


def sanitise_list(x):
    try:
        return ','.join(x)
    except TypeError:
        return ','.join(map(str, x))


def sanitise_geodataframe(gdf):
    if isinstance(gdf, GeoSeries):
        gdf = GeoDataFrame(gdf)
    gdf = gdf.fillna('None')
    object_columns = gdf.select_dtypes(['object']).columns
    for col in object_columns:
        if gdf[col].apply(lambda x: isinstance(x, (set, list))).any():
            gdf[col] = gdf[col].apply(lambda x: ','.join(x))
        elif gdf[col].apply(lambda x: isinstance(x, dict)).any():
            gdf[col] = gdf[col].apply(lambda x: str(x))
    for col in gdf.select_dtypes(include=number).columns.tolist():
        if (gdf[col] > sys.maxsize).any():
            gdf[col] = gdf[col].apply(lambda x: str(x))
    return gdf


def sanitise_dictionary_for_xml(d):
    for k, v in d.items():
        if isinstance(v, (set, list)):
            d[k] = sanitise_list(v)
        if isinstance(v, (int, float)):
            d[k] = str(v)
        if isinstance(v, dict):
            sanitise_dictionary_for_xml(v)
    return d


def sanitise_dictionary(d):
    for k, v in d.items():
        if isinstance(v, (set, list)):
            d[k] = sanitise_list(v)
        if isinstance(v, dict):
            sanitise_dictionary(v)
    return d
