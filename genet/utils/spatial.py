import polyline
import s2sphere as s2
import networkx as nx
import numpy as np
import statistics
import json
from shapely.geometry import LineString, shape, GeometryCollection
import pandas as pd
import geopandas as gpd
from typing import Union
import genet.outputs_handler.geojson as gngeojson

APPROX_EARTH_RADIUS = 6371008.8
S2_LEVELS_FOR_SPATIAL_INDEXING = [0, 6, 8, 12, 18, 24, 30]


def decode_polyline_to_s2_points(_polyline):
    """
    :param _polyline: google encoded polyline
    :return:
    """
    decoded = polyline.decode(_polyline)
    return [generate_index_s2(lat, lon) for lat, lon in decoded]


def encode_shapely_linestring_to_polyline(linestring):
    """
    :param linestring: shapely.geometry.LineString
    :return: google encoded polyline
    """
    return polyline.encode(linestring.coords)


def swap_x_y_in_linestring(linestring):
    """
    swaps x with y in a shapely linestring,e.g. from LineString([(1,2), (3,4)]) to LineString([(2,1), (4,3)])
    :param linestring: shapely.geometry.LineString
    :return: shapely.geometry.LineString
    """
    return LineString((p[1], p[0]) for p in linestring.coords)


def decode_polyline_to_shapely_linestring(_polyline):
    """
    :param _polyline: google encoded polyline
    :return: shapely.geometry.LineString
    """
    decoded = polyline.decode(_polyline)
    return LineString(decoded)


def compute_average_proximity_to_polyline(poly_1, poly_2):
    """
    Computes average distance between points in poly_1 and closest points in poly_2. Works best when poly_1 is less
    dense with points than poly_2.
    :param poly_1: google encoded polyline
    :param poly_2: google encoded polyline
    :return:
    """
    s2_poly_list_1 = decode_polyline_to_s2_points(poly_1)
    s2_poly_list_2 = decode_polyline_to_s2_points(poly_2)

    closest_distances = []
    for point in s2_poly_list_1:
        d = None
        for other_line_point in s2_poly_list_2:
            dist = distance_between_s2cellids(point, other_line_point)
            if (d is None) or (d > dist):
                d = dist
        closest_distances.append(d)
    return statistics.mean(closest_distances)


def read_geojson_to_shapely(geojson_file):
    # https://gist.github.com/pramukta/6d1a2de485d7dc4c5480bf5fbb7b93d2#file-shapely_geojson_recipe-py
    with open(geojson_file) as f:
        features = json.load(f)["features"]
    return GeometryCollection([shape(feature["geometry"]).buffer(0) for feature in features])


def s2_hex_to_cell_union(hex_area):
    hex_area = hex_area.split(',')
    cell_ids = []
    for token in hex_area:
        cell_ids.append(s2.CellId.from_token(token))
    return s2.CellUnion(cell_ids=cell_ids)


def generate_index_s2(lat, lng):
    """
    Returns s2.CellId from lat and lon
    :param lat
    :param lng
    :return:
    """
    return s2.CellId.from_lat_lng(s2.LatLng.from_degrees(lat, lng)).id()


def generate_s2_geometry(points):
    """
    Generate ordered list of s2.CellIds
    :param points: list of (lat,lng) tuples, list of shapely.geometry.Points or LineString
    :return:
    """
    if isinstance(points, LineString):
        points = list(points.coords)
    try:
        return [generate_index_s2(pt.x, pt.y) for pt in points]
    except AttributeError:
        return [generate_index_s2(pt[0], pt[1]) for pt in points]


def distance_between_s2cellids(s2cellid1, s2cellid2):
    if isinstance(s2cellid1, int):
        s2cellid1 = s2.CellId(s2cellid1)
    elif isinstance(s2cellid1, np.int64):
        s2cellid1 = s2.CellId(int(s2cellid1))
    if isinstance(s2cellid2, int):
        s2cellid2 = s2.CellId(s2cellid2)
    elif isinstance(s2cellid2, np.int64):
        s2cellid2 = s2.CellId(int(s2cellid2))
    distance = s2cellid1.to_lat_lng().get_distance(s2cellid2.to_lat_lng()).radians
    return distance * APPROX_EARTH_RADIUS


def change_proj(x, y, crs_transformer):
    return crs_transformer.transform(x, y)


def find_common_cell(edge):
    u, v, w = edge
    _u = s2.CellId(u)
    _v = s2.CellId(v)
    while _u != _v and not _u.is_face():
        _u = _u.parent()
        _v = _v.parent()
    if _u.is_face():
        # if u is a face then v will be a face too, only need to check u
        return 0
    return _u


def find_edges_from_common_cell_to_root(s2_link, link_id):
    common_cell = find_common_cell(s2_link)
    edges_to_add = []
    if common_cell != 0:
        lvl = common_cell.level()
        _lvls = [s2_lvl for s2_lvl in S2_LEVELS_FOR_SPATIAL_INDEXING if lvl >= s2_lvl]
        common_cell = common_cell.parent(_lvls[-1])
        edges_to_add.append((common_cell.id(), link_id))
        if _lvls:
            for i in range(len(_lvls) - 1):
                edges_to_add.append((common_cell.parent(_lvls[i]).id(), common_cell.parent(_lvls[i + 1]).id()))
        # add the connection to the super cell
        edges_to_add.append((0, common_cell.parent(_lvls[0]).id()))
    else:
        edges_to_add.append((0, link_id))
    return edges_to_add


def grow_point(x, distance):
    return x.buffer(distance)


def approximate_metres_distance_in_4326_degrees(distance, lat):
    return ((float(distance) / 111111) + float(distance) / (111111 * np.cos(np.radians(float(lat))))) / 2


class SpatialTree(nx.DiGraph):
    def __init__(self, n=None):
        super().__init__()
        self.links = pd.DataFrame()
        if n is not None:
            self.add_links(n)

    def add_links(self, n):
        """
        Generates the spatial tree where all links in `n` are nodes and edges exists between nodes if the two links
        share to and from (`n`) nodes; i.e. the two links are connected at a node
        :param n: genet.Network object
        :return:
        """
        self.links = gngeojson.generate_geodataframes(n.graph)[1]

        nodes = self.links.set_index('id').T.to_dict()
        self.add_nodes_from(nodes)

        cols = ['from', 'to', 'id']
        edges = pd.merge(self.links[cols], self.links[cols], left_on='to', right_on='from', suffixes=('_to', '_from'))
        self.add_edges_from(list(zip(edges['id_to'], edges['id_from'])))

    def modal_links_geodataframe(self, modes: Union(str, set)):
        if isinstance(modes, str):
            modes = {modes}
        return self.links[self.links.apply(lambda x: gngeojson.modal_subset(x, modes), axis=1)]

    def closest_links(self, gdf_points, distance_radius, modes):
        """
        Given a GeoDataFrame `gdf_points` with a`geometry` column with shapely.geometry.Points,
        finds closest links within `distance_radius` from the spatial tree which accept `mode`.
        Does not work very close to the poles.
        :param gdf_points: GeoDataFrame, uniquely indexed, in crs: EPSG:4326 shapely.geometry.Points (lon,lat)
        :param distance_radius: metres
        :param modes: str of set of strings to consider modal subgraph
        :return: GeoDataFrame
        """
        bdds = gdf_points['geometry'].bounds
        approx_lat = (bdds['miny'].mean() + bdds['maxy'].mean()) / 2
        # https://gis.stackexchange.com/questions/2951/algorithm-for-offsetting-a-latitude-longitude-by-some-amount-of-meters
        approx_degree_radius = approximate_metres_distance_in_4326_degrees(distance_radius, approx_lat)
        gdf_points['geometry'] = gdf_points['geometry'].apply(lambda x: grow_point(x, approx_degree_radius))
        closest_links = gpd.sjoin(
            self.modal_links_geodataframe(modes),
            gdf_points,
            how='right',
            op='intersects')
        return closest_links['id']

    def shortest_paths(self, df_pt_edges, modes, u_col='u', v_col='v'):
        """

        :param df_pt_edges: pandas DataFrame
        :param modes: str of set of strings to consider modal subgraph
        :return:
        """
        # todo add weight
        links = self.modal_links_geodataframe(modes)['id']
        df_pt_edges['shortest_path'] = df_pt_edges.apply(
            lambda x: nx.shortest_path(G=self.subgraph(links), source=x[u_col], target=x[v_col]), axis=1)
        return df_pt_edges

    def path_length(self, G, source, target):
        try:
            return nx.dijkstra_path_length(G, source, target)
        except nx.NetworkXNoPath:
            pass

    def shortest_path_lengths(self, df_pt_edges, modes, u_col='u', v_col='v'):
        """

        :param df_pt_edges: pandas DataFrame
        :param modes: str of set of strings to consider modal subgraph
        :return:
        """
        # todo add weight
        links = self.modal_links_geodataframe(modes)['id']
        df_pt_edges['path_lengths'] = df_pt_edges.apply(
            lambda x: self.path_length(G=self.subgraph(links), source=x[u_col], target=x[v_col]), axis=1)
        return df_pt_edges
