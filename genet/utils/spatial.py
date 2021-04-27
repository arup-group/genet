import polyline
import s2sphere as s2
import networkx as nx
import numpy as np
import statistics
import json
from shapely.geometry import LineString, shape, GeometryCollection
import pandas as pd
import geopandas as gpd
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


def grow_point(x, distance):
    return x.buffer(distance)


def map_azimuth_to_name(azimuth):
    """
    assumes -180 =< azimuth =< 180
    degrees from North (0)
    """
    azimuth_to_name = {
        (-22.5, 22.5): 'North Bound',
        (22.5, 67.5): 'North-East Bound',
        (67.5, 112.5): 'East Bound',
        (112.5, 157.5): 'South-East Bound',
        (-157.5, -112.5): 'South-West Bound',
        (-112.5, -67.5): 'West Bound',
        (-67.5, -22.5): 'North-West Bound',
    }
    if azimuth > 180 or azimuth < -180:
        raise NotImplementedError(f'Azimuth value of {azimuth} given. Only implemented for -180 =< azimuth =< 180')
    for (lower_bound, upper_bound), name in azimuth_to_name.items():
        if lower_bound < azimuth <= upper_bound:
            return name
    # (-157.5, -180 | 180, 157.5): 'South Bound'
    if azimuth > 157.5 or azimuth <= -157.5:
        return 'South Bound'


def approximate_metres_distance_in_4326_degrees(distance, lat):
    # https://gis.stackexchange.com/questions/2951/algorithm-for-offsetting-a-latitude-longitude-by-some-amount-of-meters
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
        self.links = n.to_geodataframe()['links'].to_crs('epsg:4326')
        self.links = self.links.rename(columns={'id': 'link_id'})

        nodes = self.links.set_index('link_id').T.to_dict()
        self.add_nodes_from(nodes)

        cols = ['from', 'to', 'link_id']
        edge_data_cols = list(set(self.links.columns) - set(cols + ['modes', 'geometry', 'u', 'v', 'key']))
        edges = pd.merge(self.links[cols + edge_data_cols], self.links[cols], left_on='to', right_on='from',
                         suffixes=('_to', '_from'))
        edge_data = edges[edge_data_cols].T.to_dict()
        self.add_edges_from(list(zip(edges['link_id_to'],
                                     edges['link_id_from'],
                                     [edge_data[idx] for idx in edges['link_id_to'].index])))

    def modal_links_geodataframe(self, modes):
        """
        Subsets the links geodataframe on modes
        :param modes: str or set of str
        :return:
        """
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
        approx_degree_radius = approximate_metres_distance_in_4326_degrees(distance_radius, approx_lat)
        gdf_points['geometry'] = gdf_points['geometry'].apply(lambda x: grow_point(x, approx_degree_radius))
        closest_links = gpd.sjoin(
            self.modal_links_geodataframe(modes)[['link_id', 'geometry']],
            gdf_points,
            how='right',
            op='intersects'
        )
        return closest_links

    def path(self, G, source, target, weight=None):
        try:
            return nx.shortest_path(G, source, target, weight=weight)
        except nx.NetworkXNoPath:
            pass

    def shortest_paths(self, df_pt_edges, modes, from_col='u', to_col='v', weight='length'):
        """
        :param df_pt_edges: pandas DataFrame with a `from_col` and `to_col` defining links stored in the graph for
        which a path is required
        :param modes: str of set of strings to consider modal subgraph for routing
        :param from_col: name of the column which gives ID for the source link
        :param to_col: name of the column which gives ID for the target link
        :param weight: weight for routing, defaults ot length
        :return: df_pt_edges with an extra column 'shortest_path'
        """
        links = self.modal_links_geodataframe(modes)['link_id']
        df_pt_edges['shortest_path'] = df_pt_edges.apply(
            lambda x: self.path(G=self.subgraph(links), source=x[from_col], target=x[to_col], weight=weight),
            axis=1)
        return df_pt_edges

    def path_length(self, G, source, target, weight=None):
        try:
            return nx.dijkstra_path_length(G, source, target, weight=weight)
        except nx.NetworkXNoPath:
            pass

    def shortest_path_lengths(self, df_pt_edges, modes, from_col='u', to_col='v', weight='length'):
        """
        :param df_pt_edges: pandas DataFrame with a `from_col` and `to_col` defining links stored in the graph for
        which a path length is required
        :param modes: str of set of strings to consider modal subgraph for routing
        :param from_col: name of the column which gives ID for the source link
        :param to_col: name of the column which gives ID for the target link
        :param weight: weight for routing, defaults ot length
        :return: df_pt_edges with an extra column 'shortest_path'
        """
        links = self.modal_links_geodataframe(modes)['link_id']
        df_pt_edges['path_lengths'] = df_pt_edges.apply(
            lambda x: self.path_length(G=self.subgraph(links), source=x[from_col], target=x[to_col], weight=weight),
            axis=1)
        return df_pt_edges
