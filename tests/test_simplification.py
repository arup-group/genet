import genet.inputs_handler.osmnx_customised as oxcustom
import pytest
import networkx as nx


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
    paths = oxcustom._get_paths_to_simplify(g)
    assert set(paths) == {[2, 3, 4, 5], [2, 22, 33, 44, 55, 5]}
