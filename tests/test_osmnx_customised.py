from tests.fixtures import assert_semantically_equal, full_fat_default_config
from genet.inputs_handler import osmnx_customised
import logging
import sys


def test_assume_travel_modes_works_with_nested_highway_tags(full_fat_default_config):
    modes_to_assume = ['car', 'bike']
    full_fat_default_config.MODE_INDICATORS['highway']['unclassified'] = modes_to_assume
    edge = {'osmid': 0, 'nodes': [0, 1], 'highway': 'unclassified'}
    assumed_modes = osmnx_customised.assume_travel_modes(edge, full_fat_default_config)

    assert_semantically_equal(assumed_modes, modes_to_assume)


def test_assume_travel_modes_assumes_unclassified_highway_tag_if_given_highway_road_tag(full_fat_default_config):
    modes_to_assume = ['car', 'bike', 'am_special_unclassified_mode']
    full_fat_default_config.MODE_INDICATORS['highway']['unclassified'] = modes_to_assume
    edge = {'osmid': 0, 'nodes': [0, 1], 'highway': 'road'}
    assumed_modes = osmnx_customised.assume_travel_modes(edge, full_fat_default_config)

    assert_semantically_equal(assumed_modes, modes_to_assume)


def test_assume_travel_modes_doesnt_assume_modes_for_tags_unspecified_in_config(full_fat_default_config):
    edge = {'osmid': 0, 'nodes': [0, 1], 'highway': 'what did you say?'}
    assumed_modes = osmnx_customised.assume_travel_modes(edge, full_fat_default_config)

    assert assumed_modes == []


def test_assume_travel_modes_doesnt_assume_modes_for_construction_highway_tags(full_fat_default_config):
    edge = {'osmid': 0, 'nodes': [0, 1], 'highway': 'construction'}
    assumed_modes = osmnx_customised.assume_travel_modes(edge, full_fat_default_config)

    assert assumed_modes == []


def test_assume_travel_modes_doesnt_assume_modes_for_proposed_highway_tags(full_fat_default_config):
    edge = {'osmid': 0, 'nodes': [0, 1], 'highway': 'proposed'}
    assumed_modes = osmnx_customised.assume_travel_modes(edge, full_fat_default_config)

    assert assumed_modes == []


def test_assume_travel_modes_doesnt_assume_modes_for_no_tags(full_fat_default_config):
    edge = {'osmid': 0, 'nodes': [0, 1]}
    assumed_modes = osmnx_customised.assume_travel_modes(edge, full_fat_default_config)

    assert assumed_modes == []


def test_assume_travel_modes_works_with_other_non_nested_tags(full_fat_default_config):
    modes_to_assume = ['rail']
    full_fat_default_config.MODE_INDICATORS['railway'] = modes_to_assume
    edge = {'osmid': 0, 'nodes': [0, 1], 'railway': 'yassss'}
    assumed_modes = osmnx_customised.assume_travel_modes(edge, full_fat_default_config)

    assert_semantically_equal(assumed_modes, modes_to_assume)


def test_return_edges_handles_regular_non_oneway_paths(full_fat_default_config):
    paths = {0: {'osmid': 0, 'nodes': [0, 1], 'highway': 'unclassified', 'modes': ['bike', 'car', 'walk']}}

    edges = osmnx_customised.return_edges(paths, args={'config': full_fat_default_config, 'bidirectional': False})
    assert len(edges) == 2
    assert (0, 1) in [edge for edge, attribs in edges]
    assert (1, 0) in [edge for edge, attribs in edges]
    for edge, attribs in edges:
        assert_semantically_equal(attribs, {'modes': ['bike', 'car', 'walk'], 'osmid': 0, 'highway': 'unclassified'})


def test_return_edges_handles_oneway_paths(full_fat_default_config):
    paths = {0: {'osmid': 0, 'nodes': [0, 1], 'highway': 'unclassified', 'modes': ['bike', 'car', 'walk'],
                 'oneway': 'yes'}}

    edges = osmnx_customised.return_edges(paths, args={'config': full_fat_default_config, 'bidirectional': False})
    assert len(edges) == 1
    assert (0, 1) in [edge for edge, attribs in edges]
    for edge, attribs in edges:
        assert_semantically_equal(attribs, {'modes': ['bike', 'car', 'walk'], 'osmid': 0, 'highway': 'unclassified'})


def test_return_edges_handles_reversed_oneway_paths(full_fat_default_config):
    paths = {0: {'osmid': 0, 'nodes': [0, 1], 'highway': 'unclassified', 'modes': ['bike', 'car', 'walk'],
                 'oneway': 'reverse'}}

    edges = osmnx_customised.return_edges(paths, args={'config': full_fat_default_config, 'bidirectional': False})
    assert len(edges) == 1
    assert (1, 0) in [edge for edge, attribs in edges]
    for edge, attribs in edges:
        assert_semantically_equal(attribs, {'modes': ['bike', 'car', 'walk'], 'osmid': 0, 'highway': 'unclassified'})


def test_return_edges_handles_roundabouts_as_oneway(full_fat_default_config):
    paths = {0: {'osmid': 0, 'nodes': [0, 1], 'highway': 'unclassified', 'modes': ['bike', 'car', 'walk'],
                 'junction': 'roundabout'}}

    edges = osmnx_customised.return_edges(paths, args={'config': full_fat_default_config, 'bidirectional': False})
    assert len(edges) == 1
    assert (0, 1) in [edge for edge, attribs in edges]
    for edge, attribs in edges:
        assert_semantically_equal(attribs, {'modes': ['bike', 'car', 'walk'], 'osmid': 0, 'highway': 'unclassified',
                                            'junction': 'roundabout'})
