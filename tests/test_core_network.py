import os
import sys
import ast
import uuid
import pandas as pd
import networkx as nx
import pytest
from pandas.testing import assert_frame_equal, assert_series_equal
from tests.fixtures import route, stop_epsg_27700, network_object_from_test_data, assert_semantically_equal, \
    full_fat_default_config_path, correct_schedule
from genet.inputs_handler import matsim_reader
from genet.core import Network
from genet.schedule_elements import Route, Service, Schedule
from genet.utils import plot

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
pt2matsim_network_test_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "network.xml"))
pt2matsim_schedule_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "schedule.xml"))


@pytest.fixture()
def network1():
    n1 = Network('epsg:27700')
    n1.add_node('101982',
                {'id': '101982',
                 'x': '528704.1425925883',
                 'y': '182068.78193707118',
                 'lon': -0.14625948709424305,
                 'lat': 51.52287873323954,
                 's2_id': 5221390329378179879})
    n1.add_node('101986',
                {'id': '101986',
                 'x': '528835.203274008',
                 'y': '182006.27331298392',
                 'lon': -0.14439428709377497,
                 'lat': 51.52228713323965,
                 's2_id': 5221390328605860387})
    n1.add_link('0', '101982', '101986',
                attribs={'id': '0',
                         'from': '101982',
                         'to': '101986',
                         'freespeed': 4.166666666666667,
                         'capacity': 600.0,
                         'permlanes': 1.0,
                         'oneway': '1',
                         'modes': ['car'],
                         's2_from': 5221390329378179879,
                         's2_to': 5221390328605860387,
                         'length': 52.765151087870265,
                         'attributes': {'osm:way:access': {'name': 'osm:way:access',
                                                           'class': 'java.lang.String',
                                                           'text': 'permissive'},
                                        'osm:way:highway': {'name': 'osm:way:highway',
                                                            'class': 'java.lang.String',
                                                            'text': 'unclassified'},
                                        'osm:way:id': {'name': 'osm:way:id',
                                                       'class': 'java.lang.Long',
                                                       'text': '26997928'},
                                        'osm:way:name': {'name': 'osm:way:name',
                                                         'class': 'java.lang.String',
                                                         'text': 'Brunswick Place'}}})
    return n1


@pytest.fixture()
def network2():
    n2 = Network('epsg:4326')
    n2.add_node('101982',
                {'id': '101982',
                 'x': -0.14625948709424305,
                 'y': 51.52287873323954,
                 'lon': -0.14625948709424305,
                 'lat': 51.52287873323954,
                 's2_id': 5221390329378179879})
    n2.add_node('101990',
                {'id': '101990',
                 'x': -0.14770188709624754,
                 'y': 51.5205729332399,
                 'lon': -0.14770188709624754,
                 'lat': 51.5205729332399,
                 's2_id': 5221390304444511271})
    n2.add_link('0', '101982', '101990',
                attribs={'id': '0',
                         'from': '101982',
                         'to': '101990',
                         'freespeed': 4.166666666666667,
                         'capacity': 600.0,
                         'permlanes': 1.0,
                         'oneway': '1',
                         'modes': ['car'],
                         's2_from': 5221390329378179879,
                         's2_to': 5221390304444511271,
                         'length': 52.765151087870265,
                         'attributes': {'osm:way:access': {'name': 'osm:way:access',
                                                           'class': 'java.lang.String',
                                                           'text': 'permissive'},
                                        'osm:way:highway': {'name': 'osm:way:highway',
                                                            'class': 'java.lang.String',
                                                            'text': 'unclassified'},
                                        'osm:way:id': {'name': 'osm:way:id',
                                                       'class': 'java.lang.Long',
                                                       'text': '26997928'},
                                        'osm:way:name': {'name': 'osm:way:name',
                                                         'class': 'java.lang.String',
                                                         'text': 'Brunswick Place'}}})
    return n2


def test__repr__shows_graph_info_and_schedule_info():
    n = Network('epsg:4326')
    assert 'instance at' in n.__repr__()
    assert 'graph' in n.__repr__()
    assert 'schedule' in n.__repr__()


def test__str__shows_info():
    n = Network('epsg:4326')
    assert 'Graph info' in n.__str__()
    assert 'Schedule info' in n.__str__()


def test_reproject_changes_x_y_values_for_all_nodes(network1):
    network1.reproject('epsg:4326')
    nodes = dict(network1.nodes())
    correct_nodes = {
        '101982': {'id': '101982', 'x': 51.52287873323954, 'y': -0.14625948709424305, 'lon': -0.14625948709424305,
                   'lat': 51.52287873323954, 's2_id': 5221390329378179879},
        '101986': {'id': '101986', 'x': 51.52228713323965, 'y': -0.14439428709377497, 'lon': -0.14439428709377497,
                   'lat': 51.52228713323965, 's2_id': 5221390328605860387}}

    target_change_log = pd.DataFrame(
        {'timestamp': {3: '2020-07-09 19:50:51', 4: '2020-07-09 19:50:51'}, 'change_event': {3: 'modify', 4: 'modify'},
         'object_type': {3: 'node', 4: 'node'}, 'old_id': {3: '101982', 4: '101986'},
         'new_id': {3: '101982', 4: '101986'}, 'old_attributes': {
            3: "{'id': '101982', 'x': '528704.1425925883', 'y': '182068.78193707118', 'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879}",
            4: "{'id': '101986', 'x': '528835.203274008', 'y': '182006.27331298392', 'lon': -0.14439428709377497, 'lat': 51.52228713323965, 's2_id': 5221390328605860387}"},
         'new_attributes': {
             3: "{'id': '101982', 'x': 51.52287873323954, 'y': -0.14625948709424305, 'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879}",
             4: "{'id': '101986', 'x': 51.52228713323965, 'y': -0.14439428709377497, 'lon': -0.14439428709377497, 'lat': 51.52228713323965, 's2_id': 5221390328605860387}"},
         'diff': {3: [('change', 'x', ('528704.1425925883', 51.52287873323954)),
                      ('change', 'y', ('182068.78193707118', -0.14625948709424305))],
                  4: [('change', 'x', ('528835.203274008', 51.52228713323965)),
                      ('change', 'y', ('182006.27331298392', -0.14439428709377497))]}}
    )
    assert_semantically_equal(nodes, correct_nodes)
    for i in [3, 4]:
        assert_semantically_equal(ast.literal_eval(target_change_log.loc[i, 'old_attributes']),
                                  ast.literal_eval(network1.change_log.log.loc[i, 'old_attributes']))
        assert_semantically_equal(ast.literal_eval(target_change_log.loc[i, 'new_attributes']),
                                  ast.literal_eval(network1.change_log.log.loc[i, 'new_attributes']))
    cols_to_compare = ['change_event', 'object_type', 'old_id', 'new_id', 'diff']
    assert_frame_equal(network1.change_log.log[cols_to_compare].tail(2), target_change_log[cols_to_compare],
                       check_dtype=False)


def test_reproject_delegates_reprojection_to_schedules_own_method(network1, route, mocker):
    mocker.patch.object(Schedule, 'reproject')
    network1.schedule = Schedule(epsg='epsg:27700', services=[Service(id='id', routes=[route])])
    network1.reproject('epsg:4326')
    network1.schedule.reproject.assert_called_once_with('epsg:4326', 1)


def test_adding_the_same_networks():
    n_left = Network('epsg:27700')
    n_left.add_node('1', {'id': '1', 'x': 528704.1425925883, 'y': 182068.78193707118,
                          'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879})
    n_left.add_node('2', {'id': '2', 'x': 528835.203274008, 'y': 182006.27331298392,
                          'lon': -0.14439428709377497, 'lat': 51.52228713323965, 's2_id': 5221390328605860387})
    n_left.add_link('1', '1', '2', attribs={'modes': ['walk']})

    n_right = Network('epsg:27700')
    n_right.add_node('1', {'id': '1', 'x': 528704.1425925883, 'y': 182068.78193707118,
                           'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879})
    n_right.add_node('2', {'id': '2', 'x': 528835.203274008, 'y': 182006.27331298392,
                           'lon': -0.14439428709377497, 'lat': 51.52228713323965, 's2_id': 5221390328605860387})
    n_right.add_link('1', '1', '2', attribs={'modes': ['walk']})

    n_left.add(n_right)
    assert_semantically_equal(dict(n_left.nodes()), {
        '1': {'id': '1', 'x': 528704.1425925883, 'y': 182068.78193707118, 'lon': -0.14625948709424305,
              'lat': 51.52287873323954, 's2_id': 5221390329378179879},
        '2': {'id': '2', 'x': 528835.203274008, 'y': 182006.27331298392, 'lon': -0.14439428709377497,
              'lat': 51.52228713323965, 's2_id': 5221390328605860387}})
    assert_semantically_equal(dict(n_left.links()), {'1': {'modes': ['walk'], 'from': '1', 'to': '2', 'id': '1'}})


def test_adding_the_same_networks_but_with_differing_projections():
    n_left = Network('epsg:27700')
    n_left.add_node('1', {'id': '1', 'x': 528704.1425925883, 'y': 182068.78193707118,
                          'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879})
    n_left.add_node('2', {'id': '2', 'x': 528835.203274008, 'y': 182006.27331298392,
                          'lon': -0.14439428709377497, 'lat': 51.52228713323965, 's2_id': 5221390328605860387})
    n_left.add_link('1', '1', '2', attribs={'modes': ['walk']})

    n_right = Network('epsg:27700')
    n_right.add_node('1', {'id': '1', 'x': 528704.1425925883, 'y': 182068.78193707118,
                           'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879})
    n_right.add_node('2', {'id': '2', 'x': 528835.203274008, 'y': 182006.27331298392,
                           'lon': -0.14439428709377497, 'lat': 51.52228713323965, 's2_id': 5221390328605860387})
    n_right.add_link('1', '1', '2', attribs={'modes': ['walk']})
    n_right.reproject('epsg:4326')

    n_left.add(n_right)
    assert_semantically_equal(dict(n_left.nodes()), {
        '1': {'id': '1', 'x': 528704.1425925883, 'y': 182068.78193707118, 'lon': -0.14625948709424305,
              'lat': 51.52287873323954, 's2_id': 5221390329378179879},
        '2': {'id': '2', 'x': 528835.203274008, 'y': 182006.27331298392, 'lon': -0.14439428709377497,
              'lat': 51.52228713323965, 's2_id': 5221390328605860387}})
    assert_semantically_equal(dict(n_left.links()), {'1': {'modes': ['walk'], 'from': '1', 'to': '2', 'id': '1'}})


def test_adding_networks_with_clashing_node_ids():
    n_left = Network('epsg:27700')
    n_left.add_node('1', {'id': '1', 'x': 528704.1425925883, 'y': 182068.78193707118,
                          'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879})
    n_left.add_node('2', {'id': '2', 'x': 528835.203274008, 'y': 182006.27331298392,
                          'lon': -0.14439428709377497, 'lat': 51.52228713323965, 's2_id': 5221390328605860387})
    n_left.add_link('1', '1', '2', attribs={'modes': ['walk']})

    n_right = Network('epsg:27700')
    n_right.add_node('10', {'id': '1', 'x': 528704.1425925883, 'y': 182068.78193707118,
                            'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879})
    n_right.add_node('20', {'id': '2', 'x': 528835.203274008, 'y': 182006.27331298392,
                            'lon': -0.14439428709377497, 'lat': 51.52228713323965, 's2_id': 5221390328605860387})
    n_right.add_link('1', '10', '20', attribs={'modes': ['walk']})

    n_left.add(n_right)
    assert_semantically_equal(dict(n_left.nodes()), {
        '1': {'id': '1', 'x': 528704.1425925883, 'y': 182068.78193707118, 'lon': -0.14625948709424305,
              'lat': 51.52287873323954, 's2_id': 5221390329378179879},
        '2': {'id': '2', 'x': 528835.203274008, 'y': 182006.27331298392, 'lon': -0.14439428709377497,
              'lat': 51.52228713323965, 's2_id': 5221390328605860387}})
    assert_semantically_equal(dict(n_left.links()), {'1': {'modes': ['walk'], 'from': '1', 'to': '2', 'id': '1'}})


def test_adding_networks_with_clashing_link_ids():
    n_left = Network('epsg:27700')
    n_left.add_node('1', {'id': '1', 'x': 528704.1425925883, 'y': 182068.78193707118,
                          'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879})
    n_left.add_node('2', {'id': '2', 'x': 528835.203274008, 'y': 182006.27331298392,
                          'lon': -0.14439428709377497, 'lat': 51.52228713323965, 's2_id': 5221390328605860387})
    n_left.add_link('1', '1', '2', attribs={'modes': ['walk']})

    n_right = Network('epsg:27700')
    n_right.add_node('1', {'id': '1', 'x': 528704.1425925883, 'y': 182068.78193707118,
                           'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879})
    n_right.add_node('2', {'id': '2', 'x': 528835.203274008, 'y': 182006.27331298392,
                           'lon': -0.14439428709377497, 'lat': 51.52228713323965, 's2_id': 5221390328605860387})
    n_right.add_link('10', '1', '2', attribs={'modes': ['walk']})

    n_left.add(n_right)
    assert_semantically_equal(dict(n_left.nodes()), {
        '1': {'id': '1', 'x': 528704.1425925883, 'y': 182068.78193707118, 'lon': -0.14625948709424305,
              'lat': 51.52287873323954, 's2_id': 5221390329378179879},
        '2': {'id': '2', 'x': 528835.203274008, 'y': 182006.27331298392, 'lon': -0.14439428709377497,
              'lat': 51.52228713323965, 's2_id': 5221390328605860387}})
    assert_semantically_equal(dict(n_left.links()), {'1': {'modes': ['walk'], 'from': '1', 'to': '2', 'id': '1'}})


def test_adding_networks_with_clashing_multiindices():
    n_left = Network('epsg:27700')
    n_left.add_node('1', {'id': '1', 'x': 528704.1425925883, 'y': 182068.78193707118,
                          'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879})
    n_left.add_node('2', {'id': '2', 'x': 528835.203274008, 'y': 182006.27331298392,
                          'lon': -0.14439428709377497, 'lat': 51.52228713323965, 's2_id': 5221390328605860387})
    n_left.add_link('1', '1', '2', 0, attribs={'modes': ['walk']})

    n_right = Network('epsg:27700')
    n_left.add_node('1', {'id': '1', 'x': 528704.1425925883, 'y': 182068.78193707118,
                          'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879})
    n_left.add_node('2', {'id': '2', 'x': 528835.203274008, 'y': 182006.27331298392,
                          'lon': -0.14439428709377497, 'lat': 51.52228713323965, 's2_id': 5221390328605860387})
    n_left.add_link('1', '1', '2', 0, attribs={'modes': ['walk', 'bike']})

    n_left.add(n_right)
    assert len(list(n_left.nodes())) == 2
    assert n_left.node('1') == {'id': '1', 'x': 528704.1425925883, 'y': 182068.78193707118,
                                'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879}
    assert n_left.node('2') == {'id': '2', 'x': 528835.203274008, 'y': 182006.27331298392,
                                'lon': -0.14439428709377497, 'lat': 51.52228713323965, 's2_id': 5221390328605860387}
    assert len(n_left.link_id_mapping) == 2
    assert n_left.link('1') == {'modes': ['walk'], 'from': '1', 'to': '2', 'id': '1'}
    assert n_left.graph['1']['2'][0] == {'modes': ['walk'], 'from': '1', 'to': '2', 'id': '1'}


def test_adding_disjoint_networks_with_unique_ids():
    n_left = Network('epsg:27700')
    n_left.add_node('1', {'id': '1', 'x': 528704.1425925883, 'y': 182068.78193707118,
                          'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879})
    n_left.add_node('2', {'id': '2', 'x': 528835.203274008, 'y': 182006.27331298392,
                          'lon': -0.14439428709377497, 'lat': 51.52228713323965, 's2_id': 5221390328605860387})
    n_left.add_link('1', '1', '2', attribs={'modes': ['walk']})

    n_right = Network('epsg:27700')
    n_right.add_node('10', {'id': '1', 'x': 1, 'y': 1,
                            'lon': 1, 'lat': 1, 's2_id': 1})
    n_right.add_node('20', {'id': '2', 'x': 1, 'y': 1,
                            'lon': 1, 'lat': 1, 's2_id': 2})
    n_right.add_link('100', '10', '20', attribs={'modes': ['walk']})

    n_left.add(n_right)
    assert_semantically_equal(dict(n_left.nodes()), {'10': {'id': '1', 'x': 1, 'y': 1, 'lon': 1, 'lat': 1, 's2_id': 1},
                                                     '20': {'id': '2', 'x': 1, 'y': 1, 'lon': 1, 'lat': 1, 's2_id': 2},
                                                     '1': {'id': '1', 'x': 528704.1425925883, 'y': 182068.78193707118,
                                                           'lon': -0.14625948709424305, 'lat': 51.52287873323954,
                                                           's2_id': 5221390329378179879},
                                                     '2': {'id': '2', 'x': 528835.203274008, 'y': 182006.27331298392,
                                                           'lon': -0.14439428709377497, 'lat': 51.52228713323965,
                                                           's2_id': 5221390328605860387}})
    assert_semantically_equal(dict(n_left.links()), {'100': {'modes': ['walk'], 'from': '10', 'to': '20', 'id': '100'},
                                                     '1': {'modes': ['walk'], 'from': '1', 'to': '2', 'id': '1'}})


def test_adding_disjoint_networks_with_clashing_ids():
    n_left = Network('epsg:27700')
    n_left.add_node('1', {'id': '1', 'x': 528704.1425925883, 'y': 182068.78193707118,
                          'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879})
    n_left.add_node('2', {'id': '2', 'x': 528835.203274008, 'y': 182006.27331298392,
                          'lon': -0.14439428709377497, 'lat': 51.52228713323965, 's2_id': 5221390328605860387})
    n_left.add_link('1', '1', '2', attribs={'modes': ['walk']})

    n_right = Network('epsg:27700')
    n_right.add_node('1', {'id': '1', 'x': 1, 'y': 1,
                           'lon': 1, 'lat': 1, 's2_id': 1})
    n_right.add_node('2', {'id': '2', 'x': 1, 'y': 1,
                           'lon': 1, 'lat': 1, 's2_id': 2})
    n_right.add_link('1', '1', '2', attribs={'modes': ['walk']})

    n_left.add(n_right)
    assert len(list(n_left.nodes())) == 4
    assert n_left.node('1') == {'id': '1', 'x': 528704.1425925883, 'y': 182068.78193707118,
                                'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879}
    assert n_left.node('2') == {'id': '2', 'x': 528835.203274008, 'y': 182006.27331298392,
                                'lon': -0.14439428709377497, 'lat': 51.52228713323965, 's2_id': 5221390328605860387}
    assert len(n_left.link_id_mapping) == 2
    assert n_left.link('1') == {'modes': ['walk'], 'from': '1', 'to': '2', 'id': '1'}


def test_print_shows_info(mocker):
    mocker.patch.object(Network, 'info')
    n = Network('epsg:27700')
    n.print()
    n.info.assert_called_once()


def test_plot_delegates_to_util_plot_plot_graph_routes(mocker):
    mocker.patch.object(plot, 'plot_graph_routes')
    n = Network('epsg:27700')
    n.plot()
    plot.plot_graph_routes.assert_called_once()


def test_plot_graph_delegates_to_util_plot_plot_graph(mocker):
    mocker.patch.object(plot, 'plot_graph')
    n = Network('epsg:27700')
    n.plot_graph()
    plot.plot_graph.assert_called_once()


def test_plot_schedule_delegates_to_util_plot_plot_non_routed_schedule_graph(mocker, network_object_from_test_data):
    mocker.patch.object(plot, 'plot_non_routed_schedule_graph')
    n = network_object_from_test_data
    n.plot_schedule()
    plot.plot_non_routed_schedule_graph.assert_called_once()


def test_node_attribute_data_under_key_returns_correct_pd_series_with_nested_keys():
    n = Network('epsg:27700')
    n.add_node(1, {'a': {'b': 1}})
    n.add_node(2, {'a': {'b': 4}})

    output_series = n.node_attribute_data_under_key(key={'a': 'b'})
    assert_series_equal(output_series, pd.Series({1: 1, 2: 4}))


def test_node_attribute_data_under_key_returns_correct_pd_series_with_flat_keys():
    n = Network('epsg:27700')
    n.add_node(1, {'b': 1})
    n.add_node(2, {'b': 4})

    output_series = n.node_attribute_data_under_key(key='b')
    assert_series_equal(output_series, pd.Series({1: 1, 2: 4}))


def test_node_attribute_data_under_keys(network1):
    df = network1.node_attribute_data_under_keys(['x', 'y'])

    df_to_compare = pd.DataFrame({'x': {'101982': '528704.1425925883', '101986': '528835.203274008'},
                                  'y': {'101982': '182068.78193707118', '101986': '182006.27331298392'}})

    assert_frame_equal(df, df_to_compare)


def test_node_attribute_data_under_keys_with_named_index(network1):
    df = network1.node_attribute_data_under_keys(['x', 'y'], index_name='index')
    assert df.index.name == 'index'


def test_node_attribute_data_under_keys_generates_key_for_nested_data(network1):
    network1.add_node('1', {'key': {'nested_value': {'more_nested': 4}}})
    df = network1.node_attribute_data_under_keys([{'key': {'nested_value': 'more_nested'}}])
    assert isinstance(df, pd.DataFrame)
    assert 'key::nested_value::more_nested' in df.columns


def test_node_attribute_data_under_keys_returns_dataframe_with_one_col_if_passed_one_key(network1):
    df = network1.node_attribute_data_under_keys(['x'], index_name='index')
    assert isinstance(df, pd.DataFrame)
    assert len(df.columns) == 1


def test_link_attribute_data_under_key_returns_correct_pd_series_with_nested_keys():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'a': {'b': 1}})
    n.add_link('1', 1, 2, attribs={'a': {'b': 4}})

    output_series = n.link_attribute_data_under_key(key={'a': 'b'})
    assert_series_equal(output_series, pd.Series({'0': 1, '1': 4}))


def test_link_attribute_data_under_key_returns_correct_pd_series_with_flat_keys():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'b': 1})
    n.add_link('1', 1, 2, attribs={'b': 4})

    output_series = n.link_attribute_data_under_key(key='b')
    assert_series_equal(output_series, pd.Series({'0': 1, '1': 4}))


def test_link_attribute_data_under_keys(network1):
    df = network1.link_attribute_data_under_keys(['modes', 'freespeed', 'capacity', 'permlanes'])

    df_to_compare = pd.DataFrame({'modes': {'0': ['car']}, 'freespeed': {'0': 4.166666666666667},
                                  'capacity': {'0': 600.0}, 'permlanes': {'0': 1.0}})

    assert_frame_equal(df, df_to_compare)


def test_link_attribute_data_under_keys_with_named_index(network1):
    df = network1.link_attribute_data_under_keys(['modes', 'freespeed', 'capacity', 'permlanes'], index_name='index')
    assert df.index.name == 'index'


def test_link_attribute_data_under_keys_returns_dataframe_with_one_col_if_passed_one_key(network1):
    df = network1.link_attribute_data_under_keys(['modes'])
    assert isinstance(df, pd.DataFrame)
    assert len(df.columns) == 1


def test_link_attribute_data_under_keys_generates_key_for_nested_data(network1):
    df = network1.link_attribute_data_under_keys([{'attributes': {'osm:way:access': 'text'}}])
    assert isinstance(df, pd.DataFrame)
    assert 'attributes::osm:way:access::text' in df.columns


def test_add_node_adds_node_to_graph_with_attribs():
    n = Network('epsg:27700')
    n.add_node(1, {'a': 1})
    assert n.graph.has_node(1)
    assert n.node(1) == {'a': 1}


def test_add_node_adds_node_to_graph_without_attribs():
    n = Network('epsg:27700')
    n.add_node(1)
    assert n.node(1) == {}
    assert n.graph.has_node(1)


def test_add_multiple_nodes():
    n = Network('epsg:27700')
    reindexing_dict, actual_nodes_added = n.add_nodes({1: {'x': 1, 'y': 2}, 2: {'x': 2, 'y': 2}})
    assert n.graph.has_node(1)
    assert n.node(1) == {'x': 1, 'y': 2, 'id': 1}
    assert n.graph.has_node(2)
    assert n.node(2) == {'x': 2, 'y': 2, 'id': 2}
    assert reindexing_dict == {}


def test_add_nodes_with_clashing_ids():
    n = Network('epsg:27700')
    n.add_node(1, {})
    reindexing_dict, actual_nodes_added = n.add_nodes({1: {'x': 1, 'y': 2}, 2: {'x': 2, 'y': 2}})
    assert n.graph.has_node(1)
    assert n.node(1) == {}
    assert n.graph.has_node(2)
    assert n.node(2) == {'x': 2, 'y': 2, 'id': 2}
    assert 1 in reindexing_dict
    assert n.graph.has_node(reindexing_dict[1])
    assert n.node(reindexing_dict[1]) == {'x': 1, 'y': 2, 'id': reindexing_dict[1]}


def test_add_nodes_with_multiple_clashing_ids():
    n = Network('epsg:27700')
    n.add_node(1, {})
    n.add_node(2, {})
    assert n.graph.has_node(1)
    assert n.node(1) == {}
    assert n.graph.has_node(2)
    assert n.node(2) == {}

    reindexing_dict, actual_nodes_added = n.add_nodes({1: {'x': 1, 'y': 2}, 2: {'x': 2, 'y': 2}})
    assert 1 in reindexing_dict
    assert n.graph.has_node(reindexing_dict[1])
    assert n.node(reindexing_dict[1]) == {'x': 1, 'y': 2, 'id': reindexing_dict[1]}

    assert 2 in reindexing_dict
    assert n.graph.has_node(reindexing_dict[2])
    assert n.node(reindexing_dict[2]) == {'x': 2, 'y': 2, 'id': reindexing_dict[2]}


def test_add_edge_generates_a_link_id_and_delegated_to_add_link_id(mocker):
    mocker.patch.object(Network, 'add_link')
    mocker.patch.object(Network, 'generate_index_for_edge', return_value='12345')
    n = Network('epsg:27700')
    n.add_edge(1, 2, attribs={'a': 1})

    Network.generate_index_for_edge.assert_called_once()
    Network.add_link.assert_called_once_with('12345', 1, 2, None, {'a': 1}, False)


def test_add_edge_generates_a_link_id_with_specified_multiidx(mocker):
    mocker.patch.object(Network, 'add_link')
    mocker.patch.object(Network, 'generate_index_for_edge', return_value='12345')
    n = Network('epsg:27700')
    n.add_edge(1, 2, multi_edge_idx=10, attribs={'a': 1})

    Network.generate_index_for_edge.assert_called_once()
    Network.add_link.assert_called_once_with('12345', 1, 2, 10, {'a': 1}, False)


def test_adding_multiple_edges():
    n = Network('epsg:27700')
    n.add_edges([{'from': 1, 'to': 2}, {'from': 2, 'to': 3}])
    assert n.graph.has_edge(1, 2)
    assert n.graph.has_edge(2, 3)
    assert '1' in n.link_id_mapping
    assert '2' in n.link_id_mapping
    if n.link_id_mapping['1'] == {'from': 1, 'to': 2, 'multi_edge_idx': 0}:
        assert n.link_id_mapping['2'] == {'from': 2, 'to': 3, 'multi_edge_idx': 0}
    elif n.link_id_mapping['2'] == {'from': 1, 'to': 2, 'multi_edge_idx': 0}:
        assert n.link_id_mapping['1'] == {'from': 2, 'to': 3, 'multi_edge_idx': 0}
    else:
        raise AssertionError()


def test_adding_multiple_edges_between_same_nodes():
    n = Network('epsg:27700')
    n.add_edges([{'from': 1, 'to': 2}, {'from': 1, 'to': 2}, {'from': 1, 'to': 2}, {'from': 2, 'to': 3}])
    assert n.graph.has_edge(1, 2)
    assert n.graph.number_of_edges(1, 2) == 3
    assert n.graph.has_edge(2, 3)
    assert len(n.link_id_mapping) == 4


def test_add_link_adds_edge_to_graph_with_attribs():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'a': 1})
    assert n.graph.has_edge(1, 2)
    assert '0' in n.link_id_mapping
    assert n.edge(1, 2) == {0: {'a': 1, 'from': 1, 'id': '0', 'to': 2}}


def test_add_link_adds_edge_to_graph_without_attribs():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2)
    n.graph.has_edge(1, 2)
    assert '0' in n.link_id_mapping
    assert n.link_id_mapping['0'] == {'from': 1, 'to': 2, 'multi_edge_idx': 0}


def test_adding_multiple_links():
    n = Network('epsg:27700')
    n.add_links({'0': {'from': 1, 'to': 2}, '1': {'from': 2, 'to': 3}})
    assert n.graph.has_edge(1, 2)
    assert n.graph.has_edge(2, 3)
    assert '0' in n.link_id_mapping
    assert '1' in n.link_id_mapping
    assert n.link_id_mapping['0'] == {'from': 1, 'to': 2, 'multi_edge_idx': 0}
    assert n.link_id_mapping['1'] == {'from': 2, 'to': 3, 'multi_edge_idx': 0}


def test_adding_multiple_links_with_id_clashes():
    n = Network('epsg:27700')
    n.add_link('0', 10, 20)
    assert '0' in n.link_id_mapping

    reindexing_dict, links_and_attribs = n.add_links({'0': {'from': 1, 'to': 2}, '1': {'from': 2, 'to': 3}})

    assert '1' in n.link_id_mapping
    assert '0' in reindexing_dict
    assert len(n.link_id_mapping) == 3

    assert_semantically_equal(links_and_attribs[reindexing_dict['0']], {'from': 1, 'to': 2, 'id': reindexing_dict['0']})
    assert_semantically_equal(links_and_attribs['1'], {'from': 2, 'to': 3, 'id': '1'})


def test_adding_multiple_links_with_multiple_id_clashes():
    n = Network('epsg:27700')
    n.add_link('0', 10, 20)
    n.add_link('1', 10, 20)
    assert '0' in n.link_id_mapping
    assert '1' in n.link_id_mapping

    reindexing_dict, links_and_attribs = n.add_links({'0': {'from': 1, 'to': 2}, '1': {'from': 2, 'to': 3}})

    assert '0' in reindexing_dict
    assert '1' in reindexing_dict
    assert len(n.link_id_mapping) == 4

    assert_semantically_equal(links_and_attribs[reindexing_dict['0']], {'from': 1, 'to': 2, 'id': reindexing_dict['0']})
    assert_semantically_equal(links_and_attribs[reindexing_dict['1']], {'from': 2, 'to': 3, 'id': reindexing_dict['1']})


def test_adding_loads_of_multiple_links_between_same_nodes():
    n = Network('epsg:27700')
    reindexing_dict, links_and_attribs = n.add_links({i: {'from': 1, 'to': 2} for i in range(10)})

    assert_semantically_equal(links_and_attribs, {i: {'from': 1, 'to': 2, 'id': i} for i in range(10)})
    assert_semantically_equal(n.link_id_mapping, {i: {'from': 1, 'to': 2, 'multi_edge_idx': i} for i in range(10)})


def test_adding_multiple_links_with_multi_idx_clashes():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2)
    n.add_link('1', 1, 2)
    assert '0' in n.link_id_mapping
    assert '1' in n.link_id_mapping

    n.add_links({'2': {'from': 1, 'to': 2}, '3': {'from': 1, 'to': 2}, '4': {'from': 2, 'to': 3}})

    assert n.link_id_mapping['2'] == {'from': 1, 'to': 2, 'multi_edge_idx': 2}
    assert n.link_id_mapping['3'] == {'from': 1, 'to': 2, 'multi_edge_idx': 3}
    assert n.link_id_mapping['4'] == {'from': 2, 'to': 3, 'multi_edge_idx': 0}


def test_adding_multiple_links_with_id_and_multi_idx_clashes():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2)
    n.add_link('1', 1, 2)
    assert '0' in n.link_id_mapping
    assert '1' in n.link_id_mapping

    reindexing_dict, links_and_attribs = n.add_links(
        {'0': {'from': 1, 'to': 2}, '1': {'from': 1, 'to': 2}, '2': {'from': 2, 'to': 3}})

    assert '0' in reindexing_dict
    assert '1' in reindexing_dict
    assert len(n.link_id_mapping) == 5

    assert_semantically_equal(n.link_id_mapping[reindexing_dict['0']], {'from': 1, 'to': 2, 'multi_edge_idx': 2})
    assert_semantically_equal(n.link_id_mapping[reindexing_dict['1']], {'from': 1, 'to': 2, 'multi_edge_idx': 3})


def test_adding_multiple_links_missing_some_from_nodes():
    n = Network('epsg:27700')
    with pytest.raises(RuntimeError) as error_info:
        n.add_links({'0': {'to': 2}, '1': {'from': 2, 'to': 3}})
    assert "You are trying to add links which are missing `from` (origin) nodes" in str(error_info.value)


def test_adding_multiple_links_missing_from_nodes_completely():
    n = Network('epsg:27700')
    with pytest.raises(RuntimeError) as error_info:
        n.add_links({'0': {'to': 2}, '1': {'to': 3}})
    assert "You are trying to add links which are missing `from` (origin) nodes" in str(error_info.value)


def test_adding_multiple_links_missing_some_to_nodes():
    n = Network('epsg:27700')
    with pytest.raises(RuntimeError) as error_info:
        n.add_links({'0': {'from': 2}, '1': {'from': 2, 'to': 3}})
    assert "You are trying to add links which are missing `to` (destination) nodes" in str(error_info.value)


def test_adding_multiple_links_missing_to_nodes_completely():
    n = Network('epsg:27700')
    with pytest.raises(RuntimeError) as error_info:
        n.add_links({'0': {'from': 2}, '1': {'from': 2}})
    assert "You are trying to add links which are missing `to` (destination) nodes" in str(error_info.value)


def test_network_modal_subgraph_using_general_subgraph_on_link_attribs():
    def modal_condition(modes_list):
        return set(modes_list) & {'car'}

    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'modes': ['car', 'bike']})
    n.add_link('1', 2, 3, attribs={'modes': ['car']})
    n.add_link('2', 2, 3, attribs={'modes': ['bike']})

    car_graph = n.subgraph_on_link_conditions(conditions={'modes': modal_condition})
    assert list(car_graph.edges) == [(1, 2, 0), (2, 3, 0)]


def test_network_modal_subgraph_using_specific_modal_subgraph_method_single_mode():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'modes': ['car', 'bike']})
    n.add_link('1', 2, 3, attribs={'modes': ['car']})
    n.add_link('2', 2, 3, attribs={'modes': ['bike']})

    car_graph = n.modal_subgraph(modes='car')
    assert list(car_graph.edges) == [(1, 2, 0), (2, 3, 0)]


def test_network_modal_subgraph_using_specific_modal_subgraph_method_several_modes():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'modes': ['car', 'bike']})
    n.add_link('1', 2, 3, attribs={'modes': ['car']})
    n.add_link('2', 2, 3, attribs={'modes': ['bike']})
    n.add_link('3', 2, 3, attribs={'modes': ['walk']})

    car_graph = n.modal_subgraph(modes=['car', 'bike'])
    assert list(car_graph.edges) == [(1, 2, 0), (2, 3, 0), (2, 3, 1)]


def test_find_shortest_path_when_graph_has_no_extra_edge_choices():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'modes': ['car', 'bike'], 'length': 1})
    n.add_link('1', 2, 3, attribs={'modes': ['car'], 'length': 1})
    n.add_link('2', 2, 3, attribs={'modes': ['bike'], 'length': 1})
    n.add_link('3', 2, 3, attribs={'modes': ['walk'], 'length': 1})

    bike_route = n.find_shortest_path(1, 3, modes='bike')
    assert bike_route == ['0', '2']


def test_find_shortest_path_when_subgraph_is_pre_computed():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'modes': ['car', 'bike'], 'length': 1})
    n.add_link('1', 2, 3, attribs={'modes': ['car'], 'length': 1})
    n.add_link('2', 2, 3, attribs={'modes': ['bike'], 'length': 1})
    n.add_link('3', 2, 3, attribs={'modes': ['walk'], 'length': 1})

    bike_g = n.modal_subgraph(modes='bike')

    bike_route = n.find_shortest_path(1, 3, subgraph=bike_g)
    assert bike_route == ['0', '2']


def test_find_shortest_path_defaults_to_full_graph():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'modes': ['car', 'bike'], 'length': 1})
    n.add_link('1', 2, 3, attribs={'modes': ['car'], 'freespeed': 3})
    n.add_link('2', 2, 3, attribs={'modes': ['bike'], 'freespeed': 2})
    n.add_link('3', 2, 3, attribs={'modes': ['walk'], 'freespeed': 1})

    bike_route = n.find_shortest_path(1, 3)
    assert bike_route == ['0', '1']


def test_find_shortest_path_when_graph_has_extra_edge_choice_for_freespeed_that_is_obvious():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'modes': ['car', 'bike'], 'length': 1, 'freespeed': 10})
    n.add_link('2', 2, 3, attribs={'modes': ['car', 'bike'], 'length': 1, 'freespeed': 10})
    n.add_link('3', 2, 3, attribs={'modes': ['car', 'bike'], 'length': 1, 'freespeed': 1})

    bike_route = n.find_shortest_path(1, 3, modes='bike')
    assert bike_route == ['0', '2']


def test_find_shortest_path_when_graph_has_extra_edge_choice_with_attractive_mode():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'modes': ['car', 'bike'], 'length': 1, 'freespeed': 10})
    n.add_link('2', 2, 3, attribs={'modes': ['car', 'bike'], 'length': 1, 'freespeed': 10})
    n.add_link('3', 2, 3, attribs={'modes': ['bike'], 'length': 1, 'freespeed': 1})

    bike_route = n.find_shortest_path(1, 3, modes='bike')
    assert bike_route == ['0', '3']


def test_find_shortest_path_and_return_just_nodes():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'modes': ['car', 'bike'], 'length': 1, 'freespeed': 10})
    n.add_link('1', 2, 3, attribs={'modes': ['car', 'bike'], 'length': 1, 'freespeed': 10})

    bike_route = n.find_shortest_path(1, 3, return_nodes=True)
    assert bike_route == [1, 2, 3]


def test_add_link_adds_link_with_specific_multi_idx():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, 0)
    assert '0' in n.link_id_mapping
    assert n.link_id_mapping['0'] == {'from': 1, 'to': 2, 'multi_edge_idx': 0}
    assert n.graph[1][2][0] == {'from': 1, 'to': 2, 'id': '0'}


def test_add_link_generates_new_multi_idx_if_already_exists():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, 0)
    n.add_link('1', 1, 2, 0)
    assert '0' in n.link_id_mapping
    assert '1' in n.link_id_mapping
    assert n.link_id_mapping['0'] == {'from': 1, 'to': 2, 'multi_edge_idx': 0}
    assert n.graph[1][2][0] == {'from': 1, 'to': 2, 'id': '0'}
    assert n.link_id_mapping['1']['multi_edge_idx'] != 0
    assert n.graph[1][2][n.link_id_mapping['1']['multi_edge_idx']] == {'from': 1, 'to': 2, 'id': '1'}


def test_reindex_node(network1):
    assert [id for id, attribs in network1.nodes()] == ['101982', '101986']
    assert [id for id, attribs in network1.links()] == ['0']
    assert network1.link('0')['from'] == '101982'
    assert network1.link('0')['to'] == '101986'
    assert [(from_n, to_n) for from_n, to_n, attribs in network1.edges()] == [('101982', '101986')]
    assert network1.link_id_mapping['0']['from'] == '101982'

    network1.reindex_node('101982', '007')

    assert [id for id, attribs in network1.nodes()] == ['007', '101986']
    assert [id for id, attribs in network1.links()] == ['0']
    assert network1.link('0')['from'] == '007'
    assert network1.link('0')['to'] == '101986'
    assert [(from_n, to_n) for from_n, to_n, attribs in network1.edges()] == [('007', '101986')]
    assert network1.link_id_mapping['0']['from'] == '007'

    correct_change_log_df = pd.DataFrame(
        {'timestamp': {3: '2020-06-08 19:39:08', 4: '2020-06-08 19:39:08', 5: '2020-06-08 19:39:08'},
         'change_event': {3: 'modify', 4: 'modify', 5: 'modify'}, 'object_type': {3: 'link', 4: 'node', 5: 'node'},
         'old_id': {3: '0', 4: '101982', 5: '101982'}, 'new_id': {3: '0', 4: '007', 5: '101982'}, 'old_attributes': {
            3: "{'id': '0', 'from': '101982', 'to': '101986', 'freespeed': 4.166666666666667, 'capacity': 600.0, 'permlanes': 1.0, 'oneway': '1', 'modes': ['car'], 's2_from': 5221390329378179879, 's2_to': 5221390328605860387, 'length': 52.765151087870265, 'attributes': {'osm:way:access': {'name': 'osm:way:access', 'class': 'java.lang.String', 'text': 'permissive'}, 'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'unclassified'}, 'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long', 'text': '26997928'}, 'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String', 'text': 'Brunswick Place'}}}",
            4: "{'id': '101982', 'x': '528704.1425925883', 'y': '182068.78193707118', 'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879}",
            5: "{'id': '101982', 'x': '528704.1425925883', 'y': '182068.78193707118', 'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879}"},
         'new_attributes': {
             3: "{'id': '0', 'from': '007', 'to': '101986', 'freespeed': 4.166666666666667, 'capacity': 600.0, 'permlanes': 1.0, 'oneway': '1', 'modes': ['car'], 's2_from': 5221390329378179879, 's2_to': 5221390328605860387, 'length': 52.765151087870265, 'attributes': {'osm:way:access': {'name': 'osm:way:access', 'class': 'java.lang.String', 'text': 'permissive'}, 'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'unclassified'}, 'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long', 'text': '26997928'}, 'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String', 'text': 'Brunswick Place'}}}",
             4: "{'id': '007', 'x': '528704.1425925883', 'y': '182068.78193707118', 'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879}",
             5: "{'id': '007', 'x': '528704.1425925883', 'y': '182068.78193707118', 'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879}"},
         'diff': {3: [('change', 'from', ('101982', '007'))],
                  4: [('change', 'id', ('101982', '007')), ('change', 'id', ('101982', '007'))],
                  5: [('change', 'id', ('101982', '007'))]}})
    cols_to_compare = ['change_event', 'object_type', 'old_id', 'new_id', 'old_attributes', 'new_attributes', 'diff']
    assert_frame_equal(network1.change_log.log[cols_to_compare].tail(3), correct_change_log_df[cols_to_compare],
                       check_names=False,
                       check_dtype=False)


def test_reindex_node_when_node_id_already_exists(network1):
    assert [id for id, attribs in network1.nodes()] == ['101982', '101986']
    assert [id for id, attribs in network1.links()] == ['0']
    assert network1.link('0')['from'] == '101982'
    assert network1.link('0')['to'] == '101986'
    assert [(from_n, to_n) for from_n, to_n, attribs in network1.edges()] == [('101982', '101986')]
    assert network1.link_id_mapping['0']['from'] == '101982'

    network1.reindex_node('101982', '101986')
    node_ids = [id for id, attribs in network1.nodes()]
    assert '101986' in node_ids
    assert '101982' not in node_ids
    assert len(set(node_ids)) == 2
    assert network1.node(node_ids[0]) != network1.node(node_ids[1])


def test_reindex_link(network1):
    assert [id for id, attribs in network1.nodes()] == ['101982', '101986']
    assert [id for id, attribs in network1.links()] == ['0']
    assert '0' in network1.link_id_mapping
    assert network1.link('0')['from'] == '101982'
    assert network1.link('0')['to'] == '101986'
    assert [(from_n, to_n) for from_n, to_n, attribs in network1.edges()] == [('101982', '101986')]
    assert network1.edge('101982', '101986')[0]['id'] == '0'

    network1.reindex_link('0', '007')

    assert [id for id, attribs in network1.nodes()] == ['101982', '101986']
    assert [id for id, attribs in network1.links()] == ['007']
    assert '0' not in network1.link_id_mapping
    assert '007' in network1.link_id_mapping
    assert network1.link('007')['from'] == '101982'
    assert network1.link('007')['to'] == '101986'
    assert [(from_n, to_n) for from_n, to_n, attribs in network1.edges()] == [('101982', '101986')]
    assert network1.edge('101982', '101986')[0]['id'] == '007'

    correct_change_log_df = pd.DataFrame(
        {'timestamp': {3: '2020-06-08 19:34:48', 4: '2020-06-08 19:34:48'}, 'change_event': {3: 'modify', 4: 'modify'},
         'object_type': {3: 'link', 4: 'link'}, 'old_id': {3: '0', 4: '0'}, 'new_id': {3: '007', 4: '0'},
         'old_attributes': {
             3: "{'id': '0', 'from': '101982', 'to': '101986', 'freespeed': 4.166666666666667, 'capacity': 600.0, 'permlanes': 1.0, 'oneway': '1', 'modes': ['car'], 's2_from': 5221390329378179879, 's2_to': 5221390328605860387, 'length': 52.765151087870265, 'attributes': {'osm:way:access': {'name': 'osm:way:access', 'class': 'java.lang.String', 'text': 'permissive'}, 'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'unclassified'}, 'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long', 'text': '26997928'}, 'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String', 'text': 'Brunswick Place'}}}",
             4: "{'id': '0', 'from': '101982', 'to': '101986', 'freespeed': 4.166666666666667, 'capacity': 600.0, 'permlanes': 1.0, 'oneway': '1', 'modes': ['car'], 's2_from': 5221390329378179879, 's2_to': 5221390328605860387, 'length': 52.765151087870265, 'attributes': {'osm:way:access': {'name': 'osm:way:access', 'class': 'java.lang.String', 'text': 'permissive'}, 'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'unclassified'}, 'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long', 'text': '26997928'}, 'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String', 'text': 'Brunswick Place'}}}"},
         'new_attributes': {
             3: "{'id': '007', 'from': '101982', 'to': '101986', 'freespeed': 4.166666666666667, 'capacity': 600.0, 'permlanes': 1.0, 'oneway': '1', 'modes': ['car'], 's2_from': 5221390329378179879, 's2_to': 5221390328605860387, 'length': 52.765151087870265, 'attributes': {'osm:way:access': {'name': 'osm:way:access', 'class': 'java.lang.String', 'text': 'permissive'}, 'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'unclassified'}, 'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long', 'text': '26997928'}, 'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String', 'text': 'Brunswick Place'}}}",
             4: "{'id': '007', 'from': '101982', 'to': '101986', 'freespeed': 4.166666666666667, 'capacity': 600.0, 'permlanes': 1.0, 'oneway': '1', 'modes': ['car'], 's2_from': 5221390329378179879, 's2_to': 5221390328605860387, 'length': 52.765151087870265, 'attributes': {'osm:way:access': {'name': 'osm:way:access', 'class': 'java.lang.String', 'text': 'permissive'}, 'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'unclassified'}, 'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long', 'text': '26997928'}, 'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String', 'text': 'Brunswick Place'}}}"},
         'diff': {3: [('change', 'id', ('0', '007')), ('change', 'id', ('0', '007'))],
                  4: [('change', 'id', ('0', '007'))]}})
    cols_to_compare = ['change_event', 'object_type', 'old_id', 'new_id', 'old_attributes', 'new_attributes', 'diff']
    assert_frame_equal(network1.change_log.log[cols_to_compare].tail(2), correct_change_log_df[cols_to_compare],
                       check_names=False, check_dtype=False)


def test_reindex_link_when_link_id_already_exists(network1):
    assert [id for id, attribs in network1.nodes()] == ['101982', '101986']
    assert [id for id, attribs in network1.links()] == ['0']
    assert network1.link('0')['from'] == '101982'
    assert network1.link('0')['to'] == '101986'
    assert [(from_n, to_n) for from_n, to_n, attribs in network1.edges()] == [('101982', '101986')]
    network1.add_link('1', '101986', '101982', attribs={})

    network1.reindex_link('0', '1')
    link_ids = [id for id, attribs in network1.links()]
    assert '1' in link_ids
    assert '0' not in link_ids
    assert len(set(link_ids)) == 2
    assert network1.link(link_ids[0]) != network1.link(link_ids[1])


def test_modify_node_adds_attributes_in_the_graph_and_change_is_recorded_by_change_log():
    n = Network('epsg:27700')
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
    n = Network('epsg:27700')
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
    n = Network('epsg:27700')
    n.add_node(1, {'a': 1})
    n.add_node(2, {'b': 1})
    n.apply_attributes_to_nodes({1: {'a': 4}, 2: {'a': 1}})

    assert n.node(1) == {'a': 4}
    assert n.node(2) == {'b': 1, 'a': 1}

    correct_change_log_df = pd.DataFrame(
        {'timestamp': {0: '2020-06-01 15:07:51', 1: '2020-06-01 15:07:51', 2: '2020-06-01 15:07:51',
                       3: '2020-06-01 15:07:51'}, 'change_event': {0: 'add', 1: 'add', 2: 'modify', 3: 'modify'},
         'object_type': {0: 'node', 1: 'node', 2: 'node', 3: 'node'}, 'old_id': {0: None, 1: None, 2: 1, 3: 2},
         'new_id': {0: 1, 1: 2, 2: 1, 3: 2}, 'old_attributes': {0: None, 1: None, 2: "{'a': 1}", 3: "{'b': 1}"},
         'new_attributes': {0: "{'a': 1}", 1: "{'b': 1}", 2: "{'a': 4}", 3: "{'b': 1, 'a': 1}"},
         'diff': {0: [('add', '', [('a', 1)]), ('add', 'id', 1)], 1: [('add', '', [('b', 1)]), ('add', 'id', 2)],
                  2: [('change', 'a', (1, 4))], 3: [('add', '', [('a', 1)])]}
         })

    cols_to_compare = ['change_event', 'object_type', 'old_id', 'new_id', 'old_attributes', 'new_attributes', 'diff']
    assert_frame_equal(n.change_log.log[cols_to_compare], correct_change_log_df[cols_to_compare], check_dtype=False)


def multiply_node_attribs(node_attribs):
    return node_attribs['a'] * node_attribs['c']


def test_apply_function_to_nodes():
    n = Network('epsg:27700')
    n.add_node('0', attribs={'a': 2, 'c': 3})
    n.add_node('1', attribs={'c': 100})
    n.apply_function_to_nodes(function=multiply_node_attribs, location='new_computed_attrib')
    assert_semantically_equal(dict(n.nodes()),
                              {'0': {'a': 2, 'c': 3, 'new_computed_attrib': 6},
                               '1': {'c': 100}})


def test_apply_attributes_to_edge_without_filter_conditions():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'a': 1})
    n.add_link('1', 1, 2, attribs={'b': 1})
    n.apply_attributes_to_edge(1, 2, {'c': 1})

    assert n.link('0') == {'a': 1, 'from': 1, 'to': 2, 'id': '0', 'c': 1}
    assert n.link('1') == {'b': 1, 'from': 1, 'to': 2, 'id': '1', 'c': 1}

    correct_change_log_df = pd.DataFrame(
        {'timestamp': {2: '2020-07-10 14:53:25', 3: '2020-07-10 14:53:25'}, 'change_event': {2: 'modify', 3: 'modify'},
         'object_type': {2: 'edge', 3: 'edge'}, 'old_id': {2: '(1, 2, 0)', 3: '(1, 2, 1)'},
         'new_id': {2: '(1, 2, 0)', 3: '(1, 2, 1)'},
         'old_attributes': {2: "{'a': 1, 'from': 1, 'to': 2, 'id': '0'}", 3: "{'b': 1, 'from': 1, 'to': 2, 'id': '1'}"},
         'new_attributes': {2: "{'a': 1, 'from': 1, 'to': 2, 'id': '0', 'c': 1}",
                            3: "{'b': 1, 'from': 1, 'to': 2, 'id': '1', 'c': 1}"},
         'diff': {2: [('add', '', [('c', 1)])], 3: [('add', '', [('c', 1)])]}})

    cols_to_compare = ['change_event', 'object_type', 'old_id', 'new_id', 'old_attributes', 'new_attributes', 'diff']
    assert_frame_equal(n.change_log.log[cols_to_compare].tail(2), correct_change_log_df[cols_to_compare],
                       check_dtype=False)


def test_apply_attributes_to_edge_with_filter_conditions():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'a': 1})
    n.add_link('1', 1, 2, attribs={'b': 1})
    n.apply_attributes_to_edge(1, 2, {'c': 1}, conditions={'a': (0, 2)})

    assert n.link('0') == {'a': 1, 'from': 1, 'to': 2, 'id': '0', 'c': 1}
    assert n.link('1') == {'b': 1, 'from': 1, 'to': 2, 'id': '1'}

    correct_change_log_df = pd.DataFrame(
        {'timestamp': {2: '2020-07-10 14:53:25'}, 'change_event': {2: 'modify'},
         'object_type': {2: 'edge'}, 'old_id': {2: '(1, 2, 0)'},
         'new_id': {2: '(1, 2, 0)'},
         'old_attributes': {2: "{'a': 1, 'from': 1, 'to': 2, 'id': '0'}"},
         'new_attributes': {2: "{'a': 1, 'from': 1, 'to': 2, 'id': '0', 'c': 1}"},
         'diff': {2: [('add', '', [('c', 1)])]}})

    cols_to_compare = ['change_event', 'object_type', 'old_id', 'new_id', 'old_attributes', 'new_attributes', 'diff']
    assert_frame_equal(n.change_log.log[cols_to_compare].tail(1), correct_change_log_df[cols_to_compare],
                       check_dtype=False)


def test_apply_attributes_to_multiple_edges():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'a': 1})
    n.add_link('1', 1, 2, attribs={'b': 1})
    n.add_link('2', 2, 3, attribs={'c': 1})
    n.add_link('3', 2, 3, attribs={'d': 1})
    n.apply_attributes_to_edges({(1, 2): {'e': 1}, (2, 3): {'f': 1}}, conditions=[{'a': (0, 2)}, {'c': (0, 2)}])

    assert n.link('0') == {'a': 1, 'from': 1, 'to': 2, 'id': '0', 'e': 1}
    assert n.link('1') == {'b': 1, 'from': 1, 'to': 2, 'id': '1'}
    assert n.link('2') == {'c': 1, 'from': 2, 'to': 3, 'id': '2', 'f': 1}
    assert n.link('3') == {'d': 1, 'from': 2, 'to': 3, 'id': '3'}


def test_modify_link_adds_attributes_in_the_graph_and_change_is_recorded_by_change_log():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'a': 1})
    n.apply_attributes_to_link('0', {'b': 1})

    assert n.link('0') == {'a': 1, 'from': 1, 'to': 2, 'id': '0', 'b': 1}

    correct_change_log_df = pd.DataFrame(
        {'timestamp': {0: '2020-06-12 20:02:49', 1: '2020-06-12 20:02:49'}, 'change_event': {0: 'add', 1: 'modify'},
         'object_type': {0: 'link', 1: 'link'}, 'old_id': {0: None, 1: '0'}, 'new_id': {0: '0', 1: '0'},
         'old_attributes': {0: None, 1: "{'a': 1, 'from': 1, 'to': 2, 'id': '0'}"},
         'new_attributes': {0: "{'a': 1, 'from': 1, 'to': 2, 'id': '0'}",
                            1: "{'a': 1, 'from': 1, 'to': 2, 'id': '0', 'b': 1}"},
         'diff': {0: [('add', '', [('a', 1), ('from', 1), ('to', 2), ('id', '0')]), ('add', 'id', '0')],
                  1: [('add', '', [('b', 1)])]}})

    cols_to_compare = ['change_event', 'object_type', 'old_id', 'new_id', 'old_attributes', 'new_attributes', 'diff']
    assert_frame_equal(n.change_log.log[cols_to_compare], correct_change_log_df[cols_to_compare], check_dtype=False)


def test_modify_link_overwrites_existing_attributes_in_the_graph_and_change_is_recorded_by_change_log():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'a': 1})
    n.apply_attributes_to_link('0', {'a': 4})

    assert n.link('0') == {'a': 4, 'from': 1, 'to': 2, 'id': '0'}

    correct_change_log_df = pd.DataFrame(
        {'timestamp': {0: '2020-06-12 20:04:23', 1: '2020-06-12 20:04:23'}, 'change_event': {0: 'add', 1: 'modify'},
         'object_type': {0: 'link', 1: 'link'}, 'old_id': {0: None, 1: '0'}, 'new_id': {0: '0', 1: '0'},
         'old_attributes': {0: None, 1: "{'a': 1, 'from': 1, 'to': 2, 'id': '0'}"},
         'new_attributes': {0: "{'a': 1, 'from': 1, 'to': 2, 'id': '0'}", 1: "{'a': 4, 'from': 1, 'to': 2, 'id': '0'}"},
         'diff': {0: [('add', '', [('a', 1), ('from', 1), ('to', 2), ('id', '0')]), ('add', 'id', '0')],
                  1: [('change', 'a', (1, 4))]}})

    cols_to_compare = ['change_event', 'object_type', 'old_id', 'new_id', 'old_attributes', 'new_attributes', 'diff']
    assert_frame_equal(n.change_log.log[cols_to_compare], correct_change_log_df[cols_to_compare], check_dtype=False)


def test_modify_link_adds_attributes_in_the_graph_with_multiple_edges():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'a': 1})
    n.add_link('1', 1, 2, attribs={'c': 100})
    n.apply_attributes_to_link('0', {'b': 1})

    assert n.link('0') == {'a': 1, 'from': 1, 'to': 2, 'id': '0', 'b': 1}
    assert n.link('1') == {'c': 100, 'from': 1, 'to': 2, 'id': '1'}


def test_modify_links_adds_and_changes_attributes_in_the_graph_with_multiple_edges_and_change_is_recorded_by_change_log():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'a': {'b': 1}})
    n.add_link('1', 1, 2, attribs={'c': 100})
    n.apply_attributes_to_links({'0': {'a': {'b': 100}}, '1': {'a': {'b': 10}}})

    assert n.link('0') == {'a': {'b': 100}, 'from': 1, 'to': 2, 'id': '0'}
    assert n.link('1') == {'c': 100, 'from': 1, 'to': 2, 'id': '1', 'a': {'b': 10}}

    correct_change_log_df = pd.DataFrame(
        {'timestamp': {2: '2020-06-12 19:59:40', 3: '2020-06-12 19:59:40'}, 'change_event': {2: 'modify', 3: 'modify'},
         'object_type': {2: 'link', 3: 'link'}, 'old_id': {2: '0', 3: '1'}, 'new_id': {2: '0', 3: '1'},
         'old_attributes': {2: "{'a': {'b': 1}, 'from': 1, 'to': 2, 'id': '0'}",
                            3: "{'c': 100, 'from': 1, 'to': 2, 'id': '1'}"},
         'new_attributes': {2: "{'a': {'b': 100}, 'from': 1, 'to': 2, 'id': '0'}",
                            3: "{'c': 100, 'from': 1, 'to': 2, 'id': '1', 'a': {'b': 10}}"},
         'diff': {2: [('change', 'a.b', (1, 100))], 3: [('add', '', [('a', {'b': 10})])]}})

    cols_to_compare = ['change_event', 'object_type', 'old_id', 'new_id', 'old_attributes', 'new_attributes', 'diff']
    assert_frame_equal(n.change_log.log[cols_to_compare].tail(2), correct_change_log_df[cols_to_compare],
                       check_dtype=False)


def multiply_link_attribs(link_attribs):
    return link_attribs['a'] * link_attribs['c']


def test_apply_function_to_links():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'a': 2, 'c': 3})
    n.add_link('1', 1, 2, attribs={'c': 100})
    n.apply_function_to_links(function=multiply_link_attribs, location='new_computed_attrib')
    assert_semantically_equal(dict(n.links()),
                              {'0': {'a': 2, 'c': 3, 'from': 1, 'to': 2, 'id': '0', 'new_computed_attrib': 6},
                               '1': {'c': 100, 'from': 1, 'to': 2, 'id': '1'}})


def test_resolves_link_id_clashes_by_mapping_clashing_link_to_a_new_id(mocker):
    mocker.patch.object(Network, 'generate_index_for_edge', return_value='1')
    n = Network('epsg:27700')

    n.add_link('0', 1, 2)
    assert n.graph.has_edge(1, 2)
    assert n.link_id_mapping['0'] == {'from': 1, 'to': 2, 'multi_edge_idx': 0}

    assert '1' not in n.link_id_mapping
    n.add_link('0', 3, 0)
    assert n.graph.has_edge(3, 0)
    assert n.link_id_mapping['1'] == {'from': 3, 'to': 0, 'multi_edge_idx': 0}

    # also assert that the link mapped to '0' is still as expected
    assert n.link_id_mapping['0'] == {'from': 1, 'to': 2, 'multi_edge_idx': 0}


def test_removing_single_node():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'a': 1})
    n.add_link('1', 1, 2, attribs={'b': 4})
    n.add_link('2', 2, 3, attribs={'a': 1})
    n.add_link('3', 2, 3, attribs={'b': 4})

    n.remove_node(1)
    assert list(n.graph.nodes) == [2, 3]
    assert list(n.graph.edges) == [(2, 3, 0), (2, 3, 1)]

    correct_change_log = pd.DataFrame(
        {'timestamp': {4: '2020-06-11 10:37:54'}, 'change_event': {4: 'remove'}, 'object_type': {4: 'node'},
         'old_id': {4: 1}, 'new_id': {4: None}, 'old_attributes': {4: '{}'}, 'new_attributes': {4: None},
         'diff': {4: [('remove', 'id', 1)]}})
    cols_to_compare = ['change_event', 'object_type', 'old_id', 'new_id', 'old_attributes', 'new_attributes', 'diff']
    assert_frame_equal(n.change_log.log[cols_to_compare].tail(1), correct_change_log[cols_to_compare],
                       check_dtype=False)


def test_removing_multiple_nodes():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'a': 1})
    n.add_link('1', 1, 2, attribs={'b': 4})
    n.add_link('2', 2, 3, attribs={'a': 1})
    n.add_link('3', 2, 3, attribs={'b': 4})

    n.remove_nodes([1, 2])
    assert list(n.graph.nodes) == [3]
    assert list(n.graph.edges) == []

    correct_change_log = pd.DataFrame(
        {'timestamp': {4: '2020-06-11 10:39:52', 5: '2020-06-11 10:39:52'}, 'change_event': {4: 'remove', 5: 'remove'},
         'object_type': {4: 'node', 5: 'node'}, 'old_id': {4: 1, 5: 2}, 'new_id': {4: None, 5: None},
         'old_attributes': {4: '{}', 5: '{}'}, 'new_attributes': {4: None, 5: None},
         'diff': {4: [('remove', 'id', 1)], 5: [('remove', 'id', 2)]}})
    cols_to_compare = ['change_event', 'object_type', 'old_id', 'new_id', 'old_attributes', 'new_attributes', 'diff']
    assert_frame_equal(n.change_log.log[cols_to_compare].tail(2), correct_change_log[cols_to_compare],
                       check_dtype=False)


def test_removing_single_link():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'a': 1})
    n.add_link('1', 1, 2, attribs={'b': 4})
    n.add_link('2', 2, 3, attribs={'a': 1})
    n.add_link('3', 2, 3, attribs={'b': 4})
    assert '1' in n.link_id_mapping

    n.remove_link('1')
    assert list(n.graph.nodes) == [1, 2, 3]
    assert list(n.graph.edges) == [(1, 2, 0), (2, 3, 0), (2, 3, 1)]
    assert not '1' in n.link_id_mapping

    correct_change_log = pd.DataFrame(
        {'timestamp': {4: '2020-06-12 19:58:01'}, 'change_event': {4: 'remove'}, 'object_type': {4: 'link'},
         'old_id': {4: '1'}, 'new_id': {4: None}, 'old_attributes': {4: "{'b': 4, 'from': 1, 'to': 2, 'id': '1'}"},
         'new_attributes': {4: None},
         'diff': {4: [('remove', '', [('b', 4), ('from', 1), ('to', 2), ('id', '1')]), ('remove', 'id', '1')]}})
    cols_to_compare = ['change_event', 'object_type', 'old_id', 'new_id', 'old_attributes', 'new_attributes', 'diff']
    assert_frame_equal(n.change_log.log[cols_to_compare].tail(1), correct_change_log[cols_to_compare],
                       check_dtype=False)


def test_removing_multiple_links():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'a': 1})
    n.add_link('1', 1, 2, attribs={'b': 4})
    n.add_link('2', 2, 3, attribs={'a': 1})
    n.add_link('3', 2, 3, attribs={'b': 4})
    assert '0' in n.link_id_mapping
    assert '2' in n.link_id_mapping

    n.remove_links(['0', '2'])
    assert list(n.graph.nodes) == [1, 2, 3]
    assert list(n.graph.edges) == [(1, 2, 1), (2, 3, 1)]
    assert not '0' in n.link_id_mapping
    assert not '2' in n.link_id_mapping

    correct_change_log = pd.DataFrame(
        {'timestamp': {4: '2020-06-12 19:55:10', 5: '2020-06-12 19:55:10'}, 'change_event': {4: 'remove', 5: 'remove'},
         'object_type': {4: 'link', 5: 'link'}, 'old_id': {4: '0', 5: '2'}, 'new_id': {4: None, 5: None},
         'old_attributes': {4: "{'a': 1, 'from': 1, 'to': 2, 'id': '0'}", 5: "{'a': 1, 'from': 2, 'to': 3, 'id': '2'}"},
         'new_attributes': {4: None, 5: None},
         'diff': {4: [('remove', '', [('a', 1), ('from', 1), ('to', 2), ('id', '0')]), ('remove', 'id', '0')],
                  5: [('remove', '', [('a', 1), ('from', 2), ('to', 3), ('id', '2')]), ('remove', 'id', '2')]}})
    cols_to_compare = ['change_event', 'object_type', 'old_id', 'new_id', 'old_attributes', 'new_attributes', 'diff']
    assert_frame_equal(n.change_log.log[cols_to_compare].tail(2), correct_change_log[cols_to_compare],
                       check_dtype=False)


def test_number_of_multi_edges_counts_multi_edges_on_single_edge():
    n = Network('epsg:27700')
    n.graph.add_edges_from([(1, 2), (2, 3), (3, 4)])
    assert n.number_of_multi_edges(1, 2) == 1


def test_number_of_multi_edges_counts_multi_edges_on_multi_edge():
    n = Network('epsg:27700')
    n.graph.add_edges_from([(1, 2), (1, 2), (3, 4)])
    assert n.number_of_multi_edges(1, 2) == 2


def test_number_of_multi_edges_counts_multi_edges_on_non_existing_edge():
    n = Network('epsg:27700')
    n.graph.add_edges_from([(1, 2), (1, 2), (3, 4)])
    assert n.number_of_multi_edges(1214, 21321) == 0


def test_nodes_gives_iterator_of_node_id_and_attribs():
    n = Network('epsg:27700')
    n.graph.add_edges_from([(1, 2), (2, 3), (3, 4)])
    assert list(n.nodes()) == [(1, {}), (2, {}), (3, {}), (4, {})]


def test_node_gives_node_attribss():
    n = Network('epsg:27700')
    n.graph.add_node(1, **{'attrib': 1})
    assert n.node(1) == {'attrib': 1}


def test_edges_gives_iterator_of_edge_from_to_nodes_and_attribs():
    n = Network('epsg:27700')
    n.graph.add_edges_from([(1, 2), (2, 3), (3, 4)])
    assert list(n.edges()) == [(1, 2, {0: {}}), (2, 3, {0: {}}), (3, 4, {0: {}})]


def test_edge_method_gives_attributes_for_given_from_and_to_nodes():
    n = Network('epsg:27700')
    n.graph.add_edge(1, 2, **{'attrib': 1})
    assert n.edge(1, 2) == {0: {'attrib': 1}}


def test_links_gives_iterator_of_link_id_and_edge_attribs():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'f': 's'})
    n.add_link('1', 2, 3, attribs={'h': 1})
    assert list(n.links()) == [('0', {'f': 's', 'from': 1, 'to': 2, 'id': '0'}),
                               ('1', {'h': 1, 'from': 2, 'to': 3, 'id': '1'})]


def test_link_gives_link_attribs():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'attrib': 1})
    n.add_link('0', 1, 2, attribs={'attrib': 1})
    assert n.link('0') == {'attrib': 1, 'from': 1, 'to': 2, 'id': '0'}


def test_schedule_routes(network_object_from_test_data):
    n = network_object_from_test_data
    correct_routes = [['25508485', '21667818']]
    routes = n.schedule_routes_nodes()
    assert correct_routes == routes


def test_schedule_routes_with_an_empty_service(network_object_from_test_data):
    n = network_object_from_test_data
    n.schedule['10314'].routes['1'] = Route(arrival_offsets=[], departure_offsets=[], mode='bus', trips={},
                                            route_short_name='', stops=[])
    assert set(n.schedule.service_ids()) == {'10314'}
    correct_routes = [['25508485', '21667818']]
    routes = n.schedule_routes_nodes()
    assert correct_routes == routes


def test_schedule_routes_with_disconnected_routes(network_object_from_test_data):
    n = network_object_from_test_data
    n.add_link('2', 2345678, 987875)
    n.schedule.route('VJbd8660f05fe6f744e58a66ae12bd66acbca88b98').route.append('2')
    correct_routes = [['25508485', '21667818'], [2345678, 987875]]
    routes = n.schedule_routes_nodes()
    assert correct_routes == routes


def test_reads_osm_network_into_the_right_schema(full_fat_default_config_path):
    osm_test_file = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "test_data", "osm", "osm.xml"))
    network = Network('epsg:27700')
    network.read_osm(osm_test_file, full_fat_default_config_path, 1)
    assert_semantically_equal(dict(network.nodes()), {
        '0': {'id': '0', 'x': 622502.8306679451, 'y': -5526117.781903352, 'lat': 0.008554364250688652,
              'lon': -0.0006545205888310243, 's2_id': 1152921492875543713},
        '1': {'id': '1', 'x': 622502.8132744529, 'y': -5524378.838447345, 'lat': 0.024278505899735615,
              'lon': -0.0006545205888310243, 's2_id': 1152921335974974453},
        '2': {'id': '2', 'x': 622502.8314014417, 'y': -5527856.725358106, 'lat': -0.00716977739835831,
              'lon': -0.0006545205888310243, 's2_id': 384307157539499829}})
    assert len(list(network.links())) == 10

    number_of_0_multi_idx = 0
    number_of_1_multi_idx = 0
    number_of_2_multi_idx = 0
    for link_id, edge_map in network.link_id_mapping.items():
        if edge_map['multi_edge_idx'] == 0:
            number_of_0_multi_idx += 1
        elif edge_map['multi_edge_idx'] == 1:
            number_of_1_multi_idx += 1
        elif edge_map['multi_edge_idx'] == 2:
            number_of_2_multi_idx += 1
    assert number_of_0_multi_idx == 5
    assert number_of_1_multi_idx == 4
    assert number_of_2_multi_idx == 1

    correct_link_attribs = [
        {'permlanes': 1.0, 'freespeed': 12.5, 'capacity': 600.0, 'oneway': '1', 'modes': ['walk', 'car', 'bike'],
         'from': '0', 'to': '1', 's2_from': 1152921492875543713, 's2_to': 1152921335974974453,
         'length': 1748.4487354464366,
         'attributes': {'osm:way:osmid': {'name': 'osm:way:osmid', 'class': 'java.lang.String', 'text': '0'},
                        'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String',
                                            'text': 'unclassified'}}},
        {'permlanes': 1.0, 'freespeed': 12.5, 'capacity': 600.0, 'oneway': '1', 'modes': ['walk', 'car', 'bike'],
         'from': '1', 'to': '0', 's2_from': 1152921335974974453, 's2_to': 1152921492875543713,
         'length': 1748.4487354464366,
         'attributes': {'osm:way:osmid': {'name': 'osm:way:osmid', 'class': 'java.lang.String', 'text': '0'},
                        'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String',
                                            'text': 'unclassified'}}},
        {'permlanes': 1.0, 'freespeed': 12.5, 'capacity': 600.0, 'oneway': '1', 'modes': ['walk', 'car', 'bike'],
         'from': '0', 'to': '2', 's2_from': 1152921492875543713, 's2_to': 384307157539499829,
         'length': 1748.4488584600201,
         'attributes': {'osm:way:osmid': {'name': 'osm:way:osmid', 'class': 'java.lang.String', 'text': '100'},
                        'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String',
                                            'text': 'unclassified'}}},
        {'permlanes': 1.0, 'freespeed': 12.5, 'capacity': 600.0, 'oneway': '1', 'modes': ['walk', 'car', 'bike'],
         'from': '2', 'to': '0', 's2_from': 384307157539499829, 's2_to': 1152921492875543713,
         'length': 1748.4488584600201,
         'attributes': {'osm:way:osmid': {'name': 'osm:way:osmid', 'class': 'java.lang.String', 'text': '100'},
                        'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String',
                                            'text': 'unclassified'}}},
        {'permlanes': 1.0, 'freespeed': 12.5, 'capacity': 600.0, 'oneway': '1', 'modes': ['walk', 'car', 'bike'],
         'from': '1', 'to': '0', 's2_from': 1152921335974974453, 's2_to': 1152921492875543713,
         'length': 1748.4487354464366,
         'attributes': {'osm:way:osmid': {'name': 'osm:way:osmid', 'class': 'java.lang.String', 'text': '400'},
                        'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String',
                                            'text': 'unclassified'}}},
        {'permlanes': 1.0, 'freespeed': 12.5, 'capacity': 600.0, 'oneway': '1', 'modes': ['walk', 'car', 'bike'],
         'from': '0', 'to': '1', 's2_from': 1152921492875543713, 's2_to': 1152921335974974453,
         'length': 1748.4487354464366,
         'attributes': {'osm:way:osmid': {'name': 'osm:way:osmid', 'class': 'java.lang.String', 'text': '400'},
                        'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String',
                                            'text': 'unclassified'}}},
        {'permlanes': 1.0, 'freespeed': 12.5, 'capacity': 600.0, 'oneway': '1', 'modes': ['walk', 'car', 'bike'],
         'from': '2', 'to': '0', 's2_from': 384307157539499829, 's2_to': 1152921492875543713,
         'length': 1748.4488584600201,
         'attributes': {'osm:way:osmid': {'name': 'osm:way:osmid', 'class': 'java.lang.String', 'text': '700'},
                        'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String',
                                            'text': 'unclassified'}}},
        {'permlanes': 1.0, 'freespeed': 12.5, 'capacity': 600.0, 'oneway': '1', 'modes': ['walk', 'car', 'bike'],
         'from': '0', 'to': '2', 's2_from': 1152921492875543713, 's2_to': 384307157539499829,
         'length': 1748.4488584600201,
         'attributes': {'osm:way:osmid': {'name': 'osm:way:osmid', 'class': 'java.lang.String', 'text': '700'},
                        'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String',
                                            'text': 'unclassified'}}},
        {'permlanes': 3.0, 'freespeed': 12.5, 'capacity': 1800.0, 'oneway': '1', 'modes': ['walk', 'car', 'bike'],
         'from': '2', 'to': '1', 's2_from': 384307157539499829, 's2_to': 1152921335974974453,
         'length': 3496.897593906457,
         'attributes': {'osm:way:lanes': {'name': 'osm:way:lanes', 'class': 'java.lang.String', 'text': '3'},
                        'osm:way:osmid': {'name': 'osm:way:osmid', 'class': 'java.lang.String', 'text': '47007861'},
                        'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String',
                                            'text': 'tertiary'}}},
        {'permlanes': 3.0, 'freespeed': 12.5, 'capacity': 1800.0, 'oneway': '1', 'modes': ['walk', 'car', 'bike'],
         'from': '1', 'to': '0', 's2_from': 1152921335974974453, 's2_to': 1152921492875543713,
         'length': 1748.4487354464366,
         'attributes': {'osm:way:lanes': {'name': 'osm:way:lanes', 'class': 'java.lang.String', 'text': '3'},
                        'osm:way:osmid': {'name': 'osm:way:osmid', 'class': 'java.lang.String', 'text': '47007861'},
                        'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String',
                                            'text': 'tertiary'}}}]

    cols = ['permlanes', 'freespeed', 'capacity', 'oneway', 'modes', 'from', 'to', 's2_from', 's2_to', 'length',
            'attributes']

    assert len(network.link_id_mapping) == 10
    for link in network.link_id_mapping.keys():
        satisfied = False
        attribs_to_test = network.link(link).copy()
        del attribs_to_test['id']
        for link_attrib in correct_link_attribs:
            try:
                assert_semantically_equal(attribs_to_test, link_attrib)
                satisfied = True
            except AssertionError:
                pass
        assert satisfied


def test_read_matsim_network_delegates_to_matsim_reader_read_network(mocker):
    mocker.patch.object(matsim_reader, 'read_network', return_value=(nx.MultiDiGraph(), 2, {}, {}))

    network = Network('epsg:27700')
    network.read_matsim_network(pt2matsim_network_test_file)

    matsim_reader.read_network.assert_called_once_with(pt2matsim_network_test_file, network.transformer)


def test_read_matsim_network_with_duplicated_node_ids_records_removal_in_changelog(mocker):
    dup_nodes = {'21667818': [
        {'id': '21667818', 'x': 528504.1342843144, 'y': 182155.7435136598, 'lon': -0.14910908709500162,
         'lat': 51.52370573323939, 's2_id': 5221390302696205321}]}
    mocker.patch.object(matsim_reader, 'read_network', return_value=(nx.MultiDiGraph(), 2, dup_nodes, {}))
    network = Network('epsg:27700')
    network.read_matsim_network(pt2matsim_network_test_file)

    correct_change_log_df = pd.DataFrame(
        {'timestamp': {0: '2020-07-02 11:36:54'}, 'change_event': {0: 'remove'}, 'object_type': {0: 'node'},
         'old_id': {0: '21667818'}, 'new_id': {0: None},
         'old_attributes': {
             0: "{'id': '21667818', 'x': 528504.1342843144, 'y': 182155.7435136598, 'lon': -0.14910908709500162, 'lat': 51.52370573323939, 's2_id': 5221390302696205321}"},
         'new_attributes': {0: None},
         'diff': {0: [('remove', '', [('id', '21667818'), ('x', 528504.1342843144),
                                      ('y', 182155.7435136598),
                                      ('lon', -0.14910908709500162),
                                      ('lat', 51.52370573323939),
                                      ('s2_id', 5221390302696205321)]),
                      ('remove', 'id', '21667818')]}}
    )
    cols_to_compare = ['change_event', 'object_type', 'old_id', 'new_id', 'old_attributes', 'new_attributes', 'diff']
    assert_frame_equal(network.change_log.log[cols_to_compare].tail(1), correct_change_log_df[cols_to_compare],
                       check_names=False,
                       check_dtype=False)


def test_read_matsim_network_with_duplicated_link_ids_records_reindexing_in_changelog(mocker):
    dup_links = {'1': ['1_1']}
    correct_link_id_map = {'1': {'from': '25508485', 'to': '21667818', 'multi_edge_idx': 0},
                           '1_1': {'from': '25508485', 'to': '21667818', 'multi_edge_idx': 1}}
    mocker.patch.object(matsim_reader, 'read_network',
                        return_value=(nx.MultiDiGraph(), correct_link_id_map, {}, dup_links))
    mocker.patch.object(Network, 'link', return_value={'heyooo': '1'})
    network = Network('epsg:27700')
    network.read_matsim_network(pt2matsim_network_test_file)

    correct_change_log_df = pd.DataFrame(
        {'timestamp': {0: '2020-07-02 11:59:00'}, 'change_event': {0: 'modify'}, 'object_type': {0: 'link'},
         'old_id': {0: '1'}, 'new_id': {0: '1_1'}, 'old_attributes': {0: "{'heyooo': '1'}"},
         'new_attributes': {0: "{'heyooo': '1'}"}, 'diff': {0: [('change', 'id', ('1', '1_1'))]}}
    )
    cols_to_compare = ['change_event', 'object_type', 'old_id', 'new_id', 'old_attributes', 'new_attributes', 'diff']
    assert_frame_equal(network.change_log.log[cols_to_compare].tail(1), correct_change_log_df[cols_to_compare],
                       check_names=False,
                       check_dtype=False)


def test_read_matsim_schedule_runs_schedule_read_matsim_schedule_using_epsg_from_earlier_network_run(mocker):
    mocker.patch.object(Schedule, 'read_matsim_schedule')
    network = Network('epsg:27700')
    network.read_matsim_network(pt2matsim_network_test_file)
    network.read_matsim_schedule(pt2matsim_schedule_file)

    Schedule.read_matsim_schedule.assert_called_once_with(pt2matsim_schedule_file)


def test_has_node_when_node_is_in_the_graph():
    n = Network('epsg:27700')
    n.add_node('1')
    assert n.has_node('1')


def test_has_node_when_node_is_not_in_the_graph():
    n = Network('epsg:27700')
    assert not n.has_node('1')


def test_has_nodes_when_nodes_in_the_graph():
    n = Network('epsg:27700')
    n.add_node('1')
    n.add_node('2')
    n.add_node('3')
    assert n.has_nodes(['1', '2'])


def test_has_nodes_when_only_some_nodes_in_the_graph():
    n = Network('epsg:27700')
    n.add_node('1')
    n.add_node('2')
    n.add_node('3')
    assert not n.has_nodes(['1', '4'])


def test_has_nodes_when_none_of_the_nodes_in_the_graph():
    n = Network('epsg:27700')
    n.add_node('1')
    n.add_node('2')
    n.add_node('3')
    assert not n.has_nodes(['10', '20'])


def test_has_edge_when_edge_is_in_the_graph():
    n = Network('epsg:27700')
    n.add_link('1', 1, 2)
    assert n.has_edge(1, 2)


def test_has_edge_when_edge_is_not_in_the_graph():
    n = Network('epsg:27700')
    assert not n.has_edge(1, 2)


def test_has_link_when_link_is_in_the_graph():
    n = Network('epsg:27700')
    n.add_link('1', 1, 2)
    assert n.has_link('1')


def test_has_link_when_link_is_not_in_the_graph():
    n = Network('epsg:27700')
    assert not n.has_link('1')


def test_has_link_when_link_id_is_in_the_network_but_corresponding_edge_is_not():
    # unlikely scenario but possible if someone uses a non genet method to play with the graph
    n = Network('epsg:27700')
    n.link_id_mapping['1'] = {'from': 1, 'to': 2, 'multi_edge_idx': 0}
    assert not n.has_link('1')


def test_has_links_when_links_in_the_graph():
    n = Network('epsg:27700')
    n.add_link('1', 1, 2)
    n.add_link('2', 1, 2)
    n.add_link('3', 1, 2)
    assert n.has_links(['1', '2'])


def test_has_links_when_only_some_links_in_the_graph():
    n = Network('epsg:27700')
    n.add_link('1', 1, 2)
    n.add_link('2', 1, 2)
    n.add_link('3', 1, 2)
    assert not n.has_links(['1', '4'])


def test_has_links_when_none_of_the_links_in_the_graph():
    n = Network('epsg:27700')
    n.add_link('1', 1, 2)
    n.add_link('2', 1, 2)
    n.add_link('3', 1, 2)
    assert not n.has_links(['10', '20'])


def test_has_links_with_passing_attribute_condition():
    n = Network('epsg:27700')
    n.add_link('1', 1, 2, attribs={'modes': 'car'})
    n.add_link('2', 1, 2, attribs={'modes': 'car'})
    assert n.has_links(['1', '2'], conditions={'modes': 'car'})


def test_has_links_with_failing_attribute_condition():
    n = Network('epsg:27700')
    n.add_link('1', 1, 2, attribs={'modes': 'bus'})
    n.add_link('2', 1, 2, attribs={'modes': 'walk'})
    assert not n.has_links(['1', '2'], conditions={'modes': 'car'})


def test_has_links_not_in_graph_with_attribute_condition():
    n = Network('epsg:27700')
    n.add_link('1', 1, 2, attribs={'modes': 'car'})
    n.add_link('2', 1, 2, attribs={'modes': 'car'})
    assert not n.has_links(['10', '20'], conditions={'modes': 'car'})


def test_has_valid_link_chain_with_a_valid_link_chain():
    n = Network('epsg:27700')
    n.add_link('1', 1, 3)
    n.add_link('2', 3, 4)
    assert n.has_valid_link_chain(['1', '2'])


def test_has_valid_link_chain_with_an_invalid_link_chain():
    n = Network('epsg:27700')
    n.add_link('1', 1, 3)
    n.add_link('2', 2, 4)
    assert not n.has_valid_link_chain(['1', '2'])


def test_has_valid_link_chain_with_an_empty_link_chain():
    n = Network('epsg:27700')
    n.add_link('1', 1, 3)
    n.add_link('2', 2, 4)
    assert not n.has_valid_link_chain([])


def test_calculate_route_distance_with_links_that_have_length_attrib():
    n = Network('epsg:27700')
    n.add_link('1', 1, 3, attribs={'length': 2})
    n.add_link('2', 3, 4, attribs={'length': 1})
    assert n.route_distance(['1', '2']) == 3


def test_calculate_route_distance_with_links_that_dont_have_length_attrib():
    n = Network('epsg:27700')
    n.add_node(1, attribs={'s2_id': 12345})
    n.add_node(3, attribs={'s2_id': 345435})
    n.add_node(4, attribs={'s2_id': 568767})
    n.add_link('1', 1, 3)
    n.add_link('2', 3, 4)
    assert round(n.route_distance(['1', '2']), 6) == 0.013918


def test_calculate_route_distance_returns_0_when_route_is_invalid():
    n = Network('epsg:27700')
    n.add_link('1', 1, 3)
    n.add_link('2', 5, 4)
    assert n.route_distance(['1', '2']) == 0


def test_valid_network_route():
    n = Network('epsg:27700')
    n.add_link('1', 1, 2, attribs={'modes': ['car', 'bus']})
    n.add_link('2', 2, 3, attribs={'modes': ['car', 'bus']})
    r = Route(route_short_name='', mode='bus', stops=[], trips={}, arrival_offsets=[], departure_offsets=[],
              route=['1', '2'])
    assert n.is_valid_network_route(r)


def test_network_route_with_wrong_links():
    n = Network('epsg:27700')
    n.add_link('1', 1, 2, attribs={'modes': ['car', 'bus']})
    n.add_link('2', 3, 2, attribs={'modes': ['car', 'bus']})
    r = Route(route_short_name='', mode='bus', stops=[], trips={}, arrival_offsets=[], departure_offsets=[],
              route=['1', '2'])
    assert not n.is_valid_network_route(r)


def test_network_route_with_empty_link_list():
    n = Network('epsg:27700')
    n.add_link('1', 1, 2, attribs={'modes': ['car', 'bus']})
    n.add_link('2', 3, 2, attribs={'modes': ['car', 'bus']})
    r = Route(route_short_name='', mode='bus', stops=[], trips={}, arrival_offsets=[], departure_offsets=[],
              route=[])
    assert not n.is_valid_network_route(r)


def test_network_route_with_incorrect_modes_on_link():
    n = Network('epsg:27700')
    n.add_link('1', 1, 2, attribs={'modes': ['car']})
    n.add_link('2', 3, 2, attribs={'modes': ['car', 'bus']})
    r = Route(route_short_name='', mode='bus', stops=[], trips={}, arrival_offsets=[], departure_offsets=[],
              route=['1', '2'])
    assert not n.is_valid_network_route(r)


def test_generate_index_for_node_gives_next_integer_string_when_you_have_matsim_usual_integer_index():
    n = Network('epsg:27700')
    n.add_node('1')
    assert n.generate_index_for_node() == '2'


def test_generate_index_for_node_gives_string_based_on_length_node_ids_when_you_have_mixed_index():
    n = Network('epsg:27700')
    n.add_node('1')
    n.add_node('1x')
    assert n.generate_index_for_node() == '3'


def test_generate_index_for_node_gives_string_based_on_length_node_ids_when_you_have_all_non_int_index():
    n = Network('epsg:27700')
    n.add_node('1w')
    n.add_node('1x')
    assert n.generate_index_for_node() == '3'


def test_generate_index_for_node_gives_uuid4_as_last_resort(mocker):
    mocker.patch.object(uuid, 'uuid4')
    n = Network('epsg:27700')
    n.add_node('1w')
    n.add_node('1x')
    n.add_node('4')
    n.generate_index_for_node()
    uuid.uuid4.assert_called_once()


def test_generating_n_indicies_for_nodes():
    n = Network('epsg:27700')
    n.add_nodes({str(i): {} for i in range(10)})
    idxs = n.generate_indices_for_n_nodes(5)
    assert len(idxs) == 5
    assert not set(dict(n.nodes()).keys()) & idxs


def test_generate_index_for_edge_gives_next_integer_string_when_you_have_matsim_usual_integer_index():
    n = Network('epsg:27700')
    n.link_id_mapping = {'1': {}, '2': {}}
    assert n.generate_index_for_edge() == '3'


def test_generate_index_for_edge_gives_string_based_on_length_link_id_mapping_when_you_have_mixed_index():
    n = Network('epsg:27700')
    n.link_id_mapping = {'1': {}, 'x2': {}}
    assert n.generate_index_for_edge() == '3'


def test_generate_index_for_edge_gives_string_based_on_length_link_id_mapping_when_you_have_all_non_int_index():
    n = Network('epsg:27700')
    n.link_id_mapping = {'1x': {}, 'x2': {}}
    assert n.generate_index_for_edge() == '3'


def test_generate_index_for_edge_gives_uuid4_as_last_resort(mocker):
    mocker.patch.object(uuid, 'uuid4')
    n = Network('epsg:27700')
    n.add_link('1x', 1, 2)
    n.add_link('3', 1, 2)
    n.generate_index_for_edge()
    uuid.uuid4.assert_called_once()


def test_index_graph_edges_generates_completely_new_index():
    n = Network('epsg:27700')
    n.add_link('1x', 1, 2)
    n.add_link('x2', 1, 2)
    n.index_graph_edges()
    assert list(n.link_id_mapping.keys()) == ['0', '1']


def test_generating_n_indicies_for_edges():
    n = Network('epsg:27700')
    n.add_links({str(i): {'from': 0, 'to': 1} for i in range(10)})
    idxs = n.generate_indices_for_n_edges(5)
    assert len(idxs) == 5
    assert not set(n.link_id_mapping.keys()) & idxs


def test_has_schedule_with_valid_network_routes_with_valid_routes(route):
    n = Network('epsg:27700')
    n.add_link('1', 1, 2, attribs={"modes": ['bus']})
    n.add_link('2', 2, 3, attribs={"modes": ['car', 'bus']})
    route.route = ['1', '2']
    n.schedule = Schedule(n.epsg, [Service(id='service', routes=[route, route])])
    assert n.has_schedule_with_valid_network_routes()


def test_has_schedule_with_valid_network_routes_with_some_valid_routes(route):
    n = Network('epsg:27700')
    n.add_link('1', 1, 2)
    n.add_link('2', 2, 3)
    route.route = ['1', '2']
    route_2 = Route(route_short_name='', mode='', stops=[], trips={},
                    arrival_offsets=[], departure_offsets=[], route=['10000'])
    n.schedule = Schedule(n.epsg, [Service(id='service', routes=[route, route_2])])
    assert not n.has_schedule_with_valid_network_routes()


def test_has_schedule_with_valid_network_routes_with_invalid_routes(route):
    n = Network('epsg:27700')
    n.add_link('1', 1, 2)
    n.add_link('2', 2, 3)
    route.route = ['3', '4']
    n.schedule = Schedule(n.epsg, [Service(id='service', routes=[route, route])])
    assert not n.has_schedule_with_valid_network_routes()


def test_has_schedule_with_valid_network_routes_with_empty_routes(route):
    n = Network('epsg:27700')
    n.add_link('1', 1, 2)
    n.add_link('2', 2, 3)
    route.route = []
    n.schedule = Schedule(n.epsg, [Service(id='service', routes=[route, route])])
    assert not n.has_schedule_with_valid_network_routes()


def test_invalid_network_routes_with_valid_route(route):
    n = Network('epsg:27700')
    n.add_link('1', 1, 2, attribs={"modes": ['car', 'bus']})
    n.add_link('2', 2, 3, attribs={"modes": ['bus']})
    route.route = ['1', '2']
    n.schedule = Schedule(n.epsg, [Service(id='service', routes=[route])])
    assert n.invalid_network_routes() == []


def test_invalid_network_routes_with_invalid_route(route):
    n = Network('epsg:27700')
    n.add_link('1', 1, 2)
    n.add_link('2', 2, 3)
    route.route = ['3', '4']
    route.id = 'route'
    n.schedule = Schedule(n.epsg, [Service(id='service', routes=[route])])
    assert n.invalid_network_routes() == [('service', 'route')]


def test_invalid_network_routes_with_empty_route(route):
    n = Network('epsg:27700')
    n.add_link('1', 1, 2)
    n.add_link('2', 2, 3)
    route.route = []
    route.id = 'route'
    n.schedule = Schedule(n.epsg, [Service(id='service', routes=[route])])
    assert n.invalid_network_routes() == [('service', 'route')]


def test_generate_validation_report_with_pt2matsim_network(network_object_from_test_data):
    n = network_object_from_test_data
    report = n.generate_validation_report()
    correct_report = {
        'graph': {
            'graph_connectivity': {
                'car': {'problem_nodes': {'dead_ends': ['21667818'], 'unreachable_node': ['25508485']},
                        'number_of_connected_subgraphs': 2},
                'walk': {'problem_nodes': {'dead_ends': ['21667818'], 'unreachable_node': ['25508485']},
                         'number_of_connected_subgraphs': 2},
                'bike': {'problem_nodes': {'dead_ends': [], 'unreachable_node': []},
                         'number_of_connected_subgraphs': 0}},
            'links_over_1km_length': []},
        'schedule': {
            'schedule_level': {'is_valid_schedule': False, 'invalid_stages': ['not_has_valid_services'],
                               'has_valid_services': False, 'invalid_services': ['10314']},
            'service_level': {
                '10314': {'is_valid_service': False, 'invalid_stages': ['not_has_valid_routes'],
                          'has_valid_routes': False, 'invalid_routes': ['VJbd8660f05fe6f744e58a66ae12bd66acbca88b98']}},
            'route_level': {'10314': {'VJbd8660f05fe6f744e58a66ae12bd66acbca88b98': {'is_valid_route': False,
                                                                                     'invalid_stages': [
                                                                                         'not_has_correctly_ordered_route']}}}},
        'routing': {'services_have_routes_in_the_graph': False, 'service_routes_with_invalid_network_route': [
            ('10314', 'VJbd8660f05fe6f744e58a66ae12bd66acbca88b98')], 'route_to_crow_fly_ratio': {
            '10314': {'VJbd8660f05fe6f744e58a66ae12bd66acbca88b98': 'Division by zero'}}}}
    assert_semantically_equal(report, correct_report)


def test_generate_validation_report_with_correct_schedule(correct_schedule):
    n = Network('epsg:27700')
    n.add_link('1', 1, 2, attribs={'length': 2, "modes": ['car', 'bus']})
    n.add_link('2', 2, 3, attribs={'length': 2, "modes": ['car', 'bus']})
    n.schedule = correct_schedule

    report = n.generate_validation_report()
    correct_report = {
        'graph': {
            'graph_connectivity': {
                'car': {'problem_nodes': {'dead_ends': [3], 'unreachable_node': [1]},
                        'number_of_connected_subgraphs': 3},
                'walk': {'problem_nodes': {'dead_ends': [], 'unreachable_node': []},
                         'number_of_connected_subgraphs': 0},
                'bike': {'problem_nodes': {'dead_ends': [], 'unreachable_node': []},
                         'number_of_connected_subgraphs': 0}},
            'links_over_1km_length': []},
        'schedule': {'schedule_level': {'is_valid_schedule': True, 'invalid_stages': [], 'has_valid_services': True,
                                        'invalid_services': []}, 'service_level': {
            'service': {'is_valid_service': True, 'invalid_stages': [], 'has_valid_routes': True,
                        'invalid_routes': []}}, 'route_level': {
            'service': {'1': {'is_valid_route': True, 'invalid_stages': []},
                        '2': {'is_valid_route': True, 'invalid_stages': []}}}},
        'routing': {'services_have_routes_in_the_graph': True, 'service_routes_with_invalid_network_route': [],
                    'route_to_crow_fly_ratio': {'service': {'1': 0.037918141839160244, '2': 0.037918141839160244}}}}
    assert_semantically_equal(report, correct_report)


def test_generate_validation_report_with_non_uniquely_indexed_routes(correct_schedule):
    n = Network('epsg:27700')
    n.add_link('1', 1, 2, attribs={'length': 2, "modes": ['car', 'bus']})
    n.add_link('2', 2, 3, attribs={'length': 2, "modes": ['car', 'bus']})

    for serv_id, route in correct_schedule.routes():
        route.id = '1'
    n.schedule = correct_schedule

    report = n.generate_validation_report()
    correct_report = {
        'graph': {
            'graph_connectivity': {
                'car': {'problem_nodes': {'dead_ends': [3], 'unreachable_node': [1]},
                        'number_of_connected_subgraphs': 3},
                'walk': {'problem_nodes': {'dead_ends': [], 'unreachable_node': []},
                         'number_of_connected_subgraphs': 0},
                'bike': {'problem_nodes': {'dead_ends': [], 'unreachable_node': []},
                         'number_of_connected_subgraphs': 0}},
            'links_over_1km_length': []},
        'schedule': {
            'schedule_level': {'is_valid_schedule': False, 'invalid_stages': ['not_has_valid_services'],
                               'has_valid_services': False, 'invalid_services': ['service']},
            'service_level': {'service': {'is_valid_service': False,
                                          'invalid_stages': ['not_has_uniquely_indexed_routes'],
                                          'has_valid_routes': True,
                                          'invalid_routes': []}},
            'route_level': {'service': {0: {'is_valid_route': True, 'invalid_stages': []},
                                        1: {'is_valid_route': True, 'invalid_stages': []}}}},
        'routing': {'services_have_routes_in_the_graph': True,
                    'service_routes_with_invalid_network_route': [],
                    'route_to_crow_fly_ratio': {'service': {0: 0.037918141839160244, 1: 0.037918141839160244}}}}
    assert_semantically_equal(report, correct_report)


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
    n.schedule = Schedule('epsg:27700')
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
