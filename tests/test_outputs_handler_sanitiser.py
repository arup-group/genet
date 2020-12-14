import os
from genet.outputs_handler import sanitiser
from genet.outputs_handler import geojson as gngeojson
from genet import Network
from tests.fixtures import assert_semantically_equal


def test_sanitising_list():
    sanitised = sanitiser.sanitise_list(['1', '2', 3])
    assert sanitised == '1,2,3'


def test_sanitising_set():
    sanitised = sanitiser.sanitise_list({3})
    assert sanitised == '3'


def test_sanitising_geodataframes_with_ids_list(tmpdir):
    n = Network('epsg:27700')
    n.add_node('0', attribs={'x': 528704.1425925883, 'y': 182068.78193707118})
    n.add_node('1', attribs={'x': 528804.1425925883, 'y': 182168.78193707118})
    n.add_link('link_0', '0', '1', attribs={'length': 123, 'modes': ['car', 'walk'], 'ids': ['1', '2']})

    correct_nodes = {
        'x': {'0': 528704.1425925883, '1': 528804.1425925883},
        'y': {'0': 182068.78193707118, '1': 182168.78193707118}}
    correct_links = {'length': {0: 123}, 'modes': {0: 'car,walk'}, 'from': {0: '0'}, 'to': {0: '1'},
                     'id': {0: 'link_0'}, 'ids': {0: '1,2'}, 'u': {0: '0'}, 'v': {0: '1'}, 'key': {0: 0}}

    nodes, links = gngeojson.generate_geodataframes(n.graph)
    nodes = sanitiser.sanitise_geodataframe(nodes)
    links = sanitiser.sanitise_geodataframe(links)

    assert_semantically_equal(nodes[['x', 'y']].to_dict(), correct_nodes)
    assert_semantically_equal(links[['length', 'from', 'to', 'id', 'ids', 'u', 'v', 'key', 'modes']].to_dict(),
                              correct_links)



