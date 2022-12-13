import s2sphere
import pytest
from geopandas import GeoDataFrame
from pandas import DataFrame
from numpy import int64
from pyproj import Geod
from genet.utils import spatial
from genet import Network
from tests.fixtures import *
from shapely.geometry import LineString, Polygon, Point, MultiLineString
from genet.exceptions import EmptySpatialTree


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


def test_merging_contiguous_linestrings():
    linestrings = [LineString([(1, 2), (3, 4), (5, 6)]), LineString([(5,6), (7, 8), (9, 10)])]
    assert spatial.merge_linestrings(linestrings) == LineString([(1, 2), (3, 4), (5, 6), (7, 8), (9, 10)])


def test_merging_noncontiguous_linestrings_results_in_multilinestring():
    linestrings = [LineString([(1, 2), (3, 4), (5, 6)]), LineString([(7, 8), (9, 10)])]
    assert spatial.merge_linestrings(linestrings) == MultiLineString([[(1, 2), (3, 4), (5, 6)],[(7, 8), (9, 10)]])


def test_snapping_point_on_line_returns_the_same_point():
    line = LineString([(0, 0), (0, 1), (0, 2)])
    point = Point(0, 0.5)
    assert spatial.snap_point_to_line(point, line) == point


def test_snapping_point_within_threshold_returns_the_same_point():
    line = LineString([(0, 0), (0, 1), (0, 2)])
    distance_threshold = 0.1
    point = Point(0 - (distance_threshold / 2), 0.5)
    assert spatial.snap_point_to_line(point, line, distance_threshold) == point


def test_snapping_point_over_threshold_moves_the_point():
    line = LineString([(0, 0), (0, 1), (0, 2)])
    distance_threshold = 0.1
    point = Point(0 - (distance_threshold * 2), 0.5)
    assert spatial.snap_point_to_line(point, line, distance_threshold) == Point(0, 0.5)


def test_continuing_vanilla_line():
    p1 = Point(0, 0)
    p2 = Point(1, 1)
    assert spatial.continue_line_from_two_points(p1, p2) == LineString([p1, p2, Point(2, 2)])


def test_continuing_line_going_backwards():
    p1 = Point(2, 2)
    p2 = Point(1, 1)
    assert spatial.continue_line_from_two_points(p1, p2) == LineString([p1, p2, Point(0, 0)])


def test_continuing_line_with_negative_numbers():
    p1 = Point(2, -2)
    p2 = Point(1, -1)
    assert spatial.continue_line_from_two_points(p1, p2) == LineString([p1, p2, Point(0, 0)])


def test_splitting_line_at_point_on_the_line():
    line = LineString([(0, 0), (0, 1), (0, 2)])
    point = Point(0, 0.5)
    assert spatial.split_line_at_point(point, line) == \
           (LineString([(0, 0), point]),  LineString([point, (0, 1), (0, 2)]))


def test_splitting_line_at_point_away_from_the_line_splits_at_point_on_the_line():
    line = LineString([(0, 0), (0, 1), (0, 2)])
    point = Point(-0.5, 0.5)
    assert spatial.split_line_at_point(point, line) == \
           (LineString([(0, 0), (0, 0.5)]),  LineString([(0, 0.5), (0, 1), (0, 2)]))


def test_splitting_curved_line():
    line = LineString([
        (528541.02122, 177266.68113),
        (528550.59744, 177260.35921),
        (528558.90144, 177254.29693),
        (528567.93041, 177245.54257),
        (528574.51427, 177236.01671),
        (528582.94533, 177223.5529),
        (528590.27441, 177207.14287),
        (528593.0748, 177199.19972),
        (528596.13021, 177188.65874),
        (528597.9183, 177176.03142)])
    point = Point(528568.90, 177243.42)
    split_geoms = spatial.split_line_at_point(point, line)
    assert len(split_geoms) == 2
    assert split_geoms[0].coords[0] == line.coords[0]
    assert split_geoms[1].coords[-1] == line.coords[-1]


def test_splitting_curved_line_with_a_super_close_point_warns_of_closeness(caplog):
    line = LineString([(528208.61078, 177514.31738),
        (528216.89907, 177506.02421),
        (528220.00403, 177502.9153),
        (528222.71173, 177500.8393),
        (528225.95029, 177498.93838),
        (528234.89851, 177493.7053),
        (528251.80814, 177481.14253),
        (528268.73601, 177465.54717),
        (528279.08839, 177454.14351),
        (528295.84491, 177432.3435),
        (528296.56349, 177431.18557),
        (528313.83963, 177403.42285),
        (528329.73594, 177381.84037),
        (528335.96606, 177374.68653),
        (528353.89673, 177354.94385),
        (528364.77572, 177344.71445),
        (528372.55533, 177339.14626),
        (528377.14782, 177336.30107),
        (528393.93838, 177325.89415),
        (528408.19621, 177319.28968),
        (528421.10874, 177313.31753),
        (528453.33735, 177301.41433),
        (528470.65791, 177295.10763),
        (528492.21561, 177287.25741),
        (528505.78341, 177282.32015),
        (528513.10633, 177279.62984),
        (528523.6504, 177275.41286),
        (528541.02122, 177266.68113),
        (528550.59744, 177260.35921),
        (528558.90144, 177254.29693),
        (528567.93041, 177245.54257),
        (528574.51427, 177236.01671),
        (528582.94533, 177223.5529),
        (528590.27441, 177207.14287),
        (528593.0748, 177199.19972),
        (528596.13021, 177188.65874),
        (528597.9183, 177176.03142),
        (528599.07908, 177163.11938),
        (528598.63073, 177150.92166),
        (528596.68517, 177138.57603),
        (528594.77161, 177129.68353),
        (528591.99383, 177122.47125),
        (528590.53845, 177118.68489)])
    point = Point(528569.2382220798, 177243.65036166355)
    split_geoms = spatial.split_line_at_point(point, line)
    assert len(split_geoms) == 2
    assert split_geoms[0].coords[0] == line.coords[0]
    assert split_geoms[1].coords[-1] == line.coords[-1]
    assert caplog.records[0].levelname == 'WARNING'
    assert 'Given point is very close, but not cannot be placed on the line.' in caplog.records[0].message


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


def test_subsetting_links_df_by_mode(network):
    spatial_tree = spatial.SpatialTree(network)
    df = spatial_tree.modal_links_geodataframe(modes={'car'})

    assert set(df['link_id']) == {'link_1', 'link_2', 'link_4'}


def test_subsetting_links_df_by_mode_that_isnt_present_throws_error(network):
    spatial_tree = spatial.SpatialTree(network)

    with pytest.raises(EmptySpatialTree) as e:
        df = spatial_tree.modal_links_geodataframe(modes={'piggyback'})
    assert 'No links found' in str(e.value)


def test_SpatialTree_closest_links_in_london_finds_links_within_30_metres(network):
    spatial_tree = spatial.SpatialTree(network).modal_subtree(modes='car')
    stops = GeoDataFrame({
        'id': {0: 'stop_10m_to_link_1', 1: 'stop_15m_to_link_2', 2: 'stop_20m_to_link_1'},
        'geometry': {0: Point(-0.15186089346604492, 51.51950409732838),
                     1: Point(-0.15164747576623197, 51.520660715220636),
                     2: Point(-0.1520233977548685, 51.51952913606585)}})
    stops.crs = {'init': 'epsg:4326'}

    closest_links = spatial_tree.closest_links(stops, 30)
    assert_semantically_equal(closest_links.reset_index().groupby('id')['link_id'].apply(list).to_dict(),
                              {'stop_10m_to_link_1': ['link_1'],
                               'stop_20m_to_link_1': ['link_1'],
                               'stop_15m_to_link_2': ['link_2', 'link_4']})


def test_SpatialTree_closest_links_in_london_finds_a_link_within_13_metres(network):
    spatial_tree = spatial.SpatialTree(network).modal_subtree(modes='car')
    stops = GeoDataFrame({
        'id': {0: 'stop_10m_to_link_1', 1: 'stop_15m_to_link_2', 2: 'stop_20m_to_link_1'},
        'geometry': {0: Point(-0.15186089346604492, 51.51950409732838),
                     1: Point(-0.15164747576623197, 51.520660715220636),
                     2: Point(-0.1520233977548685, 51.51952913606585)}
        },
        crs='epsg:4326'
    )

    closest_links = spatial_tree.closest_links(stops, 13)
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
    spatial_tree = spatial.SpatialTree(n).modal_subtree(modes='car')
    stops = GeoDataFrame(
        {'geometry': {'stop_15m_to_link_1': Point(109.380607, 0.320333)}},
        crs='epsg:4326'
    )

    closest_links = spatial_tree.closest_links(stops, 20)
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
    spatial_tree = spatial.SpatialTree(n).modal_subtree(modes='car')
    stops = GeoDataFrame(
        {'geometry': {'stop_15m_to_link_1': Point(109.380607, 0.320333)}},
        crs='epsg:4326'
    )

    closest_links = spatial_tree.closest_links(stops, 10)
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
    spatial_tree = spatial.SpatialTree(n).modal_subtree(modes='car')
    stops = GeoDataFrame(
        {'geometry': {'stop_15m_to_link_1': Point(-93.250971, 73.664114)}},
        crs='epsg:4326'
    )

    closest_links = spatial_tree.closest_links(stops, 30)
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
    spatial_tree = spatial.SpatialTree(n).modal_subtree(modes='car')
    stops = GeoDataFrame(
        {'geometry': {'stop_15m_to_link_1': Point(-93.250971, 73.664114)}},
        crs='epsg:4326'
    )

    closest_links = spatial_tree.closest_links(stops, 10)
    closest_links = closest_links.dropna()
    assert closest_links.empty


def test_SpatialTree_shortest_paths(network):
    spatial_tree = spatial.SpatialTree(network).modal_subtree(modes='car')
    df = DataFrame({'u': ['link_1', 'link_2', 'link_2', 'link_1'],
                    'v': ['link_2', 'link_3', 'link_4', 'link_4']})

    df = spatial_tree.shortest_paths(df)
    assert_semantically_equal(df.T.to_dict(),
                              {0: {'u': 'link_1', 'v': 'link_2', 'shortest_path': ['link_1', 'link_2']},
                               1: {'u': 'link_2', 'v': 'link_3', 'shortest_path': None},
                               2: {'u': 'link_2', 'v': 'link_4', 'shortest_path': ['link_2', 'link_4']},
                               3: {'u': 'link_1', 'v': 'link_4', 'shortest_path': ['link_1', 'link_2', 'link_4']}}
                              )


def test_SpatialTree_shortest_path_lengths(network):
    spatial_tree = spatial.SpatialTree(network).modal_subtree(modes='car')
    df = DataFrame({'u': ['link_1', 'link_2', 'link_2', 'link_1'],
                    'v': ['link_2', 'link_3', 'link_4', 'link_4']})

    df = spatial_tree.shortest_path_lengths(df)
    assert_semantically_equal(df.T.to_dict(),
                              {0: {'u': 'link_1', 'v': 'link_2', 'path_lengths': 153.0294},
                               1: {'u': 'link_2', 'v': 'link_3', 'path_lengths': float('nan')},
                               2: {'u': 'link_2', 'v': 'link_4', 'path_lengths': 78.443},
                               3: {'u': 'link_1', 'v': 'link_4', 'path_lengths': 231.4724}}
                              )
