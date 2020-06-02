from genet.core import Network, Schedule
from genet.utils import graph_operations
from anytree import Node, RenderTree


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
    n = Network()
    n.add_link('0', 1, 2, {
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_link('1', 2, 3, {
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_link('2', 3, 4, {'attributes': 'yes'})

    links = graph_operations.extract_links_on_edge_attributes(
        n,
        conditions={'attributes': 'yes'},
    )

    assert links == ['2']


def test_extract_graph_links_with_nested_condition():
    n = Network()
    n.add_link('0', 1, 2, {
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_link('1', 2, 3, {
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})

    links = graph_operations.extract_links_on_edge_attributes(
        n,
        conditions={'attributes': {'osm:way:highway': {'text': 'primary'}}},
    )

    assert links == ['0', '1']


def test_extract_graph_links_with_list_of_conditions():
    n = Network()
    n.add_link('0', 1, 2, {
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_link('1', 2, 3, {
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_link('2', 3, 4, {'attributes': 'yes'})

    links = graph_operations.extract_links_on_edge_attributes(
        n,
        conditions=[{'attributes': {'osm:way:highway': {'text': 'primary'}}},
                    {'attributes': 'yes'}],
        how='any'
    )

    assert links == ['0', '1', '2']


def test_extract_graph_links_with_list_of_conditions_strict():
    n = Network()
    n.add_link('0', 1, 2, {'attributes': {
        'osm:way:highway': {'name': 'osm:way:highway:to:hell', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_link('1', 2, 3, {
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_link('2', 3, 4, {'attributes': 'yes'})

    links = graph_operations.extract_links_on_edge_attributes(
        n,
        conditions=[{'attributes': {'osm:way:highway': {'text': 'primary'}}},
                    {'attributes': {'osm:way:highway': {'name': 'osm:way:highway'}}}],
        how='all'
    )

    assert links == ['1']


def test_extract_graph_links_with_list_condition_with():
    n = Network()
    n.add_link('0', 1, 2, {
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_link('1', 2, 3, {
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_link('2', 3, 4, {'attributes': 'yes'})

    links = graph_operations.extract_links_on_edge_attributes(
        n,
        conditions={'attributes': {'osm:way:highway': {'text': ['primary', 'some_other_highway']}}}
    )

    assert links == ['0', '1']


def test_extract_graph_links_with_bound_condition():
    n = Network()
    n.add_link('0', 1, 2,
               {'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 9}}})
    n.add_link('1', 2, 3,
               {'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 1}}})
    n.add_link('2', 3, 4, {'attributes': 'yes'})

    links = graph_operations.extract_links_on_edge_attributes(
        n,
        conditions={'attributes': {'osm:way:highway': {'text': (2, 10)}}}
    )

    assert links == ['0']


def test_extract_graph_links_with_callable_condition():
    n = Network()
    n.add_link('0', 1, 2,
               {'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 9}}})
    n.add_link('1', 2, 3,
               {'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 1}}})
    n.add_link('2', 3, 4, {'attributes': 'yes'})

    def condition(val):
        return val == 9

    links = graph_operations.extract_links_on_edge_attributes(
        n,
        conditions={'attributes': {'osm:way:highway': {'text': condition}}}
    )

    assert links == ['0']


def test_extract_graph_nodes_with_flat_condition():
    n = Network()
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
    n = Network()
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
    n = Network()
    n.add_node(1, {
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_node(2, {
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_node(3, {'attributes': 'yes'})

    nodes = graph_operations.extract_nodes_on_node_attributes(
        n,
        conditions=[{'attributes': {'osm:way:highway': {'text': 'primary'}}},
                    {'attributes': 'yes'}],
        how='any'
    )

    assert nodes == [1, 2, 3]


def test_extract_graph_nodes_with_list_of_conditions_strict():
    n = Network()
    n.add_node(1, {'attributes': {
        'osm:way:highway': {'name': 'osm:way:highway:to:hell', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_node(2, {
        'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_node(3, {'attributes': 'yes'})

    nodes = graph_operations.extract_nodes_on_node_attributes(
        n,
        conditions=[{'attributes': {'osm:way:highway': {'text': 'primary'}}},
                    {'attributes': {'osm:way:highway': {'name': 'osm:way:highway'}}}],
        how='all'
    )

    assert nodes == [2]


def test_extract_graph_nodes_with_list_condition_with():
    n = Network()
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
    n = Network()
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
    n = Network()
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

