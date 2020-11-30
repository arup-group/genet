import s2sphere
import pytest
from shapely.geometry import Point, LineString
from geopandas import GeoDataFrame
from pandas import DataFrame
from genet.utils import spatial
from genet import Network
from tests.fixtures import *


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


def test_decode_polyline_to_s2_points():
    s2_list = spatial.decode_polyline_to_s2_points('ahmyHzvYGJyBbCGHq@r@EDIJGBu@~@SToAzAEFEDIJ')
    assert s2_list == [5221390692712666847, 5221390692823346465, 5221390693003336431, 5221390693005239025,
                       5221390693026247929, 5221390693047976565, 5221390685911708669, 5221390685910265239,
                       5221390683049158953, 5221390683157459293, 5221390683301132839, 5221390683277381201,
                       5221390683276573369, 5221390683274586647]


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


def test_grabs_point_indexes_from_s2(mocker):
    mocker.patch.object(s2sphere.CellId, 'from_lat_lng', return_value=s2sphere.CellId(id_=123456789))
    point_index = spatial.grab_index_s2(53.483959, -2.244644)

    assert point_index == 123456789
    s2sphere.CellId.from_lat_lng.assert_called_once_with(s2sphere.LatLng.from_degrees(53.483959, -2.244644))


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


def test_create_subsetting_area_with_two_cells_check_distance_from_centre_is_roughly_the_same_for_both():
    cap = spatial.create_subsetting_area([5221390301001263407, 5221390302696205321])
    cap_centre = s2sphere.CellId.from_point(cap.axis())
    dist_1 = cap_centre.to_lat_lng().get_distance(s2sphere.CellId(5221390301001263407).to_lat_lng()).radians
    dist_2 = cap_centre.to_lat_lng().get_distance(s2sphere.CellId(5221390302696205321).to_lat_lng()).radians
    assert cap.contains(s2sphere.CellId(5221390301001263407).to_point())
    assert cap.contains(s2sphere.CellId(5221390302696205321).to_point())
    assert round(dist_1, 8) == round(dist_2, 8)


def test_SpatialTree_adds_links(network):
    spatial_tree = spatial.SpatialTree(network)

    assert_semantically_equal(list(spatial_tree.edges(data=True)), [('link_1', 'link_2', {}), ('link_1', 'link_3', {}),
                                                                    ('link_2', 'link_4', {}), ('link_3', 'link_4', {}),
                                                                    ('link_4', 'link_2', {}), ('link_4', 'link_3', {})])
    assert_semantically_equal(dict(spatial_tree.nodes(data=True)),
                              {'link_1': {}, 'link_2': {}, 'link_3': {}, 'link_4': {}})


def test_SpatialTree_closest_links(network):
    spatial_tree = spatial.SpatialTree(network)
    stops = GeoDataFrame({'stop': ['stop_10m_to_link_1', 'stop_20m_to_link_1', 'stop_15m_to_link_2'],
                          'geometry': [Point(-0.15186089346604492, 51.51950409732838),
                                       Point(-0.1520233977548685, 51.51952913606585),
                                       Point(-0.15164747576623197, 51.520660715220636)]})
    stops.crs = {'init': 'epsg:4326'}

    closest_links = spatial_tree.find_closest_links(stops, 30, mode='car')
    assert_semantically_equal(closest_links,
                              {'stop_10m_to_link_1': ['link_1'],
                               'stop_20m_to_link_1': ['link_1'],
                               'stop_15m_to_link_2': ['link_2', 'link_4']})


def test_SpatialTree_shortest_paths(network):
    spatial_tree = spatial.SpatialTree(network)
    stops = DataFrame({'u': ['link_1', 'link_2', 'link_2'],
                       'v': ['link_2', 'link_3', 'link_4']})

    stops = spatial_tree.shortest_path_lengths(stops, mode='car')
    pass
