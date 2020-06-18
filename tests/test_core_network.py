import os
import sys
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal, assert_series_equal
from tests.fixtures import network_object_from_test_data, assert_semantically_equal, full_fat_default_config_path
from genet.inputs_handler import matsim_reader
from genet.core import Network, Schedule

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
pt2matsim_network_test_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "network.xml"))
pt2matsim_schedule_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "schedule.xml"))


def test__repr__shows_graph_info_and_schedule_info():
    n = Network()
    assert 'instance at' in n.__repr__()
    assert 'graph' in n.__repr__()
    assert 'schedule' in n.__repr__()


def test__str__shows_info():
    n = Network()
    assert 'Graph info' in n.__str__()
    assert 'Schedule info' in n.__str__()


def test_print_shows_info(mocker):
    mocker.patch.object(Network, 'info')
    n = Network()
    n.print()
    n.info.assert_called_once()


def test_node_attribute_data_under_key_returns_correct_pd_series_with_nested_keys():
    n = Network()
    n.add_node(1, {'a': {'b': 1}})
    n.add_node(2, {'a': {'b': 4}})

    output_series = n.node_attribute_data_under_key(key={'a': 'b'})
    assert_series_equal(output_series, pd.Series({1: 1, 2: 4}))


def test_node_attribute_data_under_key_returns_correct_pd_series_with_flat_keys():
    n = Network()
    n.add_node(1, {'b': 1})
    n.add_node(2, {'b': 4})

    output_series = n.node_attribute_data_under_key(key='b')
    assert_series_equal(output_series, pd.Series({1: 1, 2: 4}))


def test_link_attribute_data_under_key_returns_correct_pd_series_with_nested_keys():
    n = Network()
    n.add_link('0', 1, 2, {'a': {'b': 1}})
    n.add_link('1', 1, 2, {'a': {'b': 4}})

    output_series = n.link_attribute_data_under_key(key={'a': 'b'})
    assert_series_equal(output_series, pd.Series({'0': 1, '1': 4}))


def test_link_attribute_data_under_key_returns_correct_pd_series_with_flat_keys():
    n = Network()
    n.add_link('0', 1, 2, {'b': 1})
    n.add_link('1', 1, 2, {'b': 4})

    output_series = n.link_attribute_data_under_key(key='b')
    assert_series_equal(output_series, pd.Series({'0': 1, '1': 4}))


def test_add_node_adds_node_to_graph_with_attribs():
    n = Network()
    n.add_node(1, {'a': 1})
    assert n.graph.has_node(1)
    assert n.node(1) == {'a': 1}


def test_add_node_adds_node_to_graph_without_attribs():
    n = Network()
    n.add_node(1)
    assert n.node(1) == {}
    assert n.graph.has_node(1)


def test_add_edge_generates_a_link_id_and_delegated_to_add_link_id(mocker):
    mocker.patch.object(Network, 'add_link')
    mocker.patch.object(Network, 'generate_index_for_edge', return_value='12345')
    n = Network()
    n.add_edge(1, 2, {'a': 1})

    Network.generate_index_for_edge.assert_called_once()
    Network.add_link.assert_called_once_with('12345', 1, 2, {'a': 1})


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
    assert n.link_id_mapping['0'] == {'from': 1, 'to': 2, 'multi_edge_idx': 0}


def test_modify_node_adds_attributes_in_the_graph_and_change_is_recorded_by_change_log():
    n = Network()
    n.add_node(1, {'a': 1})
    n.apply_attributes_to_node(1, {'b': 1})

    assert n.node(1) == {'b': 1, 'a': 1}

    correct_change_log_df = pd.DataFrame(
        {'timestamp': {0: '2020-05-28 13:49:53', 1: '2020-05-28 13:49:53'}, 'change_event': {0: 'add', 1: 'modify'},
         'object_type': {0: 'node', 1: 'node'}, 'old_id': {0: None, 1: 1}, 'new_id': {0: 1, 1: 1},
         'old_attributes': {0: None, 1: "{'a': 1}"}, 'new_attributes': {0: "{'a': 1}", 1: "{'a': 1, 'b': 1}"},
         'diff': {0: [('add', '', [('a', 1)]), ('add', 'id', 1)], 1: [('add', '', [('b', 1)])]}})

    cols_to_compare = ['change_event', 'object_type', 'old_id', 'new_id', 'old_attributes', 'new_attributes', 'diff']
    assert_frame_equal(n.change_log.log[cols_to_compare], correct_change_log_df[cols_to_compare], check_names=False,
                       check_dtype=False)


def test_modify_node_overwrites_existing_attributes_in_the_graph_and_change_is_recorded_by_change_log():
    n = Network()
    n.add_node(1, {'a': 1})
    n.apply_attributes_to_node(1, {'a': 4})

    assert n.node(1) == {'a': 4}

    correct_change_log_df = pd.DataFrame(
        {'timestamp': {0: '2020-05-28 13:49:53', 1: '2020-05-28 13:49:53'}, 'change_event': {0: 'add', 1: 'modify'},
         'object_type': {0: 'node', 1: 'node'}, 'old_id': {0: None, 1: 1}, 'new_id': {0: 1, 1: 1},
         'old_attributes': {0: None, 1: "{'a': 1}"}, 'new_attributes': {0: "{'a': 1}", 1: "{'a': 4}"},
         'diff': {0: [('add', '', [('a', 1)]), ('add', 'id', 1)], 1: [('change', 'a', (1, 4))]}})

    cols_to_compare = ['change_event', 'object_type', 'old_id', 'new_id', 'old_attributes', 'new_attributes', 'diff']
    assert_frame_equal(n.change_log.log[cols_to_compare], correct_change_log_df[cols_to_compare], check_dtype=False)


def test_modify_nodes_adds_and_changes_attributes_in_the_graph_and_change_is_recorded_by_change_log():
    n = Network()
    n.add_node(1, {'a': 1})
    n.add_node(2, {'b': 1})
    n.apply_attributes_to_nodes([1, 2], {'a': 4})

    assert n.node(1) == {'a': 4}
    assert n.node(2) == {'b': 1, 'a': 4}

    correct_change_log_df = pd.DataFrame(
        {'timestamp': {0: '2020-06-01 15:07:51', 1: '2020-06-01 15:07:51', 2: '2020-06-01 15:07:51',
                       3: '2020-06-01 15:07:51'}, 'change_event': {0: 'add', 1: 'add', 2: 'modify', 3: 'modify'},
         'object_type': {0: 'node', 1: 'node', 2: 'node', 3: 'node'}, 'old_id': {0: None, 1: None, 2: 1, 3: 2},
         'new_id': {0: 1, 1: 2, 2: 1, 3: 2}, 'old_attributes': {0: None, 1: None, 2: "{'a': 1}", 3: "{'b': 1}"},
         'new_attributes': {0: "{'a': 1}", 1: "{'b': 1}", 2: "{'a': 4}", 3: "{'b': 1, 'a': 4}"},
         'diff': {0: [('add', '', [('a', 1)]), ('add', 'id', 1)], 1: [('add', '', [('b', 1)]), ('add', 'id', 2)],
                  2: [('change', 'a', (1, 4))], 3: [('add', '', [('a', 4)])]}
         })

    cols_to_compare = ['change_event', 'object_type', 'old_id', 'new_id', 'old_attributes', 'new_attributes', 'diff']
    assert_frame_equal(n.change_log.log[cols_to_compare], correct_change_log_df[cols_to_compare], check_dtype=False)


def test_modify_link_adds_attributes_in_the_graph_and_change_is_recorded_by_change_log():
    n = Network()
    n.add_link('0', 1, 2, {'a': 1})
    n.apply_attributes_to_link('0', {'b': 1})

    assert n.link('0') == {'b': 1, 'a': 1}

    correct_change_log_df = pd.DataFrame(
        {'timestamp': {0: '2020-05-28 13:49:53', 1: '2020-05-28 13:49:53'}, 'change_event': {0: 'add', 1: 'modify'},
         'object_type': {0: 'link', 1: 'link'}, 'old_id': {0: None, 1: '0'}, 'new_id': {0: '0', 1: '0'},
         'old_attributes': {0: None, 1: "{'a': 1}"}, 'new_attributes': {0: "{'a': 1}", 1: "{'a': 1, 'b': 1}"},
         'diff': {0: [('add', '', [('a', 1)]), ('add', 'id', '0')], 1: [('add', '', [('b', 1)])]}})

    cols_to_compare = ['change_event', 'object_type', 'old_id', 'new_id', 'old_attributes', 'new_attributes', 'diff']
    assert_frame_equal(n.change_log.log[cols_to_compare], correct_change_log_df[cols_to_compare], check_dtype=False)


def test_modify_link_overwrites_existing_attributes_in_the_graph_and_change_is_recorded_by_change_log():
    n = Network()
    n.add_link('0', 1, 2, {'a': 1})
    n.apply_attributes_to_link('0', {'a': 4})

    assert n.link('0') == {'a': 4}

    correct_change_log_df = pd.DataFrame(
        {'timestamp': {0: '2020-06-01 18:23:00', 1: '2020-06-01 18:23:00'}, 'change_event': {0: 'add', 1: 'modify'},
         'object_type': {0: 'link', 1: 'link'}, 'old_id': {0: None, 1: '0'}, 'new_id': {0: '0', 1: '0'},
         'old_attributes': {0: None, 1: "{'a': 1}"}, 'new_attributes': {0: "{'a': 1}", 1: "{'a': 4}"},
         'diff': {0: [('add', '', [('a', 1)]), ('add', 'id', '0')], 1: [('change', 'a', (1, 4))]}})

    cols_to_compare = ['change_event', 'object_type', 'old_id', 'new_id', 'old_attributes', 'new_attributes', 'diff']
    assert_frame_equal(n.change_log.log[cols_to_compare], correct_change_log_df[cols_to_compare], check_dtype=False)


def test_modify_link_adds_attributes_in_the_graph_with_multiple_edges():
    n = Network()
    n.add_link('0', 1, 2, {'a': 1})
    n.add_link('1', 1, 2, {'c': 100})
    n.apply_attributes_to_link('0', {'b': 1})

    assert n.link('0') == {'b': 1, 'a': 1}
    assert n.link('1') == {'c': 100}


def test_modify_links_adds_and_changes_attributes_in_the_graph_with_multiple_edges_and_change_is_recorded_by_change_log():
    n = Network()
    n.add_link('0', 1, 2, {'a': {'b': 1}})
    n.add_link('1', 1, 2, {'c': 100})
    n.apply_attributes_to_links(['0', '1'], {'a': {'b': 100}})

    assert n.link('0') == {'a': {'b': 100}}
    assert n.link('1') == {'c': 100, 'a': {'b': 100}}

    correct_change_log_df = pd.DataFrame(
        {'timestamp': {0: '2020-06-01 18:19:59', 1: '2020-06-01 18:19:59', 2: '2020-06-01 18:20:37',
                       3: '2020-06-01 18:20:37'}, 'change_event': {0: 'add', 1: 'add', 2: 'modify', 3: 'modify'},
         'object_type': {0: 'link', 1: 'link', 2: 'link', 3: 'link'}, 'old_id': {0: None, 1: None, 2: '0', 3: '1'},
         'new_id': {0: '0', 1: '1', 2: '0', 3: '1'},
         'old_attributes': {0: None, 1: None, 2: "{'a': {'b': 1}}", 3: "{'c': 100}"},
         'new_attributes': {0: "{'a': {'b': 1}}", 1: "{'c': 100}", 2: "{'a': {'b': 100}}",
                            3: "{'c': 100, 'a': {'b': 100}}"},
         'diff': {0: [('add', '', [('a', {'b': 1})]), ('add', 'id', '0')],
                  1: [('add', '', [('c', 100)]), ('add', 'id', '1')], 2: [('change', 'a.b', (1, 100))],
                  3: [('add', '', [('a', {'b': 100})])]}})

    cols_to_compare = ['change_event', 'object_type', 'old_id', 'new_id', 'old_attributes', 'new_attributes', 'diff']
    assert_frame_equal(n.change_log.log[cols_to_compare], correct_change_log_df[cols_to_compare], check_dtype=False)


def test_resolves_link_id_clashes_by_mapping_clashing_link_to_a_new_id(mocker):
    mocker.patch.object(Network, 'generate_index_for_edge', return_value='1')
    n = Network()

    n.add_link('0', 1, 2)
    assert n.graph.has_edge(1, 2)
    assert n.link_id_mapping['0'] == {'from': 1, 'to': 2, 'multi_edge_idx': 0}

    assert '1' not in n.link_id_mapping
    n.add_link('0', 3, 0)
    assert n.graph.has_edge(3, 0)
    assert n.link_id_mapping['1'] == {'from': 3, 'to': 0, 'multi_edge_idx': 0}

    # also assert that the link mapped to '0' is still as expected
    assert n.link_id_mapping['0'] == {'from': 1, 'to': 2, 'multi_edge_idx': 0}


def test_number_of_multi_edges_counts_multi_edges_on_single_edge():
    n = Network()
    n.graph.add_edges_from([(1, 2), (2, 3), (3, 4)])
    assert n.number_of_multi_edges(1, 2) == 1


def test_number_of_multi_edges_counts_multi_edges_on_multi_edge():
    n = Network()
    n.graph.add_edges_from([(1, 2), (1, 2), (3, 4)])
    assert n.number_of_multi_edges(1, 2) == 2


def test_number_of_multi_edges_counts_multi_edges_on_non_existing_edge():
    n = Network()
    n.graph.add_edges_from([(1, 2), (1, 2), (3, 4)])
    assert n.number_of_multi_edges(1214, 21321) == 0


def test_nodes_gives_iterator_of_node_id_and_attribs():
    n = Network()
    n.graph.add_edges_from([(1, 2), (2, 3), (3, 4)])
    assert list(n.nodes()) == [(1, {}), (2, {}), (3, {}), (4, {})]


def test_node_gives_node_attribss():
    n = Network()
    n.graph.add_node(1, **{'attrib': 1})
    assert n.node(1) == {'attrib': 1}


def test_edges_gives_iterator_of_edge_from_to_nodes_and_attribs():
    n = Network()
    n.graph.add_edges_from([(1, 2), (2, 3), (3, 4)])
    assert list(n.edges()) == [(1, 2, {0: {}}), (2, 3, {0: {}}), (3, 4, {0: {}})]


def test_edge_method_gives_attributes_for_given_from_and_to_nodes():
    n = Network()
    n.graph.add_edge(1, 2, **{'attrib': 1})
    assert n.edge(1, 2) == {0: {'attrib': 1}}


def test_links_gives_iterator_of_link_id_and_edge_attribs():
    n = Network()
    n.add_link('0', 1, 2, {'f': 's'})
    n.add_link('1', 2, 3, {'h': 1})
    assert list(n.links()) == [('0', {'f': 's'}), ('1', {'h': 1})]


def test_link_gives_link_attribs():
    n = Network()
    n.add_link('0', 1, 2, {'attrib': 1})
    assert n.link('0') == {'attrib': 1}


def test_reads_osm_network_into_the_right_schema(full_fat_default_config_path):
    osm_test_file = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "test_data", "osm", "osm.xml"))
    network = Network()
    network.read_osm_to_network(osm_test_file, full_fat_default_config_path, 'epsg:27700', 1)
    assert_semantically_equal(dict(network.nodes()), {
        '0': {'id': '0', 'x': 49.76680731128457, 'y': -7.557159824733108, 'lon': -0.0006545205888310243,
              'lat': 0.008554364250688652, 's2_id': 1152921492875543713},
        '1': {'id': '1', 'x': 49.766807452044425, 'y': -7.557159840875761, 'lon': -0.0006545205888310243,
              'lat': 0.024278505899735615, 's2_id': 1152921335974974453},
        '2': {'id': '2', 'x': 49.76680717052477, 'y': -7.557159808590456, 'lon': -0.0006545205888310243,
              'lat': -0.00716977739835831, 's2_id': 384307157539499829}})
    assert len(list(network.links())) == 8

    number_of_0_multi_idx = 0
    number_of_1_multi_idx = 0
    for link_id, edge_map in network.link_id_mapping.items():
        if edge_map['multi_edge_idx'] == 0:
            number_of_0_multi_idx += 1
        elif edge_map['multi_edge_idx'] == 1:
            number_of_1_multi_idx += 1
    assert number_of_0_multi_idx == 4
    assert number_of_1_multi_idx == 4

    assert_semantically_equal(network.link('1'),
                              {'permlanes': 1.0, 'freespeed': 12.5, 'freespeedFactor': 1.0, 'capacity': 600.0,
                               'oneway': '1',
                               'modes': ['walk', 'bike', 'car'], 'from': '0', 'to': '1', 's2_from': 1152921492875543713,
                               's2_to': 1152921335974974453, 'length': 1748.4487354464366,
                               'attributes': {
                                   'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String',
                                                       'text': 'unclassified'},
                                   'osm:way:osmid': {'name': 'osm:way:osmid', 'class': 'java.lang.String',
                                                     'text': '0'}}})


def test_read_matsim_network_delegates_to_matsim_reader_read_network(mocker):
    mocker.patch.object(matsim_reader, 'read_network', return_value=(1, 3))

    network = Network()
    network.read_matsim_network(pt2matsim_network_test_file, 'epsg:27700')
    network.epsg = 'epsg:27700'

    matsim_reader.read_network.assert_called_once_with(pt2matsim_network_test_file, network.transformer)


def test_read_matsim_schedule_runs_schedule_read_matsim_schedule_using_epsg_from_earlier_network_run(mocker):
    mocker.patch.object(Schedule, 'read_matsim_schedule')
    network = Network()
    network.read_matsim_network(pt2matsim_network_test_file, 'epsg:27700')
    network.epsg = 'epsg:27700'
    network.read_matsim_schedule(pt2matsim_schedule_file)

    Schedule.read_matsim_schedule.assert_called_once_with(pt2matsim_schedule_file, 'epsg:27700')


def test_read_matsim_schedule_runs_schedule_read_matsim_schedule_using_given_epsg_independent_of_network(mocker):
    mocker.patch.object(Schedule, 'read_matsim_schedule')
    network = Network()
    network.read_matsim_schedule(pt2matsim_schedule_file, 'epsg:27700')

    Schedule.read_matsim_schedule.assert_called_once_with(pt2matsim_schedule_file, 'epsg:27700')


def test_read_matsim_schedule_throws_error_when_asked_to_use_different_epsg_than_stored():
    network = Network()
    network.epsg = 'blop'

    with pytest.raises(RuntimeError) as e:
        network.read_matsim_schedule(pt2matsim_schedule_file, 'epsg:27700')
    assert 'The epsg you have given epsg:27700 does not match the epsg currently stored for this network' in str(
        e.value)


def test_generate_index_for_edge_gives_next_integer_string_when_you_have_matsim_usual_integer_index():
    n = Network()
    n.link_id_mapping = {'1': {}, '2': {}}
    assert n.generate_index_for_edge() == '3'


def test_generate_index_for_edge_gives_string_based_on_length_link_id_mapping_when_you_have_mixed_index():
    n = Network()
    n.link_id_mapping = {'1': {}, 'x2': {}}
    assert n.generate_index_for_edge() == '3'


def test_generate_index_for_edge_gives_string_based_on_length_link_id_mapping_when_you_have_all_non_int_index():
    n = Network()
    n.link_id_mapping = {'1x': {}, 'x2': {}}
    assert n.generate_index_for_edge() == '3'


def test_index_graph_edges_generates_completely_new_index():
    n = Network()
    n.add_link('1x', 1, 2)
    n.add_link('x2', 1, 2)
    n.index_graph_edges()
    assert list(n.link_id_mapping.keys()) == ['0', '1']


def test_write_to_matsim_generates_three_matsim_files(network_object_from_test_data, tmpdir):
    # the correctness of these files is tested elsewhere
    expected_network_xml = os.path.join(tmpdir, 'network.xml')
    assert not os.path.exists(expected_network_xml)
    expected_schedule_xml = os.path.join(tmpdir, 'schedule.xml')
    assert not os.path.exists(expected_schedule_xml)
    expected_vehicle_xml = os.path.join(tmpdir, 'vehicles.xml')
    assert not os.path.exists(expected_vehicle_xml)

    network_object_from_test_data.write_to_matsim(tmpdir)

    assert os.path.exists(expected_network_xml)
    assert os.path.exists(expected_schedule_xml)
    assert os.path.exists(expected_vehicle_xml)


def test_write_to_matsim_generates_network_matsim_file_if_network_is_car_only(network_object_from_test_data, tmpdir):
    # the correctness of these files is tested elsewhere
    expected_network_xml = os.path.join(tmpdir, 'network.xml')
    assert not os.path.exists(expected_network_xml)
    expected_schedule_xml = os.path.join(tmpdir, 'schedule.xml')
    assert not os.path.exists(expected_schedule_xml)
    expected_vehicle_xml = os.path.join(tmpdir, 'vehicles.xml')
    assert not os.path.exists(expected_vehicle_xml)

    n = network_object_from_test_data
    n.schedule = Schedule()
    assert not n.schedule
    n.write_to_matsim(tmpdir)

    assert os.path.exists(expected_network_xml)
    assert not os.path.exists(expected_schedule_xml)
    assert not os.path.exists(expected_vehicle_xml)


def test_write_to_matsim_generates_change_log_csv(network_object_from_test_data, tmpdir):
    expected_change_log_path = os.path.join(tmpdir, 'change_log.csv')
    assert not os.path.exists(expected_change_log_path)

    network_object_from_test_data.write_to_matsim(tmpdir)

    assert os.path.exists(expected_change_log_path)
