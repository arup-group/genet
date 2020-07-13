import os
from genet.outputs_handler import geojson
from genet.core import Network
from tests.fixtures import assert_semantically_equal


def test_save_to_geojson(tmpdir):
    n = Network('epsg:27700')
    n.add_node('0', attribs={'x': 528704.1425925883, 'y': 182068.78193707118})
    n.add_node('1', attribs={'x': 528804.1425925883, 'y': 182168.78193707118})
    n.add_link('link_0', '0', '1', attribs={'length': 123, 'modes': ['car', 'walk']})

    correct_nodes = {
        'x': {'0': 528704.1425925883, '1': 528804.1425925883},
        'y': {'0': 182068.78193707118, '1': 182168.78193707118}}
    correct_links = {'length': {0: 123}, 'modes': {0: 'car,walk'}, 'from': {0: '0'}, 'to': {0: '1'},
                     'id': {0: 'link_0'}, 'u': {0: '0'}, 'v': {0: '1'}, 'key': {0: 0}}

    assert os.listdir(tmpdir) == []
    nodes, links = geojson.save_nodes_and_links_geojson(n.graph, tmpdir)

    assert_semantically_equal(nodes[['x', 'y']].to_dict(), correct_nodes)
    assert_semantically_equal(links[['length', 'from', 'to', 'id', 'u', 'v', 'key', 'modes']].to_dict(), correct_links)

    assert_semantically_equal({'0': nodes.loc['0', 'geometry'].coords[:], '1': nodes.loc['1', 'geometry'].coords[:]},
                              {'0': [(-0.14625948709424305, 51.52287873323954)],
                               '1': [(-0.14478238148334213, 51.523754629002234)]})
    assert_semantically_equal({0: links.loc[0, 'geometry'].coords[:]}, {0:[(-0.14625948709424305, 51.52287873323954),
                                                  (-0.14478238148334213, 51.523754629002234)]})

    assert nodes.crs == "EPSG:4326"
    assert links.crs == "EPSG:4326"

    assert_semantically_equal(os.listdir(tmpdir), ['nodes.geojson', 'links.geojson'])
