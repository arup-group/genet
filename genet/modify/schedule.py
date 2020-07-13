import genet.utils.spatial as spatial
from pyproj import Transformer


def reproj(routes_list, from_proj, to_proj):
    transformer = Transformer.from_crs(from_proj, to_proj)
    for route in routes_list:
        for stop in route.stops:
            stop.reproject(to_proj, transformer)
    return routes_list