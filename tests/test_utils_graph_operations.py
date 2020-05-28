from genet.core import Network, Schedule
from genet.utils import graph_operations


def test_extract_graph_links_with_flat_condition():
    n = Network()
    n.add_link('0', 1, 2, {'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_link('1', 2, 3, {'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_link('2', 3, 4, {'attributes': 'yes'})

    links = graph_operations.extract_links_on_edge_attributes(
        n,
        conditions={'attributes': 'yes'},
    )

    assert links == ['2']


def test_extract_graph_links_with_nested_condition():
    n = Network()
    n.add_link('0', 1, 2, {'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_link('1', 2, 3, {'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})

    links = graph_operations.extract_links_on_edge_attributes(
        n,
        conditions= {'attributes': {'osm:way:highway': {'text': 'primary'}}},
    )

    assert links == ['0', '1']


def test_extract_graph_links_with_list_of_conditions():
    n = Network()
    n.add_link('0', 1, 2, {'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_link('1', 2, 3, {'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_link('2', 3, 4, {'attributes': 'yes'})

    links = graph_operations.extract_links_on_edge_attributes(
        n,
        conditions= [{'attributes': {'osm:way:highway': {'text': 'primary'}}},
                     {'attributes': 'yes'}],
        how='any'
    )

    assert links == ['0', '1', '2']


def test_extract_graph_links_with_list_of_conditions_strict():
    n = Network()
    n.add_link('0', 1, 2, {'attributes': {'osm:way:highway': {'name': 'osm:way:highway:to:hell', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_link('1', 2, 3, {'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_link('2', 3, 4, {'attributes': 'yes'})

    links = graph_operations.extract_links_on_edge_attributes(
        n,
        conditions= [{'attributes': {'osm:way:highway': {'text': 'primary'}}},
                     {'attributes': {'osm:way:highway': {'name': 'osm:way:highway'}}}],
        how='all'
    )

    assert links == ['1']


def test_extract_graph_links_with_list_condition_with():
    n = Network()
    n.add_link('0', 1, 2, {'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_link('1', 2, 3, {'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'primary'}}})
    n.add_link('2', 3, 4, {'attributes': 'yes'})

    links = graph_operations.extract_links_on_edge_attributes(
        n,
        conditions= {'attributes': {'osm:way:highway': {'text': ['primary', 'some_other_highway']}}}
    )

    assert links == ['0', '1']


def test_extract_graph_links_with_bound_condition():
    n = Network()
    n.add_link('0', 1, 2, {'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 9}}})
    n.add_link('1', 2, 3, {'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 1}}})
    n.add_link('2', 3, 4, {'attributes': 'yes'})

    links = graph_operations.extract_links_on_edge_attributes(
        n,
        conditions= {'attributes': {'osm:way:highway': {'text': (2,10)}}}
    )

    assert links == ['0']


def test_extract_graph_links_with_callable_condition():
    n = Network()
    n.add_link('0', 1, 2, {'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 9}}})
    n.add_link('1', 2, 3, {'attributes': {'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 1}}})
    n.add_link('2', 3, 4, {'attributes': 'yes'})

    def condition(val):
        return val == 9

    links = graph_operations.extract_links_on_edge_attributes(
        n,
        conditions= {'attributes': {'osm:way:highway': {'text': condition}}}
    )

    assert links == ['0']
