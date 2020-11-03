import os
import pytest
from genet.outputs_handler import geojson
from genet.core import Network
from tests.fixtures import assert_semantically_equal


@pytest.fixture()
def network():
    n = Network('epsg:27700')
    n.add_node('0', attribs={'x': 528704.1425925883, 'y': 182068.78193707118})
    n.add_node('1', attribs={'x': 528804.1425925883, 'y': 182168.78193707118})
    n.add_link('link_0', '0', '1', attribs={'length': 123, 'modes': ['car', 'walk'], 'freespeed': 10, 'capacity': 5})
    n.add_link('link_1', '0', '1', attribs={'length': 123, 'modes': ['bike']})
    n.add_link('link_2', '1', '0', attribs={'length': 123, 'modes': ['rail']})
    return n


def test_generating_geodataframe(network):
    nodes, links = geojson.generate_geodataframes(network.graph)
    correct_nodes = {
        'x': {'0': 528704.1425925883, '1': 528804.1425925883},
        'y': {'0': 182068.78193707118, '1': 182168.78193707118}}
    correct_links = {'length': {0: 123, 1: 123, 2: 123},
                     'modes': {0: ['car', 'walk'], 1: ['bike'], 2: ['rail']},
                     'from': {0: '0', 1: '0', 2: '1'},
                     'to': {0: '1', 1: '1', 2: '0'},
                     'id': {0: 'link_0', 1: 'link_1', 2: 'link_2'},
                     'u': {0: '0', 1: '0', 2: '1'},
                     'v': {0: '1', 1: '1', 2: '0'},
                     'key': {0: 0, 1: 1, 2: 0}}

    assert_semantically_equal(nodes[['x', 'y']].to_dict(), correct_nodes)
    assert_semantically_equal(links[['length', 'from', 'to', 'id', 'u', 'v', 'key', 'modes']].to_dict(), correct_links)

    assert round(nodes.loc['0', 'geometry'].coords[:][0][0], 7) == round(-0.14625948709424305, 7)
    assert round(nodes.loc['0', 'geometry'].coords[:][0][1], 7) == round(51.52287873323954, 7)
    assert round(nodes.loc['1', 'geometry'].coords[:][0][0], 7) == round(-0.14478238148334213, 7)
    assert round(nodes.loc['1', 'geometry'].coords[:][0][1], 7) == round(51.523754629002234, 7)

    points = links.loc[0, 'geometry'].coords[:]
    assert round(points[0][0], 7) == round(-0.14625948709424305, 7)
    assert round(points[0][1], 7) == round(51.52287873323954, 7)
    assert round(points[1][0], 7) == round(-0.14478238148334213, 7)
    assert round(points[1][1], 7) == round(51.523754629002234, 7)

    assert nodes.crs == "EPSG:4326"
    assert links.crs == "EPSG:4326"


def test_modal_subset(network):
    nodes, links = geojson.generate_geodataframes(network.graph)
    car = links[links.apply(lambda x: geojson.modal_subset(x, {'car'}), axis=1)]

    assert len(car) == 1
    assert car.loc[0, 'modes'] == ['car', 'walk']


def test_save_to_geojson(network, tmpdir):
    assert os.listdir(tmpdir) == []
    network.save_network_to_geojson(tmpdir)
    assert set(os.listdir(tmpdir)) == {'nodes.geojson', 'links.geojson', 'links_geometry_only.geojson',
                                       'nodes_geometry_only.geojson'}


def test_generating_standard_outputs(network, tmpdir):
    assert os.listdir(tmpdir) == []
    network.generate_standard_outputs(tmpdir)
    assert set(os.listdir(tmpdir)) == {'car_freespeed_subgraph.geojson',
                                       'car_capacity_subgraph.geojson',
                                       'walk_subgraph_geometry.geojson',
                                       'bike_subgraph_geometry.geojson',
                                       'rail_subgraph_geometry.geojson',
                                       'car_subgraph_geometry.geojson'}