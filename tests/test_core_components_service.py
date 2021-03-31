import pytest
import pickle
import os
from pandas import DataFrame, Timestamp
from pandas.testing import assert_frame_equal
from genet.schedule_elements import Service
from genet.utils import plot
from tests.fixtures import *
from tests.test_core_components_route import self_looping_route, route


@pytest.fixture()
def service():
    route_1 = Route(id='1', route_short_name='name',
                    mode='bus',
                    stops=[Stop(id='1', x=4, y=2, epsg='epsg:27700', linkRefId='1'),
                           Stop(id='2', x=1, y=2, epsg='epsg:27700', linkRefId='2'),
                           Stop(id='3', x=3, y=3, epsg='epsg:27700', linkRefId='3'),
                           Stop(id='4', x=7, y=5, epsg='epsg:27700', linkRefId='4')],
                    trips={'trip_id': ['1', '2'],
                           'trip_departure_time': ['13:00:00', '13:30:00'],
                           'vehicle_id': ['veh_1_bus', 'veh_2_bus']},
                    arrival_offsets=['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                    departure_offsets=['00:00:00', '00:05:00', '00:09:00', '00:15:00'],
                    route=['1', '2', '3', '4'])
    route_2 = Route(id='2', route_short_name='name_2',
                    mode='bus',
                    stops=[Stop(id='5', x=4, y=2, epsg='epsg:27700', linkRefId='5'),
                           Stop(id='6', x=1, y=2, epsg='epsg:27700', linkRefId='6'),
                           Stop(id='7', x=3, y=3, epsg='epsg:27700', linkRefId='7'),
                           Stop(id='8', x=7, y=5, epsg='epsg:27700', linkRefId='8')],
                    trips={'trip_id': ['1', '2'],
                           'trip_departure_time': ['11:00:00', '13:00:00'],
                           'vehicle_id': ['veh_3_bus', 'veh_4_bus']},
                    arrival_offsets=['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                    departure_offsets=['00:00:00', '00:05:00', '00:09:00', '00:15:00'],
                    route=['5', '6', '7', '8'])
    return Service(id='service', routes=[route_1, route_2])


@pytest.fixture()
def strongly_connected_service():
    route_1 = Route(route_short_name='name',
                    mode='bus',
                    stops=[Stop(id='1', x=4, y=2, epsg='epsg:27700'), Stop(id='2', x=1, y=2, epsg='epsg:27700'),
                           Stop(id='3', x=3, y=3, epsg='epsg:27700'), Stop(id='4', x=7, y=5, epsg='epsg:27700'),
                           Stop(id='1', x=4, y=2, epsg='epsg:27700')],
                    trips={'trip_id': ['1', '2'],
                           'trip_departure_time': ['1', '2'],
                           'vehicle_id': ['veh_1_bus', 'veh_2_bus']},
                    arrival_offsets=['1', '2'], departure_offsets=['1', '2'])
    route_2 = Route(route_short_name='name_2',
                    mode='bus',
                    stops=[Stop(id='5', x=4, y=2, epsg='epsg:27700'), Stop(id='2', x=1, y=2, epsg='epsg:27700'),
                           Stop(id='7', x=3, y=3, epsg='epsg:27700'), Stop(id='8', x=7, y=5, epsg='epsg:27700'),
                           Stop(id='5', x=4, y=2, epsg='epsg:27700')],
                    trips={'trip_id': ['1', '2'],
                           'trip_departure_time': ['1', '2'],
                           'vehicle_id': ['veh_3_bus', 'veh_4_bus']},
                    arrival_offsets=['1', '2', '3', '4', '5'],
                    departure_offsets=['1', '2', '3', '4', '5'])
    return Service(id='service', routes=[route_1, route_2])


def test_initiating_service(service):
    s = service
    assert_semantically_equal(dict(s._graph.nodes(data=True)), {
        '5': {'services': {'service'}, 'routes': {'2'}, 'id': '5', 'x': 4.0, 'y': 2.0, 'epsg': 'epsg:27700', 'name': '',
              'lat': 49.76682779861249, 'lon': -7.557106577683727, 's2_id': 5205973754090531959,
              'additional_attributes': {'linkRefId'}, 'linkRefId': '5'},
        '6': {'services': {'service'}, 'routes': {'2'}, 'id': '6', 'x': 1.0, 'y': 2.0, 'epsg': 'epsg:27700', 'name': '',
              'lat': 49.766825803756994, 'lon': -7.557148039524952, 's2_id': 5205973754090365183,
              'additional_attributes': {'linkRefId'}, 'linkRefId': '6'},
        '7': {'services': {'service'}, 'routes': {'2'}, 'id': '7', 'x': 3.0, 'y': 3.0, 'epsg': 'epsg:27700', 'name': '',
              'lat': 49.76683608549253, 'lon': -7.557121424907424, 's2_id': 5205973754090203369,
              'additional_attributes': {'linkRefId'}, 'linkRefId': '7'},
        '8': {'services': {'service'}, 'routes': {'2'}, 'id': '8', 'x': 7.0, 'y': 5.0, 'epsg': 'epsg:27700', 'name': '',
              'lat': 49.766856648946295, 'lon': -7.5570681956375, 's2_id': 5205973754097123809,
              'additional_attributes': {'linkRefId'}, 'linkRefId': '8'},
        '1': {'services': {'service'}, 'routes': {'1'}, 'id': '1', 'x': 4.0, 'y': 2.0, 'epsg': 'epsg:27700', 'name': '',
              'lat': 49.76682779861249, 'lon': -7.557106577683727, 's2_id': 5205973754090531959,
              'additional_attributes': {'linkRefId'}, 'linkRefId': '1'},
        '2': {'services': {'service'}, 'routes': {'1'}, 'id': '2', 'x': 1.0, 'y': 2.0, 'epsg': 'epsg:27700', 'name': '',
              'lat': 49.766825803756994, 'lon': -7.557148039524952, 's2_id': 5205973754090365183,
              'additional_attributes': {'linkRefId'}, 'linkRefId': '2'},
        '4': {'services': {'service'}, 'routes': {'1'}, 'id': '4', 'x': 7.0, 'y': 5.0, 'epsg': 'epsg:27700', 'name': '',
              'lat': 49.766856648946295, 'lon': -7.5570681956375, 's2_id': 5205973754097123809,
              'additional_attributes': {'linkRefId'}, 'linkRefId': '4'},
        '3': {'services': {'service'}, 'routes': {'1'}, 'id': '3', 'x': 3.0, 'y': 3.0, 'epsg': 'epsg:27700', 'name': '',
              'lat': 49.76683608549253, 'lon': -7.557121424907424, 's2_id': 5205973754090203369,
              'additional_attributes': {'linkRefId'}, 'linkRefId': '3'}})
    assert_semantically_equal(service._graph.edges(data=True)._adjdict,
                              {'5': {'6': {'services': {'service'}, 'routes': {'2'}}},
                               '6': {'7': {'services': {'service'}, 'routes': {'2'}}},
                               '7': {'8': {'services': {'service'}, 'routes': {'2'}}}, '8': {},
                               '2': {'3': {'services': {'service'}, 'routes': {'1'}}}, '4': {},
                               '1': {'2': {'services': {'service'}, 'routes': {'1'}}},
                               '3': {'4': {'services': {'service'}, 'routes': {'1'}}}})
    log = s._graph.graph.pop('change_log')
    assert log.empty
    assert_semantically_equal(s._graph.graph,
                              {'name': 'Service graph',
                               'routes': {
                                   '2': {'route_short_name': 'name_2', 'mode': 'bus',
                                         'trips': {'trip_id': ['1', '2'],
                                                   'trip_departure_time': ['11:00:00', '13:00:00'],
                                                   'vehicle_id': ['veh_3_bus', 'veh_4_bus']},
                                         'arrival_offsets': ['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                                         'departure_offsets': ['00:00:00', '00:05:00', '00:09:00', '00:15:00'],
                                         'route_long_name': '', 'id': '2',
                                         'route': ['5', '6', '7', '8'], 'await_departure': [],
                                         'ordered_stops': ['5', '6', '7', '8']},
                                   '1': {'route_short_name': 'name', 'mode': 'bus',
                                         'trips': {'trip_id': ['1', '2'],
                                                   'trip_departure_time': ['13:00:00', '13:30:00'],
                                                   'vehicle_id': ['veh_1_bus', 'veh_2_bus']},
                                         'arrival_offsets': ['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                                         'departure_offsets': ['00:00:00', '00:05:00', '00:09:00', '00:15:00'],
                                         'route_long_name': '', 'id': '1',
                                         'route': ['1', '2', '3', '4'], 'await_departure': [],
                                         'ordered_stops': ['1', '2', '3', '4']}},
                               'services': {
                                   'service': {'id': 'service', 'name': 'name'}},
                               'route_to_service_map': {'1': 'service', '2': 'service'},
                               'service_to_route_map': {'service': ['1', '2']},
                               'crs': {'init': 'epsg:27700'}})


def test__repr__shows_route_length(service):
    assert str(len(service)) in service.__repr__()


def test__str__shows_info(service):
    assert service.id in service.__str__()
    assert service.name in service.__str__()
    assert str(len(service)) in service.__str__()


def test_print_shows_info(mocker, service):
    mocker.patch.object(Service, 'info')
    service.print()
    Service.info.assert_called_once()


def test_info_shows_id_name_and_len(service):
    info = service.info()
    assert service.id in info
    assert service.name in info
    assert str(len(service)) in info


def test_plot_delegates_to_util_plot_plot_graph_routes(mocker, route):
    mocker.patch.object(plot, 'plot_graph')
    route.plot()
    plot.plot_graph.assert_called_once()


def test_services_equal(route, similar_non_exact_test_route):
    a = Service(id='service',
                routes=[route, similar_non_exact_test_route])

    b = Service(id='service',
                routes=[route, similar_non_exact_test_route])

    assert a == b


def test_services_exact(route, similar_non_exact_test_route):
    a = Service(id='service',
                routes=[route, similar_non_exact_test_route])

    b = Service(id='service',
                routes=[route, similar_non_exact_test_route])

    assert a.is_exact(b)


def test_route_isin_exact_list(test_service):
    a = test_service

    assert a.isin_exact([test_service, test_service])


def test_route_is_not_in_exact_list(similar_non_exact_test_route, test_service):
    a = Service(id='service',
                routes=[similar_non_exact_test_route])

    assert not a.isin_exact([test_service, test_service])


def test_build_graph_builds_correct_graph():
    route_1 = Route(route_short_name='name', id='1',
                    mode='bus',
                    stops=[Stop(id='1', x=4, y=2, epsg='epsg:27700'), Stop(id='2', x=1, y=2, epsg='epsg:27700'),
                           Stop(id='3', x=3, y=3, epsg='epsg:27700'), Stop(id='4', x=7, y=5, epsg='epsg:27700')],
                    trips={'trip_id': ['1', '2'],
                           'trip_departure_time': ['1', '2'],
                           'vehicle_id': ['veh_1_bus', 'veh_2_bus']},
                    arrival_offsets=['1', '2'], departure_offsets=['1', '2'])
    route_2 = Route(route_short_name='name_2', id='2',
                    mode='bus',
                    stops=[Stop(id='5', x=4, y=2, epsg='epsg:27700'), Stop(id='6', x=1, y=2, epsg='epsg:27700'),
                           Stop(id='7', x=3, y=3, epsg='epsg:27700'), Stop(id='8', x=7, y=5, epsg='epsg:27700')],
                    trips={'trip_id': ['1', '2'],
                           'trip_departure_time': ['1', '2'],
                           'vehicle_id': ['veh_3_bus', 'veh_4_bus']},
                    arrival_offsets=['1', '2'], departure_offsets=['1', '2'])
    service = Service(id='service',
                      routes=[route_1, route_2])

    g = service.graph()

    assert_semantically_equal(dict(g.nodes(data=True)),
                              {'5': {'routes': {'2'}, 'id': '5', 'x': 4.0, 'y': 2.0, 'epsg': 'epsg:27700',
                                     'lat': 49.76682779861249, 'lon': -7.557106577683727, 's2_id': 5205973754090531959,
                                     'name': '', 'additional_attributes': set(), 'services': {'service'}},
                               '6': {'routes': {'2'}, 'id': '6', 'x': 1.0, 'y': 2.0, 'epsg': 'epsg:27700',
                                     'lat': 49.766825803756994, 'lon': -7.557148039524952, 's2_id': 5205973754090365183,
                                     'name': '', 'additional_attributes': set(), 'services': {'service'}},
                               '7': {'routes': {'2'}, 'id': '7', 'x': 3.0, 'y': 3.0, 'epsg': 'epsg:27700',
                                     'lat': 49.76683608549253, 'lon': -7.557121424907424, 's2_id': 5205973754090203369,
                                     'name': '', 'additional_attributes': set(), 'services': {'service'}},
                               '8': {'routes': {'2'}, 'id': '8', 'x': 7.0, 'y': 5.0, 'epsg': 'epsg:27700',
                                     'lat': 49.766856648946295, 'lon': -7.5570681956375, 's2_id': 5205973754097123809,
                                     'name': '', 'additional_attributes': set(), 'services': {'service'}},
                               '1': {'routes': {'1'}, 'id': '1', 'x': 4.0, 'y': 2.0, 'epsg': 'epsg:27700',
                                     'lat': 49.76682779861249, 'lon': -7.557106577683727, 's2_id': 5205973754090531959,
                                     'name': '', 'additional_attributes': set(), 'services': {'service'}},
                               '2': {'routes': {'1'}, 'id': '2', 'x': 1.0, 'y': 2.0, 'epsg': 'epsg:27700',
                                     'lat': 49.766825803756994, 'lon': -7.557148039524952, 's2_id': 5205973754090365183,
                                     'name': '', 'additional_attributes': set(), 'services': {'service'}},
                               '3': {'routes': {'1'}, 'id': '3', 'x': 3.0, 'y': 3.0, 'epsg': 'epsg:27700',
                                     'lat': 49.76683608549253, 'lon': -7.557121424907424, 's2_id': 5205973754090203369,
                                     'name': '', 'additional_attributes': set(), 'services': {'service'}},
                               '4': {'routes': {'1'}, 'id': '4', 'x': 7.0, 'y': 5.0, 'epsg': 'epsg:27700',
                                     'lat': 49.766856648946295, 'lon': -7.5570681956375, 's2_id': 5205973754097123809,
                                     'name': '', 'additional_attributes': set(), 'services': {'service'}}})
    assert_semantically_equal(g.edges(data=True)._adjdict,
                              {'5': {'6': {'services': {'service'}, 'routes': {'2'}}},
                               '6': {'7': {'services': {'service'}, 'routes': {'2'}}},
                               '7': {'8': {'services': {'service'}, 'routes': {'2'}}}, '8': {},
                               '2': {'3': {'services': {'service'}, 'routes': {'1'}}}, '4': {},
                               '3': {'4': {'services': {'service'}, 'routes': {'1'}}},
                               '1': {'2': {'services': {'service'}, 'routes': {'1'}}}})


def test_build_graph_builds_correct_graph_when_some_stops_overlap():
    route_1 = Route(route_short_name='name', id='1',
                    mode='bus',
                    stops=[Stop(id='1', x=4, y=2, epsg='epsg:27700'), Stop(id='2', x=1, y=2, epsg='epsg:27700'),
                           Stop(id='3', x=3, y=3, epsg='epsg:27700'), Stop(id='4', x=7, y=5, epsg='epsg:27700')],
                    trips={'trip_id': ['1', '2'],
                           'trip_departure_time': ['1', '2'],
                           'vehicle_id': ['veh_1_bus', 'veh_2_bus']},
                    arrival_offsets=['1', '2'], departure_offsets=['1', '2'])
    route_2 = Route(route_short_name='name_2', id='2',
                    mode='bus',
                    stops=[Stop(id='1', x=4, y=2, epsg='epsg:27700'), Stop(id='6', x=1, y=2, epsg='epsg:27700'),
                           Stop(id='7', x=3, y=3, epsg='epsg:27700'), Stop(id='4', x=7, y=5, epsg='epsg:27700')],
                    trips={'trip_id': ['1', '2'],
                           'trip_departure_time': ['1', '2'],
                           'vehicle_id': ['veh_3_bus', 'veh_4_bus']},
                    arrival_offsets=['1', '2'], departure_offsets=['1', '2'])
    service = Service(id='service',
                      routes=[route_1, route_2])

    g = service.graph()

    assert_semantically_equal(dict(g.nodes(data=True)),
                              {'1': {'routes': {'2', '1'}, 'id': '1', 'x': 4.0, 'y': 2.0, 'epsg': 'epsg:27700',
                                     'lat': 49.76682779861249, 'lon': -7.557106577683727, 's2_id': 5205973754090531959,
                                     'name': '', 'additional_attributes': set(), 'services': {'service'}},
                               '6': {'routes': {'2'}, 'id': '6', 'x': 1.0, 'y': 2.0, 'epsg': 'epsg:27700',
                                     'lat': 49.766825803756994, 'lon': -7.557148039524952, 's2_id': 5205973754090365183,
                                     'name': '', 'additional_attributes': set(), 'services': {'service'}},
                               '7': {'routes': {'2'}, 'id': '7', 'x': 3.0, 'y': 3.0, 'epsg': 'epsg:27700',
                                     'lat': 49.76683608549253, 'lon': -7.557121424907424, 's2_id': 5205973754090203369,
                                     'name': '', 'additional_attributes': set(), 'services': {'service'}},
                               '4': {'routes': {'2', '1'}, 'id': '4', 'x': 7.0, 'y': 5.0, 'epsg': 'epsg:27700',
                                     'lat': 49.766856648946295, 'lon': -7.5570681956375, 's2_id': 5205973754097123809,
                                     'name': '', 'additional_attributes': set(), 'services': {'service'}},
                               '2': {'routes': {'1'}, 'id': '2', 'x': 1.0, 'y': 2.0, 'epsg': 'epsg:27700',
                                     'lat': 49.766825803756994, 'lon': -7.557148039524952, 's2_id': 5205973754090365183,
                                     'name': '', 'additional_attributes': set(), 'services': {'service'}},
                               '3': {'routes': {'1'}, 'id': '3', 'x': 3.0, 'y': 3.0, 'epsg': 'epsg:27700',
                                     'lat': 49.76683608549253, 'lon': -7.557121424907424, 's2_id': 5205973754090203369,
                                     'name': '', 'additional_attributes': set(), 'services': {'service'}}})
    assert_semantically_equal(list(g.edges), [('1', '6'), ('6', '7'), ('7', '4'), ('1', '2'), ('2', '3'), ('3', '4')])
    assert 'Service' in g.name


def test_is_strongly_connected_with_strongly_connected_service(strongly_connected_service):
    assert strongly_connected_service.is_strongly_connected()


def test_is_strongly_connected_with_not_strongly_connected_service(service):
    assert not service.is_strongly_connected()


def test_has_self_loops_with_self_has_self_looping_service(self_looping_route):
    s = Service(id='1', routes=[self_looping_route])
    assert s.has_self_loops()


def test_has_self_loops_returns_self_looping_stops(self_looping_route):
    s = Service(id='1', routes=[self_looping_route])
    loop_nodes = s.has_self_loops()
    assert loop_nodes == ['1']


def test_has_self_loops_with_non_looping_route(service):
    assert not service.has_self_loops()


def test_validity_of_routes(self_looping_route, route):
    s = Service(id='1', routes=[self_looping_route, route])
    assert s.validity_of_routes() == [False, True]


def test_has_valid_routes(self_looping_route, route):
    s = Service(id='1', routes=[self_looping_route, route])
    assert not s.has_valid_routes()


def test_has_valid_routes_with_only_valid_routes(route):
    a = Stop(id='1', x=4, y=2, epsg='epsg:27700', linkRefId='1')
    b = Stop(id='2', x=1, y=2, epsg='epsg:27700', linkRefId='2')
    c = Stop(id='3', x=3, y=3, epsg='epsg:27700', linkRefId='3')
    d = Stop(id='4', x=7, y=5, epsg='epsg:27700', linkRefId='4')
    r = Route(
        route_short_name='name_2',
        mode='bus',
        stops=[a, b, c, d],
        trips={'trip_id': ['1', '2'],
               'trip_departure_time': ['10:00:00', '20:00:00'],
               'vehicle_id': ['veh_1_bus', 'veh_2_bus']},
        arrival_offsets=['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
        departure_offsets=['00:00:00', '00:05:00', '00:09:00', '00:15:00'],
        route=['1', '2', '3', '4'], id='2')
    s = Service(id='1', routes=[route, r])
    assert s.has_valid_routes()


def test_invalid_routes_shows_invalid_routes(self_looping_route, route):
    s = Service(id='1', routes=[self_looping_route, route])
    assert s.invalid_routes() == [self_looping_route]


def test_has_id(service):
    assert service.has_id()


def test_is_valid_with_valid_service(service):
    assert service.is_valid_service()


def test_is_valid_with_looping_route(self_looping_route, route):
    s = Service(id='1', routes=[self_looping_route, route])
    assert not s.is_valid_service()


def test_is_valid_with_non_network_route(service):
    service._graph.graph['routes']['1']['route'] = []
    service._graph.graph['routes']['2']['route'] = []
    assert not service.is_valid_service()


def test_building_trips_dataframe(service):
    df = service.route_trips_with_stops_to_dataframe()

    correct_df = DataFrame({'departure_time': {0: Timestamp('1970-01-01 13:00:00'), 1: Timestamp('1970-01-01 13:05:00'),
                                               2: Timestamp('1970-01-01 13:09:00'), 3: Timestamp('1970-01-01 13:30:00'),
                                               4: Timestamp('1970-01-01 13:35:00'), 5: Timestamp('1970-01-01 13:39:00'),
                                               6: Timestamp('1970-01-01 11:00:00'), 7: Timestamp('1970-01-01 11:05:00'),
                                               8: Timestamp('1970-01-01 11:09:00'), 9: Timestamp('1970-01-01 13:00:00'),
                                               10: Timestamp('1970-01-01 13:05:00'),
                                               11: Timestamp('1970-01-01 13:09:00')},
                            'arrival_time': {0: Timestamp('1970-01-01 13:03:00'), 1: Timestamp('1970-01-01 13:07:00'),
                                             2: Timestamp('1970-01-01 13:13:00'), 3: Timestamp('1970-01-01 13:33:00'),
                                             4: Timestamp('1970-01-01 13:37:00'), 5: Timestamp('1970-01-01 13:43:00'),
                                             6: Timestamp('1970-01-01 11:03:00'), 7: Timestamp('1970-01-01 11:07:00'),
                                             8: Timestamp('1970-01-01 11:13:00'), 9: Timestamp('1970-01-01 13:03:00'),
                                             10: Timestamp('1970-01-01 13:07:00'),
                                             11: Timestamp('1970-01-01 13:13:00')},
                            'from_stop': {0: '1', 1: '2', 2: '3', 3: '1', 4: '2', 5: '3', 6: '5', 7: '6', 8: '7',
                                          9: '5', 10: '6', 11: '7'},
                            'to_stop': {0: '2', 1: '3', 2: '4', 3: '2', 4: '3', 5: '4', 6: '6', 7: '7', 8: '8', 9: '6',
                                        10: '7', 11: '8'},
                            'trip': {0: '1', 1: '1', 2: '1', 3: '2', 4: '2', 5: '2', 6: '1', 7: '1', 8: '1', 9: '2',
                                     10: '2', 11: '2'},
                            'vehicle_id': {0: 'veh_1_bus', 1: 'veh_1_bus', 2: 'veh_1_bus', 3: 'veh_2_bus',
                                           4: 'veh_2_bus', 5: 'veh_2_bus', 6: 'veh_3_bus', 7: 'veh_3_bus',
                                           8: 'veh_3_bus', 9: 'veh_4_bus', 10: 'veh_4_bus', 11: 'veh_4_bus'},
                            'route': {0: '1', 1: '1', 2: '1', 3: '1', 4: '1', 5: '1', 6: '2', 7: '2', 8: '2', 9: '2',
                                      10: '2', 11: '2'},
                            'route_name': {0: 'name', 1: 'name', 2: 'name', 3: 'name', 4: 'name', 5: 'name',
                                           6: 'name_2', 7: 'name_2', 8: 'name_2', 9: 'name_2', 10: 'name_2',
                                           11: 'name_2'},
                            'mode': {0: 'bus', 1: 'bus', 2: 'bus', 3: 'bus', 4: 'bus', 5: 'bus', 6: 'bus', 7: 'bus',
                                     8: 'bus', 9: 'bus', 10: 'bus', 11: 'bus'},
                            'from_stop_name': {0: '', 1: '', 2: '', 3: '', 4: '', 5: '', 6: '', 7: '', 8: '', 9: '',
                                               10: '', 11: ''},
                            'to_stop_name': {0: '', 1: '', 2: '', 3: '', 4: '', 5: '', 6: '', 7: '', 8: '', 9: '',
                                             10: '', 11: ''},
                            'service': {0: 'service', 1: 'service', 2: 'service', 3: 'service', 4: 'service',
                                        5: 'service', 6: 'service', 7: 'service', 8: 'service', 9: 'service',
                                        10: 'service', 11: 'service'},
                            'service_name': {0: 'name', 1: 'name', 2: 'name', 3: 'name', 4: 'name', 5: 'name',
                                             6: 'name', 7: 'name', 8: 'name', 9: 'name', 10: 'name', 11: 'name'}})

    assert_frame_equal(df, correct_df)
