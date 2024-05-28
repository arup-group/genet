import json
import logging
import statistics
from typing import Union

import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
import polyline
import s2sphere as s2
from shapely.geometry import GeometryCollection, LineString, MultiLineString, Point, shape
from shapely.ops import linemerge, split
from sklearn.neighbors import BallTree

import genet
import genet.output.geojson as gngeojson
from genet.exceptions import EmptySpatialTree

APPROX_EARTH_RADIUS = 6371008.8
S2_LEVELS_FOR_SPATIAL_INDEXING = [0, 6, 8, 12, 18, 24, 30]


def decode_polyline_to_s2_points(_polyline: str) -> list[int]:
    """

    Args:
        _polyline (str): google encoded polyline.

    Returns:
        list[int]: S2 points describing the polyline.
    """
    decoded = polyline.decode(_polyline)
    return [generate_index_s2(lat, lon) for lat, lon in decoded]


def encode_shapely_linestring_to_polyline(linestring: LineString) -> str:
    """

    Args:
        linestring (LineString): Shapely LineString to encode.

    Returns:
        str: Google encoded polyline.
    """
    return polyline.encode(linestring.coords)


def swap_x_y_in_linestring(linestring: LineString) -> LineString:
    """Swaps x with y in a shapely linestring.

    e.g. from LineString([(1,2), (3,4)]) to LineString([(2,1), (4,3)]).

    Args:
        linestring (LineString): Input linestring.

    Returns:
        LineString: Input linestring with swapped x and y coordinates.
    """
    return LineString((p[1], p[0]) for p in linestring.coords)


def merge_linestrings(linestring_list: list[LineString]) -> Union[LineString, MultiLineString]:
    """

    Args:
        linestring_list (list[LineString]): ordered list of shapely.geometry.Linestring objects.

    Returns:
        Union[LineString, MultiLineString]:
            Assumes lines are contiguous. If they are not, will result in a MultiLineString.
    """
    multi_line = MultiLineString(linestring_list)
    return linemerge(multi_line)


def snap_point_to_line(point: Point, line: LineString, distance_threshold: float = 1e-8) -> Point:
    """Snap a point to a line, if over a distance threshold.

    Not using 'contains' method due to too high accuracy required to evaluate to True.

    Args:
        point (Point): Point to be potentially snapped to line.
        line (LineString): Line to use for the Point to snap to
        distance_threshold (float, optional): Acceptable distance of point from line before snapping. Defaults to 1e-8.

    Returns:
        Point: Point on line that is closest to input `point` or `point` itself, if it is within `distance_threshold`.
    """
    if line.distance(point) > distance_threshold:
        point = line.interpolate(line.project(point))
    return point


def continue_line_from_two_points(p1: Point, p2: Point) -> LineString:
    """Builds a line from p1, p2 and another point, ahead, the same distance and direction from p2 as p1.

    Args:
        p1 (Point): Start point of line.
        p2 (Point): End point of line.

    Returns:
        LineString: Line from p1 to p2.
    """
    return LineString([p1, p2, (p2.x + (p2.x - p1.x), p2.y + (p2.y - p1.y))])


def split_line_at_point(point: Point, line: LineString) -> tuple[LineString, LineString]:
    """Returns a two-tuple of linestring slices of given line, split at the given point.

    If the point is not close enough to the line, it will be snapped.

    The order in the returned tuple preserves the given line.

    Args:
        point (Point): point used for dividing the line
        line (LineString): line to divide

    Returns:
        tuple[LineString, LineString]:
            If given line from A - B, the output will be (A - point, point - B) - subject to point needing to snap closer to the line.
    """
    # the point has to be on the line for shapely split
    # https://shapely.readthedocs.io/en/stable/manual.html#splitting
    projected_point = snap_point_to_line(point, line, distance_threshold=0)
    result = tuple(split(line, projected_point).geoms)
    if len(result) == 1:
        # our lines can have curves which makes them impossible to split with a point, instead we build a line to cut
        # it, the end points of the linestring will likely not match with the point projected to the curved line, but
        # are very close.
        if point.distance(projected_point) < 1e-8:
            # the points are too close
            logging.warning(
                "Given point is very close, but not cannot be placed on the line. We move it slightly "
                "and the resulting split may not be exact."
            )
            point = Point(round(point.x, 2), round(point.y, 2))
        split_line = continue_line_from_two_points(point, projected_point)
        result = tuple(split(line, split_line).geoms)
    return result


def decode_polyline_to_shapely_linestring(_polyline: str) -> LineString:
    """

    Args:
        _polyline (str): google encoded polyline

    Returns:
        LineString: Shapely linestring representation of input polyline.
    """
    decoded = polyline.decode(_polyline)
    return LineString(decoded)


def compute_average_proximity_to_polyline(poly_1: str, poly_2: str) -> float:
    """Computes average distance between points in poly_1 and closest points in poly_2.

    Works best when poly_1 is less dense with points than poly_2.

    Args:
        poly_1 (str): google encoded polyline.
        poly_2 (str): google encoded polyline

    Returns:
        float: Average distance between points in poly_1 and their respective closest points in poly_2.
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
    hex_area = hex_area.split(",")
    cell_ids = []
    for token in hex_area:
        cell_ids.append(s2.CellId.from_token(token))
    return s2.CellUnion(cell_ids=cell_ids)


def generate_index_s2(lat: float, lng: float) -> int:
    """Returns s2.CellId from lat and lon

    Args:
        lat (float): Latitude.
        lng (float): Longitude.

    Returns:
        int: S2 cell ID.
    """
    return s2.CellId.from_lat_lng(s2.LatLng.from_degrees(lat, lng)).id()


def generate_s2_geometry(
    points: Union[LineString, list[tuple[float, float]], list[Point]]
) -> list[int]:
    """Generate ordered list of s2.CellIds

    Args:
        points (Union[LineString, list[tuple[float, float]], list[Point]]): Points to convert to S2 Cell IDs

    Returns:
        list[int]: List of S2 Cell IDs
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


def map_azimuth_to_name(azimuth: float) -> str:
    """

    Args:
        azimuth (float): degrees from North (0).

    Raises:
        NotImplementedError: assumes -180 =< azimuth =< 180.

    Returns:
        str: String defining compass direction, e.g. "North Bound".
    """
    azimuth_to_name = {
        (-22.5, 22.5): "North Bound",
        (22.5, 67.5): "North-East Bound",
        (67.5, 112.5): "East Bound",
        (112.5, 157.5): "South-East Bound",
        (-157.5, -112.5): "South-West Bound",
        (-112.5, -67.5): "West Bound",
        (-67.5, -22.5): "North-West Bound",
    }
    if azimuth > 180 or azimuth < -180:
        raise NotImplementedError(
            f"Azimuth value of {azimuth} given. Only implemented for -180 =< azimuth =< 180"
        )
    for (lower_bound, upper_bound), name in azimuth_to_name.items():
        if lower_bound < azimuth <= upper_bound:
            return name
    # (-157.5, -180 | 180, 157.5): 'South Bound'
    if azimuth > 157.5 or azimuth <= -157.5:
        return "South Bound"


def get_nearest(src_points, candidates, k_neighbors=1):
    # https://autogis-site.readthedocs.io/en/latest/notebooks/L3/06_nearest-neighbor-faster.html
    """Find nearest neighbors for all source points from a set of candidate points"""

    # Create tree from the candidate points
    tree = BallTree(candidates, leaf_size=15, metric="haversine")

    # Find closest points and distances
    distances, indices = tree.query(src_points, k=k_neighbors)

    # Transpose to get distances and indices into arrays
    distances = distances.transpose()
    indices = indices.transpose()

    # Get closest indices and distances (i.e. array at index 0)
    # note: for the second closest points, you would take index 1, etc.
    closest = indices[0]
    closest_dist = distances[0]

    # Return indices and distances
    return (closest, closest_dist)


def nearest_neighbor(left_gdf, right_gdf, return_dist=False):
    # https://autogis-site.readthedocs.io/en/latest/notebooks/L3/06_nearest-neighbor-faster.html
    """
    For each point in left_gdf, find closest point in right GeoDataFrame and return them.

    NOTICE: Assumes that the input Points are in WGS84 projection (lat/lon).
    """

    left_geom_col = left_gdf.geometry.name
    right_geom_col = right_gdf.geometry.name

    # Ensure that index in right gdf is formed of sequential numbers
    right = right_gdf.copy().reset_index(drop=True)

    # Parse coordinates from points and insert them into a numpy array as RADIANS
    # Notice: should be in Lat/Lon format
    left_radians = np.array(
        left_gdf[left_geom_col]
        .apply(lambda geom: (geom.y * np.pi / 180, geom.x * np.pi / 180))
        .to_list()
    )
    right_radians = np.array(
        right[right_geom_col]
        .apply(lambda geom: (geom.y * np.pi / 180, geom.x * np.pi / 180))
        .to_list()
    )

    # Find the nearest points
    # -----------------------
    # closest ==> index in right_gdf that corresponds to the closest point
    # dist ==> distance between the nearest neighbors (in meters)

    closest, dist = get_nearest(src_points=left_radians, candidates=right_radians)

    # Return points from right GeoDataFrame that are closest to points in left GeoDataFrame
    closest_points = right.loc[closest]

    # Ensure that the index corresponds the one in left_gdf
    closest_points = closest_points.set_index(left_gdf.index)

    # Add distance if requested
    if return_dist:
        # Convert to meters from radians
        closest_points["distance"] = dist * APPROX_EARTH_RADIUS

    return closest_points


def approximate_metres_distance_in_4326_degrees(distance, lat):
    # https://gis.stackexchange.com/questions/2951/algorithm-for-offsetting-a-latitude-longitude-by-some-amount-of-meters
    return (
        (float(distance) / 111111) + float(distance) / (111111 * np.cos(np.radians(float(lat))))
    ) / 2


class SpatialTree(nx.DiGraph):
    def __init__(self, n=None):
        super().__init__()
        self.links = gpd.GeoDataFrame(columns=["link_id", "modes", "geometry"])
        if n is not None:
            self.add_links(n)

    def add_links(self, n: "genet.core.Network"):
        """Generates a spatial tree from links in a network.

        Nodes of the spatial tree are generated to represent the links of the network.
        Edges of the spatial tree are generated between the network links which share `to` and `from` nodes;
        i.e. the two links are connected at a node.

        Args:
            n (genet.core.Network): GeNet network.
        """
        self.links = n.to_geodataframe()["links"].to_crs("epsg:4326")
        self.links = self.links.rename(columns={"id": "link_id"})
        self.links = self.links.set_index("link_id", drop=False)

        nodes = self.links.set_index("link_id").T.to_dict()
        self.add_nodes_from(nodes)

        cols = ["from", "to", "link_id"]
        edge_data_cols = list(
            set(self.links.columns) - set(cols + ["modes", "geometry", "u", "v", "key"])
        )
        edges = pd.merge(
            self.links[cols + edge_data_cols],
            self.links[cols],
            left_on="to",
            right_on="from",
            suffixes=("_to", "_from"),
        )
        edge_data = edges[edge_data_cols].T.to_dict()
        self.add_edges_from(
            list(
                zip(
                    edges["link_id_to"],
                    edges["link_id_from"],
                    [edge_data[idx] for idx in edges["link_id_to"].index],
                )
            )
        )

    def modal_links_geodataframe(self, modes: Union[str, set[str]]) -> gpd.GeoDataFrame:
        """Subsets the links geodataframe on modes

        Args:
            modes (Union[str, set[str]]): single or set of modes.

        Raises:
            EmptySpatialTree: At least one link must include one of the input modes.

        Returns:
            gpd.GeoDataFrame: links that include subset of modes.
        """
        if isinstance(modes, str):
            modes = {modes}
        _df = self.links[self.links.apply(lambda x: gngeojson.modal_subset(x, modes), axis=1)]
        if _df.empty:
            raise EmptySpatialTree(f"No links found satisfying modes: {modes}")
        return _df

    def modal_subtree(self, modes: Union[str, set[str]]) -> nx.Graph:
        """Create a networkx subgraph from subset of links which match the input modes.

        Args:
            modes (Union[str, set[str]]): single or set of modes.

        Returns:
            nx.Graph: Subgraph of Self.
        """

        sub_tree = self.__class__()
        links = gpd.GeoDataFrame(self.modal_links_geodataframe(modes))
        sub_tree = self.subgraph(links["link_id"])
        sub_tree.links = links
        return sub_tree

    def closest_links(
        self, gdf_points: gpd.GeoDataFrame, distance_radius: float
    ) -> gpd.GeoDataFrame:
        """Finds closest links from a list of points within a given radius.

        Given a GeoDataFrame `gdf_points` with a `geometry` column of shapely.geometry.Points,
        finds closest links within `distance_radius` from the spatial tree which accept `mode`.

        Does not work very close to the poles.

        Args:
            gdf_points (gpd.GeoDataFrame): Uniquely indexed, in crs: EPSG:4326 and only containing shapely.geometry.Points (lon,lat).
            distance_radius (float): Metres in which to consider possible links.

        Returns:
            gpd.GeoDataFrame: Closest links to points.
        """
        bdds = gdf_points["geometry"].bounds
        approx_lat = (bdds["miny"].mean() + bdds["maxy"].mean()) / 2
        approx_degree_radius = approximate_metres_distance_in_4326_degrees(
            distance_radius, approx_lat
        )
        gdf_points["geometry"] = gdf_points["geometry"].apply(
            lambda x: grow_point(x, approx_degree_radius)
        )
        try:
            closest_links = gpd.sjoin(
                self.links[["link_id", "geometry"]], gdf_points, how="right", predicate="intersects"
            )
            return closest_links
        except EmptySpatialTree:
            return gpd.GeoDataFrame(
                columns=set(gdf_points.columns) | {"index_left", "link_id", "geometry"},
                crs="epsg:4326",
            )

    def path(self, G, source, target, weight=None):
        try:
            return nx.shortest_path(G, source, target, weight=weight)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            pass

    def shortest_paths(
        self,
        df_pt_edges: pd.DataFrame,
        from_col: str = "u",
        to_col: str = "v",
        weight: str = "length",
    ) -> pd.DataFrame:
        """

        Args:
            df_pt_edges (pd.DataFrame):
                DataFrame with a `from_col` and `to_col` defining links stored in the graph for which a path is required
            from_col (str, optional): Name of the column which gives ID for the source link. Defaults to "u".
            to_col (str, optional): Name of the column which gives ID for the target link. Defaults to "v".
            weight (str, optional): Weight for routing. Defaults to "length".

        Returns:
            pd.DataFrame: `df_pt_edges` with an extra column 'shortest_path'
        """
        if df_pt_edges.empty:
            df_pt_edges["shortest_path"] = None
        else:
            try:
                df_pt_edges["shortest_path"] = df_pt_edges.apply(
                    lambda x: self.path(
                        G=self, source=x[from_col], target=x[to_col], weight=weight
                    ),
                    axis=1,
                )
            except EmptySpatialTree:
                logging.warning("Shortest path could not be found due to an empty SpatialTree")
                df_pt_edges["shortest_path"] = None
        return df_pt_edges

    def path_length(self, G, source, target, weight=None):
        try:
            return nx.dijkstra_path_length(G, source=source, target=target, weight=weight)
        except nx.NetworkXNoPath:
            pass

    def shortest_path_lengths(
        self,
        df_pt_edges: pd.DataFrame,
        from_col: str = "u",
        to_col: str = "v",
        weight: str = "length",
    ) -> pd.DataFrame:
        """

        Args:
            df_pt_edges (pd.DataFrame):
                DataFrame with a `from_col` and `to_col` defining links stored in the graph for which a path length is required.
            from_col (str, optional): Name of the column which gives ID for the source link. Defaults to "u".
            to_col (str, optional): Name of the column which gives ID for the target link. Defaults to "v".
            weight (str, optional): Weight for routing. Defaults to "length".

        Returns:
            pd.DataFrame: `df_pt_edges` with an extra column 'shortest_path'
        """
        if df_pt_edges.empty:
            df_pt_edges["path_lengths"] = None
        else:
            try:
                df_pt_edges["path_lengths"] = df_pt_edges.apply(
                    lambda x: self.path_length(
                        G=self, source=x[from_col], target=x[to_col], weight=weight
                    ),
                    axis=1,
                )
            except EmptySpatialTree:
                df_pt_edges["path_lengths"] = None
        return df_pt_edges
