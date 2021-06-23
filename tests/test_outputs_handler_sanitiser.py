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
    n.add_node('0', attribs={'x': 528704.1425925883, 'y': 182068.78193707118, 's2_id': 7860190995130875979})
    n.add_node('1', attribs={'x': 528804.1425925883, 'y': 182168.78193707118, 's2_id': 12118290696817869383})
    n.add_link('link_0', '0', '1', attribs={'length': 123, 'modes': ['car', 'walk'], 'ids': ['1', '2']})

    correct_nodes = {
        'x': {'0': 528704.1425925883, '1': 528804.1425925883},
        'y': {'0': 182068.78193707118, '1': 182168.78193707118},
        's2_id': {'0': '7860190995130875979', '1': '12118290696817869383'}}
    correct_links = {'length': {'link_0': 123}, 'from': {'link_0': '0'}, 'to': {'link_0': '1'},
                     'id': {'link_0': 'link_0'}, 'ids': {'link_0': '1,2'}, 'u': {'link_0': '0'}, 'v': {'link_0': '1'},
                     'modes': {'link_0': 'car,walk'}}

    gdfs = gngeojson.generate_geodataframes(n.graph)
    nodes, links = gdfs['nodes'], gdfs['links']
    nodes = sanitiser.sanitise_geodataframe(nodes)
    links = sanitiser.sanitise_geodataframe(links)

    assert_semantically_equal(nodes[['x', 'y', 's2_id']].to_dict(), correct_nodes)
    assert_semantically_equal(links[['length', 'from', 'to', 'id', 'ids', 'u', 'v', 'modes']].to_dict(),
                              correct_links)
