import os
import sys
import pytest
import networkx
from genet.inputs_handler import matsim_reader
from genet.core import Network, Schedule

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
pt2matsim_network_test_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_data", "matsim", "network.xml"))
pt2matsim_schedule_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_data", "matsim", "schedule.xml"))


def test__repr__shows_graph_info_and_schedule_info(mocker):
    mocker.patch.object(networkx, 'info')
    mocker.patch.object(Schedule, 'info')
    n = Network()
    n.__repr__()
    networkx.info.assert_called_once()
    Schedule.info.assert_called_once()


def test__str__shows_info(mocker):
    mocker.patch.object(Network, 'info')
    n = Network()
    n.__str__()
    Network.info.assert_called_once()


def test_print_shows_info(mocker):
    mocker.patch.object(Network, 'info')
    n = Network()
    n.print()
    n.info.assert_called_once()


def test_add_node_adds_node_to_graph_with_attribs():
    n = Network()
    n.add_node(1, {'a': 1})
    assert n.graph.has_node(1)
    assert n.node(1) == {'a': 1}


def test_add_node_adds_node_to_graph_without_attribs():
    n = Network()
    n.add_node(1)
    assert n.graph.has_node(1)


def test_add_edge_generates_a_link_id_and_delegated_to_add_link_id(mocker):
    mocker.patch.object(Network, 'add_link')
    mocker.patch.object(Network, 'generate_index_for_edge')
    n = Network()
    n.add_edge(1, 2, {'a': 1})

    Network.add_link.assert_called_once()
    Network.generate_index_for_edge.assert_called_once()


def test_add_link_adds_edge_to_graph_with_attribs():
    n = Network()
    n.add_link('0', 1, 2, {'a': 1})
    assert n.graph.has_edge(1, 2)
    assert '0' in n.link_id_mapping
    assert n.edge(1, 2) == {0: {'a': 1}}


def test_add_link_adds_edge_to_graph_without_attribs():
    n = Network()
    n.add_link('0', 1, 2)
    n.graph.has_edge(1, 2)
    assert '0' in n.link_id_mapping


def test_add_link_generates_a_new_link_id_if_already_exists(mocker):
    mocker.patch.object(Network, 'generate_index_for_edge')
    n = Network()
    n.add_link('0', 1, 2)
    n.graph.has_edge(1, 2)
    assert '0' in n.link_id_mapping

    n.add_link('0', 3, 0)
    Network.generate_index_for_edge.assert_called_once()


def test_nodes_gives_iterator_of_node_id_and_attribs():
    n = Network()
    n.graph.add_edges_from([(1,2), (2,3), (3,4)])
    assert list(n.nodes()) == [(1, {}), (2, {}), (3, {}), (4, {})]


def test_node_gives_node_attribss():
    n = Network()
    n.graph.add_node(1, **{'attrib': 1})
    assert n.node(1) == {'attrib': 1}


def test_edges_gives_iterator_of_edge_from_to_nodes_and_attribs():
    n = Network()
    n.graph.add_edges_from([(1,2), (2,3), (3,4)])
    assert list(n.edges()) ==  [(1, 2, {}), (2, 3, {}), (3, 4, {})]


def test_edge_gives_edge_attribs_if_given_from_to_nodes():
    n = Network()
    n.graph.add_edge(1, 2, **{'attrib': 1})
    assert n.edge(1, 2) == {0: {'attrib': 1}}


def test_links_gives_iterator_of_link_id_and_edge_attribs():
    n = Network()
    n.graph.add_edges_from([(1,2), (2,3), (3,4)])
    assert list(n.edges()) ==  [(1, 2, {}), (2, 3, {}), (3, 4, {})]


def test_link_gives_link_attribs():
    n = Network()
    n.graph.add_edge(1, 2, **{'attrib': 1})
    assert n.edge(1, 2) == {0: {'attrib': 1}}


def test_read_matsim_network_delegates_to_matsim_reader_read_network(mocker):
    mocker.patch.object(matsim_reader, 'read_network', return_value = (1,3))

    network = Network()
    network.read_matsim_network(pt2matsim_network_test_file, 'epsg:27700')

    matsim_reader.read_network.assert_called_once_with(pt2matsim_network_test_file, network.transformer)


def test_read_matsim_schedule_runs_schedule_read_matsim_schedule_using_epsg_from_earlier_network_run(mocker):
    mocker.patch.object(Schedule, 'read_matsim_schedule')
    network = Network()
    network.read_matsim_network(pt2matsim_network_test_file, 'epsg:27700')
    network.read_matsim_schedule(pt2matsim_schedule_file)

    Schedule.read_matsim_schedule.assert_called_once_with(pt2matsim_schedule_file, 'epsg:27700')


def test_read_matsim_schedule_runs_schedule_read_matsim_schedule_using_given_epsg_independent_of_network(mocker):
    mocker.patch.object(Schedule, 'read_matsim_schedule')
    network = Network()
    network.read_matsim_schedule(pt2matsim_schedule_file, 'epsg:27700')

    Schedule.read_matsim_schedule.assert_called_once_with(pt2matsim_schedule_file, 'epsg:27700')


def test_read_matsim_schedule_when_asked_to_use_different_epsg_than_stored():
    network = Network()
    network.epsg = 'blop'

    with pytest.raises(RuntimeError) as e:
        network.read_matsim_schedule(pt2matsim_schedule_file, 'epsg:27700')
    assert 'The epsg you have given epsg:27700 does not match the epsg currently stored for this network' in str(e.value)


def test_generate_index_for_edge_when_you_have_matsim_usual_integer_index():
    n = Network()
    n.link_id_mapping = {'1': {}, '2': {}}
    assert n.generate_index_for_edge() == '3'


def test_generate_index_for_edge_when_you_have_mixed_index():
    n = Network()
    n.link_id_mapping = {'1': {}, 'x2': {}}
    assert n.generate_index_for_edge() == '3'


def test_generate_index_for_edge_when_you_have_non_int_index():
    n = Network()
    n.link_id_mapping = {'1x': {}, 'x2': {}}
    assert n.generate_index_for_edge() == '3'


def test_generate_index_for_edge_when_you_have_non_int_index():
    n = Network()
    n.link_id_mapping = {'1x': {}, 'x2': {}}
    assert n.generate_index_for_edge() == '3'


def test_index_graph_edges_generates_completely_new_index():
    n = Network()
    n.add_link('1x', 1, 2)
    n.add_link('x2', 1, 2)
    n.index_graph_edges()
    assert list(n.link_id_mapping.keys()) == ['0', '1']
