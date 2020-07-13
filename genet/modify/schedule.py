from pyproj import Transformer


def reproj(routes_dict, from_proj, to_proj):
    transformer = Transformer.from_crs(from_proj, to_proj)
    for _id, route in routes_dict.items():
        for stop in route.stops:
            stop.reproject(to_proj, transformer)
    return routes_dict
