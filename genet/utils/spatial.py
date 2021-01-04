import polyline
import s2sphere as s2
import networkx as nx
import numpy as np
import statistics
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
    return [grab_index_s2(lat, lon) for lat, lon in decoded]


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


def grab_index_s2(lat, lng):
    """
    Returns s2.CellID from lat and lon
    :param lat
    :param lng
    :return:
    """
    return s2.CellId.from_lat_lng(s2.LatLng.from_degrees(lat, lng)).id()


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

    def closest_links(self, gdf_points, distance_radius, mode):
        """
        Given a GeoDataFrame `gdf_points` with a`geometry` column with Points, finds closest links within
        `distance_radius` from the spatial tree which accept `mode`
        :param gdf_points:
        :param distance_radius:
        :param mode:
        :return: GeoDataFrame
        """
        # todo make work with metres
        gdf_points['geometry'] = gdf_points['geometry'].apply(lambda x: grow_point(x, distance_radius))
        closest_links = gpd.sjoin(
            self.links[self.links.apply(lambda x: gngeojson.modal_subset(x, {mode}), axis=1)],
            gdf_points,
            how='right',
            op='intersects')
        return closest_links[['stop', 'id']]

    def shortest_paths(self, df_pt_edges, mode, u_col='u', v_col='v'):
        """

        :param df_pt_edges: pandas DataFrame
        :param mode:
        :return:
        """
        # todo add weight
        links = self.links[self.links.apply(lambda x: gngeojson.modal_subset(x, {mode}), axis=1)]['id']
        df_pt_edges['shortest_path'] = df_pt_edges.apply(
            lambda x: nx.shortest_path(G=self.subgraph(links), source=x[u_col], target=x[v_col]), axis=1)
        return df_pt_edges


    def path_length(self, G, source, target):
        try:
            return nx.dijkstra_path_length(G, source, target)
        except nx.NetworkXNoPath:
            pass


    def shortest_path_lengths(self, df_pt_edges, mode, u_col='u', v_col='v'):
        """

        :param df_pt_edges: pandas DataFrame
        :param mode:
        :return:
        """
        # todo add weight
        links = self.links[self.links.apply(lambda x: gngeojson.modal_subset(x, {mode}), axis=1)]['id']
        df_pt_edges['path_lengths'] = df_pt_edges.apply(
            lambda x: self.path_length(G=self.subgraph(links), source=x[u_col], target=x[v_col]), axis=1)
        return df_pt_edges
