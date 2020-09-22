import genet.inputs_handler.osmnx_customised as oxcustom
import pytest
import networkx as nx
from shapely.geometry import LineString
from tests.fixtures import assert_semantically_equal


def assert_correct_edge_groups(edge_groups_1, edge_groups_2):
    for edge_group_1 in edge_groups_1:
        for edge_group_2 in edge_groups_2:
            if edge_group_1 == edge_group_2:
                edge_groups_2.remove(edge_group_2)
    assert not edge_groups_2


@pytest.fixture()
def simple_graph_with_junctions():
    g = nx.DiGraph()
    g.add_edges_from([(1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (11, 2), (2, 22), (22, 33), (33, 44), (44, 55), (55, 5)])
    return g


def test_getting_endpoints_with_simple_graph_with_junctions(simple_graph_with_junctions):
    g = simple_graph_with_junctions
    endpts = oxcustom._is_endpoint(
        {node: {'successors': list(g.successors(node)), 'predecessors': list(g.predecessors(node))}
         for node in g.nodes}
    )
    assert set(endpts) == {1, 2, 5, 6, 11}


def test_simplified_paths_with_simple_graph_with_junctions(simple_graph_with_junctions):
    g = simple_graph_with_junctions
    edge_groups = oxcustom._get_edge_groups_to_simplify(g)
    assert_correct_edge_groups(edge_groups,
                               [[2, 3, 4, 5], [2, 22, 33, 44, 55, 5]])


@pytest.fixture()
def graph_with_junctions_directed_both_ways():
    g = nx.DiGraph()
    g.add_edges_from([(1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (11, 2), (2, 22), (22, 33), (33, 44), (44, 55), (55, 5),
                      (2, 1), (3, 2), (4, 3), (5, 4), (6, 5), (2, 11), (22, 2), (33, 22), (44, 33), (55, 44), (5, 55)])
    return g


def test_getting_endpoints_with_graph_with_junctions_directed_both_ways(graph_with_junctions_directed_both_ways):
    g = graph_with_junctions_directed_both_ways
    endpts = oxcustom._is_endpoint(
        {node: {'successors': list(g.successors(node)), 'predecessors': list(g.predecessors(node))}
         for node in g.nodes}
    )
    assert set(endpts) == {2, 3, 4, 5, 22, 33, 44, 55}


def test_simplified_paths_with_graph_with_junctions_directed_both_ways(graph_with_junctions_directed_both_ways):
    g = graph_with_junctions_directed_both_ways
    edge_groups = oxcustom._get_edge_groups_to_simplify(g)
    assert_correct_edge_groups(edge_groups, [[2, 1, 2], [5, 6, 5], [2, 11, 2]])


@pytest.fixture()
def indexed_edge_groups():
    return {'new_link_id': {
        'path': [1, 2, 3],
        'link_data': {'permlanes': [3.0, 5.0], 'freespeed': [20, 40],
                      'capacity': [1000.0, 2000.0], 'oneway': ['1', '1'],
                      'modes': [['car'], ['car']],
                      'from': [1, 2],
                      'to': [2, 3],
                      'id': ['1926', '1927'],
                      's2_from': [5221390326122671999, 5221390326036762795],
                      's2_to': [5221390326036762795, 5221390326952602895],
                      'length': [12.0, 14.0],
                      'attributes': [
                          {'osm:way:lanes': {'name': 'osm:way:lanes', 'class': 'java.lang.String', 'text': '3'},
                           'osm:way:osmid': {'name': 'osm:way:osmid', 'class': 'java.lang.String', 'text': '18769878'},
                           'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String',
                                               'text': 'trunk'}},
                          {'osm:way:lanes': {'name': 'osm:way:lanes', 'class': 'java.lang.String', 'text': '3'},
                           'osm:way:osmid': {'name': 'osm:way:osmid', 'class': 'java.lang.String', 'text': '18769879'},
                           'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String',
                                               'text': 'unclassified'}}]},
        'node_data': {
            1: {'id': 1, 'x': 528915.9309752393, 'y': 181899.48948011652, 'lon': -0.14327038749428384,
                'lat': 51.52130909540579, 's2_id': 5221390326122671999},
            2: {'id': 2, 'x': 528888.1581643537, 'y': 181892.3086225874, 'lon': -0.14367308749449406,
                'lat': 51.52125089540575, 's2_id': 5221390326036762795},
            3: {'id': 3, 'x': 528780.3405144282, 'y': 181859.84184561518, 'lon': -0.14523808749533396,
                'lat': 51.520983695405526, 's2_id': 5221390326952602895}}}
    }


def test_merging_edge_data(indexed_edge_groups):
    links_to_add = oxcustom.process_path(indexed_edge_groups)

    links_to_add['new_link_id']['attributes']['osm:way:osmid']['text'] = links_to_add['new_link_id']['attributes']['osm:way:osmid']['text'].split(',')
    links_to_add['new_link_id']['attributes']['osm:way:highway']['text'] = links_to_add['new_link_id']['attributes']['osm:way:highway']['text'].split(',')
    assert_semantically_equal(links_to_add, {
                'new_link_id': {
                    'permlanes': 4,
                    'freespeed': 40.0,
                    'capacity': 1500.0,
                    'oneway': '1',
                    'modes': ['car'],
                    'from': 1,
                    'to': 3,
                    'id': 'new_link_id',
                    's2_from': 5221390326122671999,
                    's2_to': 5221390326952602895,
                    'length': 26,
                    'attributes': {
                        'osm:way:lanes': {'name': 'osm:way:lanes', 'class': 'java.lang.String', 'text': '3'},
                        'osm:way:osmid': {'name': 'osm:way:osmid', 'class': 'java.lang.String', 'text': '18769878,18769879'.split(',')},
                        'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'trunk,unclassified'.split(',')}},
                    'geometry': LineString([(528915.9309752393, 181899.48948011652), (528888.1581643537, 181892.3086225874), (528780.3405144282, 181859.84184561518)]),
                    'ids': ['1926', '1927']}})
