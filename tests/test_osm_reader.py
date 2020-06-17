import os
import sys
from genet.inputs_handler import osm_reader
from tests.fixtures import assert_semantically_equal, full_fat_default_config

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
osm_test_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "osm", "osm.xml"))

config = osm_reader.Config(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "configs",
                                                        "default_config.yml")))


def test_generate_osm_graph_edges_from_file(full_fat_default_config):
    nodes, edges = osm_reader.generate_osm_graph_edges_from_file(osm_test_file, full_fat_default_config, 1)

    assert_semantically_equal(nodes, {
        0: {'osmid': 0, 's2id': 1152921492875543713, 'x': -0.0006545205888310243, 'y': 0.008554364250688652},
        1: {'osmid': 1, 's2id': 1152921335974974453, 'x': -0.0006545205888310243, 'y': 0.024278505899735615},
        2: {'osmid': 2, 's2id': 384307157539499829, 'x': -0.0006545205888310243, 'y': -0.00716977739835831}})

    assert len(edges) == 8
    correct_edge_data = {
        0: {'osmid': 0, 'modes': ['walk', 'car', 'bike'], 'highway': 'unclassified', 'length': 1748.4487354464366},
        1: {'osmid': 0, 'modes': ['walk', 'car', 'bike'], 'highway': 'unclassified', 'length': 1748.4487354464366},
        2: {'osmid': 100, 'modes': ['walk', 'car', 'bike'], 'highway': 'unclassified', 'length': 1748.4488584600201},
        3: {'osmid': 100, 'modes': ['walk', 'car', 'bike'], 'highway': 'unclassified', 'length': 1748.4488584600201},
        4: {'osmid': 400, 'modes': ['walk', 'car', 'bike'], 'highway': 'unclassified', 'length': 1748.4487354464366},
        5: {'osmid': 400, 'modes': ['walk', 'car', 'bike'], 'highway': 'unclassified', 'length': 1748.4487354464366},
        6: {'osmid': 700, 'modes': ['walk', 'car', 'bike'], 'highway': 'unclassified', 'length': 1748.4488584600201},
        7: {'osmid': 700, 'modes': ['walk', 'car', 'bike'], 'highway': 'unclassified', 'length': 1748.4488584600201}}
    correct_edges = {0: (0, 1), 1: (1, 0), 2: (0, 2), 3: (2, 0), 4: (1, 0), 5: (0, 1), 6: (2, 0), 7: (0, 2)}

    i = 0
    for edge, attribs in edges:
        assert edge == correct_edges[i]
        assert_semantically_equal(attribs, correct_edge_data[i])
        i += 1