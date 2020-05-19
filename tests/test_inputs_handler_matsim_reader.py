import os
import sys
from pyproj import Proj, Transformer
from genet.inputs_handler import matsim_reader

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
pt2matsim_network_test_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_data", "network.xml"))


def dict_with_lists_are_equal(d1, d2):
    for k, v in d1.items():
        assert k in d2, '{} for {}'.format(KeyError, k)
        if isinstance(v, list):
            assert set(v) == set(d2[k])
        else:
            assert v == d2[k]


def test_read_network_builds_graph_with_correct_data_on_nodes_and_edges():
    nodes = {'5221390302696205321': {"id": "21667818", "x": "528504.1342843144", "y": "182155.7435136598"},
             '5221390301001263407': {"id": "25508485", "x": "528489.467895946", "y": "182206.20303669578"}}

    edges = {'5221390301001263407_5221390302696205321': {
        'id': "1", 'from': "25508485", 'to': "21667818", 'length': 52.765151087870265,
        'freespeed': "4.166666666666667", 'capacity': "600.0", 'permlanes': "1.0", 'oneway': "1",
        'modes': ['subway,metro', 'walk', 'car'], 'attributes': {
            'osm:way:access': {'name': 'osm:way:access', 'class': 'java.lang.String', 'text': 'permissive'},
            'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'unclassified'},
            'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long', 'text': '26997928'},
            'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String', 'text': 'Brunswick Place'}
        }}}

    transformer = Transformer.from_proj(Proj(init='epsg:27700'), Proj(init='epsg:4326'))

    g, node_id_mapping, link_id_mapping = matsim_reader.read_network(pt2matsim_network_test_file, transformer)

    for u, data in g.nodes(data=True):
        assert str(u) in nodes
        assert data == nodes[str(u)]

    for u, v, data in g.edges(data=True):
        edge = '{}_{}'.format(u,v)
        assert edge in edges
        dict_with_lists_are_equal(data, edges[edge])

    print('')
