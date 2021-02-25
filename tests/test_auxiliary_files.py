import pytest
import sys
import os
from genet import Network, Service, Route, Stop, AuxiliaryFile
from tests.fixtures import assert_semantically_equal

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

    assert links_benchmark.is_attached()
    assert links_benchmark.attachments == [{'car': {'1': {'in': 'links'}}}, {'car': {'1': {'out': 'links'}}},
                                           {'car': {'2': {'in': 'links'}}}, {'car': {'2': {'out': 'links'}}},
                                           {'bus': {'1': {'in': 'links'}}}, {'bus': {'1': {'out': 'links'}}},
                                           {'bus': {'2': {'in': 'links'}}}, {'bus': {'2': {'out': 'links'}}}]


def test_building_identity_map_for_links_benchmark(links_benchmark):
    links_benchmark.attachments = [{'car': {'1': {'in': 'links'}}}, {'car': {'1': {'out': 'links'}}},
                                   {'car': {'2': {'in': 'links'}}}, {'car': {'2': {'out': 'links'}}},
                                   {'bus': {'1': {'in': 'links'}}}, {'bus': {'1': {'out': 'links'}}},
                                   {'bus': {'2': {'in': 'links'}}}, {'bus': {'2': {'out': 'links'}}}]

    links_benchmark.build_identity_map()
    assert links_benchmark.map == {'0': '0', '3': '3', '2': '2', '1': '1', '4': '4'}


def test_updating_links_benchmark(links_benchmark):
    links_benchmark.attachments = [{'car': {'1': {'in': 'links'}}}, {'car': {'1': {'out': 'links'}}},
                                   {'car': {'2': {'in': 'links'}}}, {'car': {'2': {'out': 'links'}}},
                                   {'bus': {'1': {'in': 'links'}}}, {'bus': {'1': {'out': 'links'}}},
                                   {'bus': {'2': {'in': 'links'}}}, {'bus': {'2': {'out': 'links'}}}]
    links_benchmark.map = {'0': '000', '3': '003', '2': '002', '1': '001', '4': '004'}

    links_benchmark.update()

    assert_semantically_equal(
        links_benchmark.data,
        {'car': {'1': {'in': {'links': ['000'],
                              'counts': {'0': 78.0, '1': 46.0, '2': 39.0, '3': 45.0, '4': 72.0, '5': 188.0, '6': 475.0,
                                         '7': 734.0, '8': 651.0, '9': 605.0, '10': 605.0, '11': 625.0, '12': 569.0,
                                         '13': 632.0, '14': 586.0, '15': 585.0, '16': 825.0, '17': 756.0, '18': 711.0,
                                         '19': 597.0, '20': 405.0, '21': 285.0, '22': 218.0, '23': 136.0}},
                       'out': {'links': ['001'],
                               'counts': {'0': 76.0, '1': 45.0, '2': 40.0, '3': 38.0, '4': 63.0, '5': 165.0, '6': 608.0,
                                          '7': 858.0, '8': 725.0, '9': 514.0, '10': 415.0, '11': 485.0, '12': 554.0,
                                          '13': 463.0, '14': 589.0, '15': 616.0, '16': 835.0, '17': 901.0, '18': 704.0,
                                          '19': 476.0, '20': 355.0, '21': 283.0, '22': 219.0, '23': 134.0}}},
                 '2': {'in': {'links': ['002'],
                              'counts': {'0': 92.0, '1': 57.0, '2': 53.0, '3': 55.0, '4': 88.0, '5': 222.0, '6': 637.0,
                                         '7': 1146.0, '8': 1017.0, '9': 691.0, '10': 578.0, '11': 519.0, '12': 540.0,
                                         '13': 615.0, '14': 619.0, '15': 630.0, '16': 828.0, '17': 913.0, '18': 890.0,
                                         '19': 629.0, '20': 326.0, '21': 315.0, '22': 252.0, '23': 159.0}},
                       'out': {'links': ['003', '004'],
                               'counts': {'0': 81.0, '1': 53.0, '2': 47.0, '3': 45.0, '4': 77.0, '5': 182.0, '6': 385.0,
                                          '7': 721.0, '8': 592.0, '9': 487.0, '10': 488.0, '11': 514.0, '12': 498.0,
                                          '13': 659.0, '14': 749.0, '15': 786.0, '16': 1009.0, '17': 908.0, '18': 845.0,
                                          '19': 578.0, '20': 370.0, '21': 273.0, '22': 230.0, '23': 137.0}}}},
         'bus': {'1': {'in': {'links': ['000'],
                              'counts': {'0': 78.0, '1': 46.0, '2': 39.0, '3': 45.0, '4': 72.0, '5': 188.0, '6': 475.0,
                                         '7': 734.0, '8': 651.0, '9': 605.0, '10': 605.0, '11': 625.0, '12': 569.0,
                                         '13': 632.0, '14': 586.0, '15': 585.0, '16': 825.0, '17': 756.0, '18': 711.0,
                                         '19': 597.0, '20': 405.0, '21': 285.0, '22': 218.0, '23': 136.0}},
                       'out': {'links': ['001'],
                               'counts': {'0': 76.0, '1': 45.0, '2': 40.0, '3': 38.0, '4': 63.0, '5': 165.0, '6': 608.0,
                                          '7': 858.0, '8': 725.0, '9': 514.0, '10': 415.0, '11': 485.0, '12': 554.0,
                                          '13': 463.0, '14': 589.0, '15': 616.0, '16': 835.0, '17': 901.0, '18': 704.0,
                                          '19': 476.0, '20': 355.0, '21': 283.0, '22': 219.0, '23': 134.0}}},
                 '2': {'in': {'links': ['002'],
                              'counts': {'0': 92.0, '1': 57.0, '2': 53.0, '3': 55.0, '4': 88.0, '5': 222.0, '6': 637.0,
                                         '7': 1146.0, '8': 1017.0, '9': 691.0, '10': 578.0, '11': 519.0, '12': 540.0,
                                         '13': 615.0, '14': 619.0, '15': 630.0, '16': 828.0, '17': 913.0, '18': 890.0,
                                         '19': 629.0, '20': 326.0, '21': 315.0, '22': 252.0, '23': 159.0}},
                       'out': {'links': ['003', '004'],
                               'counts': {'0': 81.0, '1': 53.0, '2': 47.0, '3': 45.0, '4': 77.0, '5': 182.0, '6': 385.0,
                                          '7': 721.0, '8': 592.0, '9': 487.0, '10': 488.0, '11': 514.0, '12': 498.0,
                                          '13': 659.0, '14': 749.0, '15': 786.0, '16': 1009.0, '17': 908.0, '18': 845.0,
                                          '19': 578.0, '20': 370.0, '21': 273.0, '22': 230.0, '23': 137.0}}}}})
    assert not links_benchmark.has_updates()
