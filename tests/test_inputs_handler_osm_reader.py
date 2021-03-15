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


def test_find_matsim_link_values_finds_values_based_on_modes_defaults_in_config_when_tags_missing(
        full_fat_default_config):
    edge_data = {'osmid': 0, 'modes': ['rail'], 'length': 1748.4487354464366}
    matsim_vals = osm_reader.find_matsim_link_values(edge_data, full_fat_default_config)
    assert_semantically_equal(matsim_vals,
                              {'permlanes': 1.0, 'freespeed': 44.44, 'capacity': 9999.0})


def test_find_matsim_link_values_settles_on_bigger_capacity_values_if_finding_values_based_on_several_modes(
        full_fat_default_config):
    edge_data = {'osmid': 0, 'modes': ['walk', 'car'], 'length': 1748.4487354464366}
    matsim_vals = osm_reader.find_matsim_link_values(edge_data, full_fat_default_config)
    assert_semantically_equal(matsim_vals,
                              {'permlanes': 1.0, 'freespeed': 16.68, 'capacity': 1000.0})


def test_find_matsim_link_values_to_highway_secondary_values_if_surrounded_with_gibberish_modes(
        full_fat_default_config):
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
        0: {'osmid': 0, 's2id': 1152921492875543713, 'y': 0.008554364250688652, 'x': -0.0006545205888310243},
        1: {'osmid': 1, 's2id': 1152921335974974453, 'y': 0.024278505899735615, 'x': -0.0006545205888310243},
        2: {'osmid': 2, 's2id': 384307157539499829, 'y': -0.00716977739835831, 'x': -0.0006545205888310243}})

    assert len(edges) == 11
    correct_edge_data = {
        0: {'osmid': 0, 'modes': ['walk', 'car', 'bike'], 'highway': 'unclassified'},
        1: {'osmid': 0, 'modes': ['walk', 'car', 'bike'], 'highway': 'unclassified'},
        2: {'osmid': 100, 'modes': ['walk', 'car', 'bike'], 'highway': 'unclassified'},
        3: {'osmid': 100, 'modes': ['walk', 'car', 'bike'], 'highway': 'unclassified'},
        4: {'osmid': 400, 'modes': ['walk', 'car', 'bike'], 'highway': 'unclassified'},
        5: {'osmid': 400, 'modes': ['walk', 'car', 'bike'], 'highway': 'unclassified'},
        6: {'osmid': 700, 'modes': ['walk', 'car', 'bike'], 'highway': 'unclassified'},
        7: {'osmid': 700, 'modes': ['walk', 'car', 'bike'], 'highway': 'unclassified'},
        8: {'osmid': 47007861, 'modes': ['car', 'walk', 'bike'], 'highway': 'tertiary', 'lanes': '3'},
        9: {'osmid': 47007861, 'modes': ['car', 'walk', 'bike'], 'highway': 'tertiary', 'lanes': '3'},
        # funny osm lane data currently defaults to matsim osm values
        10: {'osmid': 47007862, 'modes': ['car', 'walk', 'bike'], 'highway': 'tertiary', 'lanes': '3;2'}
    }
    correct_edges = {0: (0, 1), 1: (1, 0), 2: (0, 2), 3: (2, 0), 4: (1, 0), 5: (0, 1), 6: (2, 0), 7: (0, 2), 8: (2, 1),
                     9: (1, 0), 10: (1, 0)}

    i = 0
    for edge, attribs in edges:
        assert edge == correct_edges[i]
        assert_semantically_equal(attribs, correct_edge_data[i])
        i += 1


def test_generate_graph_nodes():
    nodes = {0: {'osmid': 0, 's2id': 1152921492875543713, 'x': 0.008554364250688652, 'y': -0.0006545205888310243},
             1: {'osmid': 1, 's2id': 1152921335974974453, 'x': 0.024278505899735615, 'y': -0.0006545205888310243},
             2: {'osmid': 2, 's2id': 384307157539499829, 'x': -0.00716977739835831, 'y': -0.0006545205888310243}}

    generated_nodes = osm_reader.generate_graph_nodes(nodes, epsg='epsg:27700')
    assert_semantically_equal(generated_nodes, {
        '0': {'id': '0', 'x': 623528.0918284899, 'y': -5527136.199112928, 'lat': -0.0006545205888310243,
              'lon': 0.008554364250688652, 's2_id': 1152921492875543713},
        '1': {'id': '1', 'x': 625278.7312853877, 'y': -5527136.1998170335, 'lat': -0.0006545205888310243,
              'lon': 0.024278505899735615, 's2_id': 1152921335974974453},
        '2': {'id': '2', 'x': 621777.4693340246, 'y': -5527136.198414324, 'lat': -0.0006545205888310243,
              'lon': -0.00716977739835831, 's2_id': 384307157539499829}})


def test_generate_graph_edges():
    edges = [((0, 1), {'osmid': 0, 'modes': ['car', 'walk', 'bike'], 'highway': 'unclassified',
                       'length': 1748.4487354464366}), ((1, 0), {'osmid': 0, 'modes': ['car', 'walk', 'bike'],
                                                                 'highway': 'unclassified',
                                                                 'length': 1748.4487354464366}), ((0, 2),
                                                                                                  {'osmid': 100,
                                                                                                   'modes': [
                                                                                                       'car',
                                                                                                       'walk',
                                                                                                       'bike'],
                                                                                                   'highway': 'unclassified',
                                                                                                   'length': 1748.4488584600201}),
             ((2, 0), {'osmid': 100, 'modes': ['car', 'walk', 'bike'], 'highway': 'unclassified',
                       'length': 1748.4488584600201}), ((1, 0), {'osmid': 400, 'modes': ['car', 'walk', 'bike'],
                                                                 'highway': 'unclassified',
                                                                 'length': 1748.4487354464366}), ((0, 1),
                                                                                                  {'osmid': 400,
                                                                                                   'modes': [
                                                                                                       'car',
                                                                                                       'walk',
                                                                                                       'bike'],
                                                                                                   'highway': 'unclassified',
                                                                                                   'length': 1748.4487354464366}),
             ((2, 0), {'osmid': 700, 'modes': ['car', 'walk', 'bike'], 'highway': 'unclassified',
                       'length': 1748.4488584600201}), ((0, 2), {'osmid': 700, 'modes': ['car', 'walk', 'bike'],
                                                                 'highway': 'unclassified',
                                                                 'length': 1748.4488584600201})]

    generated_edges = osm_reader.generate_graph_edges(
        edges,
        reindexing_dict={},
        config_path=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "genet", "configs", "OSM", "default_config.yml")),
        nodes_and_attributes={
            '0': {'id': '0', 'x': 622502.8306679451, 'y': -5526117.781903352, 'lat': 0.008554364250688652,
                  'lon': -0.0006545205888310243, 's2_id': 1152921492875543713},
            '1': {'id': '1', 'x': 622502.8132744529, 'y': -5524378.838447345, 'lat': 0.024278505899735615,
                  'lon': -0.0006545205888310243, 's2_id': 1152921335974974453},
            '2': {'id': '2', 'x': 622502.8314014417, 'y': -5527856.725358106, 'lat': -0.00716977739835831,
                  'lon': -0.0006545205888310243, 's2_id': 384307157539499829}}
    )
    assert_semantically_equal(generated_edges, [
        {'permlanes': 1.0, 'freespeed': 12.5, 'capacity': 600.0, 'oneway': '1', 'modes': ['car', 'walk', 'bike'],
         'from': '0', 'to': '1', 's2_from': 1152921492875543713, 's2_to': 1152921335974974453,
         'length': 1748.4487354464366,
         'attributes': {'osm:way:osmid': {'name': 'osm:way:osmid', 'class': 'java.lang.String', 'text': '0'},
                        'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String',
                                            'text': 'unclassified'}}},
        {'permlanes': 1.0, 'freespeed': 12.5, 'capacity': 600.0, 'oneway': '1', 'modes': ['car', 'walk', 'bike'],
         'from': '1', 'to': '0', 's2_from': 1152921335974974453, 's2_to': 1152921492875543713,
         'length': 1748.4487354464366,
         'attributes': {'osm:way:osmid': {'name': 'osm:way:osmid', 'class': 'java.lang.String', 'text': '0'},
                        'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String',
                                            'text': 'unclassified'}}},
        {'permlanes': 1.0, 'freespeed': 12.5, 'capacity': 600.0, 'oneway': '1', 'modes': ['car', 'walk', 'bike'],
         'from': '0', 'to': '2', 's2_from': 1152921492875543713, 's2_to': 384307157539499829,
         'length': 1748.4488584600201,
         'attributes': {'osm:way:osmid': {'name': 'osm:way:osmid', 'class': 'java.lang.String', 'text': '100'},
                        'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String',
                                            'text': 'unclassified'}}},
        {'permlanes': 1.0, 'freespeed': 12.5, 'capacity': 600.0, 'oneway': '1', 'modes': ['car', 'walk', 'bike'],
         'from': '2', 'to': '0', 's2_from': 384307157539499829, 's2_to': 1152921492875543713,
         'length': 1748.4488584600201,
         'attributes': {'osm:way:osmid': {'name': 'osm:way:osmid', 'class': 'java.lang.String', 'text': '100'},
                        'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String',
                                            'text': 'unclassified'}}},
        {'permlanes': 1.0, 'freespeed': 12.5, 'capacity': 600.0, 'oneway': '1', 'modes': ['car', 'walk', 'bike'],
         'from': '1', 'to': '0', 's2_from': 1152921335974974453, 's2_to': 1152921492875543713,
         'length': 1748.4487354464366,
         'attributes': {'osm:way:osmid': {'name': 'osm:way:osmid', 'class': 'java.lang.String', 'text': '400'},
                        'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String',
                                            'text': 'unclassified'}}},
        {'permlanes': 1.0, 'freespeed': 12.5, 'capacity': 600.0, 'oneway': '1', 'modes': ['car', 'walk', 'bike'],
         'from': '0', 'to': '1', 's2_from': 1152921492875543713, 's2_to': 1152921335974974453,
         'length': 1748.4487354464366,
         'attributes': {'osm:way:osmid': {'name': 'osm:way:osmid', 'class': 'java.lang.String', 'text': '400'},
                        'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String',
                                            'text': 'unclassified'}}},
        {'permlanes': 1.0, 'freespeed': 12.5, 'capacity': 600.0, 'oneway': '1', 'modes': ['car', 'walk', 'bike'],
         'from': '2', 'to': '0', 's2_from': 384307157539499829, 's2_to': 1152921492875543713,
         'length': 1748.4488584600201,
         'attributes': {'osm:way:osmid': {'name': 'osm:way:osmid', 'class': 'java.lang.String', 'text': '700'},
                        'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String',
                                            'text': 'unclassified'}}},
        {'permlanes': 1.0, 'freespeed': 12.5, 'capacity': 600.0, 'oneway': '1', 'modes': ['car', 'walk', 'bike'],
         'from': '0', 'to': '2', 's2_from': 1152921492875543713, 's2_to': 384307157539499829,
         'length': 1748.4488584600201,
         'attributes': {'osm:way:osmid': {'name': 'osm:way:osmid', 'class': 'java.lang.String', 'text': '700'},
                        'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String',
                                            'text': 'unclassified'}}}])


def test_generate_graph_edges_with_node_reindexing():
    edges = [((0, 1), {'osmid': 0, 'modes': ['car', 'walk', 'bike'], 'highway': 'unclassified',
                       'length': 1748.4487354464366}),
             ((1, 0), {'osmid': 0, 'modes': ['car', 'walk', 'bike'], 'highway': 'unclassified',
                       'length': 1748.4487354464366})]

    generated_edges = osm_reader.generate_graph_edges(
        edges,
        reindexing_dict={'0': '10', '1': '11'},
        config_path=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "genet", "configs", "OSM", "default_config.yml")),
        nodes_and_attributes={
            '10': {'id': '0', 'x': 622502.8306679451, 'y': -5526117.781903352, 'lat': 0.008554364250688652,
                   'lon': -0.0006545205888310243, 's2_id': 1152921492875543713},
            '11': {'id': '1', 'x': 622502.8132744529, 'y': -5524378.838447345, 'lat': 0.024278505899735615,
                   'lon': -0.0006545205888310243, 's2_id': 1152921335974974453}}
    )
    assert_semantically_equal(generated_edges, [
        {'permlanes': 1.0, 'freespeed': 12.5, 'capacity': 600.0, 'oneway': '1', 'modes': ['car', 'walk', 'bike'],
         'from': '10', 'to': '11', 's2_from': 1152921492875543713, 's2_to': 1152921335974974453,
         'length': 1748.4487354464366,
         'attributes': {'osm:way:osmid': {'name': 'osm:way:osmid', 'class': 'java.lang.String', 'text': '0'},
                        'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String',
                                            'text': 'unclassified'}}},
        {'permlanes': 1.0, 'freespeed': 12.5, 'capacity': 600.0, 'oneway': '1', 'modes': ['car', 'walk', 'bike'],
         'from': '11', 'to': '10', 's2_from': 1152921335974974453, 's2_to': 1152921492875543713,
         'length': 1748.4487354464366,
         'attributes': {'osm:way:osmid': {'name': 'osm:way:osmid', 'class': 'java.lang.String', 'text': '0'},
                        'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String',
                                            'text': 'unclassified'}}}])
