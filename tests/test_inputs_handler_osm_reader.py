import os
import sys
from genet.inputs_handler import osm_reader
from tests.fixtures import assert_semantically_equal, full_fat_default_config

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
osm_test_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "osm", "osm.xml"))


def test_assume_travel_modes_works_with_nested_highway_tags(full_fat_default_config):
    modes_to_assume = ['car', 'bike']
    full_fat_default_config.MODE_INDICATORS['highway']['unclassified'] = modes_to_assume
    edge = {'osmid': 0, 'nodes': [0, 1], 'highway': 'unclassified'}
    assumed_modes = osm_reader.assume_travel_modes(edge, full_fat_default_config)

    assert_semantically_equal(assumed_modes, modes_to_assume)


def test_assume_travel_modes_assumes_unclassified_highway_tag_if_given_highway_road_tag(full_fat_default_config):
    modes_to_assume = ['car', 'bike', 'am_special_unclassified_mode']
    full_fat_default_config.MODE_INDICATORS['highway']['unclassified'] = modes_to_assume
    edge = {'osmid': 0, 'nodes': [0, 1], 'highway': 'road'}
    assumed_modes = osm_reader.assume_travel_modes(edge, full_fat_default_config)

    assert_semantically_equal(assumed_modes, modes_to_assume)


def test_assume_travel_modes_doesnt_assume_modes_for_tags_unspecified_in_config(full_fat_default_config):
    edge = {'osmid': 0, 'nodes': [0, 1], 'highway': 'what did you say?'}
    assumed_modes = osm_reader.assume_travel_modes(edge, full_fat_default_config)

    assert assumed_modes == []


def test_assume_travel_modes_doesnt_assume_modes_for_construction_highway_tags(full_fat_default_config):
    edge = {'osmid': 0, 'nodes': [0, 1], 'highway': 'construction'}
    assumed_modes = osm_reader.assume_travel_modes(edge, full_fat_default_config)

    assert assumed_modes == []


def test_assume_travel_modes_doesnt_assume_modes_for_proposed_highway_tags(full_fat_default_config):
    edge = {'osmid': 0, 'nodes': [0, 1], 'highway': 'proposed'}
    assumed_modes = osm_reader.assume_travel_modes(edge, full_fat_default_config)

    assert assumed_modes == []


def test_assume_travel_modes_doesnt_assume_modes_for_no_tags(full_fat_default_config):
    edge = {'osmid': 0, 'nodes': [0, 1]}
    assumed_modes = osm_reader.assume_travel_modes(edge, full_fat_default_config)

    assert assumed_modes == []


def test_assume_travel_modes_works_with_other_non_nested_tags(full_fat_default_config):
    modes_to_assume = ['rail']
    full_fat_default_config.MODE_INDICATORS['railway'] = modes_to_assume
    edge = {'osmid': 0, 'nodes': [0, 1], 'railway': 'yassss'}
    assumed_modes = osm_reader.assume_travel_modes(edge, full_fat_default_config)

    assert_semantically_equal(assumed_modes, modes_to_assume)


def test_find_matsim_link_values_finds_values_for_well_defined_highway_osm_tag(full_fat_default_config):
    edge_data = {'highway': 'motorway', 'osmid': 0, 'modes': ['walk', 'car', 'bike'], 'length': 1748.4487354464366}
    matsim_vals = osm_reader.find_matsim_link_values(edge_data, full_fat_default_config)
    assert_semantically_equal(matsim_vals,
                              {'permlanes': 2.0, 'freespeed': 33.36, 'capacity': 2000.0})


def test_find_matsim_link_values_defaults_to_highway_secondary_if_unknown_highway_osm_tag(full_fat_default_config):
    edge_data = {'highway': 'whaaaaaaaat', 'osmid': 0, 'modes': ['walk', 'car', 'bike'], 'length': 1748.4487354464366}
    matsim_vals = osm_reader.find_matsim_link_values(edge_data, full_fat_default_config)
    assert_semantically_equal(matsim_vals,
                              {'permlanes': 1.0, 'freespeed': 16.68, 'capacity': 1000.0})


def test_find_matsim_link_values_finds_values_for_non_highway_osm_tag(full_fat_default_config):
    edge_data = {'railway': 'yassss', 'osmid': 0, 'modes': ['rail'], 'length': 1748.4487354464366}
    matsim_vals = osm_reader.find_matsim_link_values(edge_data, full_fat_default_config)
    assert_semantically_equal(matsim_vals,
                              {'permlanes': 1.0, 'freespeed': 44.44, 'capacity': 9999.0})


def test_find_matsim_link_values_finds_values_based_on_modes_defaults_in_config_when_tags_missing(full_fat_default_config):
    edge_data = {'osmid': 0, 'modes': ['rail'], 'length': 1748.4487354464366}
    matsim_vals = osm_reader.find_matsim_link_values(edge_data, full_fat_default_config)
    assert_semantically_equal(matsim_vals,
                              {'permlanes': 1.0, 'freespeed': 44.44, 'capacity': 9999.0})


def test_find_matsim_link_values_settles_on_bigger_capacity_values_if_finding_values_based_on_several_modes(full_fat_default_config):
    edge_data = {'osmid': 0, 'modes': ['walk', 'car'], 'length': 1748.4487354464366}
    matsim_vals = osm_reader.find_matsim_link_values(edge_data, full_fat_default_config)
    assert_semantically_equal(matsim_vals,
                              {'permlanes': 1.0, 'freespeed': 16.68, 'capacity': 1000.0})


def test_find_matsim_link_values_to_highway_secondary_values_if_surrounded_with_gibberish_modes(full_fat_default_config):
    edge_data = {'osmid': 0, 'modes': ['piggyback', 'walk', 'levitating'], 'length': 1748.4487354464366}
    matsim_vals = osm_reader.find_matsim_link_values(edge_data, full_fat_default_config)
    assert_semantically_equal(matsim_vals,
                              {'permlanes': 1.0, 'freespeed': 16.68, 'capacity': 1000.0})


def test_find_matsim_link_values_defaults_to_highway_secondary_values_when_everything_fails(full_fat_default_config):
    edge_data = {'osmid': 0, 'modes': ['piggyback', 'levitating'], 'length': 1748.4487354464366}
    matsim_vals = osm_reader.find_matsim_link_values(edge_data, full_fat_default_config)
    assert_semantically_equal(matsim_vals,
                              {'permlanes': 1.0, 'freespeed': 16.68, 'capacity': 1000.0})


def test_generate_osm_graph_edges_from_file(full_fat_default_config):
    nodes, edges = osm_reader.generate_osm_graph_edges_from_file(osm_test_file, full_fat_default_config, 1)

    assert_semantically_equal(nodes, {
        0: {'osmid': 0, 's2id': 1152921492875543713, 'x':  0.008554364250688652, 'y': -0.0006545205888310243},
        1: {'osmid': 1, 's2id': 1152921335974974453, 'x': 0.024278505899735615, 'y': -0.0006545205888310243},
        2: {'osmid': 2, 's2id': 384307157539499829, 'x': -0.00716977739835831, 'y': -0.0006545205888310243}})

    assert len(edges) == 8
    correct_edge_data = {
        0: {'osmid': 0, 'modes': ['walk', 'car', 'bike'], 'highway': 'unclassified', 'length': 1748.4487354464366},
        1: {'osmid': 0, 'modes': ['walk', 'car', 'bike'], 'highway': 'unclassified', 'length': 1748.4487354464366},
        2: {'osmid': 100, 'modes': ['walk', 'car', 'bike'], 'highway': 'unclassified', 'length': 1748.4488584600201},
        3: {'osmid': 100, 'modes': ['walk', 'car', 'bike'], 'highway': 'unclassified', 'length': 1748.4488584600201},
        4: {'osmid': 400, 'modes': ['walk', 'car', 'bike'], 'highway': 'unclassified', 'length': 1748.4487354464366},
        5: {'osmid': 400, 'modes': ['walk', 'car', 'bike'], 'highway': 'unclassified', 'length': 1748.4487354464366},
        6: {'osmid': 700, 'modes': ['walk', 'car', 'bike'], 'highway': 'unclassified', 'length': 1748.4488584600201},
        7: {'osmid': 700, 'modes': ['walk', 'car', 'bike'], 'highway': 'unclassified', 'length': 1748.4488584600201}}
    correct_edges = {0: (0, 1), 1: (1, 0), 2: (0, 2), 3: (2, 0), 4: (1, 0), 5: (0, 1), 6: (2, 0), 7: (0, 2)}

    i = 0
    for edge, attribs in edges:
        assert edge == correct_edges[i]
        assert_semantically_equal(attribs, correct_edge_data[i])
        i += 1
