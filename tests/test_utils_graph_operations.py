from genet.core import Network
from genet.utils import graph_operations
from anytree import Node, RenderTree
from tests.fixtures import assert_semantically_equal
import logging


def generate_output_tree(root):
    output_tree = []
    for pre, fill, node in RenderTree(root):
        if node.parent is not None:
            if hasattr(node, 'values'):
                output_tree.append((node.depth, node.parent.name, node.name, node.values))
            else:
                output_tree.append((node.depth, node.parent.name, node.name))
        else:
            if hasattr(node, 'values'):
                output_tree.append((node.depth, None, node.name, node.values))
            else:
                output_tree.append((node.depth, None, node.name))
    return output_tree


def test_extract_graph_links_with_flat_condition():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_link('1', 2, 3, attribs={
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_link('2', 3, 4, attribs={'attributes': 'yes'})

    links = graph_operations.extract_links_on_edge_attributes(
        n,
        conditions={'attributes': 'yes'},
    )

    assert links == ['2']


def test_extract_graph_links_with_nested_condition():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_link('1', 2, 3, attribs={
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})

    links = graph_operations.extract_links_on_edge_attributes(
        n,
        conditions={'attributes': {'osm:way:highway': {'text': 'primary'}}},
    )

    assert links == ['0', '1']


def test_extract_graph_links_with_list_of_conditions():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_link('1', 2, 3, attribs={
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_link('2', 3, 4, attribs={'attributes': 'yes'})

    links = graph_operations.extract_links_on_edge_attributes(
        n,
        conditions=[{'attributes': {'osm:way:highway': {'text': 'primary'}}},
                    {'attributes': 'yes'}],
        how=any
    )

    assert links == ['0', '1', '2']


def test_extract_graph_links_with_list_of_conditions_strict():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'attributes': {
        'osm:way:highway': {'name': 'osm:way:highway:to:hell', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_link('1', 2, 3, attribs={
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_link('2', 3, 4, attribs={'attributes': 'yes'})

    links = graph_operations.extract_links_on_edge_attributes(
        n,
        conditions=[{'attributes': {'osm:way:highway': {'text': 'primary'}}},
                    {'attributes': {'osm:way:highway': {'name': 'osm:way:highway'}}}],
        how=all
    )

    assert links == ['1']


def test_extract_graph_links_with_list_condition_with():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_link('1', 2, 3, attribs={
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_link('2', 3, 4, attribs={'attributes': 'yes'})

    links = graph_operations.extract_links_on_edge_attributes(
        n,
        conditions={'attributes': {'osm:way:highway': {'text': ['primary', 'some_other_highway']}}}
    )

    assert links == ['0', '1']


def test_extract_graph_links_with_bound_condition():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 9}}})
    n.add_link('1', 2, 3, attribs={
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 1}}})
    n.add_link('2', 3, 4, attribs={'attributes': 'yes'})

    links = graph_operations.extract_links_on_edge_attributes(
        n,
        conditions={'attributes': {'osm:way:highway': {'text': (2, 10)}}}
    )

    assert links == ['0']


def test_extract_graph_links_with_callable_condition():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 9}}})
    n.add_link('1', 2, 3, attribs={
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 1}}})
    n.add_link('2', 3, 4, attribs={'attributes': 'yes'})

    def condition(val):
        return val == 9

    links = graph_operations.extract_links_on_edge_attributes(
        n,
        conditions={'attributes': {'osm:way:highway': {'text': condition}}}
    )

    assert links == ['0']


def test_extract_graph_nodes_with_flat_condition():
    n = Network('epsg:27700')
    n.add_node(1, {
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_node(2, {
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_node(3, {'attributes': 'yes'})

    nodes = graph_operations.extract_nodes_on_node_attributes(
        n,
        conditions={'attributes': 'yes'},
    )

    assert nodes == [3]


def test_extract_graph_nodes_with_nested_condition():
    n = Network('epsg:27700')
    n.add_node(1, {
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_node(2, {
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})

    nodes = graph_operations.extract_nodes_on_node_attributes(
        n,
        conditions={'attributes': {'osm:way:highway': {'text': 'primary'}}},
    )

    assert nodes == [1, 2]


def test_extract_graph_nodes_with_list_of_conditions():
    n = Network('epsg:27700')
    n.add_node(1, {
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_node(2, {
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_node(3, {'attributes': 'yes'})

    nodes = graph_operations.extract_nodes_on_node_attributes(
        n,
        conditions=[{'attributes': {'osm:way:highway': {'text': 'primary'}}},
                    {'attributes': 'yes'}],
        how=any
    )

    assert nodes == [1, 2, 3]


def test_extract_graph_nodes_with_list_of_conditions_strict():
    n = Network('epsg:27700')
    n.add_node(1, {'attributes': {
        'osm:way:highway': {'name': 'osm:way:highway:to:hell', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_node(2, {
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_node(3, {'attributes': 'yes'})

    nodes = graph_operations.extract_nodes_on_node_attributes(
        n,
        conditions=[{'attributes': {'osm:way:highway': {'text': 'primary'}}},
                    {'attributes': {'osm:way:highway': {'name': 'osm:way:highway'}}}],
        how=all
    )

    assert nodes == [2]


def test_extract_graph_nodes_with_list_condition_with():
    n = Network('epsg:27700')
    n.add_node(1, {
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_node(2, {
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_node(3, {'attributes': 'yes'})

    nodes = graph_operations.extract_nodes_on_node_attributes(
        n,
        conditions={'attributes': {'osm:way:highway': {'text': ['primary', 'some_other_highway']}}}
    )

    assert nodes == [1, 2]


def test_extract_graph_nodes_with_bound_condition():
    n = Network('epsg:27700')
    n.add_node(1,
               {'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 9}}})
    n.add_node(2,
               {'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 1}}})
    n.add_node(3, {'attributes': 'yes'})

    nodes = graph_operations.extract_nodes_on_node_attributes(
        n,
        conditions={'attributes': {'osm:way:highway': {'text': (2, 10)}}}
    )

    assert nodes == [1]


def test_extract_graph_nodes_with_callable_condition():
    n = Network('epsg:27700')
    n.add_node(1,
               {'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 9}}})
    n.add_node(2,
               {'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 1}}})
    n.add_node(3, {'attributes': 'yes'})

    def condition(val):
        return val == 9

    nodes = graph_operations.extract_nodes_on_node_attributes(
        n,
        conditions={'attributes': {'osm:way:highway': {'text': condition}}}
    )

    assert nodes == [1]


def test_get_attribute_schema_with_nested_dictionaries():
    input_list = [
        ('0', {'attributes': {'osm:way:highway': {'name': 'osm:way:highway',
                                                  'class': 'java.lang.String',
                                                  'text': 'primary'}}}),
        ('1', {'attributes': {'osm:way:id': {'name': 'osm:way:id',
                                             'class': 'java.lang.String',
                                             'text': '1234'}}})
    ]

    root = graph_operations.get_attribute_schema(input_list)

    output_tree = generate_output_tree(root)

    assert output_tree == [(0, None, 'attribute'),
                           (1, 'attribute', 'attributes'),
                           (2, 'attributes', 'osm:way:highway'),
                           (3, 'osm:way:highway', 'name'),
                           (3, 'osm:way:highway', 'class'),
                           (3, 'osm:way:highway', 'text'),
                           (2, 'attributes', 'osm:way:id'),
                           (3, 'osm:way:id', 'name'),
                           (3, 'osm:way:id', 'class'),
                           (3, 'osm:way:id', 'text')]


def test_get_attribute_schema_with_different_in_a_nested_dictionary_with_same_keys():
    input_list = [
        ('0', {'attributes': {'osm:way:highway': {'name': 'osm:way:highway',
                                                  'class': 'java.lang.String',
                                                  'text': 'primary'}}}),
        ('1', {'attributes': {'osm:way:highway': {'name': 'osm:way:highway',
                                                  'class': 'java.lang.String',
                                                  'text': 'secondary'}}})
    ]

    root = graph_operations.get_attribute_schema(input_list, data=True)

    output_tree = generate_output_tree(root)

    assert output_tree == [(0, None, 'attribute'),
                           (1, 'attribute', 'attributes'),
                           (2, 'attributes', 'osm:way:highway'),
                           (3, 'osm:way:highway', 'name', {'osm:way:highway'}),
                           (3, 'osm:way:highway', 'class', {'java.lang.String'}),
                           (3, 'osm:way:highway', 'text', {'primary', 'secondary'})]


def test_get_attribute_schema_merges_lists():
    input_list = [
        ('0', {'modes': ['car']}),
        ('1', {'modes': ['walk', 'bike']})
    ]

    root = graph_operations.get_attribute_schema(input_list, data=True)

    output_tree = generate_output_tree(root)

    assert output_tree == [(0, None, 'attribute'), (1, 'attribute', 'modes', {'bike', 'car', 'walk'})]


def test_get_attribute_data_under_key_with_non_nested_key():
    input_list = [
        ('0', {'attributes': {'osm:way:highway': {'name': 'osm:way:highway',
                                                  'class': 'java.lang.String',
                                                  'text': 'primary'}}}),
        ('1', {'attributes': {'osm:way:highway': {'name': 'osm:way:highway',
                                                  'class': 'java.lang.String',
                                                  'text': 'secondary'}}}),
        ('2', {'modes': ['car', 'walk']})
    ]

    data = graph_operations.get_attribute_data_under_key(input_list, 'modes')
    assert_semantically_equal(data, {'2': ['walk', 'car']})


def test_get_attribute_data_under_key_with_nested_link_data_and_nested_key():
    input_list = [
        ('0', {'attributes': {'osm:way:highway': {'name': 'osm:way:highway',
                                                  'class': 'java.lang.String',
                                                  'text': 'primary'}}}),
        ('1', {'attributes': {'osm:way:highway': {'name': 'osm:way:highway',
                                                  'class': 'java.lang.String',
                                                  'text': 'secondary'}}})
    ]

    data = graph_operations.get_attribute_data_under_key(input_list, {'attributes': {'osm:way:highway': 'text'}})
    assert_semantically_equal(data, {'0': 'primary', '1': 'secondary'})


def test_consolidating_node_ids_does_nothing_to_matching_nodes_in_matching_coordinate_system():
    n_left = Network('epsg:27700')
    n_left.epsg = 'epsg:27700'
    n_left.add_node('101982', {'id': '101982', 'x': '528704.1425925883', 'y': '182068.78193707118',
                               'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879})
    n_right = Network('epsg:27700')
    n_right.epsg = 'epsg:27700'
    n_right.add_node('101982', {'id': '101982', 'x': '528704.1425925883', 'y': '182068.78193707118',
                                'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879})

    output_n_right = graph_operations.consolidate_node_indices(n_left, n_right)
    assert output_n_right.graph.has_node('101982')
    assert output_n_right.node('101982') == {'id': '101982', 'x': '528704.1425925883', 'y': '182068.78193707118',
                                             'lon': -0.14625948709424305, 'lat': 51.52287873323954,
                                             's2_id': 5221390329378179879}


def test_consolidating_node_ids_updates_nodes_data_for_overlapping_nodes_of_different_coordinate_system():
    n_left = Network('epsg:27700')
    n_left.epsg = 'epsg:27700'
    n_left.add_node('101982', {'id': '101982', 'x': '528704.1434730452', 'y': '182068.78144827875',
                               'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879})
    n_right = Network('epsg:27700')
    n_right.epsg = 'epsg:4326'
    n_right.add_node('101982', {'id': '101982', 'x': 51.52287873323954, 'y': -0.14625948709424305,
                                'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879})
    n_right.reproject('epsg:27700')

    output_n_right = graph_operations.consolidate_node_indices(n_left, n_right)

    assert_semantically_equal(output_n_right.node('101982'),
                              {'id': '101982', 'x': 528704.1434730452, 'y': 182068.78144827875,
                               'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879})


def test_consolidating_node_ids_reprojects_non_overlapping_nodes():
    n_left = Network('epsg:27700')
    n_left.epsg = 'epsg:27700'
    n_left.add_node('101986', {'id': '101986', 'x': '528835.203274008', 'y': '182006.27331298392',
                               'lon': -0.14439428709377497, 'lat': 51.52228713323965, 's2_id': 5221390328605860387})
    n_right = Network('epsg:27700')
    n_right.epsg = 'epsg:4326'
    n_right.add_node('101990', {'id': '101990', 'x': 51.5205729332399, 'y': -0.14770188709624754,
                                'lon': -0.14770188709624754, 'lat': 51.5205729332399, 's2_id': 5221390304444511271})
    n_right.reproject('epsg:27700')

    output_n_right = graph_operations.consolidate_node_indices(n_left, n_right)

    assert_semantically_equal(output_n_right.node('101990'),
                              {'id': '101990', 'x': 528610.5722059759, 'y': 181809.83345613896,
                               'lon': -0.14770188709624754, 'lat': 51.5205729332399,
                               's2_id': 5221390304444511271})


def test_add_reindexes_node_if_clashes_with_spatially_matched_nodes():
    n_left = Network('epsg:27700')
    n_left.epsg = 'epsg:27700'
    n_left.add_node('101982', {'id': '101982', 'x': '528704.1434730452', 'y': '182068.78144827875',
                               'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879})
    n_right = Network('epsg:27700')
    n_right.epsg = 'epsg:4326'
    n_right.add_node('101990', {'id': '101990', 'x': 51.52287873323954, 'y': -0.14625948709424305,
                                'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879})
    n_right.reproject('epsg:27700')

    output_n_right = graph_operations.consolidate_node_indices(n_left, n_right)

    assert output_n_right.graph.has_node('101982')
    assert not output_n_right.graph.has_node('101990')
    assert_semantically_equal(output_n_right.node('101982'),
                              {'id': '101982', 'x': 528704.1434730452, 'y': 182068.78144827875,
                               'lon': -0.14625948709424305, 'lat': 51.52287873323954,
                               's2_id': 5221390329378179879})


def test_add_reindexes_node_if_clashes_with_spatially_unmatched_nodes():
    n_left = Network('epsg:27700')
    n_left.epsg = 'epsg:27700'
    n_left.add_node('101982', {'id': '101982', 'x': '528704.1425925883', 'y': '182068.78193707118',
                               'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879})
    n_right = Network('epsg:27700')
    n_right.epsg = 'epsg:4326'
    n_right.add_node('101982', {'id': '101982', 'x': 51.5205729332399, 'y': -0.14770188709624754,
                                'lon': -0.14770188709624754, 'lat': 51.5205729332399, 's2_id': 5221390304444511271})
    n_right.reproject('epsg:27700')

    output_n_right = graph_operations.consolidate_node_indices(n_left, n_right)

    assert not output_n_right.graph.has_node('101982')
    the_node = [i for i, a in output_n_right.nodes()][0]
    assert_semantically_equal(output_n_right.node(the_node),
                              {'id': the_node, 'x': 528610.5722059759, 'y': 181809.83345613896,
                               'lon': -0.14770188709624754, 'lat': 51.5205729332399,
                               's2_id': 5221390304444511271})


def test_consolidating_link_ids_does_nothing_to_completely_matching_links():
    n_left = Network('epsg:27700')
    n_left.add_link('1', 1, 2, attribs={'modes': ['walk']})
    n_right = Network('epsg:27700')
    n_right.add_link('1', 1, 2, attribs={'modes': ['walk']})

    output_n_right = graph_operations.consolidate_link_indices(n_left, n_right)
    assert output_n_right.graph.has_edge(1, 2, 0)
    assert '1' in output_n_right.link_id_mapping
    assert output_n_right.graph[1][2][0] == {'modes': ['walk'], 'from': 1, 'to': 2, 'id': '1'}


def test_consolidating_link_ids_imposes_link_indexing_from_left_on_overlapping_links():
    n_left = Network('epsg:27700')
    n_left.add_link('100', 1, 2, attribs={'modes': ['walk']})
    n_right = Network('epsg:27700')
    n_right.add_link('1', 1, 2, attribs={'modes': ['walk']})

    output_n_right = graph_operations.consolidate_link_indices(n_left, n_right)
    assert output_n_right.graph.has_edge(1, 2, 0)
    assert '100' in output_n_right.link_id_mapping
    assert output_n_right.graph[1][2][0] == {'modes': ['walk'], 'from': 1, 'to': 2, 'id': '100'}


def test_consolidating_link_ids_imposes_multiindex_on_overlapping_links_matching_link_ids():
    n_left = Network('epsg:27700')
    n_left.add_link('1', 1, 2, 1, attribs={'modes': ['walk']})
    n_right = Network('epsg:27700')
    n_right.add_link('1', 1, 2, 0, attribs={'modes': ['walk']})

    output_n_right = graph_operations.consolidate_link_indices(n_left, n_right)
    assert output_n_right.graph.has_edge(1, 2, 1)
    assert '1' in output_n_right.link_id_mapping
    assert output_n_right.graph[1][2][1] == {'modes': ['walk'], 'from': 1, 'to': 2, 'id': '1'}


def test_consolidating_link_ids_imposes_multiindex_and_link_id_on_overlapping_links_not_matching_link_ids():
    n_left = Network('epsg:27700')
    n_left.add_link('1', 1, 2, 1, attribs={'modes': ['walk']})
    n_right = Network('epsg:27700')
    n_right.add_link('100', 1, 2, 0, attribs={'modes': ['walk']})

    output_n_right = graph_operations.consolidate_link_indices(n_left, n_right)
    assert output_n_right.graph.has_edge(1, 2, 1)
    assert '1' in output_n_right.link_id_mapping
    assert output_n_right.graph[1][2][1] == {'modes': ['walk'], 'from': 1, 'to': 2, 'id': '1'}


def test_consolidating_link_ids_generates_unique_index_for_non_matching_link_with_clashing_link_id():
    n_left = Network('epsg:27700')
    n_left.add_link('1', 1, 2, 1, attribs={'modes': ['walk']})
    n_right = Network('epsg:27700')
    n_right.add_link('1', 10, 20, 0, attribs={'modes': ['bike']})

    output_n_right = graph_operations.consolidate_link_indices(n_left, n_right)
    assert list(output_n_right.graph.edges) == [(10, 20, 0)]
    assert not '1' in output_n_right.link_id_mapping
    assert len(output_n_right.link_id_mapping) == 1
    assert output_n_right.graph[10][20][0]['id'] != '1'


def test_consolidating_link_ids_generates_unique_indices_for_non_overlapping_link_with_clashing_link_id_and_multiindex():
    n_left = Network('epsg:27700')
    n_left.add_link('1', 1, 2, 1, attribs={'modes': ['walk']})
    n_right = Network('epsg:27700')
    n_right.add_link('1', 1, 2, 1, attribs={'modes': ['bike']})

    output_n_right = graph_operations.consolidate_link_indices(n_left, n_right)
    assert list(output_n_right.graph.edges) != [(1, 2, 1)]
    assert not '1' in output_n_right.link_id_mapping
    assert len(output_n_right.link_id_mapping) == 1
    u, v, midx = list(output_n_right.graph.edges)[0]
    assert midx != 1
    assert output_n_right.graph[1][2][midx]['id'] != '1'


def test_consolidating_link_ids_generates_unique_indices_for_non_overlapping_link_with_clashing_multiindex():
    n_left = Network('epsg:27700')
    n_left.add_link('1', 1, 2, 1, attribs={'modes': ['walk']})
    n_right = Network('epsg:27700')
    n_right.add_link('2', 1, 2, 1, attribs={'modes': ['bike']})

    output_n_right = graph_operations.consolidate_link_indices(n_left, n_right)
    assert list(output_n_right.graph.edges) != [(1, 2, 1)]
    assert not '1' in output_n_right.link_id_mapping
    assert len(output_n_right.link_id_mapping) == 1
    u, v, midx = list(output_n_right.graph.edges)[0]
    assert midx != 1


def test_convert_list_of_link_ids_to_network_nodes_with_connected_link_id_list():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={})
    n.add_link('1', 2, 3, attribs={})
    n.add_link('2', 3, 4, attribs={})

    network_nodes = graph_operations.convert_list_of_link_ids_to_network_nodes(n, ['0', '1', '2'])
    assert network_nodes == [[1, 2, 3, 4]]


def test_convert_list_of_link_ids_to_network_nodes_with_disconnected_link_id_list(mocker):
    mocker.patch.object(logging,  'Logger')
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={})
    n.add_link('1', 2, 3, attribs={})
    n.add_link('2', 3, 4, attribs={})

    network_nodes = graph_operations.convert_list_of_link_ids_to_network_nodes(n, ['0', '2'])

    assert network_nodes == [[1, 2], [3, 4]]
