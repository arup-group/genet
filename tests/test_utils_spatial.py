import s2sphere
import pytest
from shapely.geometry import Point
from geopandas import GeoDataFrame
from genet.utils import spatial
from genet import Network
from tests.fixtures import *


@pytest.fixture()
def network():
    n = Network('epsg:27700')
    n.add_nodes({
        'node_1': {'x': 1, 'y': 2},
        'node_2': {'x': 2, 'y': 2},
        'node_3': {'x': 3, 'y': 2},
        'node_4': {'x': 3, 'y': 3},
        'node_5': {'x': 1, 'y': 1}
    })
    n.add_links({
        'link_1': {'from': 'node_1', 'to': 'node_2', 'modes': ['car', 'walk']},
        'link_2': {'from': 'node_2', 'to': 'node_3', 'modes': ['car']},
        'link_3': {'from': 'node_2', 'to': 'node_3', 'modes': ['walk']},
        'link_4': {'from': 'node_3', 'to': 'node_2', 'modes': ['car', 'walk']},
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


def test_SpatialTree_adds_a_link(network):
    spatial_tree = spatial.SpatialTree(network)

    assert_semantically_equal(list(spatial_tree.edges(data=True)), [('link_1', 'link_2', {}), ('link_1', 'link_3', {}),
                                                                    ('link_2', 'link_4', {}), ('link_3', 'link_4', {}),
                                                                    ('link_4', 'link_2', {}), ('link_4', 'link_3', {})])
    assert_semantically_equal(dict(spatial_tree.nodes(data=True)), {})


def test_SpatialTree_closest_links(network):
    spatial_tree = spatial.SpatialTree(network)
    stops = GeoDataFrame({'stop': ['stop_1', 'stop_2', 'stop_3'],
                          'geometry': [Point(1.5, 2), Point(2.9, 2.8), Point(1.1, 0.8)]})
    stops.crs = {'init': 'epsg:27700'}
    stops = stops.to_crs("EPSG:4326")

    assert_semantically_equal(spatial_tree.find_closest_links(stops, 100, mode='car'),
                              {'stop_1': ['link_1', 'link_2', 'link_4'], 'stop_2': ['link_1', 'link_2', 'link_4'],
                               'stop_3': ['link_1', 'link_2', 'link_4']})
