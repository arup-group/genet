import s2sphere as s2


def grab_index_s2(lat, lng):
    """
    Returns s2.CellID from lat and lon
    :param lat
    :param lng
    :return:
    """
    return s2.CellId.from_lat_lng(s2.LatLng.from_degrees(lat, lng)).id()


def change_proj(x, y, crs_transformer):
    return crs_transformer.transform(x, y)
