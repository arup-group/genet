import pytest
import sys
import os
from genet import Network, Service, Route, Stop, AuxiliaryFile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
links_benchmark_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "auxiliary_files", "links_benchmark.json"))
pt_stop_benchmark_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "auxiliary_files", "pt_stop_benchmark.json"))


@pytest.fixture()
def network():
    n = Network('epsg:27700')
    n.add_links({str(i): {'from': '1', 'to': '2', 'modes': ['car', 'bus']} for i in range(10)})
    n.schedule.add_service(
        Service('service_1',
                routes=[Route(id='route_1',
                              route_short_name='route_1',
                              mode='bus',
                              trips={},
                              stops=[Stop('stop_1', epsg='epsg:27700', x=1, y=2),
                                     Stop('stop_2', epsg='epsg:27700', x=3, y=2)],
                              arrival_offsets=[''],
                              departure_offsets=['']
                              )]))
    return n


@pytest.fixture()
def links_benchmark():
    return AuxiliaryFile(links_benchmark_path)


# pt stops are not currently able to change indices
# this fixture and corresponding file are added in
# case of future change in usage
@pytest.fixture()
def pt_stop_benchmark():
    return AuxiliaryFile(pt_stop_benchmark_path)


def test_attaching_links_benchmark_to_network(links_benchmark, network):
    links_benchmark.attach({link_id for link_id, dat in network.links()})
    links_benchmark.attach({node_id for node_id, dat in network.nodes()})

    assert links_benchmark.is_attached()
    assert links_benchmark.attachments == [{'car': {'1': {'in': 'links'}}}, {'car': {'1': {'out': 'links'}}},
                                           {'car': {'2': {'in': 'links'}}}, {'car': {'2': {'out': 'links'}}},
                                           {'bus': {'1': {'in': 'links'}}}, {'bus': {'1': {'out': 'links'}}},
                                           {'bus': {'2': {'in': 'links'}}}, {'bus': {'2': {'out': 'links'}}},
                                           {'car': {'1': {'out': 'links'}}}, {'car': {'2': {'in': 'links'}}},
                                           {'bus': {'1': {'out': 'links'}}}, {'bus': {'2': {'in': 'links'}}}]


def test_building_identity_map_for_links_benchmark(links_benchmark):
    links_benchmark.attachments = [{'car': {'1': {'in': 'links'}}}, {'car': {'1': {'out': 'links'}}},
                                   {'car': {'2': {'in': 'links'}}}, {'car': {'2': {'out': 'links'}}},
                                   {'bus': {'1': {'in': 'links'}}}, {'bus': {'1': {'out': 'links'}}},
                                   {'bus': {'2': {'in': 'links'}}}, {'bus': {'2': {'out': 'links'}}},
                                   {'car': {'1': {'out': 'links'}}}, {'car': {'2': {'in': 'links'}}},
                                   {'bus': {'1': {'out': 'links'}}}, {'bus': {'2': {'in': 'links'}}}]

    links_benchmark.build_identity_map()
    assert links_benchmark.map == {'0': '0', '3': '3', '2': '2', '1': '1', '4': '4'}
