import genet.utils.simplification as simplification
import networkx as nx
import pytest
from shapely.geometry import LineString


@pytest.fixture
def assert_correct_edge_groups():
    def _assert_correct_edge_groups(edge_groups_1, edge_groups_2):
        assert len(edge_groups_1) == len(edge_groups_2)
        for edge_group_1 in edge_groups_1:
            for edge_group_2 in edge_groups_2:
                if edge_group_1 == edge_group_2:
                    edge_groups_2.remove(edge_group_2)
        assert not edge_groups_2

    return _assert_correct_edge_groups


@pytest.fixture()
def simple_graph_with_junctions():
    g = nx.MultiDiGraph()
    g.add_edges_from(
        [
            (1, 2),
            (2, 3),
            (3, 4),
            (4, 5),
            (5, 6),
            (11, 2),
            (2, 22),
            (22, 33),
            (33, 44),
            (44, 55),
            (55, 5),
        ]
    )
    return g


def test_getting_endpoints_with_simple_graph_with_junctions(simple_graph_with_junctions):
    g = simple_graph_with_junctions
    endpts = simplification._is_endpoint(
        {
            node: {"successors": set(g.successors(node)), "predecessors": set(g.predecessors(node))}
            for node in g.nodes
        }
    )
    assert set(endpts) == {1, 2, 5, 6, 11}


def test_simplified_paths_with_simple_graph_with_junctions(
    assert_correct_edge_groups, simple_graph_with_junctions
):
    g = simple_graph_with_junctions
    edge_groups = simplification._get_edge_groups_to_simplify(g)
    assert_correct_edge_groups(edge_groups, [[2, 3, 4, 5], [2, 22, 33, 44, 55, 5]])


@pytest.fixture()
def graph_with_junctions_directed_both_ways_and_loop():
    g = nx.MultiDiGraph()
    g.add_edges_from(
        [
            (1, 2),
            (2, 3),
            (3, 4),
            (4, 5),
            (5, 6),
            (11, 2),
            (2, 22),
            (22, 33),
            (33, 44),
            (44, 55),
            (55, 5),
            (2, 1),
            (3, 2),
            (4, 3),
            (5, 4),
            (6, 5),
            (2, 11),
            (22, 2),
            (33, 22),
            (44, 33),
            (55, 44),
            (5, 55),
            (11, 11),
        ]
    )
    return g


def test_getting_endpoints_with_graph_with_junctions_directed_both_ways(
    graph_with_junctions_directed_both_ways_and_loop,
):
    g = graph_with_junctions_directed_both_ways_and_loop
    endpts = simplification._is_endpoint(
        {
            node: {"successors": set(g.successors(node)), "predecessors": set(g.predecessors(node))}
            for node in g.nodes
        }
    )
    assert set(endpts) == {1, 2, 5, 6, 11}


def test_simplified_paths_with_graph_with_junctions_directed_both_ways(
    assert_correct_edge_groups, graph_with_junctions_directed_both_ways_and_loop
):
    g = graph_with_junctions_directed_both_ways_and_loop
    edge_groups = simplification._get_edge_groups_to_simplify(g)
    assert_correct_edge_groups(
        edge_groups, [[2, 3, 4, 5], [2, 22, 33, 44, 55, 5], [5, 4, 3, 2], [5, 55, 44, 33, 22, 2]]
    )


@pytest.fixture()
def graph_with_loop_at_the_end():
    g = nx.MultiDiGraph()
    g.add_edges_from([(0, 1), (1, 0), (1, 2), (2, 1), (2, 3), (3, 4), (4, 4)])
    return g


def test_getting_endpoints_with_graph_with_loop_at_the_end(graph_with_loop_at_the_end):
    g = graph_with_loop_at_the_end
    endpts = simplification._is_endpoint(
        {
            node: {"successors": set(g.successors(node)), "predecessors": set(g.predecessors(node))}
            for node in g.nodes
        }
    )
    assert set(endpts) == {0, 2, 4}


def test_simplified_paths_with_graph_with_loop_at_the_end(
    assert_correct_edge_groups, graph_with_loop_at_the_end
):
    g = graph_with_loop_at_the_end
    edge_groups = simplification._get_edge_groups_to_simplify(g)
    assert_correct_edge_groups(edge_groups, [[2, 1, 0], [0, 1, 2], [2, 3, 4]])


@pytest.fixture()
def indexed_edge_groups():
    return {
        "new_link_id": {
            "path": [1, 2, 3, 4],
            "link_data": {
                "permlanes": [3.0, 3.0, 5.0],
                "freespeed": [20, 20, 40],
                "capacity": [1000.0, 1000.0, 2000.0],
                "oneway": ["1", "1", "1"],
                "modes": [["car"], ["car"], ["car"]],
                "from": [1, 2, 3],
                "to": [2, 3, 4],
                "id": ["1926", "1927", "1928"],
                "s2_from": [5221390326122671999, 5221390326036762795],
                "s2_to": [5221390326036762795, 5221390326952602895],
                "length": [12.0, 14.0, 5.0],
                "attributes": [
                    {"osm:way:lanes": "3", "osm:way:osmid": "18769878", "osm:way:highway": "trunk"},
                    {
                        "osm:way:lanes": "3",
                        "osm:way:osmid": "18769879",
                        "osm:way:highway": "unclassified",
                    },
                ],
            },
            "node_data": {
                1: {
                    "id": 1,
                    "x": 528915.9309752393,
                    "y": 181899.48948011652,
                    "lon": -0.14327038749428384,
                    "lat": 51.52130909540579,
                    "s2_id": 5221390326122671999,
                },
                2: {
                    "id": 2,
                    "x": 528888.1581643537,
                    "y": 181892.3086225874,
                    "lon": -0.14367308749449406,
                    "lat": 51.52125089540575,
                    "s2_id": 5221390326036762795,
                },
                3: {
                    "id": 3,
                    "x": 528780.3405144282,
                    "y": 181859.84184561518,
                    "lon": -0.14523808749533396,
                    "lat": 51.520983695405526,
                    "s2_id": 5221390326952602895,
                },
                4: {
                    "id": 3,
                    "x": 528780.3405144282,
                    "y": 181859.84184561518,
                    "lon": -0.14523808749533396,
                    "lat": 51.520983695405526,
                    "s2_id": 5221390326952602895,
                },
            },
        }
    }


def test_merging_edge_data(assert_semantically_equal, indexed_edge_groups):
    links_to_add = simplification._process_path(indexed_edge_groups)

    assert_semantically_equal(
        links_to_add,
        {
            "new_link_id": {
                "permlanes": 3,
                "freespeed": 40.0,
                "capacity": 1000.0,
                "oneway": "1",
                "modes": {"car"},
                "from": 1,
                "to": 4,
                "id": "new_link_id",
                "s2_from": 5221390326122671999,
                "s2_to": 5221390326952602895,
                "length": 31,
                "attributes": {
                    "osm:way:lanes": "3",
                    "osm:way:osmid": {"18769878", "18769879"},
                    "osm:way:highway": {"trunk", "unclassified"},
                },
                "geometry": LineString(
                    [
                        (528915.9309752393, 181899.48948011652),
                        (528888.1581643537, 181892.3086225874),
                        (528780.3405144282, 181859.84184561518),
                        (528780.3405144282, 181859.84184561518),
                    ]
                ),
                "ids": ["1926", "1927", "1928"],
            }
        },
    )


def test_merging_edge_data_without_attributes(assert_semantically_equal):
    links_to_add = simplification._process_path(
        {
            "new_link_id": {
                "path": [
                    "5219839471651578159",
                    "5219840163616449177",
                    "5219840164134345369",
                    "5219840193105047721",
                    "5219840192721593713",
                    "5219840201713556083",
                ],
                "link_data": {
                    "id": [
                        "5219839471651578159_5219840163616449177",
                        "5219840163616449177_5219840164134345369",
                        "5219840164134345369_5219840193105047721",
                        "5219840193105047721_5219840192721593713",
                        "5219840192721593713_5219840201713556083",
                    ],
                    "from": [
                        "5219839471651578159",
                        "5219840163616449177",
                        "5219840164134345369",
                        "5219840193105047721",
                        "5219840192721593713",
                    ],
                    "to": [
                        "5219840163616449177",
                        "5219840164134345369",
                        "5219840193105047721",
                        "5219840192721593713",
                        "5219840201713556083",
                    ],
                    "freespeed": [16.68, 16.68, 16.68, 16.68, 16.68],
                    "capacity": [1000.0, 1000.0, 1000.0, 1000.0, 1000.0],
                    "permlanes": [1.0, 1.0, 1.0, 1.0, 1.0],
                    "oneway": ["1", "1", "1", "1", "1"],
                    "modes": [
                        ["pt", "bus"],
                        ["pt", "bus"],
                        ["pt", "bus"],
                        ["pt", "bus"],
                        ["pt", "bus"],
                    ],
                    "s2_from": [
                        5219839471651578159,
                        5219840163616449177,
                        5219840164134345369,
                        5219840193105047721,
                        5219840192721593713,
                    ],
                    "s2_to": [
                        5219840163616449177,
                        5219840164134345369,
                        5219840193105047721,
                        5219840192721593713,
                        5219840201713556083,
                    ],
                    "length": [
                        575.4392557548131,
                        83.15169892493816,
                        489.30505992573757,
                        144.83445362807095,
                        281.97884051508083,
                    ],
                },
                "node_data": {
                    "5219839471651578159": {
                        "id": 1,
                        "x": 528915.9309752393,
                        "y": 181899.48948011652,
                        "lon": -0.14327038749428384,
                        "lat": 51.52130909540579,
                        "s2_id": 5219839471651578159,
                    },
                    "5219840163616449177": {
                        "id": 1,
                        "x": 528915.9309752393,
                        "y": 181899.48948011652,
                        "lon": -0.14327038749428384,
                        "lat": 51.52130909540579,
                        "s2_id": 5219840163616449177,
                    },
                    "5219840164134345369": {
                        "id": 1,
                        "x": 528915.9309752393,
                        "y": 181899.48948011652,
                        "lon": -0.14327038749428384,
                        "lat": 51.52130909540579,
                        "s2_id": 5219840164134345369,
                    },
                    "5219840193105047721": {
                        "id": 1,
                        "x": 528915.9309752393,
                        "y": 181899.48948011652,
                        "lon": -0.14327038749428384,
                        "lat": 51.52130909540579,
                        "s2_id": 5219840193105047721,
                    },
                    "5219840192721593713": {
                        "id": 1,
                        "x": 528915.9309752393,
                        "y": 181899.48948011652,
                        "lon": -0.14327038749428384,
                        "lat": 51.52130909540579,
                        "s2_id": 5219840192721593713,
                    },
                    "5219840201713556083": {
                        "id": 1,
                        "x": 528915.9309752393,
                        "y": 181899.48948011652,
                        "lon": -0.14327038749428384,
                        "lat": 51.52130909540579,
                        "s2_id": 5219840201713556083,
                    },
                },
            }
        }
    )

    assert_semantically_equal(
        links_to_add,
        {
            "new_link_id": {
                "id": "new_link_id",
                "from": "5219839471651578159",
                "to": "5219840201713556083",
                "freespeed": 16.68,
                "capacity": 1000,
                "permlanes": 1,
                "oneway": "1",
                "modes": {"pt", "bus"},
                "s2_from": 5219839471651578159,
                "s2_to": 5219840201713556083,
                "length": 1574.7093087486405,
                "geometry": LineString(
                    [
                        (528915.9309752393, 181899.48948011652),
                        (528915.9309752393, 181899.48948011652),
                        (528915.9309752393, 181899.48948011652),
                        (528915.9309752393, 181899.48948011652),
                        (528915.9309752393, 181899.48948011652),
                        (528915.9309752393, 181899.48948011652),
                    ]
                ),
                "ids": [
                    "5219839471651578159_5219840163616449177",
                    "5219840163616449177_5219840164134345369",
                    "5219840164134345369_5219840193105047721",
                    "5219840193105047721_5219840192721593713",
                    "5219840192721593713_5219840201713556083",
                ],
            }
        },
    )


def test_merging_set_attribute_values(assert_semantically_equal):
    edge_group = {
        "new_link_id": {
            "path": [1, 2, 3],
            "link_data": {
                "permlanes": [3.0, 3.0],
                "freespeed": [20, 20],
                "capacity": [1000.0, 1000.0],
                "oneway": ["1", "1"],
                "modes": [["car"], ["car"]],
                "from": [1, 2],
                "to": [2, 3],
                "id": ["1926", "1927"],
                "s2_from": [5221390326122671999, 5221390326036762795],
                "s2_to": [5221390326036762795, 5221390326952602895],
                "length": [12.0, 14.0],
                "attributes": [{"osm:way:lanes": {"1", "2"}}, {"osm:way:lanes": "3"}],
            },
            "node_data": {
                1: {
                    "id": 1,
                    "x": 528915.9309752393,
                    "y": 181899.48948011652,
                    "lon": -0.14327038749428384,
                    "lat": 51.52130909540579,
                    "s2_id": 5221390326122671999,
                },
                2: {
                    "id": 2,
                    "x": 528888.1581643537,
                    "y": 181892.3086225874,
                    "lon": -0.14367308749449406,
                    "lat": 51.52125089540575,
                    "s2_id": 5221390326036762795,
                },
                3: {
                    "id": 3,
                    "x": 528780.3405144282,
                    "y": 181859.84184561518,
                    "lon": -0.14523808749533396,
                    "lat": 51.520983695405526,
                    "s2_id": 5221390326952602895,
                },
            },
        }
    }
    links_to_add = simplification._process_path(edge_group)

    assert_semantically_equal(
        links_to_add,
        {
            "new_link_id": {
                "permlanes": 3,
                "freespeed": 20.0,
                "capacity": 1000.0,
                "oneway": "1",
                "modes": {"car"},
                "from": 1,
                "to": 3,
                "id": "new_link_id",
                "s2_from": 5221390326122671999,
                "s2_to": 5221390326952602895,
                "length": 26,
                "attributes": {"osm:way:lanes": {"1", "2", "3"}},
                "geometry": LineString(
                    [
                        (528915.9309752393, 181899.48948011652),
                        (528888.1581643537, 181892.3086225874),
                        (528780.3405144282, 181859.84184561518),
                    ]
                ),
                "ids": ["1926", "1927"],
            }
        },
    )


def test_building_paths():
    path_start_points = {(1, 2), (1, 22)}
    endpoints = {1, 4}
    neighbours = {1: {2, 22}, 2: {3}, 3: {4}, 4: {}, 22: {33}, 33: {44}, 44: {4}}
    paths = simplification._build_paths(path_start_points, endpoints, neighbours)
    assert paths == [[1, 2, 3, 4], [1, 22, 33, 44, 4]]


def test_building_path_for_link_that_is_already_simple_enough():
    # i.e. the from and to nodes are both endpoints
    path_start_points = {(1, 2)}
    endpoints = {1, 2}
    neighbours = {1: {2}, 2: {}}
    paths = simplification._build_paths(path_start_points, endpoints, neighbours)
    assert paths == []


def test_building_path_for_loop():
    path_start_points = {(1, 2)}
    endpoints = {1}
    neighbours = {1: {2}, 2: {3}, 3: {4}, 4: {1}}
    paths = simplification._build_paths(path_start_points, endpoints, neighbours)
    assert paths == [[1, 2, 3, 4, 1]]


def test_building_path_for_bidirected_links():
    path_start_points = {(1, 2), (4, 3)}
    endpoints = {1, 4}
    neighbours = {1: {2}, 2: {3, 1}, 3: {2, 4}, 4: {3}}
    paths = simplification._build_paths(path_start_points, endpoints, neighbours)
    assert paths == [[1, 2, 3, 4], [4, 3, 2, 1]]


def test_building_path_throws_error_when_there_is_undetected_branching():
    # i.e. shouldnt happen as the condition automatically makes anything with more than two neighbours an endpoint but..
    path_start_points = {(1, 2)}
    endpoints = {1}
    neighbours = {1: {2}, 2: {3, 1}, 3: {2, 4, 11}, 4: {3}}
    with pytest.raises(RuntimeError) as error_info:
        simplification._build_paths(path_start_points, endpoints, neighbours)
    assert "branching" in str(error_info.value)
