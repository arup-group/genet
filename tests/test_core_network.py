import ast
import json
import logging
import os
import sys
import uuid

import lxml
import networkx as nx
import pandas as pd
import geopandas as gpd
import pytest
from pandas.testing import assert_frame_equal, assert_series_equal
from geopandas.testing import assert_geodataframe_equal
from shapely.geometry import LineString, Polygon, Point

from genet.core import Network
from genet.input import matsim_reader
from tests.test_output_matsim_xml_writer import network_dtd, schedule_dtd
from genet.schedule_elements import Route, Service, Schedule, Stop
from genet.utils import plot, spatial
from genet.validate import network as network_validation
from genet.input import read
from genet import exceptions
from tests.fixtures import assert_semantically_equal, route, stop_epsg_27700, network_object_from_test_data, \
    full_fat_default_config_path, correct_schedule, vehicle_definitions_config_path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
pt2matsim_network_test_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "network.xml"))
pt2matsim_schedule_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "schedule.xml"))

puma_network_test_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "puma", "network.xml"))
puma_schedule_test_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "puma", "schedule.xml"))

simplified_network = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "simplified_network", "network.xml"))
simplified_schedule = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "simplified_network", "schedule.xml"))

network_link_attrib_text_missing = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "network_link_attrib_text_missing.xml"))


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


@pytest.fixture()
def network3():
    n3 = Network('epsg:4326')
    n3.add_node('101982',
                {'id': '101982',
                 'x': '114.161432',
                 'y': '22.279784',
                 'lon': 114.161432,
                 'lat': 22.279784,
                 's2_id': 5221390329378179871})
    n3.add_node('101986',
                {'id': '101986',
                 'x': '114.155850',
                 'y': '22.290983',
                 'lon': 114.155850,
                 'lat': 22.290983,
                 's2_id': 5221390328605860382})
    n3.add_link('0', '101982', '101986',
                attribs={'id': '0',
                         'from': '101982',
                         'to': '101986',
                         'freespeed': 4.166666666666667,
                         'capacity': 600.0,
                         'permlanes': 1.0,
                         'oneway': '1',
                         'modes': ['car'],
                         's2_from': 5221390329378179871,
                         's2_to': 5221390328605860382,
                         'length': 52.765151087870265,
                         'attributes': {'osm:way:access': {'name': 'osm:way:access',
                                                           'class': 'java.lang.String',
                                                           'text': 'permissive'},
                                        'osm:way:highway': {'name': 'osm:way:highway',
                                                            'class': 'java.lang.String',
                                                            'text': 'unclassified'},
                                        'osm:way:id': {'name': 'osm:way:id',
                                                       'class': 'java.lang.Long',
                                                       'text': '26997928564'},
                                        'osm:way:name': {'name': 'osm:way:name',
                                                         'class': 'java.lang.String',
                                                         'text': 'Garden Road'}}})
    return n3


@pytest.fixture()
def network4():
    n4 = Network('epsg:4326')
    n4.add_node('101982',
                {'id': '101982',
                 'x': '114.161432',
                 'y': '22.279784',
                 'z': -51,
                 'lon': 114.161432,
                 'lat': 22.279784,
                 's2_id': 5221390329378179871})
    n4.add_node('101986',
                {'id': '101986',
                 'x': '114.155850',
                 'y': '22.290983',
                 'z': 100,
                 'lon': 114.155850,
                 'lat': 22.290983,
                 's2_id': 5221390328605860382})
    n4.add_link('0', '101982', '101986',
                attribs={'id': '0',
                         'from': '101982',
                         'to': '101986',
                         'freespeed': 4.166666666666667,
                         'capacity': 600.0,
                         'permlanes': 1.0,
                         'oneway': '1',
                         'modes': ['car'],
                         's2_from': 5221390329378179871,
                         's2_to': 5221390328605860382,
                         'length': 52.765151087870265,
                         'attributes': {'osm:way:access': {'name': 'osm:way:access',
                                                           'class': 'java.lang.String',
                                                           'text': 'permissive'},
                                        'osm:way:highway': {'name': 'osm:way:highway',
                                                            'class': 'java.lang.String',
                                                            'text': 'unclassified'},
                                        'osm:way:id': {'name': 'osm:way:id',
                                                       'class': 'java.lang.Long',
                                                       'text': '26997928564'},
                                        'osm:way:name': {'name': 'osm:way:name',
                                                         'class': 'java.lang.String',
                                                         'text': 'Garden Road'}}})
    return n4


@pytest.fixture()
def network_for_summary_stats():
    n = Network('epsg:27700')
    n.add_node('0', attribs={'x': 528704.1425925883, 'y': 182068.78193707118})
    n.add_node('1', attribs={'x': 528804.1425925883, 'y': 182168.78193707118})
    n.add_link('link_0', '0', '1', attribs={'length': 123, 'modes': ['car', 'walk'], 'freespeed': 10, 'capacity': 5})
    n.add_link('link_1', '0', '1', attribs={'length': 123, 'modes': ['bike'],
                                            'attributes': {'osm:way:highway': 'secondary'}})
    n.add_link('link_2', '1', '0', attribs={'length': 123, 'modes': ['rail']})

    n.schedule = Schedule(epsg='epsg:27700', services=[
        Service(id='bus_service',
                routes=[
                    Route(id='1', route_short_name='', mode='bus',
                          stops=[
                              Stop(id='0', x=529455.7452394223, y=182401.37630677427, epsg='epsg:27700',
                                   linkRefId='link_1', attributes={'bikeAccessible': 'true',
                                                                   'accessLinkId_car': '1',
                                                                   'carAccessible': 'true',
                                                                   'distance_catchment': '25'}),
                              Stop(id='1', x=529350.7866124967, y=182388.0201078112, epsg='epsg:27700',
                                   linkRefId='link_2')],
                          trips={'trip_id': ['VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00'],
                                 'trip_departure_time': ['04:40:00'],
                                 'vehicle_id': ['veh_1_bus']},
                          arrival_offsets=['00:00:00', '00:02:00'],
                          departure_offsets=['00:00:00', '00:02:00'],
                          route=['link_1', 'link_2']),
                    Route(id='2', route_short_name='route2', mode='bus',
                          stops=[
                              Stop(id='0', x=529455.7452394223, y=182401.37630677427, epsg='epsg:27700',
                                   linkRefId='link_1'),
                              Stop(id='1', x=529350.7866124967, y=182388.0201078112, epsg='epsg:27700',
                                   linkRefId='link_2')],
                          trips={'trip_id': ['1_05:40:00', '2_05:45:00', '3_05:50:00', '4_06:40:00', '5_06:46:00'],
                                 'trip_departure_time': ['05:40:00', '05:45:00', '05:50:00', '06:40:00', '06:46:00'],
                                 'vehicle_id': ['veh_2_bus', 'veh_3_bus', 'veh_4_bus', 'veh_5_bus', 'veh_6_bus']},
                          arrival_offsets=['00:00:00', '00:03:00'],
                          departure_offsets=['00:00:00', '00:05:00'],
                          route=['link_1', 'link_2'])
                ]),
        Service(id='rail_service',
                routes=[Route(
                    route_short_name=r"RTR_I/love\_being//difficult",
                    mode='rail',
                    stops=[
                        Stop(id='RSN', x=-0.1410946, y=51.5231335, epsg='epsg:4326', name=r"I/love\_being//difficult"),
                        Stop(id='RSE', x=-0.1421595, y=51.5192615, epsg='epsg:4326')],
                    trips={'trip_id': ['RT1', 'RT2', 'RT3', 'RT4'],
                           'trip_departure_time': ['03:21:00', '03:31:00', '03:41:00', '03:51:00'],
                           'vehicle_id': ['veh_7_rail', 'veh_8_rail', 'veh_9_rail', 'veh_10_rail']},
                    arrival_offsets=['0:00:00', '0:02:00'],
                    departure_offsets=['0:00:00', '0:02:00']
                )])
    ])

    return n


def test_network_graph_initiates_as_not_simplififed():
    n = Network('epsg:27700')
    assert not n.is_simplified()


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
        '101982': {'id': '101982', 'x': -0.14625948709424305, 'y': 51.52287873323954, 'lon': -0.14625948709424305,
                   'lat': 51.52287873323954, 's2_id': 5221390329378179879},
        '101986': {'id': '101986', 'x': -0.14439428709377497, 'y': 51.52228713323965, 'lon': -0.14439428709377497,
                   'lat': 51.52228713323965, 's2_id': 5221390328605860387}}

    target_change_log = pd.DataFrame(
        {'timestamp': {3: '2020-07-09 19:50:51', 4: '2020-07-09 19:50:51'}, 'change_event': {3: 'modify', 4: 'modify'},
         'object_type': {3: 'node', 4: 'node'}, 'old_id': {3: '101982', 4: '101986'},
         'new_id': {3: '101982', 4: '101986'}, 'old_attributes': {
            3: "{'id': '101982', 'x': '528704.1425925883', 'y': '182068.78193707118', 'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879}",
            4: "{'id': '101986', 'x': '528835.203274008', 'y': '182006.27331298392', 'lon': -0.14439428709377497, 'lat': 51.52228713323965, 's2_id': 5221390328605860387}"},
         'new_attributes': {
             3: "{'id': '101982', 'x': -0.14625948709424305, 'y': 51.52287873323954, 'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879}",
             4: "{'id': '101986', 'x': -0.14439428709377497, 'y': 51.52228713323965, 'lon': -0.14439428709377497, 'lat': 51.52228713323965, 's2_id': 5221390328605860387}"},
         'diff': {3: [('change', 'x', ('528704.1425925883', -0.14625948709424305)),
                      ('change', 'y', ('182068.78193707118', 51.52287873323954))],
                  4: [('change', 'x', ('528835.203274008', -0.14439428709377497)),
                      ('change', 'y', ('182006.27331298392', 51.52228713323965))]}}
    )
    assert_semantically_equal(nodes, correct_nodes)
    for i in [3, 4]:
        assert_semantically_equal(ast.literal_eval(target_change_log.loc[i, 'old_attributes']),
                                  ast.literal_eval(network1.change_log.loc[i, 'old_attributes']))
        assert_semantically_equal(ast.literal_eval(target_change_log.loc[i, 'new_attributes']),
                                  ast.literal_eval(network1.change_log.loc[i, 'new_attributes']))
    cols_to_compare = ['change_event', 'object_type', 'old_id', 'new_id', 'diff']
    assert_frame_equal(network1.change_log[cols_to_compare].tail(2), target_change_log[cols_to_compare],
                       check_dtype=False)


def test_reproject_delegates_reprojection_to_schedules_own_method(network1, route, mocker):
    mocker.patch.object(Schedule, 'reproject')
    network1.schedule = Schedule(epsg='epsg:27700', services=[Service(id='id', routes=[route])])
    network1.reproject('epsg:4326')
    network1.schedule.reproject.assert_called_once_with('epsg:4326', 1)


def test_reproject_updates_graph_crs(network1):
    network1.reproject('epsg:4326')
    assert network1.graph.graph['crs'] == 'epsg:4326'


def test_reprojecting_links_with_geometries():
    n = Network('epsg:27700')
    n.add_nodes({'A': {'x': -82514.72274, 'y': 220772.02798},
                 'B': {'x': -82769.25894, 'y': 220773.0637}})
    n.add_links({'1': {'from': 'A', 'to': 'B',
                       'geometry': LineString([(-82514.72274, 220772.02798),
                                               (-82546.23894, 220772.88254),
                                               (-82571.87107, 220772.53339),
                                               (-82594.92709, 220770.68385),
                                               (-82625.33255, 220770.45579),
                                               (-82631.26842, 220770.40158),
                                               (-82669.7309, 220770.04349),
                                               (-82727.94946, 220770.79793),
                                               (-82757.38528, 220771.75412),
                                               (-82761.82425, 220771.95614),
                                               (-82769.25894, 220773.0637)])}})
    n.reproject('epsg:2157')

    geometry_coords = list(n.link('1')['geometry'].coords)

    assert round(geometry_coords[0][0], 7) == 532006.5605980
    assert round(geometry_coords[0][1], 7) == 547653.3751768

    assert round(geometry_coords[-1][0], 7) == 531753.4315189
    assert round(geometry_coords[-1][1], 7) == 547633.5224837


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


def test_adding_networks_with_clashing_node_ids_does_not_duplicate_data():
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
    n_right.add_node('1', {'id': '1', 'x': 528704.1425925883, 'y': 182068.78193707118,
                          'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879})
    n_right.add_node('2', {'id': '2', 'x': 528835.203274008, 'y': 182006.27331298392,
                          'lon': -0.14439428709377497, 'lat': 51.52228713323965, 's2_id': 5221390328605860387})
    n_right.add_link('1', '1', '2', 0, attribs={'modes': ['walk', 'bike']})

    assert len(list(n_left.nodes())) == 2
    assert n_left.node('1') == {'id': '1', 'x': 528704.1425925883, 'y': 182068.78193707118,
                                'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879}
    assert n_left.node('2') == {'id': '2', 'x': 528835.203274008, 'y': 182006.27331298392,
                                'lon': -0.14439428709377497, 'lat': 51.52228713323965, 's2_id': 5221390328605860387}
    assert len(n_left.link_id_mapping) == 1
    assert n_left.link('1') == {'modes': ['walk'], 'from': '1', 'to': '2', 'id': '1'}
    assert n_left.graph['1']['2'][0] == {'modes': ['walk'], 'from': '1', 'to': '2', 'id': '1'}


def test_adding_disjoint_networks_with_unique_ids_results_in_distinct_data_together():
    n_left = Network('epsg:27700')
    n_left.add_node('1', {'id': '1', 'x': 528704.1425925883, 'y': 182068.78193707118,
                          'lon': -0.14625948709424305, 'lat': 51.52287873323954, 's2_id': 5221390329378179879})
    n_left.add_node('2', {'id': '2', 'x': 528835.203274008, 'y': 182006.27331298392,
                          'lon': -0.14439428709377497, 'lat': 51.52228713323965, 's2_id': 5221390328605860387})
    n_left.add_link('1', '1', '2', attribs={'modes': ['walk']})

    n_right = Network('epsg:27700')
    n_right.add_node('10', {'id': '10', 'x': 1, 'y': 1,
                            'lon': 1, 'lat': 1, 's2_id': 1})
    n_right.add_node('20', {'id': '20', 'x': 1, 'y': 1,
                            'lon': 1, 'lat': 1, 's2_id': 2})
    n_right.add_link('100', '10', '20', attribs={'modes': ['walk']})

    n_left.add(n_right)
    assert_semantically_equal(dict(n_left.nodes()), {'10': {'id': '10', 'x': 1, 'y': 1, 'lon': 1, 'lat': 1, 's2_id': 1},
                                                     '20': {'id': '20', 'x': 1, 'y': 1, 'lon': 1, 'lat': 1, 's2_id': 2},
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


def test_adding_simplified_network_and_not_throws_error():
    n = Network('epsg:2770')
    m = Network('epsg:2770')
    m._mark_as_simplified()

    with pytest.raises(RuntimeError) as error_info:
        n.add(m)
    assert "cannot add" in str(error_info.value)


def test_print_shows_info(mocker):
    mocker.patch.object(Network, 'info')
    n = Network('epsg:27700')
    n.print()
    n.info.assert_called_once()


def test_plot_delegates_to_plot_kepler(mocker, network_object_from_test_data):
    mocker.patch.object(plot, 'plot_geodataframes_on_kepler_map')
    network_object_from_test_data.plot()
    plot.plot_geodataframes_on_kepler_map.assert_called_once()


def test_plot_saves_to_the_specified_directory(tmpdir, network_object_from_test_data):
    filename = 'network_with_pt_routes'
    expected_plot_path = os.path.join(tmpdir, filename + '.html')
    assert not os.path.exists(expected_plot_path)

    network_object_from_test_data.plot(output_dir=tmpdir)

    assert os.path.exists(expected_plot_path)


def test_plot_graph_delegates_to_plot_kepler(mocker, network_object_from_test_data):
    mocker.patch.object(plot, 'plot_geodataframes_on_kepler_map')

    network_object_from_test_data.plot_graph()

    plot.plot_geodataframes_on_kepler_map.assert_called_once()


def test_plot_graph_saves_to_the_specified_directory(tmpdir, network_object_from_test_data):
    filename = 'network_graph'
    expected_plot_path = os.path.join(tmpdir, filename + '.html')
    assert not os.path.exists(expected_plot_path)

    network_object_from_test_data.plot_graph(output_dir=tmpdir)

    assert os.path.exists(expected_plot_path)


def test_plot_schedule_delegates_to_plot_kepler(mocker, network_object_from_test_data):
    mocker.patch.object(plot, 'plot_geodataframes_on_kepler_map')

    network_object_from_test_data.plot_schedule()

    plot.plot_geodataframes_on_kepler_map.assert_called_once()


def test_plot_schedule_saves_to_the_specified_directory(tmpdir, network_object_from_test_data):
    filename = 'network_and_schedule'
    expected_plot_path = os.path.join(tmpdir, filename + '.html')
    assert not os.path.exists(expected_plot_path)

    network_object_from_test_data.plot_schedule(output_dir=tmpdir)

    assert os.path.exists(expected_plot_path)


def test_attempt_to_simplify_already_simplified_network_throws_error():
    n = Network('epsg:27700')
    n._mark_as_simplified()

    with pytest.raises(RuntimeError) as error_info:
        n.simplify()
    assert "cannot simplify" in str(error_info.value)


@pytest.fixture()
def puma_network():
    return read.read_matsim(
        path_to_network=puma_network_test_file, epsg='epsg:27700', path_to_schedule=puma_schedule_test_file)


@pytest.fixture()
def puma_network_with_pt_stops_at_risk_of_oversimplification(puma_network):
    return {
        'network': puma_network,
        'pt_stops_at_risk': ['5221390681543854913', '5221390302070799085', '5221390323679791901']
    }


@pytest.fixture()
def network_with_simplified_schema():
    # characterised by complex geometry link attribute and set text value in nested attributes dictionary
    n = Network('epsg:27700')
    n.add_node('101982',
               {'id': '101982',
                'x': '528704.1425925883',
                'y': '182068.78193707118',
                'lon': -0.14625948709424305,
                'lat': 51.52287873323954,
                's2_id': 5221390329378179879})
    n.add_node('101986',
               {'id': '101986',
                'x': '528835.203274008',
                'y': '182006.27331298392',
                'lon': -0.14439428709377497,
                'lat': 51.52228713323965,
                's2_id': 5221390328605860387})
    n.add_link('0', '101982', '101986',
               attribs={'id': '0',
                        'from': '101982',
                        'to': '101986',
                        'freespeed': 4.166666666666667,
                        'capacity': 600.0,
                        'permlanes': 1.0,
                        'oneway': '1',
                        'modes': {'car'},
                        'geometry': LineString(
                            [(528704.1425925883, 182068.78193707118), (528754.425925883, 182038.78193707118),
                             (528835.203274008, 182006.27331298392)]),
                        's2_from': 5221390329378179879,
                        's2_to': 5221390328605860387,
                        'length': 52.765151087870265,
                        'attributes': {'osm:way:highway': {'name': 'osm:way:highway',
                                                           'class': 'java.lang.String',
                                                           'text': {'unclassified', 'other'}}}})
    return n


def test_simplifing_puma_network_results_in_correct_record_of_simplified_links(puma_network):
    assert not puma_network.is_simplified()
    link_ids_pre_simplify = set(dict(puma_network.links()).keys())

    puma_network.simplify()
    assert puma_network.is_simplified()

    link_ids_post_simplify = set(dict(puma_network.links()).keys())

    new_links = link_ids_post_simplify - link_ids_pre_simplify
    deleted_links = link_ids_pre_simplify - link_ids_post_simplify

    # check the links removed in simplification are mapped to new links
    assert set(puma_network.link_simplification_map.keys()).issubset(deleted_links)
    # check map points to new links
    assert set(puma_network.link_simplification_map.values()) == new_links
    # check all new links in the network have edge mappings (present in link_id_mapping)
    assert (set(puma_network.link_id_mapping.keys()) & new_links) == new_links


def test_simplifing_puma_network_results_in_a_valid_schedule(puma_network):
    puma_network.simplify()
    puma_network.schedule.is_valid_schedule()


def test_simplifing_puma_network_results_in_a_schedule_with_valid_network_routes(puma_network):
    puma_network.simplify()
    puma_network.has_schedule_with_valid_network_routes()


def test_simplify_does_not_oversimplify_PT_endpoints(puma_network_with_pt_stops_at_risk_of_oversimplification):
    puma_network = puma_network_with_pt_stops_at_risk_of_oversimplification['network']
    pt_stops_at_risk = puma_network_with_pt_stops_at_risk_of_oversimplification['pt_stops_at_risk']

    assert not puma_network.is_simplified()
    for s in pt_stops_at_risk:
        assert puma_network.link(puma_network.schedule.stop(s).linkRefId)['length'] == 1

    puma_network.simplify()

    for s in pt_stops_at_risk:
        assert puma_network.link(puma_network.schedule.stop(s).linkRefId)['length'] == 1


def test_simplify_keeps_pt_stop_loops(puma_network):
    puma_network.simplify()

    for stop in puma_network.schedule.stops():
        assert puma_network.link(stop.linkRefId)['from'] == puma_network.link(stop.linkRefId)['to']
        assert puma_network.link(stop.linkRefId)['length'] == 1


def test_simplified_network_saves_to_correct_dtds(tmpdir, network_dtd, network_with_simplified_schema):
    network_with_simplified_schema.write_to_matsim(tmpdir)

    generated_network_file_path = os.path.join(tmpdir, 'network.xml')
    xml_obj = lxml.etree.parse(generated_network_file_path)
    assert network_dtd.validate(xml_obj), \
        'Doc generated at {} is not valid against DTD due to {}'.format(generated_network_file_path,
                                                                        network_dtd.error_log.filter_from_errors())


def test_network_tagged_as_simplified_saves_to_correct_dtds(tmpdir, network_dtd):
    n = Network(epsg='epsg:27700')
    n._mark_as_simplified()

    n.write_to_matsim(tmpdir)
    generated_network_file_path = os.path.join(tmpdir, 'network.xml')

    xml_obj = lxml.etree.parse(generated_network_file_path)
    assert network_dtd.validate(xml_obj), \
        'Doc generated at {} is not valid against DTD due to {}'.format(generated_network_file_path,
                                                                        network_dtd.error_log.filter_from_errors())


def test_simplifying_network_with_multi_edges_resulting_in_multi_paths():
    n = Network('epsg:27700')
    n.add_nodes({
        'n_-1': {'x': -1, 'y': -1, 's2_id': -1},
        'n_0': {'x': 0, 'y': 0, 's2_id': 0},
        'n_1': {'x': 1, 'y': 1, 's2_id': 1},
        'n_2': {'x': 2, 'y': 2, 's2_id': 2},
        'n_3': {'x': 3, 'y': 3, 's2_id': 3},
        'n_4': {'x': 4, 'y': 4, 's2_id': 4},
        'n_5': {'x': 5, 'y': 5, 's2_id': 5},
        'n_6': {'x': 6, 'y': 5, 's2_id': 6},
    })
    n.add_links({
        'l_-1': {'from': 'n_-1', 'to': 'n_1', 'freespeed': 1, 'capacity': 1, 'permlanes': 1, 'length': 1,
                 'modes': {'car'}},
        'l_0': {'from': 'n_0', 'to': 'n_1', 'freespeed': 1, 'capacity': 1, 'permlanes': 1, 'length': 1,
                'modes': {'car'}},
        'l_1': {'from': 'n_1', 'to': 'n_2', 'freespeed': 1, 'capacity': 1, 'permlanes': 1, 'length': 1,
                'modes': {'car'}},
        'l_2': {'from': 'n_1', 'to': 'n_2', 'freespeed': 1, 'capacity': 1, 'permlanes': 1, 'length': 1,
                'modes': {'car'}},
        'l_3': {'from': 'n_2', 'to': 'n_3', 'freespeed': 1, 'capacity': 1, 'permlanes': 1, 'length': 1,
                'modes': {'car'}},
        'l_4': {'from': 'n_2', 'to': 'n_3', 'freespeed': 1, 'capacity': 1, 'permlanes': 1, 'length': 1,
                'modes': {'car'}},
        'l_5': {'from': 'n_3', 'to': 'n_4', 'freespeed': 1, 'capacity': 1, 'permlanes': 1, 'length': 1,
                'modes': {'car'}},
        'l_6': {'from': 'n_3', 'to': 'n_4', 'freespeed': 1, 'capacity': 1, 'permlanes': 1, 'length': 1,
                'modes': {'car'}},
        'l_7': {'from': 'n_4', 'to': 'n_5', 'freespeed': 1, 'capacity': 1, 'permlanes': 1, 'length': 1,
                'modes': {'car'}},
        'l_8': {'from': 'n_4', 'to': 'n_6', 'freespeed': 1, 'capacity': 1, 'permlanes': 1, 'length': 1,
                'modes': {'car'}}
    })

    n.simplify()

    assert set(n.link_simplification_map) == {'l_4', 'l_1', 'l_5', 'l_3', 'l_6', 'l_2'}


def test_reading_back_simplified_network():
    # simplified networks have additional geometry attribute and some of their attributes are composite, e.g. links
    # now refer to a number of osm ways each with a unique id
    n = read.read_matsim(path_to_network=simplified_network, epsg='epsg:27700',
                         path_to_schedule=simplified_schedule)

    number_of_simplified_links = 659

    links_with_geometry = n.extract_links_on_edge_attributes(conditions={'geometry': lambda x: True})

    assert len(links_with_geometry) == number_of_simplified_links

    for link in links_with_geometry:
        attribs = n.link(link)
        if 'attributes' in attribs:
            assert not 'geometry' in attribs['attributes']
            for k, v in attribs['attributes'].items():
                if isinstance(v, str):
                    assert not ',' in v


def test_simplified_tag_for_network_is_read_correctly_with_bool_attribute():
    n = read.read_matsim(path_to_network=simplified_network, epsg='epsg:27700',
                         path_to_schedule=simplified_schedule)
    assert n.attributes['simplified']


def test_network_with_missing_link_attribute_elem_text_is_read_and_able_to_save_again(tmpdir):
    n = read.read_matsim(path_to_network=network_link_attrib_text_missing, epsg='epsg:27700')
    n.write_to_matsim(tmpdir)


def test_node_attribute_data_under_key_returns_correct_pd_series_with_nested_keys():
    n = Network('epsg:27700')
    n.add_node(1, {'x': 1, 'y': 2, 'a': {'b': 1}})
    n.add_node(2, {'x': 1, 'y': 2, 'a': {'b': 4}})

    output_series = n.node_attribute_data_under_key(key={'a': 'b'})
    assert_series_equal(output_series, pd.Series({1: 1, 2: 4}))


def test_node_attribute_data_under_key_returns_correct_pd_series_with_flat_keys():
    n = Network('epsg:27700')
    n.add_node(1, {'x': 1, 'y': 2, 'b': 1})
    n.add_node(2, {'x': 1, 'y': 2, 'b': 4})

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
    network1.add_node('1', {'x': 1, 'y': 2, 'key': {'nested_value': {'more_nested': 4}}})
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
    n.add_node(1, {'x': 1, 'y': 2, 'a': 1})
    assert n.graph.has_node(1)
    assert n.node(1)['x'] == 1
    assert n.node(1)['y'] == 2
    assert n.node(1)['a'] == 1


def test_add_node_without_attribs_raises_error():
    with pytest.raises(TypeError):
        n = Network('epsg:27700')
        n.add_node(1)


def test_adding_node_with_only_lat_lon_attribs_fills_in_x_y():
    n = Network('epsg:27700')
    n.add_node(1, {'lat': 51.521719064780775, 'lon': -0.13777870665428316})

    assert round(n.node(1)['x'], 2) == 529295.75
    assert round(n.node(1)['y'], 2) == 181954.76


def test_adding_node_with_only_lat_lon_attribs_fills_in_s2_id():
    n = Network('epsg:27700')
    n.add_node(1, {'lat': 51.521719064780775, 'lon': -0.13777870665428316})

    assert n.node(1)['s2_id'] == 5221390681084663239


def test_adding_node_with_only_x_y_attribs_fills_in_lat_lon():
    n = Network('epsg:27700')
    n.add_node(1, {'x': 529295.7525339661, 'y': 181954.76039674896})

    assert round(n.node(1)['lat'], 6) == 51.521719
    assert round(n.node(1)['lon'], 6) == -0.137779


def test_adding_nodes_with_mismatched_spatial_attribs_gets_filled_in():
    n = Network('epsg:27700')
    n.add_nodes({1: {'lat': 51.521719064780775, 'lon': -0.13777870665428316},
                 2: {'x': 529295.7525339661, 'y': 181954.76039674896}})

    assert round(n.node(1)['x'], 2) == 529295.75
    assert round(n.node(1)['y'], 2) == 181954.76

    assert round(n.node(2)['lat'], 6) == 51.521719
    assert round(n.node(2)['lon'], 6) == -0.137779


def test_adding_nodes_with_mismatched_spatial_attribs_generates_s2ids():
    n = Network('epsg:27700')
    n.add_nodes({1: {'lat': 51.521719064780775, 'lon': -0.13777870665428316},
                 2: {'x': 529295.7525339661, 'y': 181954.76039674896}})

    assert n.node(1)['s2_id'] == 5221390681084663239
    assert n.node(2)['s2_id'] == 5221390681084663239


def test_adding_node_with_clashing_id_reindexes_new_node():
    n = Network('epsg:27700')
    n.add_node(1, {'x': 1, 'y': 2})

    new_node = n.add_node(1, {'x': 2, 'y': 2, 'a': 2})
    assert 1 in new_node


def test_add_multiple_nodes():
    n = Network('epsg:27700')
    reindexing_dict, actual_nodes_added = n.add_nodes({1: {'x': 1, 'y': 2}, 2: {'x': 2, 'y': 2}})
    assert n.graph.has_node(1)
    assert n.node(1)['x'] == 1
    assert n.node(1)['y'] == 2
    assert n.node(1)['id'] == 1
    assert n.graph.has_node(2)
    assert n.node(2)['x'] == 2
    assert n.node(2)['y'] == 2
    assert n.node(2)['id'] == 2
    assert reindexing_dict == {}


def test_add_nodes_with_clashing_ids():
    n = Network('epsg:27700')
    n.add_node(1, {'x': 1, 'y': 2})
    reindexing_dict, actual_nodes_added = n.add_nodes({1: {'x': 1, 'y': 2}, 2: {'x': 2, 'y': 2}})
    assert n.graph.has_node(1)
    assert n.node(1)['x'] == 1
    assert n.node(1)['y'] == 2
    assert n.node(1)['id'] == 1
    assert n.graph.has_node(2)
    assert n.node(2)['x'] == 2
    assert n.node(2)['y'] == 2
    assert n.node(2)['id'] == 2
    assert 1 in reindexing_dict
    assert n.graph.has_node(reindexing_dict[1])
    assert n.node(reindexing_dict[1])['x'] == 1
    assert n.node(reindexing_dict[1])['y'] == 2
    assert n.node(reindexing_dict[1])['id'] == reindexing_dict[1]


def test_add_nodes_with_multiple_clashing_ids():
    n = Network('epsg:27700')
    n.add_node(1, {'x': 1, 'y': 2})
    n.add_node(2, {'x': 1, 'y': 2})
    assert n.graph.has_node(1)
    assert n.node(1)['x'] == 1
    assert n.node(1)['y'] == 2
    assert n.node(1)['id'] == 1
    assert n.graph.has_node(2)
    assert n.node(2)['x'] == 1
    assert n.node(2)['y'] == 2
    assert n.node(2)['id'] == 2
    reindexing_dict, actual_nodes_added = n.add_nodes({1: {'x': 1, 'y': 2}, 2: {'x': 2, 'y': 2}})
    assert 1 in reindexing_dict
    assert n.graph.has_node(reindexing_dict[1])
    assert n.node(reindexing_dict[1])['x'] == 1
    assert n.node(reindexing_dict[1])['y'] == 2
    assert n.node(reindexing_dict[1])['id'] == reindexing_dict[1]

    assert 2 in reindexing_dict
    assert n.graph.has_node(reindexing_dict[2])
    assert n.node(reindexing_dict[2])['x'] == 2
    assert n.node(reindexing_dict[2])['y'] == 2
    assert n.node(reindexing_dict[2])['id'] == reindexing_dict[2]


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
    assert '0' in n.link_id_mapping
    assert '1' in n.link_id_mapping
    if n.link_id_mapping['0'] == {'from': 1, 'to': 2, 'multi_edge_idx': 0}:
        assert n.link_id_mapping['1'] == {'from': 2, 'to': 3, 'multi_edge_idx': 0}
    elif n.link_id_mapping['1'] == {'from': 1, 'to': 2, 'multi_edge_idx': 0}:
        assert n.link_id_mapping['0'] == {'from': 2, 'to': 3, 'multi_edge_idx': 0}
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


def test_adding_links_with_different_non_overlapping_attributes():
    # generates a nan attribute for link attributes
    n = Network('epsg:27700')
    reindexing_dict, links_and_attributes = n.add_links({
        '2': {'from': 1, 'to': 2, 'speed': 20},
        '3': {'from': 1, 'to': 2, 'capacity': 123},
        '4': {'from': 2, 'to': 3, 'modes': [1, 2, 3]}})

    assert reindexing_dict == {}
    assert_semantically_equal(links_and_attributes, {
        '2': {'id': '2', 'from': 1, 'to': 2, 'speed': 20},
        '3': {'id': '3', 'from': 1, 'to': 2, 'capacity': 123},
        '4': {'id': '4', 'from': 2, 'to': 3, 'modes': [1, 2, 3]}})


def test_adding_multiple_links_to_same_edge_clashing_with_existing_edge():
    n = Network('epsg:27700')
    n.add_link(link_id='0', u='2', v='2', attribs={'speed': 20})

    n.add_links({'1': {'from': '2', 'to': '2', 'something': 20},
                 '2': {'from': '2', 'to': '2', 'capacity': 123}})

    assert_semantically_equal(dict(n.links()), {'0': {'speed': 20, 'from': '2', 'to': '2', 'id': '0'},
                                                '1': {'from': '2', 'to': '2', 'something': 20.0, 'id': '1'},
                                                '2': {'from': '2', 'to': '2', 'capacity': 123.0, 'id': '2'}})
    assert_semantically_equal(n.link_id_mapping, {'0': {'from': '2', 'to': '2', 'multi_edge_idx': 0},
                                                  '1': {'from': '2', 'to': '2', 'multi_edge_idx': 1},
                                                  '2': {'from': '2', 'to': '2', 'multi_edge_idx': 2}})


def test_network_modal_subgraph_using_general_subgraph_on_link_attribs():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'modes': ['car', 'bike']})
    n.add_link('1', 2, 3, attribs={'modes': ['car']})
    n.add_link('2', 2, 3, attribs={'modes': ['bike']})

    car_graph = n.subgraph_on_link_conditions(conditions={'modes': 'car'}, mixed_dtypes=True)
    assert list(car_graph.edges) == [(1, 2, 0), (2, 3, 0)]


def test_modes():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'modes': ['car', 'bike']})
    n.add_link('1', 2, 3, attribs={'modes': ['car']})
    n.add_link('2', 2, 3, attribs={'modes': ['bike']})
    n.add_link('3', 2, 3, attribs={})

    assert n.modes() == {'car', 'bike'}


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

    car_bike_graph = n.modal_subgraph(modes=['car', 'bike'])
    assert list(car_bike_graph.edges) == [(1, 2, 0), (2, 3, 0), (2, 3, 1)]


def test_links_on_modal_condition():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'modes': ['car', 'bike']})
    n.add_link('1', 2, 3, attribs={'modes': ['car']})
    n.add_link('2', 2, 3, attribs={'modes': ['bike']})
    n.add_link('3', 2, 3, attribs={'modes': ['walk']})

    car_links = n.links_on_modal_condition(modes=['car'])
    assert set(car_links) == {'0', '1'}


def test_nodes_on_modal_condition():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'modes': ['car', 'bike']})
    n.add_link('1', 2, 3, attribs={'modes': ['car']})
    n.add_link('2', 2, 3, attribs={'modes': ['bike']})
    n.add_link('3', 2, 3, attribs={'modes': ['walk']})

    car_nodes = n.nodes_on_modal_condition(modes=['car'])
    assert set(car_nodes) == {1, 2, 3}


test_geojson = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "test_geojson.geojson"))


def test_nodes_on_spatial_condition_with_geojson(network_object_from_test_data):
    network_object_from_test_data.add_node('1', {'id': '1', 'x': 508400, 'y': 162050})
    nodes = network_object_from_test_data.nodes_on_spatial_condition(test_geojson)
    assert set(nodes) == {'21667818', '25508485'}


def test_nodes_on_spatial_condition_with_shapely_geom(network_object_from_test_data):
    region = Polygon([(-0.1487016677856445, 51.52556684350165), (-0.14063358306884766, 51.5255134425896),
                      (-0.13865947723388672, 51.5228700191647), (-0.14093399047851562, 51.52006622056997),
                      (-0.1492595672607422, 51.51974577545329), (-0.1508045196533203, 51.52276321095246),
                      (-0.1487016677856445, 51.52556684350165)])
    network_object_from_test_data.add_node('1', {'id': '1', 'x': 508400, 'y': 162050})
    nodes = network_object_from_test_data.nodes_on_spatial_condition(region)
    assert set(nodes) == {'21667818', '25508485'}


def test_nodes_on_spatial_condition_with_s2_region(network_object_from_test_data):
    region = '48761ad04d,48761ad054,48761ad05c,48761ad061,48761ad085,48761ad08c,48761ad094,48761ad09c,48761ad0b,48761ad0d,48761ad0f,48761ad14,48761ad182c,48761ad19c,48761ad1a4,48761ad1ac,48761ad1b4,48761ad1bac,48761ad3d7f,48761ad3dc,48761ad3e4,48761ad3ef,48761ad3f4,48761ad3fc,48761ad41,48761ad43,48761ad5d,48761ad5e4,48761ad5ec,48761ad5fc,48761ad7,48761ad803,48761ad81c,48761ad824,48761ad82c,48761ad9d,48761ad9e4,48761ad9e84,48761ad9fc,48761ada04,48761ada0c,48761b2804,48761b2814,48761b281c,48761b283,48761b2844,48761b284c,48761b2995,48761b29b4,48761b29bc,48761b29d,48761b29f,48761b2a04'
    network_object_from_test_data.add_node(
        '1', {'id': '1', 'x': 508400, 'y': 162050, 's2_id': spatial.generate_index_s2(51.3472033, 0.4449167)})
    nodes = network_object_from_test_data.nodes_on_spatial_condition(region)
    assert set(nodes) == {'21667818', '25508485'}


def test_links_on_spatial_condition_with_geojson(network_object_from_test_data):
    network_object_from_test_data.add_node('1', {'id': '1', 'x': 508400, 'y': 162050})
    network_object_from_test_data.add_link('2', u='21667818', v='1')
    links = network_object_from_test_data.links_on_spatial_condition(test_geojson)
    assert set(links) == {'1', '2'}


def test_links_on_spatial_condition_with_shapely_geom(network_object_from_test_data):
    region = Polygon([(-0.1487016677856445, 51.52556684350165), (-0.14063358306884766, 51.5255134425896),
                      (-0.13865947723388672, 51.5228700191647), (-0.14093399047851562, 51.52006622056997),
                      (-0.1492595672607422, 51.51974577545329), (-0.1508045196533203, 51.52276321095246),
                      (-0.1487016677856445, 51.52556684350165)])
    network_object_from_test_data.add_node('1', {'id': '1', 'x': 508400, 'y': 162050})
    network_object_from_test_data.add_link('2', u='21667818', v='1')
    links = network_object_from_test_data.links_on_spatial_condition(region)
    assert set(links) == {'1', '2'}


def test_links_on_spatial_condition_with_s2_region(network_object_from_test_data):
    region = '48761ad04d,48761ad054,48761ad05c,48761ad061,48761ad085,48761ad08c,48761ad094,48761ad09c,48761ad0b,48761ad0d,48761ad0f,48761ad14,48761ad182c,48761ad19c,48761ad1a4,48761ad1ac,48761ad1b4,48761ad1bac,48761ad3d7f,48761ad3dc,48761ad3e4,48761ad3ef,48761ad3f4,48761ad3fc,48761ad41,48761ad43,48761ad5d,48761ad5e4,48761ad5ec,48761ad5fc,48761ad7,48761ad803,48761ad81c,48761ad824,48761ad82c,48761ad9d,48761ad9e4,48761ad9e84,48761ad9fc,48761ada04,48761ada0c,48761b2804,48761b2814,48761b281c,48761b283,48761b2844,48761b284c,48761b2995,48761b29b4,48761b29bc,48761b29d,48761b29f,48761b2a04'
    network_object_from_test_data.add_node('1', {'id': '1', 'x': 508400, 'y': 162050})
    network_object_from_test_data.add_link('2', u='21667818', v='1')
    links = network_object_from_test_data.links_on_spatial_condition(region)
    assert set(links) == {'1', '2'}


def test_links_on_spatial_condition_with_intersection_and_complex_geometry_that_falls_outside_region(
        network_object_from_test_data):
    region = Polygon([(-0.1487016677856445, 51.52556684350165), (-0.14063358306884766, 51.5255134425896),
                      (-0.13865947723388672, 51.5228700191647), (-0.14093399047851562, 51.52006622056997),
                      (-0.1492595672607422, 51.51974577545329), (-0.1508045196533203, 51.52276321095246),
                      (-0.1487016677856445, 51.52556684350165)])
    network_object_from_test_data.add_link(
        '2', u='21667818', v='25508485',
        attribs={'geometry': LineString(
            [(528504.1342843144, 182155.7435136598), (508400, 162050), (528489.467895946, 182206.20303669578)])})
    links = network_object_from_test_data.links_on_spatial_condition(region, how='intersect')
    assert set(links) == {'1', '2'}


def test_links_on_spatial_condition_with_containement(network_object_from_test_data):
    region = Polygon([(-0.1487016677856445, 51.52556684350165), (-0.14063358306884766, 51.5255134425896),
                      (-0.13865947723388672, 51.5228700191647), (-0.14093399047851562, 51.52006622056997),
                      (-0.1492595672607422, 51.51974577545329), (-0.1508045196533203, 51.52276321095246),
                      (-0.1487016677856445, 51.52556684350165)])
    network_object_from_test_data.add_node('1', {'id': '1', 'x': 508400, 'y': 162050})
    network_object_from_test_data.add_link('2', u='21667818', v='1')
    links = network_object_from_test_data.links_on_spatial_condition(region, how='within')
    assert set(links) == {'1'}


def test_links_on_spatial_condition_with_containement_and_complex_geometry_that_falls_outside_region(
        network_object_from_test_data):
    region = Polygon([(-0.1487016677856445, 51.52556684350165), (-0.14063358306884766, 51.5255134425896),
                      (-0.13865947723388672, 51.5228700191647), (-0.14093399047851562, 51.52006622056997),
                      (-0.1492595672607422, 51.51974577545329), (-0.1508045196533203, 51.52276321095246),
                      (-0.1487016677856445, 51.52556684350165)])
    network_object_from_test_data.add_link(
        '2', u='21667818', v='25508485',
        attribs={'geometry': LineString(
            [(528504.1342843144, 182155.7435136598), (508400, 162050), (528489.467895946, 182206.20303669578)])})
    links = network_object_from_test_data.links_on_spatial_condition(region, how='within')
    assert set(links) == {'1'}


def test_links_on_spatial_condition_with_containement_and_s2_region(network_object_from_test_data):
    region = '48761ad04d,48761ad054,48761ad05c,48761ad061,48761ad085,48761ad08c,48761ad094,48761ad09c,48761ad0b,48761ad0d,48761ad0f,48761ad14,48761ad182c,48761ad19c,48761ad1a4,48761ad1ac,48761ad1b4,48761ad1bac,48761ad3d7f,48761ad3dc,48761ad3e4,48761ad3ef,48761ad3f4,48761ad3fc,48761ad41,48761ad43,48761ad5d,48761ad5e4,48761ad5ec,48761ad5fc,48761ad7,48761ad803,48761ad81c,48761ad824,48761ad82c,48761ad9d,48761ad9e4,48761ad9e84,48761ad9fc,48761ada04,48761ada0c,48761b2804,48761b2814,48761b281c,48761b283,48761b2844,48761b284c,48761b2995,48761b29b4,48761b29bc,48761b29d,48761b29f,48761b2a04'
    network_object_from_test_data.add_node('1', {'id': '1', 'x': 508400, 'y': 162050})
    network_object_from_test_data.add_link('2', u='21667818', v='1')
    links = network_object_from_test_data.links_on_spatial_condition(region, how='within')
    assert set(links) == {'1'}


def test_links_on_spatial_condition_with_containement_and_complex_geometry_that_falls_outside_s2_region(
        network_object_from_test_data):
    region = '48761ad04d,48761ad054,48761ad05c,48761ad061,48761ad085,48761ad08c,48761ad094,48761ad09c,48761ad0b,48761ad0d,48761ad0f,48761ad14,48761ad182c,48761ad19c,48761ad1a4,48761ad1ac,48761ad1b4,48761ad1bac,48761ad3d7f,48761ad3dc,48761ad3e4,48761ad3ef,48761ad3f4,48761ad3fc,48761ad41,48761ad43,48761ad5d,48761ad5e4,48761ad5ec,48761ad5fc,48761ad7,48761ad803,48761ad81c,48761ad824,48761ad82c,48761ad9d,48761ad9e4,48761ad9e84,48761ad9fc,48761ada04,48761ada0c,48761b2804,48761b2814,48761b281c,48761b283,48761b2844,48761b284c,48761b2995,48761b29b4,48761b29bc,48761b29d,48761b29f,48761b2a04'
    network_object_from_test_data.add_link(
        '2', u='21667818', v='25508485',
        attribs={'geometry': LineString(
            [(528504.1342843144, 182155.7435136598), (508400, 162050), (528489.467895946, 182206.20303669578)])})
    links = network_object_from_test_data.links_on_spatial_condition(region, how='within')
    assert set(links) == {'1'}


@pytest.fixture()
def network_to_subset():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'modes': ['car'], 'length': 1})
    n.add_link('1', 2, 3, attribs={'modes': ['car'], 'length': 1})
    n.add_link('2', 3, 2, attribs={'modes': ['car'], 'length': 1})
    n.add_link('3', 2, 1, attribs={'modes': ['car'], 'length': 1})
    return n


def test_modifying_subnetwork_does_not_affect_the_original(network_to_subset):
    assert {_id for _id, dat in network_to_subset.links()} == {'0', '1', '2', '3'}

    subnet = network_to_subset.subnetwork({'0', '3'})

    assert {_id for _id, dat in subnet.links()} == {'0', '3'}
    assert set(subnet.link_id_mapping.keys()) == {'0', '3'}
    assert {_id for _id, dat in network_to_subset.links()} == {'0', '1', '2', '3'}
    assert set(network_to_subset.link_id_mapping.keys()) == {'0', '1', '2', '3'}


def test_extracting_subnetwork_results_in_strongly_connected_graph(network_to_subset):
    subnet = network_to_subset.subnetwork({'0', '2', '3'})
    assert {_id for _id, dat in subnet.links()} == {'0', '3'}


def test_extracting_subnetwork_updates_link_id_map(network_to_subset):
    subnet = network_to_subset.subnetwork({'0', '3'})
    assert set(subnet.link_id_mapping.keys()) == {'0', '3'}


def test_extracting_subnetwork_with_schedule_retains_pt_routes(network_object_from_test_data):
    subnet = network_object_from_test_data.subnetwork({}, {'10314'})
    assert set(subnet.link_id_mapping.keys()) == {'1'}


def test_extracting_subnetwork_with_schedule_returns_subschedule(network_object_from_test_data):
    subnet = network_object_from_test_data.subnetwork({}, {'10314'})
    assert set(subnet.schedule.service_ids()) == {'10314'}


def test_subnetwork_on_spatial_condition_delagates_to_spatial_methods_to_get_subset_items(mocker,
                                                                                          network_object_from_test_data):
    mocker.patch.object(Schedule, 'services_on_spatial_condition', return_value={'service'})
    mocker.patch.object(Network, 'links_on_spatial_condition', return_value={'link'})
    mocker.patch.object(Network, 'subnetwork')

    network_object_from_test_data.subnetwork_on_spatial_condition(region_input='region')

    Schedule.services_on_spatial_condition.assert_called_once_with(region_input='region', how='intersect')
    Network.links_on_spatial_condition.assert_called_once_with(region_input='region', how='intersect')
    Network.subnetwork.assert_called_once_with(links={'link'}, services={'service'}, n_connected_components=1,
                                               strongly_connected_modes=None)


def test_removing_mode_from_links_updates_the_modes():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'modes': {'car', 'bike'}, 'length': 1})
    n.add_link('1', 2, 3, attribs={'modes': {'car'}, 'length': 1})
    n.add_link('2', 2, 3, attribs={'modes': {'bike'}, 'length': 1})
    n.add_link('3', 2, 3, attribs={'modes': {'walk'}, 'length': 1})

    n.remove_mode_from_links(links=['0'], mode='bike')
    assert n.link('0')['modes'] == {'car'}


def test_removing_multiple_modes_from_links_updates_the_modes():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'modes': {'car', 'bike'}, 'length': 1})
    n.add_link('1', 2, 3, attribs={'modes': {'car'}, 'length': 1})
    n.add_link('2', 2, 3, attribs={'modes': {'bike'}, 'length': 1})
    n.add_link('3', 2, 3, attribs={'modes': {'walk', 'car'}, 'length': 1})

    n.remove_mode_from_links(links=['0', '3'], mode=['bike', 'walk'])
    assert n.link('0')['modes'] == {'car'}
    assert n.link('3')['modes'] == {'car'}


def test_removing_mode_from_links_removes_empty_links():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'modes': {'car', 'bike'}, 'length': 1})
    n.add_link('1', 2, 3, attribs={'modes': {'car'}, 'length': 1})
    n.add_link('2', 2, 3, attribs={'modes': {'bike'}, 'length': 1})
    n.add_link('3', 2, 3, attribs={'modes': {'walk'}, 'length': 1})

    n.remove_mode_from_links(links=['0', '2'], mode='bike')
    assert not n.has_link('2')
    assert n.has_link('0')


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
    # no need to test new_attributes and old_attributes columns if testing diff - it depends on those
    cols_to_compare = ['change_event', 'object_type', 'old_id', 'new_id', 'diff']
    assert_frame_equal(network1.change_log[cols_to_compare].tail(3), correct_change_log_df[cols_to_compare],
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
    assert_frame_equal(network1.change_log[cols_to_compare].tail(2), correct_change_log_df[cols_to_compare],
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
    n.add_node(1, {'id': 1, 'x': 1, 'y': 2, 'a': 1})
    n.apply_attributes_to_node(1, {'b': 1})

    assert_semantically_equal(
        n.node(1),
        {'id': 1, 'x': 1, 'y': 2, 'b': 1, 'a': 1, 'lat': 49.766825803756994, 'lon': -7.55714803952495,'s2_id': 5205973754090365183})

    correct_change_log_df = pd.DataFrame(
        {'timestamp': {0: '2020-05-28 13:49:53', 1: '2020-05-28 13:49:53'}, 'change_event': {0: 'add', 1: 'modify'},
         'object_type': {0: 'node', 1: 'node'}, 'old_id': {0: None, 1: 1}, 'new_id': {0: 1, 1: 1},
         'old_attributes': {0: None, 1: "{'x': 1, 'y': 2, 'a': 1, 'id': 1}"},
         'new_attributes': {0: "{'x': 1, 'y': 2, 'a': 1, 'id': 1}", 1: "{'x': 1, 'y': 2, 'a': 1, 'b': 1, 'id': 1}"},
         'diff': {0: [('add', '', [('x', 1), ('y', 2), ('lon', -7.55714803952495), ('lat', 49.766825803756994), ('id', 1), ('a', 1), ('s2_id', 5205973754090365183)]), ('add', 'id', 1)],
                  1: [('add', '', [('b', 1)])]}})
    # no need to test new_attributes and old_attributes columns if testing diff - it depends on those
    cols_to_compare = ['change_event', 'object_type', 'old_id', 'new_id', 'diff']
    assert_series_equal(n.change_log.loc[1, cols_to_compare], correct_change_log_df.loc[1, cols_to_compare], check_names=False,
                       check_dtype=False)


def test_modify_node_overwrites_existing_attributes_in_the_graph_and_change_is_recorded_by_change_log():
    n = Network('epsg:27700')
    n.add_node(1, {'x': 1, 'y': 2, 'a': 1})
    n.apply_attributes_to_node(1, {'a': 4})

    assert_semantically_equal(
        n.node(1),
        {'id': 1, 'x': 1, 'y': 2, 'a': 4, 'lat': 49.766825803756994, 'lon': -7.55714803952495, 's2_id': 5205973754090365183}
    )

    correct_change_log_df = pd.DataFrame(
        {'timestamp': {0: '2020-05-28 13:49:53', 1: '2020-05-28 13:49:53'},
         'change_event': {0: 'add', 1: 'modify'},
         'object_type': {0: 'node', 1: 'node'},
         'old_id': {0: None, 1: 1},
         'new_id': {0: 1, 1: 1},
         'old_attributes': {0: None, 1: {'x': 1, 'y': 2, 'a': 1}},
         'new_attributes': {0: "{'x': 1, 'y': 2, 'a': 1}", 1: "{'x': 1, 'y': 2, 'a': 4}"},
         'diff': {0: [('add', '', [('x', 1), ('y', 2), ('lon', -7.55714803952495), ('lat', 49.766825803756994), ('id', 1.0), ('a', 1), ('s2_id', 5205973754090365183)]), ('add', 'id', 1)],
                  1: [('change', 'a', (1, 4))]}})
    # no need to test new_attributes and old_attributes columns if testing diff - it depends on those
    cols_to_compare = ['change_event', 'object_type', 'old_id', 'new_id', 'diff']
    assert_series_equal(n.change_log.loc[1, cols_to_compare], correct_change_log_df.loc[1, cols_to_compare], check_dtype=False)


def test_modify_nodes_adds_and_changes_attributes_in_the_graph_and_change_is_recorded_by_change_log():
    n = Network('epsg:27700')
    n.add_node(1, {'x': 1, 'y': 2, 'a': 1})
    n.add_node(2, {'x': 1, 'y': 2, 'b': 1})
    n.apply_attributes_to_nodes({1: {'a': 4}, 2: {'a': 1}})

    assert_semantically_equal(
        n.node(1),
        {'id': 1, 'x': 1, 'y': 2, 'a': 4, 'lat': 49.766825803756994, 'lon': -7.55714803952495, 's2_id': 5205973754090365183}
    )
    assert_semantically_equal(
        n.node(2),
        {'id': 2, 'x': 1, 'y': 2, 'b': 1, 'a': 1, 'lat': 49.766825803756994, 'lon': -7.55714803952495, 's2_id': 5205973754090365183}
    )

    correct_change_log_df = pd.DataFrame(
        {'timestamp': {0: '2020-06-01 15:07:51', 1: '2020-06-01 15:07:51', 2: '2020-06-01 15:07:51',
                       3: '2020-06-01 15:07:51'}, 'change_event': {0: 'add', 1: 'add', 2: 'modify', 3: 'modify'},
         'object_type': {0: 'node', 1: 'node', 2: 'node', 3: 'node'}, 'old_id': {0: None, 1: None, 2: 1, 3: 2},
         'new_id': {0: 1, 1: 2, 2: 1, 3: 2},
         'old_attributes': {0: None, 1: None, 2: "{'x': 1, 'y': 2, 'a': 1}", 3: "{'x': 1, 'y': 2, 'b': 1}"},
         'new_attributes': {0: "{'x': 1, 'y': 2, 'a': 1}", 1: "{'x': 1, 'y': 2, 'b': 1}",
                            2: "{'x': 1, 'y': 2, 'a': 4}", 3: "{'x': 1, 'y': 2, 'b': 1, 'a': 1}"},
         'diff': {0: [('add', '', [('x', 1), ('y', 2), ('lon', -7.55714803952495), ('lat', 49.766825803756994), ('id', 1.0), ('a', 1), ('s2_id', 5205973754090365183)]), ('add', 'id', 1)],
                  1: [('add', '', [('x', 1), ('y', 2), ('lon', -7.55714803952495), ('lat', 49.766825803756994), ('id', 1.0), ('b', 1), ('s2_id', 5205973754090365183)]), ('add', 'id', 2)],
                  2: [('change', 'a', (1, 4))],
                  3: [('add', '', [('a', 1)])]}
         })
    # no need to test new_attributes and old_attributes columns if testing diff - it depends on those
    cols_to_compare = ['change_event', 'object_type', 'old_id', 'new_id', 'diff']
    assert_frame_equal(n.change_log.loc[[2,3], cols_to_compare], correct_change_log_df.loc[[2,3], cols_to_compare], check_dtype=False)


def multiply_node_attribs(node_attribs):
    return node_attribs['a'] * node_attribs['c']


def test_apply_function_to_nodes():
    n = Network('epsg:27700')
    n.add_node('0', attribs={'x': 1, 'y': 2, 'a': 2, 'c': 3})
    n.add_node('1', attribs={'x': 1, 'y': 2, 'c': 100})
    n.apply_function_to_nodes(function=multiply_node_attribs, location='new_computed_attrib')
    assert 'new_computed_attrib' in n.node('0')
    assert n.node('0')['new_computed_attrib'] == 6
    assert 'new_computed_attrib' not in n.node('1')


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
    assert_frame_equal(n.change_log[cols_to_compare].tail(2), correct_change_log_df[cols_to_compare],
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
    assert_frame_equal(n.change_log[cols_to_compare].tail(1), correct_change_log_df[cols_to_compare],
                       check_dtype=False)


def test_apply_attributes_to_multiple_edges():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'a': 1})
    n.add_link('1', 1, 2, attribs={'b': 1})
    n.add_link('2', 2, 3, attribs={'c': 1})
    n.add_link('3', 2, 3, attribs={'d': 1})
    n.apply_attributes_to_edges({(1, 2): {'e': 1}, (2, 3): {'f': 1}})

    assert n.link('0') == {'a': 1, 'from': 1, 'to': 2, 'id': '0', 'e': 1}
    assert n.link('1') == {'b': 1, 'from': 1, 'to': 2, 'id': '1', 'e': 1}
    assert n.link('2') == {'c': 1, 'from': 2, 'to': 3, 'id': '2', 'f': 1}
    assert n.link('3') == {'d': 1, 'from': 2, 'to': 3, 'id': '3', 'f': 1}


def test_apply_attributes_to_multiple_edges_with_conditions():
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
    assert_frame_equal(n.change_log[cols_to_compare], correct_change_log_df[cols_to_compare], check_dtype=False)


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
    assert_frame_equal(n.change_log[cols_to_compare], correct_change_log_df[cols_to_compare], check_dtype=False)


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
    assert_frame_equal(n.change_log[cols_to_compare].tail(2), correct_change_log_df[cols_to_compare],
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
    assert_frame_equal(n.change_log[cols_to_compare].tail(1), correct_change_log[cols_to_compare],
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
    assert_frame_equal(n.change_log[cols_to_compare].tail(2), correct_change_log[cols_to_compare],
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
    assert_frame_equal(n.change_log[cols_to_compare].tail(1), correct_change_log[cols_to_compare],
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
    assert_frame_equal(n.change_log[cols_to_compare].tail(2), correct_change_log[cols_to_compare],
                       check_dtype=False)


@pytest.fixture()
def islands_network_in_line():
    n = Network('epsg:4326')
    n.add_nodes({
        '1': {'x': 0, 'y': 0}, '2': {'x': 0, 'y': 0.5}, '3': {'x': 0, 'y': 1},
        '4': {'x': 0, 'y': 2}, '5': {'x': 0, 'y': 2.5}, '6': {'x': 0, 'y': 3},
        '7': {'x': 0, 'y': 4}, '8': {'x': 0, 'y': 4.5}, '9': {'x': 0, 'y': 5}
    })
    n.add_links({
        '1_2': {'from': '1', 'to': '2', 'freespeed': 10, 'capacity': 5, 'modes': {'car'}},
        '2_3': {'from': '2', 'to': '3', 'freespeed': 10, 'capacity': 5, 'modes': {'car'}},
        '3_1': {'from': '3', 'to': '1', 'freespeed': 10, 'capacity': 5, 'modes': {'car'}},
        '4_5': {'from': '4', 'to': '5', 'freespeed': 10, 'capacity': 5, 'modes': {'car'}},
        '5_6': {'from': '5', 'to': '6', 'freespeed': 10, 'capacity': 5, 'modes': {'car'}},
        '6_4': {'from': '6', 'to': '4', 'freespeed': 10, 'capacity': 5, 'modes': {'car'}},
        '7_8': {'from': '7', 'to': '8', 'freespeed': 10, 'capacity': 5, 'modes': {'car'}},
        '8_9': {'from': '8', 'to': '9', 'freespeed': 10, 'capacity': 5, 'modes': {'car'}},
        '9_7': {'from': '9', 'to': '7', 'freespeed': 10, 'capacity': 5, 'modes': {'car'}},
    })
    return n


@pytest.fixture()
def islands_network_in_circle():
    pass


def test_connecting_components_mode_free_results_in_four_links_added(islands_network_in_line):
    # because there are 3 components (2 x 2 directions links)
    added_links = islands_network_in_line.connect_components()
    assert len(added_links) == 4
    assert islands_network_in_line.is_strongly_connected()


def test_connecting_components_specifying_mode_results_in_four_links_added(islands_network_in_line):
    # because there are 3 components (2 x 2 directions links)
    added_links = islands_network_in_line.connect_components(modes=['car'])
    assert len(added_links) == 4
    assert islands_network_in_line.is_strongly_connected(modes='car')


def test_connecting_components_of_connected_graph_raises_warning_without_changes(network1, caplog):
    # add link to connect it up >_> ....
    network1.add_link('1', '101986', '101982',
                      attribs={'id': '1',
                               'from': '101986',
                               'to': '101982',
                               'freespeed': 4.166666666666667,
                               'capacity': 600.0,
                               'permlanes': 1.0,
                               'oneway': '1',
                               'modes': ['car'],
                               's2_from': 5221390329378179879,
                               's2_to': 5221390328605860387,
                               'length': 52.765151087870265})
    added_links = network1.connect_components()
    assert added_links is None
    assert caplog.records[0].levelname == 'WARNING'
    assert 'has only one strongly connected component' in caplog.records[0].message


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
    n.schedule._graph.graph['routes']['1'] = {
        'route_short_name': '', 'mode': 'bus',
        'trips': {},
        'arrival_offsets': [], 'departure_offsets': [],
        'route_long_name': '', 'id': '1', 'route': [],
        'await_departure': [], 'ordered_stops': []}
    n.schedule._graph.graph['service_to_route_map']['10314'].append('1')
    n.schedule._graph.graph['route_to_service_map']['1'] = '10314'

    assert set(n.schedule.service_ids()) == {'10314'}
    correct_routes = [['25508485', '21667818']]
    routes = n.schedule_routes_nodes()
    assert correct_routes == routes


def test_schedule_routes_with_disconnected_routes(network_object_from_test_data):
    n = network_object_from_test_data
    n.add_link('2', 2345678, 987875)
    n.schedule.apply_attributes_to_routes({'VJbd8660f05fe6f744e58a66ae12bd66acbca88b98': {'route': ['1', '2']}})
    correct_routes = [['25508485', '21667818'], [2345678, 987875]]
    routes = n.schedule_routes_nodes()
    assert correct_routes == routes


def test_reads_osm_network_into_the_right_schema(full_fat_default_config_path):
    osm_test_file = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "test_data", "osm", "osm.xml"))
    network = read.read_osm(osm_test_file, full_fat_default_config_path, 1, 'epsg:27700')
    assert_semantically_equal(dict(network.nodes()), {
        '0': {'id': '0', 'x': 622502.8306679451, 'y': -5526117.781903352, 'lat': 0.008554364250688652,
              'lon': -0.0006545205888310243, 's2_id': 1152921492875543713},
        '1': {'id': '1', 'x': 622502.8132744529, 'y': -5524378.838447345, 'lat': 0.024278505899735615,
              'lon': -0.0006545205888310243, 's2_id': 1152921335974974453},
        '2': {'id': '2', 'x': 622502.8314014417, 'y': -5527856.725358106, 'lat': -0.00716977739835831,
              'lon': -0.0006545205888310243, 's2_id': 384307157539499829}})
    assert len(list(network.links())) == 11

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
         'attributes': {'osm:way:osmid': 0,
                        'osm:way:highway': 'unclassified'}},
        {'permlanes': 1.0, 'freespeed': 12.5, 'capacity': 600.0, 'oneway': '1', 'modes': ['walk', 'car', 'bike'],
         'from': '1', 'to': '0', 's2_from': 1152921335974974453, 's2_to': 1152921492875543713,
         'length': 1748.4487354464366,
         'attributes': {'osm:way:osmid': 0,
                        'osm:way:highway': 'unclassified'}},
        {'permlanes': 1.0, 'freespeed': 12.5, 'capacity': 600.0, 'oneway': '1', 'modes': ['walk', 'car', 'bike'],
         'from': '0', 'to': '2', 's2_from': 1152921492875543713, 's2_to': 384307157539499829,
         'length': 1748.4488584600201,
         'attributes': {'osm:way:osmid': 100,
                        'osm:way:highway': 'unclassified'}},
        {'permlanes': 1.0, 'freespeed': 12.5, 'capacity': 600.0, 'oneway': '1', 'modes': ['walk', 'car', 'bike'],
         'from': '2', 'to': '0', 's2_from': 384307157539499829, 's2_to': 1152921492875543713,
         'length': 1748.4488584600201,
         'attributes': {'osm:way:osmid': 100,
                        'osm:way:highway': 'unclassified'}},
        {'permlanes': 1.0, 'freespeed': 12.5, 'capacity': 600.0, 'oneway': '1', 'modes': ['walk', 'car', 'bike'],
         'from': '1', 'to': '0', 's2_from': 1152921335974974453, 's2_to': 1152921492875543713,
         'length': 1748.4487354464366,
         'attributes': {'osm:way:osmid': 400,
                        'osm:way:highway': 'unclassified'}},
        {'permlanes': 1.0, 'freespeed': 12.5, 'capacity': 600.0, 'oneway': '1', 'modes': ['walk', 'car', 'bike'],
         'from': '0', 'to': '1', 's2_from': 1152921492875543713, 's2_to': 1152921335974974453,
         'length': 1748.4487354464366,
         'attributes': {'osm:way:osmid': 400,
                        'osm:way:highway': 'unclassified'}},
        {'permlanes': 1.0, 'freespeed': 12.5, 'capacity': 600.0, 'oneway': '1', 'modes': ['walk', 'car', 'bike'],
         'from': '2', 'to': '0', 's2_from': 384307157539499829, 's2_to': 1152921492875543713,
         'length': 1748.4488584600201,
         'attributes': {'osm:way:osmid': 700,
                        'osm:way:highway': 'unclassified'}},
        {'permlanes': 1.0, 'freespeed': 12.5, 'capacity': 600.0, 'oneway': '1', 'modes': ['walk', 'car', 'bike'],
         'from': '0', 'to': '2', 's2_from': 1152921492875543713, 's2_to': 384307157539499829,
         'length': 1748.4488584600201,
         'attributes': {'osm:way:osmid': 700,
                        'osm:way:highway': 'unclassified'}},
        {'permlanes': 3.0, 'freespeed': 12.5, 'capacity': 1800.0, 'oneway': '1', 'modes': ['walk', 'car', 'bike'],
         'from': '2', 'to': '1', 's2_from': 384307157539499829, 's2_to': 1152921335974974453,
         'length': 3496.897593906457,
         'attributes': {'osm:way:lanes': '3',
                        'osm:way:osmid': 47007861,
                        'osm:way:highway': 'tertiary'}},
        {'permlanes': 3.0, 'freespeed': 12.5, 'capacity': 1800.0, 'oneway': '1', 'modes': ['walk', 'car', 'bike'],
         'from': '1', 'to': '0', 's2_from': 1152921335974974453, 's2_to': 1152921492875543713,
         'length': 1748.4487354464366,
         'attributes': {'osm:way:lanes': '3',
                        'osm:way:osmid': 47007861,
                        'osm:way:highway': 'tertiary'}},
        {'permlanes': 1.0, 'freespeed': 12.5, 'capacity': 600.0, 'oneway': '1',
         'modes': ['car', 'walk', 'bike'], 'from': '1', 'to': '0',
         's2_from': 1152921335974974453, 's2_to': 1152921492875543713,
         'length': 1748.4487354464366, 'attributes': {
            'osm:way:osmid': 47007862,
            'osm:way:lanes': '3;2',
            'osm:way:highway': 'tertiary'}}
    ]

    cols = ['permlanes', 'freespeed', 'capacity', 'oneway', 'modes', 'from', 'to', 's2_from', 's2_to', 'length',
            'attributes']

    assert len(network.link_id_mapping) == 11
    for link in network.link_id_mapping.keys():
        satisfied = False
        attribs_to_test = network.link(link).copy()
        del attribs_to_test['id']
        for link_attrib in correct_link_attribs:
            try:
                assert_semantically_equal(attribs_to_test, link_attrib)
                satisfied = True
                break
            except AssertionError:
                pass
        assert satisfied


def test_read_matsim_network_with_duplicated_node_ids_records_removal_in_changelog(mocker):
    dup_nodes = {'21667818': [
        {'id': '21667818', 'x': 528504.1342843144, 'y': 182155.7435136598, 'lon': -0.14910908709500162,
         'lat': 51.52370573323939, 's2_id': 5221390302696205321}]}
    mocker.patch.object(matsim_reader, 'read_network', return_value=(nx.MultiDiGraph(), 2, dup_nodes, {}, {}))
    network = read.read_matsim(path_to_network=pt2matsim_network_test_file, epsg='epsg:27700')

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
    assert_frame_equal(network.change_log[cols_to_compare].tail(1), correct_change_log_df[cols_to_compare],
                       check_names=False,
                       check_dtype=False)


def test_read_matsim_network_with_duplicated_link_ids_records_reindexing_in_changelog(mocker):
    dup_links = {'1': ['1_1']}
    correct_link_id_map = {'1': {'from': '25508485', 'to': '21667818', 'multi_edge_idx': 0},
                           '1_1': {'from': '25508485', 'to': '21667818', 'multi_edge_idx': 1}}
    mocker.patch.object(matsim_reader, 'read_network',
                        return_value=(nx.MultiDiGraph(), correct_link_id_map, {}, dup_links, {}))
    mocker.patch.object(Network, 'link', return_value={'heyooo': '1'})
    network = read.read_matsim(path_to_network=pt2matsim_network_test_file, epsg='epsg:27700')

    correct_change_log_df = pd.DataFrame(
        {'timestamp': {0: '2020-07-02 11:59:00'}, 'change_event': {0: 'modify'}, 'object_type': {0: 'link'},
         'old_id': {0: '1'}, 'new_id': {0: '1_1'}, 'old_attributes': {0: "{'heyooo': '1'}"},
         'new_attributes': {0: "{'heyooo': '1'}"}, 'diff': {0: [('change', 'id', ('1', '1_1'))]}}
    )
    cols_to_compare = ['change_event', 'object_type', 'old_id', 'new_id', 'old_attributes', 'new_attributes', 'diff']
    assert_frame_equal(network.change_log[cols_to_compare].tail(1), correct_change_log_df[cols_to_compare],
                       check_names=False,
                       check_dtype=False)


def test_generating_pt_network_route_geodataframe():
    n = Network('epsg:4326')
    n.add_nodes({
        'n1': {'id': 'n1', 'x': '1', 'y': '1', 'lon': 1, 'lat': 1},
        'n2': {'id': 'n2', 'x': '2', 'y': '2', 'lon': 2, 'lat': 2}
    })
    n.add_links({'l1': {'from': 'n1', 'to': 'n2'}, 'l2': {'from': 'n2', 'to': 'n1'}})
    n.schedule = Schedule(
        n.epsg,
        [Service(id='service',
                 routes=[Route(route_short_name='route', mode='bus',
                               stops=[Stop(id='0', x=1, y=1, epsg='epsg:4326'),
                                      Stop(id='1', x=2, y=2, epsg='epsg:4326')],
                               trips={'trip_id': ['trip-04:40:00'],
                                      'trip_departure_time': ['04:40:00'],
                                      'vehicle_id': ['veh_1_bus']},
                               route=['l1', 'l2'],
                               arrival_offsets=['00:00:00', '00:02:00', '00:04:00'],
                               departure_offsets=['00:00:00', '00:02:00', '00:04:00'])])])

    gdf = n.schedule_network_routes_geodataframe()
    correct_gdf = gpd.GeoDataFrame(
        {'service_id': {0: 'service'}, 'route_id': {0: 'service_0'}, 'mode': {0: 'bus'},
         'route_short_name': {0: 'route'}, 'geometry': {0: LineString([(1, 1), (2, 2), (1, 1)])}},
    ).set_crs(n.epsg)
    correct_gdf.columns.name = 0

    assert_geodataframe_equal(
        gdf.reindex(sorted(gdf.columns), axis=1),
        correct_gdf.reindex(sorted(correct_gdf.columns), axis=1)
    )


def test_has_node_when_node_is_in_the_graph():
    n = Network('epsg:27700')
    n.add_node('1', {'x': 1, 'y': 2})
    assert n.has_node('1')


def test_has_node_when_node_is_not_in_the_graph():
    n = Network('epsg:27700')
    assert not n.has_node('1')


def test_has_nodes_when_nodes_in_the_graph():
    n = Network('epsg:27700')
    n.add_node('1', {'x': 1, 'y': 2})
    n.add_node('2', {'x': 1, 'y': 2})
    n.add_node('3', {'x': 1, 'y': 2})
    assert n.has_nodes(['1', '2'])


def test_has_nodes_when_only_some_nodes_in_the_graph():
    n = Network('epsg:27700')
    n.add_node('1', {'x': 1, 'y': 2})
    n.add_node('2', {'x': 1, 'y': 2})
    n.add_node('3', {'x': 1, 'y': 2})
    assert not n.has_nodes(['1', '4'])


def test_has_nodes_when_none_of_the_nodes_in_the_graph():
    n = Network('epsg:27700')
    n.add_node('1', {'x': 1, 'y': 2})
    n.add_node('2', {'x': 1, 'y': 2})
    n.add_node('3', {'x': 1, 'y': 2})
    assert not n.has_nodes(['10', '20'])


@pytest.fixture()
def network_with_isolated_nodes():
    n = Network('epsg:27700')
    n.add_node('1', attribs={'x': 1, 'y': 2})
    n.add_node('2', attribs={'x': 1, 'y': 2})
    n.add_node('3', attribs={'x': 1, 'y': 2})
    n.add_link('link', u='2', v='3')
    return {'network': n, 'isolated_nodes': ['1']}


@pytest.fixture()
def network_without_isolated_nodes():
    n = Network('epsg:27700')
    n.add_node('0', attribs={'x': 1, 'y': 2})
    n.add_node('1', attribs={'x': 1, 'y': 2})
    n.add_link('link', u='0', v='1')
    return {'network': n, 'isolated_nodes': []}


@pytest.fixture()
def network_cases_for_testing_isolated_nodes(network_with_isolated_nodes, network_without_isolated_nodes):
    return {
        'with_isolated_nodes': network_with_isolated_nodes,
        'without_isolated_nodes': network_without_isolated_nodes
    }


def test_network_has_isolated_nodes(network_with_isolated_nodes):
    assert network_with_isolated_nodes['network'].has_isolated_nodes()


def test_network_does_not_have_isolated_nodes(network_without_isolated_nodes):
    assert not network_without_isolated_nodes['network'].has_isolated_nodes()


@pytest.mark.parametrize("network_case", ['with_isolated_nodes', 'without_isolated_nodes'])
def test_networks_report_correct_isolated_nodes(network_case, network_cases_for_testing_isolated_nodes):
    assert network_cases_for_testing_isolated_nodes[network_case]['network'].isolated_nodes() == \
           network_cases_for_testing_isolated_nodes[network_case]['isolated_nodes']


def test_removes_isolated_nodes(network_with_isolated_nodes):
    n = network_with_isolated_nodes['network']
    n.remove_isolated_nodes()
    assert not list(nx.isolates(n.graph))


def test_logs_number_of_isolated_nodes_when_removing(network_with_isolated_nodes, caplog):
    caplog.set_level(logging.INFO)
    n = network_with_isolated_nodes['network']
    n.remove_isolated_nodes()

    assert caplog.records[0].levelname == 'INFO'
    assert '1 isolated node' in caplog.records[0].message


def test_isolated_nodes_are_recorded_in_changelog_after_removal(network_with_isolated_nodes):
    n = network_with_isolated_nodes['network']
    n.remove_isolated_nodes()

    assert len(n.change_log[n.change_log['change_event'] == 'remove']) == 1
    assert n.change_log.iloc[-1]['change_event'] == 'remove'
    assert n.change_log.iloc[-1]['old_id'] == '1'


def test_warns_of_no_isolated_nodes_when_trying_to_remove(network_without_isolated_nodes, caplog):
    caplog.set_level(logging.WARNING)
    n = network_without_isolated_nodes['network']
    n.remove_isolated_nodes()

    assert caplog.records[0].levelname == 'WARNING'
    assert 'no isolated nodes' in caplog.records[0].message


def test_isolated_nodes_show_up_in_validation_report(network_with_isolated_nodes):
    n = network_with_isolated_nodes['network']
    report = n.generate_validation_report()

    assert_semantically_equal(
        report['graph']['isolated_nodes'],
        {'number_of_nodes': 1, 'nodes': ['1']}
    )


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
    n.add_node(1, attribs={'x': 1, 'y': 2, 's2_id': 12345})
    n.add_node(3, attribs={'x': 1, 'y': 2, 's2_id': 345435})
    n.add_node(4, attribs={'x': 1, 'y': 2, 's2_id': 568767})
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
    n.add_node('1', {'x': 1, 'y': 2})
    assert n.generate_index_for_node() == '2'


def test_generate_index_for_node_gives_string_based_on_length_node_ids_when_you_have_mixed_index():
    n = Network('epsg:27700')
    n.add_node('1', {'x': 1, 'y': 2})
    n.add_node('1x', {'x': 1, 'y': 2})
    assert n.generate_index_for_node() == '3'


def test_generate_index_for_node_gives_string_based_on_length_node_ids_when_you_have_all_non_int_index():
    n = Network('epsg:27700')
    n.add_node('1w', {'x': 1, 'y': 2})
    n.add_node('1x', {'x': 1, 'y': 2})
    assert n.generate_index_for_node() == '3'


def test_generate_index_for_node_gives_uuid4_as_last_resort(mocker):
    mocker.patch.object(uuid, 'uuid4')
    n = Network('epsg:27700')
    n.add_node('1w', {'x': 1, 'y': 2})
    n.add_node('1x', {'x': 1, 'y': 2})
    n.add_node('4', {'x': 1, 'y': 2})
    n.generate_index_for_node()
    uuid.uuid4.assert_called_once()


def test_generating_n_indicies_for_nodes():
    n = Network('epsg:27700')
    nodes_dict = {}
    for i in range(10):
        nodes_dict[i] = {'x': 1, 'y': 2}
    n.add_nodes(nodes_dict)
    idxs = n.generate_indices_for_n_nodes(5)
    assert len(idxs) == 5
    assert not set(dict(n.nodes()).keys()) & idxs


def test_generate_index_for_edge_gives_next_integer_string_when_you_have_matsim_usual_integer_index():
    n = Network('epsg:27700')
    n.link_id_mapping = {'1': {}, '2': {}}
    new_idx = n.generate_index_for_edge()
    assert isinstance(new_idx, str)
    assert new_idx not in ['1', '2']


def test_generate_index_for_edge_gives_string_based_on_length_link_id_mapping_when_you_have_mixed_index():
    n = Network('epsg:27700')
    n.link_id_mapping = {'1': {}, 'x2': {}}
    new_idx = n.generate_index_for_edge()
    assert isinstance(new_idx, str)
    assert new_idx not in ['1', 'x2']


def test_generate_index_for_edge_gives_string_based_on_length_link_id_mapping_when_you_have_all_non_int_index():
    n = Network('epsg:27700')
    n.link_id_mapping = {'1x': {}, 'x2': {}}
    new_idx = n.generate_index_for_edge()
    assert isinstance(new_idx, str)
    assert new_idx not in ['1x', 'x2']


def test_index_graph_edges_generates_completely_new_index():
    n = Network('epsg:27700')
    n.add_link('1x', 1, 2)
    n.add_link('x2', 1, 2)
    n.index_graph_edges()
    assert list(n.link_id_mapping.keys()) == ['0', '1']


def test_generating_n_indicies_for_edges():
    n = Network('epsg:27700')
    n.add_links({str(i): {'from': 0, 'to': 1} for i in range(11)})
    idxs = n.generate_indices_for_n_edges(7)
    assert len(idxs) == 7
    for i in idxs:
        assert isinstance(i, str)
    assert not set(n.link_id_mapping.keys()) & idxs


def test_has_schedule_with_valid_network_routes_with_valid_routes(route):
    n = Network('epsg:27700')
    n.add_link('1', 1, 2, attribs={"modes": ['bus']})
    n.add_link('2', 2, 3, attribs={"modes": ['car', 'bus']})
    route.route = ['1', '2']
    n.schedule = Schedule(n.epsg, [Service(id='service', routes=[route])])
    route.reindex('service_1')
    n.schedule.add_route('service', route)
    n.schedule.apply_attributes_to_routes({'service_0': {'route': ['1', '2']}, 'service_1': {'route': ['1', '2']}})
    assert n.has_schedule_with_valid_network_routes()


def test_has_schedule_with_valid_network_routes_with_some_valid_routes(route):
    n = Network('epsg:27700')
    n.add_link('1', 1, 2)
    n.add_link('2', 2, 3)
    route.route = ['1', '2']
    route_2 = Route(route_short_name='', mode='bus', stops=[],
                    trips={'trip_id': ['1'], 'trip_departure_time': ['13:00:00'], 'vehicle_id': ['veh_1_bus']},
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
    route.reindex('route')
    n.schedule = Schedule(n.epsg, [Service(id='service', routes=[route])])
    n.schedule.apply_attributes_to_routes({'route': {'route': ['1', '2']}})
    assert n.invalid_network_routes() == []


def test_invalid_network_routes_with_invalid_route(route):
    n = Network('epsg:27700')
    n.add_link('1', 1, 2)
    n.add_link('2', 2, 3)
    route.reindex('route')
    n.schedule = Schedule(n.epsg, [Service(id='service', routes=[route])])
    n.schedule.apply_attributes_to_routes({'route': {'route': ['3', '4']}})
    assert n.invalid_network_routes() == ['route']


def test_invalid_network_routes_with_empty_route(route):
    n = Network('epsg:27700')
    n.add_link('1', 1, 2)
    n.add_link('2', 2, 3)
    route.reindex('route')
    n.schedule = Schedule(n.epsg, [Service(id='service', routes=[route])])
    n.schedule.apply_attributes_to_routes({'route': {'route': []}})
    assert n.invalid_network_routes() == ['route']


@pytest.fixture()
def invalid_pt2matsim_network_for_validation(network_object_from_test_data):
    return {
        'network': network_object_from_test_data,
        'subgraph_no_per_mode': {
            'car': 2,
            'walk': 2,
            'bike': 0
        },
        'is_valid_schedule': False,
        'invalid_service_id': '10314',
        'valid_PT_network_routes': False,
        'pt_routes_with_invalid_network_route': ['VJbd8660f05fe6f744e58a66ae12bd66acbca88b98'],
    }


def test_connectivity_in_report_with_invalid_network(invalid_pt2matsim_network_for_validation):
    report = invalid_pt2matsim_network_for_validation['network'].generate_validation_report()
    for mode, expected_connected_subgraphs in invalid_pt2matsim_network_for_validation['subgraph_no_per_mode'].items():
        assert report['graph']['graph_connectivity'][mode]['number_of_connected_subgraphs'] == expected_connected_subgraphs


def test_schedule_validity_in_report_with_invalid_network(invalid_pt2matsim_network_for_validation):
    report = invalid_pt2matsim_network_for_validation['network'].generate_validation_report()
    assert report['schedule']['schedule_level']['is_valid_schedule'] == invalid_pt2matsim_network_for_validation['is_valid_schedule']


def test_invalid_service_identified_in_report_with_invalid_network(invalid_pt2matsim_network_for_validation):
    report = invalid_pt2matsim_network_for_validation['network'].generate_validation_report()
    invalid_service_id = invalid_pt2matsim_network_for_validation['invalid_service_id']
    assert not report['schedule']['service_level'][invalid_service_id]['is_valid_service']


def test_network_routing_in_report_with_invalid_network(invalid_pt2matsim_network_for_validation):
    report = invalid_pt2matsim_network_for_validation['network'].generate_validation_report()
    assert report['routing']['services_have_routes_in_the_graph'] == invalid_pt2matsim_network_for_validation['valid_PT_network_routes']


def test_invalid_network_routes_show_in_report_with_invalid_network(invalid_pt2matsim_network_for_validation):
    report = invalid_pt2matsim_network_for_validation['network'].generate_validation_report()
    route_ids_with_invalid_network_route = invalid_pt2matsim_network_for_validation['pt_routes_with_invalid_network_route']
    assert report['routing']['service_routes_with_invalid_network_route'] == route_ids_with_invalid_network_route


@pytest.fixture()
def valid_network_for_validation(correct_schedule):
    n = Network('epsg:27700')
    n.add_link('1', 1, 2, attribs={'length': 2, "modes": ['car', 'bus']})
    n.add_link('2', 2, 1, attribs={'length': 2, "modes": ['car', 'bus']})
    n.schedule = correct_schedule

    return {
        'network': n,
        'subgraph_no_per_mode': {
            'car': 1,
            'walk': 0,
            'bike': 0
        },
        'is_valid_schedule': True,
        'has_valid_PT_network_routes': True
    }


def test_connectivity_in_report_with_valid_network(valid_network_for_validation):
    report = valid_network_for_validation['network'].generate_validation_report()
    for mode, expected_connected_subgraphs in valid_network_for_validation['subgraph_no_per_mode'].items():
        assert report['graph']['graph_connectivity'][mode]['number_of_connected_subgraphs'] == expected_connected_subgraphs


def test_schedule_validity_in_report_with_valid_network(valid_network_for_validation):
    report = valid_network_for_validation['network'].generate_validation_report()
    assert report['schedule']['schedule_level']['is_valid_schedule'] == valid_network_for_validation['is_valid_schedule']


def test_network_routing_in_report_with_valid_network(valid_network_for_validation):
    report = valid_network_for_validation['network'].generate_validation_report()
    assert report['routing']['services_have_routes_in_the_graph'] == valid_network_for_validation['has_valid_PT_network_routes']


def test_long_links_show_up_in_validation_report():
    n = Network('epsg:27700')
    n.add_link('1', 1, 2, attribs={'length': 10000, 'capacity': 1, 'freespeed': 1, "modes": ['car', 'bus']})
    n.add_link('2', 2, 3, attribs={'length': 2, 'capacity': 1, 'freespeed': 2, "modes": ['car', 'bus']})

    report = n.generate_validation_report()

    assert_semantically_equal(
        report['graph']['link_attributes']['links_over_1000_length'],
        {'number_of': 1, 'percentage': 0.5, 'link_ids': ['1']}
    )


offending_link_attribute_values_and_names = [('zero', '0'), ('negative', '-1'), ('infinite', 'inf'), ('fractional', '0.1'), ('none', 'None')]

@pytest.mark.parametrize("value,offending_value", offending_link_attribute_values_and_names)
def test_values_of_ids_are_not_flagged_in_validation_report(value, offending_value):
    n = Network('epsg:27700')
    n.add_link(offending_value, 1, 2, attribs={'length': 1, 'capacity': 1, 'freespeed': 1, "modes": ['car', 'bus']})
    n.add_link('2', 2, 3, attribs={'length': 2, 'capacity': 1, 'freespeed': 2, "modes": ['car', 'bus']})

    report = n.generate_validation_report()

    assert_semantically_equal(
        report['graph']['link_attributes'][f'{value}_attributes'],
        {}
    )


@pytest.mark.parametrize("value,offending_value", offending_link_attribute_values_and_names)
def test_values_of_from_node_are_not_flagged_in_validation_report(value, offending_value):
    n = Network('epsg:27700')
    n.add_link('1', offending_value, 2, attribs={'length': 1, 'capacity': 1, 'freespeed': 1, "modes": ['car', 'bus']})
    n.add_link('2', 2, 3, attribs={'length': 2, 'capacity': 1, 'freespeed': 2, "modes": ['car', 'bus']})

    report = n.generate_validation_report()

    assert_semantically_equal(
        report['graph']['link_attributes'][f'{value}_attributes'],
        {}
    )


@pytest.mark.parametrize("value,offending_value", offending_link_attribute_values_and_names)
def test_values_of_to_node_are_not_flagged_in_validation_report(value, offending_value):
    n = Network('epsg:27700')
    n.add_link('1', 1, offending_value, attribs={'length': 1, 'capacity': 1, 'freespeed': 1, "modes": ['car', 'bus']})
    n.add_link('2', 2, 3, attribs={'length': 2, 'capacity': 1, 'freespeed': 2, "modes": ['car', 'bus']})

    report = n.generate_validation_report()

    assert_semantically_equal(
        report['graph']['link_attributes'][f'{value}_attributes'],
        {}
    )


def test_zero_value_attributes_show_up_in_validation_report():
    n = Network('epsg:27700')
    n.add_link('1', 1, 2, attribs={'length': 0, 'capacity': 0.0, 'freespeed': '0.0', "modes": ['car', 'bus']})
    n.add_link('2', 2, 3, attribs={'length': 2, 'capacity': 1, 'freespeed': 2, "modes": ['car', 'bus']})

    report = n.generate_validation_report()

    assert_semantically_equal(
        report['graph']['link_attributes']['zero_attributes'],
        {
            'length': {'number_of': 1, 'percentage': 0.5, 'link_ids': ['1']},
            'capacity': {'number_of': 1, 'percentage': 0.5, 'link_ids': ['1']},
            'freespeed': {'number_of': 1, 'percentage': 0.5, 'link_ids': ['1']}
        }
    )


def test_negative_value_attributes_show_up_in_validation_report():
    n = Network('epsg:27700')
    n.add_link('1', 1, 2, attribs={'length': -1, 'capacity': 1, 'freespeed': '-5', "modes": ['car', 'bus']})
    n.add_link('2', 2, 3, attribs={'length': 2, 'capacity': 1, 'freespeed': 2, "modes": ['car', 'bus']})

    report = n.generate_validation_report()

    assert_semantically_equal(
        report['graph']['link_attributes']['negative_attributes'],
        {
            'length': {'number_of': 1, 'percentage': 0.5, 'link_ids': ['1']},
            'freespeed': {'number_of': 1, 'percentage': 0.5, 'link_ids': ['1']}
        }
    )


def test_infinite_value_attributes_show_up_in_validation_report():
    n = Network('epsg:27700')
    n.add_link('1', 1, 2, attribs={'length': float('inf'), 'capacity': 0.0, 'freespeed': 'inf', "modes": ['car', 'bus']})
    n.add_link('2', 2, 3, attribs={'length': 2, 'capacity': 1, 'freespeed': 2, "modes": ['car', 'bus']})

    report = n.generate_validation_report()

    assert_semantically_equal(
        report['graph']['link_attributes']['infinite_attributes'],
        {
            'length': {'number_of': 1, 'percentage': 0.5, 'link_ids': ['1']},
            'freespeed': {'number_of': 1, 'percentage': 0.5, 'link_ids': ['1']}
        }
    )


def test_fractional_value_attributes_show_up_in_validation_report():
    n = Network('epsg:27700')
    n.add_link('1', 1, 2, attribs={'length': 0.1, 'capacity': '0.0', 'freespeed': '0.2', "modes": ['car', 'bus']})
    n.add_link('2', 2, 3, attribs={'length': 2, 'capacity': 1, 'freespeed': 2, "modes": ['car', 'bus']})

    report = n.generate_validation_report()

    assert_semantically_equal(
        report['graph']['link_attributes']['fractional_attributes'],
        {
            'length': {'number_of': 1, 'percentage': 0.5, 'link_ids': ['1']},
            'freespeed': {'number_of': 1, 'percentage': 0.5, 'link_ids': ['1']}
        }
    )


def test_none_value_attributes_show_up_in_validation_report():
    n = Network('epsg:27700')
    n.add_link('1', 1, 2, attribs={'length': 1, 'capacity': 'None', 'freespeed': None, "modes": ['car', 'bus']})
    n.add_link('2', 2, 3, attribs={'length': 2, 'capacity': 1, 'freespeed': 2, "modes": ['car', 'bus']})

    report = n.generate_validation_report()

    assert_semantically_equal(
        report['graph']['link_attributes']['none_attributes'],
        {
            'capacity': {'number_of': 1, 'percentage': 0.5, 'link_ids': ['1']},
            'freespeed': {'number_of': 1, 'percentage': 0.5, 'link_ids': ['1']}
        }
    )


def test_nested_values_show_up_in_validation_report():
    n = Network('epsg:27700')
    n.add_link('1', 1, 2,
               attribs={'length': 1, 'capacity': '0.0', 'freespeed': '2', "modes": ['car', 'bus'],
                        'attributes': {'osm:way:lanes': -1}
                        })

    report = n.generate_validation_report()

    assert_semantically_equal(
        report['graph']['link_attributes']['negative_attributes'],
        {
            'attributes::osm:way:lanes': {'number_of': 1, 'percentage': 1, 'link_ids': ['1']},
        }
    )


def test_check_connectivity_for_mode_warns_of_graphs_with_more_than_single_component(mocker, caplog):
    mocker.patch.object(network_validation, 'describe_graph_connectivity',
                        return_value={'problem_nodes': {'dead_ends': [], 'unreachable_node': ['1']},
                                      'number_of_connected_subgraphs': 2})

    Network('epsg:27700').check_connectivity_for_mode('car')

    assert caplog.records[0].levelname == 'WARNING'
    assert 'more than one connected component' in caplog.records[0].message


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
    expected_change_log_path = os.path.join(tmpdir, 'network_change_log.csv')
    expected_schedule_change_log_path = os.path.join(tmpdir, 'schedule_change_log.csv')
    assert not os.path.exists(expected_change_log_path)

    network_object_from_test_data.write_to_matsim(tmpdir)

    assert os.path.exists(expected_change_log_path)
    assert os.path.exists(expected_schedule_change_log_path)


benchmark_path_json = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "auxiliary_files", "links_benchmark.json"))
benchmark_path_csv = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "auxiliary_files", "links_benchmark.csv"))


@pytest.fixture()
def aux_network():
    n = Network('epsg:27700')
    n.add_nodes({'1': {'x': 1, 'y': 2, 's2_id': 0}, '2': {'x': 1, 'y': 2, 's2_id': 0},
                 '3': {'x': 1, 'y': 2, 's2_id': 0}, '4': {'x': 1, 'y': 2, 's2_id': 0}})
    n.add_links(
        {'1': {'from': '1', 'to': '2', 'freespeed': 1, 'capacity': 1, 'permlanes': 1, 'length': 1, 'modes': {'car'}},
         '2': {'from': '1', 'to': '3', 'freespeed': 1, 'capacity': 1, 'permlanes': 1, 'length': 1, 'modes': {'car'}},
         '3': {'from': '2', 'to': '4', 'freespeed': 1, 'capacity': 1, 'permlanes': 1, 'length': 1, 'modes': {'car'}},
         '4': {'from': '3', 'to': '4', 'freespeed': 1, 'capacity': 1, 'permlanes': 1, 'length': 1, 'modes': {'car'}}})
    n.read_auxiliary_link_file(benchmark_path_json)
    n.read_auxiliary_node_file(benchmark_path_csv)
    return n


def test_reindexing_network_node_with_auxiliary_files(aux_network):
    aux_network.reindex_node('3', '0')
    assert aux_network.auxiliary_files['node']['links_benchmark.csv'].map == {'2': '2', '3': '0', '4': '4', '1': '1'}
    assert aux_network.auxiliary_files['link']['links_benchmark.json'].map == {'2': '2', '1': '1', '3': '3', '4': '4'}


def test_reindexing_network_link_with_auxiliary_files(aux_network):
    aux_network.reindex_link('2', '0')
    assert aux_network.auxiliary_files['node']['links_benchmark.csv'].map == {'2': '2', '3': '3', '4': '4', '1': '1'}
    assert aux_network.auxiliary_files['link']['links_benchmark.json'].map == {'2': '0', '1': '1', '3': '3', '4': '4'}


def test_removing_network_node_with_auxiliary_files(aux_network):
    aux_network.remove_nodes(['1', '2'])
    aux_network.remove_node('3')
    assert aux_network.auxiliary_files['node']['links_benchmark.csv'].map == {'2': None, '3': None, '4': '4', '1': None}
    assert aux_network.auxiliary_files['link']['links_benchmark.json'].map == {'2': '2', '1': '1', '3': '3', '4': '4'}


def test_removing_network_link_with_auxiliary_files(aux_network):
    aux_network.remove_links(['1', '2'])
    aux_network.remove_link('3')
    assert aux_network.auxiliary_files['node']['links_benchmark.csv'].map == {'2': '2', '3': '3', '4': '4', '1': '1'}
    assert aux_network.auxiliary_files['link']['links_benchmark.json'].map == {'2': None, '1': None, '3': None,
                                                                               '4': '4'}


def test_simplifying_network_with_auxiliary_files(aux_network):
    aux_network.simplify()

    assert aux_network.auxiliary_files['node']['links_benchmark.csv'].map == {'1': '1', '2': None, '3': None, '4': '4'}
    assert aux_network.auxiliary_files['link']['links_benchmark.json'].map == {
        '2': aux_network.link_simplification_map['2'],
        '1': aux_network.link_simplification_map['1'],
        '3': aux_network.link_simplification_map['3'],
        '4': aux_network.link_simplification_map['4']}


def test_saving_network_with_auxiliary_files_with_changes(aux_network, tmpdir):
    aux_network.auxiliary_files['node']['links_benchmark.csv'].map = {'2': None, '3': None, '4': '04', '1': None}
    aux_network.auxiliary_files['link']['links_benchmark.json'].map = {'2': '002', '1': '001', '3': '003', '4': '004'}

    expected_json_aux_file = os.path.join(tmpdir, 'auxiliary_files', 'links_benchmark.json')
    expected_csv_aux_file = os.path.join(tmpdir, 'auxiliary_files', 'links_benchmark.csv')

    assert not os.path.exists(expected_json_aux_file)
    assert not os.path.exists(expected_csv_aux_file)

    aux_network.write_to_matsim(tmpdir)

    assert os.path.exists(expected_json_aux_file)
    assert os.path.exists(expected_csv_aux_file)

    with open(expected_json_aux_file) as json_file:
        assert json.load(json_file)['car']['2']['in']['links'] == ['002']

    assert pd.read_csv(expected_csv_aux_file)['links'].to_dict() == {0: '[None]', 1: '[None]', 2: '[None]', 3: "['04']"}


@pytest.fixture()
def network_1_geo_and_json(network1):
    nodes = gpd.GeoDataFrame({
        '101982': {'id': '101982', 'x': '528704.1425925883', 'y': '182068.78193707118', 'lon': -0.14625948709424305,
                   'lat': 51.52287873323954, 's2_id': 5221390329378179879,
                   'geometry': Point(528704.1425925883, 182068.78193707118)},
        '101986': {'id': '101986', 'x': '528835.203274008', 'y': '182006.27331298392', 'lon': -0.14439428709377497,
                   'lat': 51.52228713323965, 's2_id': 5221390328605860387,
                   'geometry': Point(528835.203274008, 182006.27331298392)}}).T
    nodes.index = nodes.index.set_names(['index'])
    links = gpd.GeoDataFrame({
        '0': {'id': '0', 'from': '101982', 'to': '101986', 'freespeed': 4.166666666666667, 'capacity': 600.0,
              'permlanes': 1.0, 'oneway': '1', 'modes': ['car', 'bike'], 's2_from': 5221390329378179879,
              's2_to': 5221390328605860387, 'length': 52.765151087870265,
              'geometry': LineString(
                  [(528704.1425925883, 182068.78193707118), (528835.203274008, 182006.27331298392)]),
              'u': '101982', 'v': '101986',
              'attributes': {
                  'osm:way:access': {'name': 'osm:way:access', 'class': 'java.lang.String',
                                     'text': 'permissive'},
                  'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String',
                                      'text': 'unclassified'},
                  'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long', 'text': '26997928'},
                  'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String',
                                   'text': 'Brunswick Place'}}}}).T
    links.index = links.index.set_names(['index'])

    # most networks are expected to have complex geometries
    network1.apply_attributes_to_links(
        {'0': {
            'modes': ['car', 'bike'],
            'geometry': LineString([(528704.1425925883, 182068.78193707118), (528835.203274008, 182006.27331298392)])}})

    return {
        'network': network1,
        'expected_json': {'nodes': {
            '101982': {'id': '101982', 'x': '528704.1425925883', 'y': '182068.78193707118', 'lon': -0.14625948709424305,
                       'lat': 51.52287873323954, 's2_id': 5221390329378179879,
                       'geometry': [528704.1425925883, 182068.78193707118]},
            '101986': {'id': '101986', 'x': '528835.203274008', 'y': '182006.27331298392', 'lon': -0.14439428709377497,
                       'lat': 51.52228713323965, 's2_id': 5221390328605860387,
                       'geometry': [528835.203274008, 182006.27331298392]}},
            'links': {
                '0': {'id': '0', 'from': '101982', 'to': '101986', 'freespeed': 4.166666666666667, 'capacity': 600.0,
                      'permlanes': 1.0, 'oneway': '1', 'modes': ['car', 'bike'], 's2_from': 5221390329378179879,
                      's2_to': 5221390328605860387, 'length': 52.765151087870265,
                      'geometry': 'ez~hinaBc~sze|`@gx|~W|uo|J', 'u': '101982', 'v': '101986',
                      'attributes': {
                          'osm:way:access': {'name': 'osm:way:access', 'class': 'java.lang.String',
                                             'text': 'permissive'},
                          'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String',
                                              'text': 'unclassified'},
                          'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long', 'text': '26997928'},
                          'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String',
                                           'text': 'Brunswick Place'}}}}},
        'expected_sanitised_json': {'nodes': {
            '101982': {'id': '101982', 'x': '528704.1425925883', 'y': '182068.78193707118', 'lon': -0.14625948709424305,
                       'lat': 51.52287873323954, 's2_id': 5221390329378179879,
                       'geometry': '528704.1425925883,182068.78193707118'},
            '101986': {'id': '101986', 'x': '528835.203274008', 'y': '182006.27331298392', 'lon': -0.14439428709377497,
                       'lat': 51.52228713323965, 's2_id': 5221390328605860387,
                       'geometry': '528835.203274008,182006.27331298392'}},
            'links': {
                '0': {'id': '0', 'from': '101982', 'to': '101986', 'freespeed': 4.166666666666667, 'capacity': 600.0,
                      'permlanes': 1.0, 'oneway': '1', 'modes': 'car,bike', 's2_from': 5221390329378179879,
                      's2_to': 5221390328605860387, 'length': 52.765151087870265,
                      'geometry': 'ez~hinaBc~sze|`@gx|~W|uo|J', 'u': '101982', 'v': '101986',
                      'attributes': {
                          'osm:way:access': {'name': 'osm:way:access', 'class': 'java.lang.String',
                                             'text': 'permissive'},
                          'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String',
                                              'text': 'unclassified'},
                          'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long', 'text': '26997928'},
                          'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String',
                                           'text': 'Brunswick Place'}}}}},
        'expected_geodataframe': {'nodes': nodes, 'links': links}
    }


def test_transforming_network_to_json(network_1_geo_and_json):
    assert_semantically_equal(network_1_geo_and_json['network'].to_json(), network_1_geo_and_json['expected_json'])


def test_transforming_uneven_network_to_json():
    # some nodes and links have different params, we expect only those with values in the json
    n = Network(epsg='epsg:4326')
    n.add_node('101982',
               {'id': '101982',
                'x': '528704.1425925883',
                'y': '182068.78193707118',
                'lon': -0.14625948709424305,
                'lat': 51.52287873323954,
                's2_id': 5221390329378179879,
                'name': 'hello'
                })
    n.add_node('101986',
               {'id': '101986',
                'x': '528835.203274008',
                'y': '182006.27331298392',
                'lon': -0.14439428709377497,
                'lat': 51.52228713323965,
                's2_id': 5221390328605860387})
    n.add_link('0', '101982', '101986',
               attribs={'id': '0',
                        'from': '101982',
                        'to': '101986',
                        'freespeed': 4})
    n.add_link('0', '101982', '101986',
               attribs={'id': '0',
                        'from': '101982',
                        'to': '101986',
                        'capacity': 5})

    assert_semantically_equal(
        n.to_json(),
        {'nodes': {
            '101982': {'id': '101982', 'x': '528704.1425925883', 'y': '182068.78193707118', 'lon': -0.14625948709424305,
                       'lat': 51.52287873323954, 's2_id': 5221390329378179879, 'name': 'hello',
                       'geometry': [528704.1425925883, 182068.78193707118]},
            '101986': {'id': '101986', 'x': '528835.203274008', 'y': '182006.27331298392', 'lon': -0.14439428709377497,
                       'lat': 51.52228713323965, 's2_id': 5221390328605860387,
                       'geometry': [528835.203274008, 182006.27331298392]}}, 'links': {
            '0': {'id': '0', 'from': '101982', 'to': '101986', 'freespeed': 4.0,
                  'geometry': 'ez~hinaBc~sze|`@gx|~W|uo|J', 'u': '101982', 'v': '101986'},
            '1': {'id': '1', 'from': '101982', 'to': '101986', 'capacity': 5.0,
                  'geometry': 'ez~hinaBc~sze|`@gx|~W|uo|J', 'u': '101982', 'v': '101986'}}}
    )


def test_saving_network_to_json(network_1_geo_and_json, tmpdir):
    network_1_geo_and_json['network'].write_to_json(tmpdir)
    expected_network_json = os.path.join(tmpdir, 'network.json')
    assert os.path.exists(expected_network_json)
    with open(expected_network_json) as json_file:
        output_json = json.load(json_file)
    assert_semantically_equal(
        output_json,
        network_1_geo_and_json['expected_sanitised_json'])


def test_transforming_network_to_geodataframe(network_1_geo_and_json):
    node_cols = ['id', 'x', 'y', 'lon', 'lat', 's2_id', 'geometry']
    link_cols = ['id', 'from', 'to', 'freespeed', 'capacity', 'permlanes', 'oneway', 'modes', 's2_from', 's2_to',
                 'length', 'geometry', 'attributes', 'u', 'v']
    _network = network_1_geo_and_json['network'].to_geodataframe()
    assert set(_network['nodes'].columns) == set(node_cols)
    assert_frame_equal(_network['nodes'][node_cols],
                       network_1_geo_and_json['expected_geodataframe']['nodes'][node_cols], check_dtype=False)
    assert set(_network['links'].columns) == set(link_cols)
    assert_frame_equal(_network['links'][link_cols],
                       network_1_geo_and_json['expected_geodataframe']['links'][link_cols], check_dtype=False)


def test_saving_network_to_geojson(network1, correct_schedule, tmpdir):
    network1.schedule = correct_schedule
    network1.write_to_geojson(tmpdir)
    assert set(os.listdir(tmpdir)) == {'network_nodes_geometry_only.geojson', 'network_nodes.geojson',
                                       'network_change_log.csv', 'schedule_links_geometry_only.geojson',
                                       'network_links.geojson', 'network_links_geometry_only.geojson',
                                       'schedule_nodes_geometry_only.geojson', 'schedule_links.geojson',
                                       'schedule_nodes.geojson', 'schedule_change_log.csv'}


def test_saving_network_to_csv(network1, correct_schedule, tmpdir):
    network1.schedule = correct_schedule
    network1.write_to_csv(tmpdir)
    assert set(os.listdir(tmpdir)) == {'network', 'schedule'}
    assert set(os.listdir(os.path.join(tmpdir, 'network'))) == {'nodes.csv', 'links.csv', 'network_change_log.csv'}
    assert set(os.listdir(os.path.join(tmpdir, 'schedule'))) == {'calendar.csv', 'stop_times.csv', 'trips.csv',
                                                                 'routes.csv', 'schedule_change_log.csv', 'stops.csv'}
    output_nodes = pd.read_csv(os.path.join(tmpdir, 'network', 'nodes.csv'))
    assert_semantically_equal(
        output_nodes.to_dict(),
        {'index': {0: 101982, 1: 101986}, 'lat': {0: 51.52287873323954, 1: 51.52228713323965},
         's2_id': {0: 5221390329378179879, 1: 5221390328605860387},
         'lon': {0: -0.14625948709424305, 1: -0.14439428709377494}, 'id': {0: 101982, 1: 101986},
         'x': {0: 528704.1425925883, 1: 528835.203274008},
         'geometry': {0: '[528704.1425925883, 182068.78193707118]',
                      1: '[528835.203274008, 182006.27331298392]'},
         'y': {0: 182068.7819370712, 1: 182006.27331298392}}
    )
    output_links = pd.read_csv(os.path.join(tmpdir, 'network', 'links.csv'))
    assert_semantically_equal(
        output_links.to_dict(),
        {'index': {0: 0}, 'modes': {0: "['car']"}, 'to': {0: 101986}, 's2_from': {0: 5221390329378179879},
         'length': {0: 52.76515108787025}, 'id': {0: 0}, 'from': {0: 101982}, 's2_to': {0: 5221390328605860387},
         'capacity': {0: 600.0},
         'u': {0: 101982},
         'v': {0: 101986},
         'geometry': {0: 'ez~hinaBc~sze|`@gx|~W|uo|J'},
         'oneway': {0: 1}, 'freespeed': {0: 4.166666666666667}, 'permlanes': {0: 1.0}, 'attributes': {
            0: "{'osm:way:access': {'name': 'osm:way:access', 'class': 'java.lang.String', 'text': 'permissive'}, 'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'unclassified'}, 'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long', 'text': '26997928'}, 'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String', 'text': 'Brunswick Place'}}"}}
    )


def test_reads_node_elevations_from_tif_file(network3):
    elevation_test_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_data", "elevation"))
    elevation_tif_file = os.path.join(elevation_test_folder, 'hk_elevation_example.tif')

    elev_dict = network3.get_node_elevation_dictionary(elevation_tif_file, null_value=-32768)

    # elevation value (25m) that corresponds to the coordinate of this node in the network has been double checked here:
    # https://www.freemaptools.com/elevation-finder.htm
    assert elev_dict['101982']['z'] == 25


def test_replaces_missing_node_elevations_with_zero(network3):
    elevation_test_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_data", "elevation"))
    elevation_tif_file = os.path.join(elevation_test_folder, 'hk_elevation_example.tif')

    elev_dict = network3.get_node_elevation_dictionary(elevation_tif_file, null_value=-32768)
    # the coordinate of this node in the network corresponds to a pixel with null (no data) value in the tif file
    assert elev_dict['101986']['z'] == 0


def test_getting_link_slope_dictionary(network3):
    # based on network4() fixture
    elevation_dictionary = {'101982': {'z': -51}, '101986': {'z': 100}}
    z_1 = elevation_dictionary['101982']['z']
    z_2 = elevation_dictionary['101986']['z']
    length = 52.765151087870265
    link_slope = (z_2 - z_1) / length
    slope_dict = network3.get_link_slope_dictionary(elevation_dictionary)
    assert slope_dict['0']['slope'] == link_slope


def test_splitting_link_at_point_gets_data_right(mocker):
    new_node_ID = 'new_node_ID'
    new_link_1_ID = 'new_link_1_ID'
    new_link_2_ID = 'new_link_2_ID'
    mocker.patch.object(Network, 'generate_index_for_node', return_value=new_node_ID)
    mocker.patch.object(Network, 'generate_indices_for_n_edges', return_value=(new_link_1_ID, new_link_2_ID))

    n = Network('epsg:27700')
    n.add_nodes({
        'n1': {'id': 'n1', 'x': 528568, 'y': 177243},
        'n2': {'id': 'n2', 'x': 528570, 'y': 177243}
    })
    n.add_links({'l1': {
        'from': 'n1', 'to': 'n2', 'id': 'l1', 'freespeed': 4, 'capacity': 600.0,
        'permlanes': 1.0, 'oneway': '1', 'modes': ['car'],
        'length': 10,
        'geometry': LineString([(528568, 177243), (528569, 177243), (528570, 177243)]),
        'attributes': {'osm:way:access': {'name': 'osm:way:access', 'class': 'java.lang.String', 'text': 'permissive'}}}
    })

    data = n.split_link_at_point('l1', 528568.5, 177243.5)

    assert {k: v for k, v in data['node_attributes'].items() if k in ['id', 'x', 'y']} == {'id': new_node_ID, 'x': 528568.5, 'y': 177243.0}
    assert list(data['links'][new_link_1_ID].pop('geometry').coords) == [(528568, 177243), (528568.5, 177243)]
    assert data['links'][new_link_1_ID] == {
                'from': 'n1', 'to': new_node_ID, 'id': new_link_1_ID, 'freespeed': 4, 'capacity': 600.0,
                'permlanes': 1.0, 'oneway': '1', 'modes': ['car'],
                'length': 2.5,  's2_from': n.node('n1')['s2_id'], 's2_to': data['node_attributes']['s2_id'],
                'attributes': {
                    'osm:way:access': {'name': 'osm:way:access', 'class': 'java.lang.String', 'text': 'permissive'}}
    }
    assert list(data['links'][new_link_2_ID].pop('geometry').coords) == [(528568.5, 177243), (528569, 177243), (528570, 177243)]
    assert data['links'][new_link_2_ID] == {
                'from': new_node_ID, 'to': 'n2', 'id': new_link_2_ID, 'freespeed': 4, 'capacity': 600.0,
                'permlanes': 1.0, 'oneway': '1', 'modes': ['car'],
                'length': 7.5,  's2_from': data['node_attributes']['s2_id'], 's2_to': n.node('n2')['s2_id'],
                'attributes': {
                    'osm:way:access': {'name': 'osm:way:access', 'class': 'java.lang.String', 'text': 'permissive'}}
    }


def test_splitting_link_at_point_deletes_old_link():
    n = Network('epsg:27700')
    n.add_nodes({
        'n1': {'id': 'n1', 'x': 528568, 'y': 177243},
        'n2': {'id': 'n2', 'x': 528570, 'y': 177243}
    })
    n.add_links({'l1': {'from': 'n1', 'to': 'n2', 'id': 'l1', 'length': 10}})
    assert n.has_link('l1')

    n.split_link_at_point('l1', 528568.5, 177243.5)

    assert not n.has_link('l1')


def test_splitting_link_without_geometry_at_point_creates_sensible_geometry_and_length(mocker):
    new_link_1_ID = 'new_link_1_ID'
    new_link_2_ID = 'new_link_2_ID'
    mocker.patch.object(Network, 'generate_indices_for_n_edges', return_value=(new_link_1_ID, new_link_2_ID))
    n = Network('epsg:27700')
    n.add_nodes({
        'n1': {'id': 'n1', 'x': 528568, 'y': 177243},
        'n2': {'id': 'n2', 'x': 528570, 'y': 177243}
    })
    n.add_links({'l1': {'from': 'n1', 'to': 'n2', 'id': 'l1', 'length': 10}})

    n.split_link_at_point('l1', 528568.5, 177243)

    assert list(n.link(new_link_1_ID)['geometry'].coords) == [(528568, 177243), (528568.5, 177243)]
    assert list(n.link(new_link_2_ID)['geometry'].coords) == [(528568.5, 177243), (528570, 177243)]
    assert n.link(new_link_1_ID)['length'] == 2.5
    assert n.link(new_link_2_ID)['length'] == 7.5


def test_splitting_link_with_suggested_node_id_uses_that_id():
    n = Network('epsg:27700')
    n.add_nodes({
        'n1': {'id': 'n1', 'x': 528568, 'y': 177243},
        'n2': {'id': 'n2', 'x': 528570, 'y': 177243}
    })
    n.add_links({'l1': {'from': 'n1', 'to': 'n2', 'id': 'l1', 'length': 10}})
    suggested_node_id = 'suggested_node_id'

    data = n.split_link_at_point('l1', 528568.5, 177243, suggested_node_id)

    assert data['node_attributes']['id'] == suggested_node_id


def test_splitting_link_with_existing_node_id_generates_new_index(mocker):
    mocker.patch.object(Network, 'generate_index_for_node')
    n = Network('epsg:27700')
    n.add_nodes({
        'n1': {'id': 'n1', 'x': 528568, 'y': 177243},
        'n2': {'id': 'n2', 'x': 528570, 'y': 177243}
    })
    n.add_links({'l1': {'from': 'n1', 'to': 'n2', 'id': 'l1', 'length': 10}})
    suggested_node_id = 'n1'

    data = n.split_link_at_point('l1', 528568.5, 177243, suggested_node_id)

    n.generate_index_for_node.assert_called_once()


def test_splitting_link_at_node_far_away_throws_error():
    n = Network('epsg:27700')
    n.add_nodes({
        'n1': {'id': 'n1', 'x': 528568, 'y': 177243},
        'n2': {'id': 'n2', 'x': 528570, 'y': 177243},
        'split_node': {'id': 'split_node', 'x': 628570, 'y': 277243},
    })
    n.add_links({'l1': {'from': 'n1', 'to': 'n2', 'id': 'l1', 'length': 10}})

    with pytest.raises(exceptions.MisalignedNodeError) as error_info:
        n.split_link_at_node('l1', 'split_node')
    assert "does not lie close enough to the geometry of the link" in str(error_info.value)


def test_splitting_link_updates_route_in_schedule(mocker):
    new_link_1_ID = 'new_link_1_ID'
    new_link_2_ID = 'new_link_2_ID'
    mocker.patch.object(Network, 'generate_indices_for_n_edges', return_value=(new_link_1_ID, new_link_2_ID))
    n = Network('epsg:27700')
    n.add_nodes({
        'n1': {'id': 'n1', 'x': 528568, 'y': 177243},
        'n2': {'id': 'n2', 'x': 528570, 'y': 177243},
    })
    n.add_links({'l1': {'from': 'n1', 'to': 'n2', 'id': 'l1', 'length': 10}})
    n.schedule = Schedule(
        epsg='epsg:27700',
        services=[Service(id='bus_service',
                          routes=[Route(id='1', route_short_name='', mode='bus',
                          stops=[
                              Stop(id='0', x=528568, y=177243, epsg='epsg:27700',
                                   linkRefId='A'),
                              Stop(id='1', x=528570, y=177243, epsg='epsg:27700',
                                   linkRefId='B')],
                          trips={'trip_id': ['trip_04:40:00'],
                                 'trip_departure_time': ['04:40:00'],
                                 'vehicle_id': ['veh_1_bus']},
                          arrival_offsets=['00:00:00', '00:02:00'],
                          departure_offsets=['00:00:00', '00:02:00'],
                          route=['AAA', 'l1', 'BBB'])]
        )]
    )
    n.split_link_at_point('l1', 528568.5, 177243)

    assert n.schedule.route('1').route == ['AAA', new_link_1_ID, new_link_2_ID, 'BBB']


def test_generating_summary_report(network_for_summary_stats):
    report = network_for_summary_stats.summary_report()
    correct_report = {'network':
                          {'network_graph_info':
                               {'Number of network links': 2, 'Number of network nodes': 3},
                           'modes': {'Modes on network links': {'bike', 'walk', 'rail', 'car'},
                                     'Number of links by mode': {'bike': 1, 'walk': 1, 'rail': 1, 'car': 1}},
                           'osm_highway_tags': {'Number of links by tag': {'secondary': 1}}},
                      'schedule':
                          {'schedule_info':
                               {'Number of services': 2, 'Number of routes': 3, 'Number of stops': 4},
                           'modes': {'Modes in schedule': {'rail', 'bus'},
                                     'Services by mode': {'rail': 1, 'bus': 1},
                                     'PT stops by mode': {'rail': 2, 'bus': 2}},
                           'accessibility_tags': {'Stops with tag bikeAccessible': 1,
                                                  'Unique values for bikeAccessible tag': {'true'},
                                                  'Stops with tag carAccessible': 1,
                                                  'Unique values for carAccessible tag': {'true'}}}}
    assert_semantically_equal(report, correct_report)
