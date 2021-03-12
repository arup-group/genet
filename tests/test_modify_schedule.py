import pytest
import sys
import os
from pyproj import Transformer
from genet import Stop, Route, Service, Schedule, Network, MaxStableSet
from genet.modify import schedule as mod_schedule
import genet.utils.spatial as spatial
from tests.fixtures import assert_semantically_equal


def test_reproj_stops():
    stops = {'26997928P': {'routes': ['10314_0'], 'id': '26997928P', 'x': 528464.1342843144, 'y': 182179.7435136598,
                           'epsg': 'epsg:27700', 'lat': 51.52393050617373, 'lon': -0.14967658860132668,
                           's2_id': 5221390302759871369, 'additional_attributes': [], 'services': ['10314']},
             '26997928P.link:1': {'routes': ['10314_0'], 'id': '26997928P.link:1', 'x': 528464.1342843144,
                                  'y': 182179.7435136598, 'epsg': 'epsg:27700', 'lat': 51.52393050617373,
                                  'lon': -0.14967658860132668, 's2_id': 5221390302759871369,
                                  'additional_attributes': [], 'services': ['10314']}}
    reprojected = mod_schedule.reproj_stops(stops, 'epsg:4326')
    assert_semantically_equal(reprojected,
                              {'26997928P': {'x': -0.14967658860132668, 'y': 51.52393050617373, 'epsg': 'epsg:4326'},
                               '26997928P.link:1': {'x': -0.14967658860132668, 'y': 51.52393050617373,
                                                    'epsg': 'epsg:4326'}})


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
network_test_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "simplified_network", "network.xml"))
schedule_test_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "simplified_network", "schedule.xml"))


@pytest.fixture()
def test_network():
    n = Network('epsg:27700')
    n.read_matsim_network(network_test_file)
    n.read_matsim_schedule(schedule_test_file)
    return n

@pytest.fixture()
def test_spatialtree(test_network):
    return spatial.SpatialTree(test_network)


def test_snapping_pt_route_results_in_all_stops_with_link_references_and_routes_between_them(
        test_network, test_spatialtree):
    mss = MaxStableSet(pt_graph=test_network.schedule.route('40230_1').graph(),
                       network_spatial_tree=test_spatialtree,
                       modes={'car', 'bus'},
                       distance_threshold=10)

    mss.solve()
    assert mss.all_stops_solved()
    mss.route_edges()
    assert mss.pt_edges['shortest_path'].notna().all()
