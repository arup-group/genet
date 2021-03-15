import s2sphere
import pytest
from geopandas import GeoDataFrame
from pandas import DataFrame
from numpy import int64
from pyproj import Geod
from genet.utils import spatial
from genet import Network
from tests.fixtures import *
from shapely.geometry import LineString, Polygon, Point

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
test_geojson = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "test_geojson.geojson"))


def test_azimuth_to_name_with_east():
    geodesic = Geod(ellps='WGS84')
    # lon = x, lat = y
    assert 'East Bound' == spatial.map_azimuth_to_name(geodesic.inv(lons1=0, lats1=0, lons2=1, lats2=0)[0])


def test_azimuth_to_name_with_south():
    geodesic = Geod(ellps='WGS84')
    # lon = x, lat = y
    assert 'South Bound' == spatial.map_azimuth_to_name(geodesic.inv(lons1=0, lats1=0, lons2=0, lats2=-1)[0])


def test_azimuth_to_name_with_south_west():
    geodesic = Geod(ellps='WGS84')
    # lon = x, lat = y
    assert 'South-West Bound' == spatial.map_azimuth_to_name(geodesic.inv(lons1=0, lats1=0, lons2=-1, lats2=-1)[0])


def test_decode_polyline_to_s2_points():
    s2_list = spatial.decode_polyline_to_s2_points('ahmyHzvYGJyBbCGHq@r@EDIJGBu@~@SToAzAEFEDIJ')
    assert s2_list == [5221390692712666847, 5221390692823346465, 5221390693003336431, 5221390693005239025,
                       5221390693026247929, 5221390693047976565, 5221390685911708669, 5221390685910265239,
                       5221390683049158953, 5221390683157459293, 5221390683301132839, 5221390683277381201,
                       5221390683276573369, 5221390683274586647]


def test_swaping_x_y_in_linestring():
    assert spatial.swap_x_y_in_linestring(LineString([(1, 2), (3, 4), (5, 6)])) == LineString([(2, 1), (4, 3), (6, 5)])


def test_compute_average_proximity_to_polyline():
    poly_1 = 'ahmyHzvYkCvCuCdDcBrB'
    poly_2 = 'ahmyHzvYGJyBbCGHq@r@EDIJGBu@~@SToAzAEFEDIJ'
    dist = spatial.compute_average_proximity_to_polyline(poly_1, poly_2)
    assert round(dist, 5) == round(1.306345084680333, 5)


def test_compute_average_proximity_to_polyline_when_they_are_the_same_line():
    poly_1 = 'ahmyHzvYkCvCuCdDcBrB'
    poly_2 = 'ahmyHzvYkCvCuCdDcBrB'
    dist = spatial.compute_average_proximity_to_polyline(poly_1, poly_2)
    assert dist == 0


def test_reading_geojson_to_shapely():
    p = spatial.read_geojson_to_shapely(test_geojson)
    assert len(p) == 1
    assert isinstance(p[0], Polygon)
    assert list(p[0].exterior.coords) == [(-0.1487016677856445, 51.52556684350165),
                                          (-0.14063358306884766, 51.5255134425896),
                                          (-0.13865947723388672, 51.5228700191647),
                                          (-0.14093399047851562, 51.52006622056997),
                                          (-0.1492595672607422, 51.51974577545329),
                                          (-0.1508045196533203, 51.52276321095246),
                                          (-0.1487016677856445, 51.52556684350165)]


def test_s2_hex_to_cell_union():
    hex_area = '48761ad71,48761ad723,48761ad724c,48761ad73c,48761ad744,48761ad75d3,48761ad75d5,48761ad765,48761ad767,' \
               '48761ad76c,48761ad774,48761ad779,48761ad77b,48761ad783,48761ad784c,48761ad7854,48761ad794,48761ad79c,' \
               '48761ad7a4,48761ad7ac,48761ad7b1,48761ad7bc'
    cell_union = spatial.s2_hex_to_cell_union(hex_area)
    assert {cell.id() for cell in cell_union.cell_ids()} == {
        5221390329319522304, 5221390329709592576, 5221390328971395072, 5221390329290162176, 5221390329843810304,
        5221390330266386432, 5221390330268483584, 5221390330397458432, 5221390330431012864, 5221390330514898944,
        5221390330649116672, 5221390330733002752, 5221390330766557184, 5221390330900774912, 5221390330930135040,
        5221390330938523648, 5221390331185987584, 5221390331320205312, 5221390331454423040, 5221390331588640768,
        5221390331672526848, 5221390331857076224}


def test_grabs_point_indexes_from_s2(mocker):
    mocker.patch.object(s2sphere.CellId, 'from_lat_lng', return_value=s2sphere.CellId(id_=123456789))
    point_index = spatial.generate_index_s2(53.483959, -2.244644)

    assert point_index == 123456789
    s2sphere.CellId.from_lat_lng.assert_called_once_with(s2sphere.LatLng.from_degrees(53.483959, -2.244644))


def test_generating_s2_geometry_with_tuples():
    s2_geoms = spatial.generate_s2_geometry([(53.483959, -2.244644), (53.53959, -2.34644)])
    assert s2_geoms == [5222963659595391499, 5222961020721801439]


def test_generating_s2_geometry_with_shapely_points():
    s2_geoms = spatial.generate_s2_geometry([Point(53.483959, -2.244644), Point(53.53959, -2.34644)])
    assert s2_geoms == [5222963659595391499, 5222961020721801439]


def test_delegates_distance_between_points_query_to_s2(mocker):
    mocker.patch.object(s2sphere.LatLng, 'get_distance', return_value=s2sphere.Angle(radians=3))
    distance = spatial.distance_between_s2cellids(
        s2sphere.CellId.from_lat_lng(s2sphere.LatLng.from_degrees(53.483959, -2.244644)),
        s2sphere.CellId.from_lat_lng(s2sphere.LatLng.from_degrees(53.583959, -2.344644)))

    earth_radius_metres = 6371008.8
    assert distance == 3 * earth_radius_metres
    s2sphere.LatLng.get_distance.assert_called_once()


def test_delegates_distance_between_int_points_query_to_s2(mocker):
    mocker.patch.object(s2sphere.LatLng, 'get_distance', return_value=s2sphere.Angle(radians=3))
    distance = spatial.distance_between_s2cellids(
        s2sphere.CellId.from_lat_lng(s2sphere.LatLng.from_degrees(53.483959, -2.244644)).id(),
        s2sphere.CellId.from_lat_lng(s2sphere.LatLng.from_degrees(53.583959, -2.344644)).id())

    earth_radius_metres = 6371008.8
    assert distance == 3 * earth_radius_metres
    s2sphere.LatLng.get_distance.assert_called_once()


def test_delegates_distance_between_npint64_points_query_to_s2(mocker):
    mocker.patch.object(s2sphere.LatLng, 'get_distance', return_value=s2sphere.Angle(radians=3))
    distance = spatial.distance_between_s2cellids(
        int64(s2sphere.CellId.from_lat_lng(s2sphere.LatLng.from_degrees(53.483959, -2.244644)).id()),
        int64(s2sphere.CellId.from_lat_lng(s2sphere.LatLng.from_degrees(53.583959, -2.344644)).id()))

    earth_radius_metres = 6371008.8
    assert distance == 3 * earth_radius_metres
    s2sphere.LatLng.get_distance.assert_called_once()


@pytest.fixture()
def network():
    n = Network('epsg:27700')
    n.add_nodes({
        '5221390309039202089': {'x': 528344.70518, 'y': 181583.80217},
        '5221390307703020221': {'x': 528328.94676, 'y': 181736.07904},
        '5221390306965404303': {'x': 528320.26640, 'y': 181814.06237},
    })
    n.add_links({
        'link_1': {'from': '5221390309039202089',
                   'to': '5221390307703020221',
                   'modes': ['car', 'walk'],
                   'length': 153.0294,
                   'geometry': LineString(
                       [(528344.70518, 181583.80217), (528342.99487, 181598.89393), (528337.75892, 181652.61953),
                        (528333.77989, 181689.01855), (528330.46435, 181722.27602), (528328.94676, 181736.07904)])},
        'link_2': {'from': '5221390307703020221',
                   'to': '5221390306965404303',
                   'modes': ['car'],
                   'length': 78.443,
                   'geometry': LineString(
                       [(528328.94676, 181736.07904), (528327.95867, 181743.58574), (528320.87099, 181810.80295),
                        (528320.2664, 181814.06237)])},
        'link_3': {'from': '5221390307703020221',
                   'to': '5221390306965404303',
                   'modes': ['walk'],
                   'length': 78.443,
                   'geometry': LineString(
                       [(528328.94676, 181736.07904), (528327.95867, 181743.58574), (528320.87099, 181810.80295),
                        (528320.2664, 181814.06237)])},
        'link_4': {'from': '5221390306965404303',
                   'to': '5221390307703020221',
                   'modes': ['car', 'walk'],
                   'length': 78.443,
                   'geometry': LineString(
                       [(528320.2664, 181814.06237), (528320.87099, 181810.80295), (528327.95867, 181743.58574),
                        (528328.94676, 181736.07904)])},
    })
    return n


def test_SpatialTree_adds_links(network):
    spatial_tree = spatial.SpatialTree(network)

    assert_semantically_equal(list(spatial_tree.edges(data=True)),
                              [('link_1', 'link_2', {'length': 153.0294}), ('link_1', 'link_3', {'length': 153.0294}),
                               ('link_2', 'link_4', {'length': 78.443}), ('link_3', 'link_4', {'length': 78.443}),
                               ('link_4', 'link_2', {'length': 78.443}), ('link_4', 'link_3', {'length': 78.443})]
                              )
    assert_semantically_equal(dict(spatial_tree.nodes(data=True)),
                              {'link_1': {}, 'link_2': {}, 'link_3': {}, 'link_4': {}})


def test_SpatialTree_closest_links_in_london_finds_links_within_30_metres(network):
    spatial_tree = spatial.SpatialTree(network)
    stops = GeoDataFrame({
        'id': {0: 'stop_10m_to_link_1', 1: 'stop_15m_to_link_2', 2: 'stop_20m_to_link_1'},
        'geometry': {0: Point(-0.15186089346604492, 51.51950409732838),
                     1: Point(-0.15164747576623197, 51.520660715220636),
                     2: Point(-0.1520233977548685, 51.51952913606585)}})
    stops.crs = {'init': 'epsg:4326'}

    closest_links = spatial_tree.closest_links(stops, 30, modes='car')
    assert_semantically_equal(closest_links.reset_index().groupby('id')['link_id'].apply(list).to_dict(),
                              {'stop_10m_to_link_1': ['link_1'],
                               'stop_20m_to_link_1': ['link_1'],
                               'stop_15m_to_link_2': ['link_2', 'link_4']})


def test_SpatialTree_closest_links_in_london_finds_a_link_within_13_metres(network):
    spatial_tree = spatial.SpatialTree(network)
    stops = GeoDataFrame({
        'id': {0: 'stop_10m_to_link_1', 1: 'stop_15m_to_link_2', 2: 'stop_20m_to_link_1'},
        'geometry': {0: Point(-0.15186089346604492, 51.51950409732838),
                     1: Point(-0.15164747576623197, 51.520660715220636),
                     2: Point(-0.1520233977548685, 51.51952913606585)}})
    stops.crs = {'init': 'epsg:4326'}

    closest_links = spatial_tree.closest_links(stops, 13, modes='car')
    closest_links = closest_links.dropna()
    assert_semantically_equal(closest_links.reset_index().groupby('id')['link_id'].apply(list).to_dict(),
                              {'stop_10m_to_link_1': ['link_1']})


def test_SpatialTree_closest_links_in_indonesia_finds_link_within_20_metres():
    # (close to equator)
    n = Network('epsg:4326')
    n.add_nodes({'1': {'x': 109.380477773586, 'y': 0.3203433505415778},
                 '2': {'x': 109.38042852136014, 'y': 0.32031507655538294}})
    n.add_link(link_id='link_1', u='1', v='2',
               attribs={
                   'modes': ['car']
               })
    spatial_tree = spatial.SpatialTree(n)
    stops = GeoDataFrame({'geometry': {
        'stop_15m_to_link_1': Point(109.380607, 0.320333)
    }})
    stops.crs = {'init': 'epsg:4326'}

    closest_links = spatial_tree.closest_links(stops, 20, modes='car')
    closest_links = closest_links.dropna()
    assert_semantically_equal(closest_links.reset_index().groupby('index')['link_id'].apply(list).to_dict(),
                              {'stop_15m_to_link_1': ['link_1']})


def test_SpatialTree_closest_links_in_indonesia_doesnt_find_link_within_10_metres():
    # (close to equator)
    n = Network('epsg:4326')
    n.add_nodes({'1': {'x': 109.380477773586, 'y': 0.3203433505415778},
                 '2': {'x': 109.38042852136014, 'y': 0.32031507655538294}})
    n.add_link(link_id='link_1', u='1', v='2',
               attribs={
                   'modes': ['car']
               })
    spatial_tree = spatial.SpatialTree(n)
    stops = GeoDataFrame({'geometry': {
        'stop_15m_to_link_1': Point(109.380607, 0.320333)
    }})
    stops.crs = {'init': 'epsg:4326'}

    closest_links = spatial_tree.closest_links(stops, 10, modes='car')
    closest_links = closest_links.dropna()
    assert closest_links.empty


def test_SpatialTree_closest_links_in_north_canada_finds_link_within_30_metres():
    # (out in the boonies)
    n = Network('epsg:4326')
    n.add_nodes({'1': {'x': -93.25129666354827, 'y': 73.66401680598872},
                 '2': {'x': -93.25140295754169, 'y': 73.66417415921647}})
    n.add_link(link_id='link_1', u='1', v='2',
               attribs={
                   'modes': ['car']
               })
    spatial_tree = spatial.SpatialTree(n)
    stops = GeoDataFrame({'geometry': {
        'stop_15m_to_link_1': Point(-93.250971, 73.664114)
    }})
    stops.crs = {'init': 'epsg:4326'}

    closest_links = spatial_tree.closest_links(stops, 30, modes='car')
    assert_semantically_equal(closest_links.reset_index().groupby('index')['link_id'].apply(list).to_dict(),
                              {'stop_15m_to_link_1': ['link_1']})


def test_SpatialTree_closest_links_in_north_canada_doesnt_find_link_within_10_metres():
    # (out in the boonies)
    n = Network('epsg:4326')
    n.add_nodes({'1': {'x': -93.25129666354827, 'y': 73.66401680598872},
                 '2': {'x': -93.25140295754169, 'y': 73.66417415921647}})
    n.add_link(link_id='link_1', u='1', v='2',
               attribs={
                   'modes': ['car']
               })
    spatial_tree = spatial.SpatialTree(n)
    stops = GeoDataFrame({'geometry': {
        'stop_15m_to_link_1': Point(-93.250971, 73.664114)
    }})
    stops.crs = {'init': 'epsg:4326'}

    closest_links = spatial_tree.closest_links(stops, 10, modes='car')
    closest_links = closest_links.dropna()
    assert closest_links.empty


def test_SpatialTree_shortest_paths(network):
    spatial_tree = spatial.SpatialTree(network)
    df = DataFrame({'u': ['link_1', 'link_2', 'link_2', 'link_1'],
                    'v': ['link_2', 'link_3', 'link_4', 'link_4']})

    df = spatial_tree.shortest_paths(df, modes='car')
    assert_semantically_equal(df.T.to_dict(),
                              {0: {'u': 'link_1', 'v': 'link_2', 'shortest_path': ['link_1', 'link_2']},
                               1: {'u': 'link_2', 'v': 'link_3', 'shortest_path': None},
                               2: {'u': 'link_2', 'v': 'link_4', 'shortest_path': ['link_2', 'link_4']},
                               3: {'u': 'link_1', 'v': 'link_4', 'shortest_path': ['link_1', 'link_2', 'link_4']}}
                              )


def test_SpatialTree_shortest_path_lengths(network):
    spatial_tree = spatial.SpatialTree(network)
    df = DataFrame({'u': ['link_1', 'link_2', 'link_2', 'link_1'],
                    'v': ['link_2', 'link_3', 'link_4', 'link_4']})

    df = spatial_tree.shortest_path_lengths(df, modes='car')
    assert_semantically_equal(df.T.to_dict(),
                              {0: {'u': 'link_1', 'v': 'link_2', 'path_lengths': 153.0294},
                               1: {'u': 'link_2', 'v': 'link_3', 'path_lengths': float('nan')},
                               2: {'u': 'link_2', 'v': 'link_4', 'path_lengths': 78.443},
                               3: {'u': 'link_1', 'v': 'link_4', 'path_lengths': 231.4724}}
                              )
