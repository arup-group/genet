import pytest

from genet import Schedule, Service, Route, Stop, schedule_elements
from genet.validate import schedule
from tests.fixtures import test_schedule, assert_semantically_equal

@pytest.fixture()
def correct_schedule():
    return Schedule(epsg='epsg:27700', services=[
        Service(id='service',
                routes=[
                    Route(id='1', route_short_name='route', mode='bus',
                          stops=[
                              Stop(id='0', x=529455.7452394223, y=182401.37630677427, epsg='epsg:27700', linkRefId='1'),
                              Stop(id='1', x=529350.7866124967, y=182388.0201078112, epsg='epsg:27700', linkRefId='2')],

                          trips={'trip_id': ['VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00'],
                                 'trip_departure_time': ['04:40:00'],
                                 'vehicle_id': ['veh_1_bus']},
                          arrival_offsets=['00:00:00', '00:02:00'],
                          departure_offsets=['00:00:00', '00:02:00'],
                          route=['1', '2']),
                    Route(id='2', route_short_name='route1', mode='bus',
                          stops=[
                              Stop(id='0', x=529455.7452394223, y=182401.37630677427, epsg='epsg:27700', linkRefId='1'),
                              Stop(id='1', x=529350.7866124967, y=182388.0201078112, epsg='epsg:27700', linkRefId='2')],
                          trips={'trip_id': ['Blep_04:40:00'],
                                 'trip_departure_time': ['05:40:00'],
                                 'vehicle_id': ['veh_2_bus']},
                          arrival_offsets=['00:00:00', '00:03:00'],
                          departure_offsets=['00:00:00', '00:05:00'],
                          route=['1', '2'])
                ])
    ])


def test_generate_validation_report_for_correct_schedule(correct_schedule):
    correct_report = {
        'schedule_level': {'is_valid_schedule': True, 'invalid_stages': [], 'has_valid_services': True,
                           'invalid_services': []},
        'service_level': {
            'service': {'is_valid_service': True, 'invalid_stages': [],
                        'has_valid_routes': True, 'invalid_routes': []}},
        'route_level': {
            'service': {'1': {'is_valid_route': True, 'invalid_stages': []},
                        '2': {'is_valid_route': True, 'invalid_stages': []}}},
        'vehicle_level': {'vehicle_definitions_valid': True,
                          'vehicle_definitions_validity_components': {
                              'missing_vehicles': {'missing_vehicles_types': set(),
                                                   'vehicles_affected': {}},
                              'multiple_use_vehicles': {},
                              'unused_vehicles': set()}}}

    report = schedule_validation.generate_validation_report(correct_schedule)
    assert_semantically_equal(report, correct_report)


def test_generate_validation_report_for_incorrect_schedule(test_schedule):
    correct_report = {
        'schedule_level': {'is_valid_schedule': False, 'invalid_stages': ['not_has_valid_services'],
                           'has_valid_services': False, 'invalid_services': ['service']},
        'service_level': {'service': {'is_valid_service': False,
                        'invalid_stages': ['not_has_valid_routes'],
                        'has_valid_routes': False, 'invalid_routes': ['service_0', 'service_1']}},
        'route_level': {'service': {'service_0': {'is_valid_route': False,
                                                  'invalid_stages': ['not_has_correctly_ordered_route',
                                                                     'has_self_loops']},
                                    'service_1': {'is_valid_route': False,
                                                  'invalid_stages': ['not_has_correctly_ordered_route',
                                                                     'has_self_loops']}}},
        'vehicle_level': {'vehicle_definitions_valid': True,
                          'vehicle_definitions_validity_components': {
                              'missing_vehicles': {'missing_vehicles_types': set(),
                                                   'vehicles_affected': {}},
                              'multiple_use_vehicles': {},
                              'unused_vehicles': set()}}}
    report = schedule_validation.generate_validation_report(test_schedule)
    assert_semantically_equal(report, correct_report)


@pytest.fixture()
def schedule_with_incomplete_vehicle_definition():
    s = Schedule(epsg='epsg:27700', services=[
        Service(id='service',
                routes=[
                    Route(route_short_name='route', mode='bus',
                          stops=[Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700'),
                                 Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700')],
                          trips={'trip_id': ['VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00'],
                                 'trip_departure_time': ['04:40:00'],
                                 'vehicle_id': ['veh_1_bus']},
                          arrival_offsets=['00:00:00', '00:02:00'],
                          departure_offsets=['00:00:00', '00:02:00']),
                    Route(route_short_name='route1', mode='bus',
                          stops=[Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700'),
                                 Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700')],
                          trips={'trip_id': ['Blep_04:40:00'],
                                 'trip_departure_time': ['05:40:00'],
                                 'vehicle_id': ['veh_2_bus']},
                          arrival_offsets=['00:00:00', '00:03:00'],
                          departure_offsets=['00:00:00', '00:05:00'])
                ])
    ])
    s.vehicle_types = {}
    return s


def test_generate_validation_report_with_schedule_incomplete_vehicle_definitions(schedule_with_incomplete_vehicle_definition):
    correct_report = {'route_level': {'service': {'service_0': {'invalid_stages': ['not_has_correctly_ordered_route',
                                                                      'has_self_loops'],
                                                   'is_valid_route': False},
                                     'service_1': {'invalid_stages': ['not_has_correctly_ordered_route',
                                                                      'has_self_loops'],
                                                   'is_valid_route': False}}},
         'schedule_level': {'has_valid_services': False,
                            'invalid_services': ['service'],
                            'invalid_stages': ['not_has_valid_services'],
                            'is_valid_schedule': False},
         'service_level': {'service': {'has_valid_routes': False,
                                       'invalid_routes': ['service_0', 'service_1'],
                                       'invalid_stages': ['not_has_valid_routes'],
                                       'is_valid_service': False}},
         'vehicle_level': {'vehicle_definitions_valid': False,
                           'vehicle_definitions_validity_components': {
                               'missing_vehicles': {'missing_vehicles_types': {'bus'},
                                                    'vehicles_affected': {'veh_1_bus': {'type': 'bus'},
                                                                          'veh_2_bus': {'type': 'bus'}}},
                               'multiple_use_vehicles': {},
                               'unused_vehicles': set()}}}

    report = schedule_validation.generate_validation_report(schedule_with_incomplete_vehicle_definition)
    print(report)
    assert_semantically_equal(report, correct_report)



def test_schedule_with_no_unused_vehicles(correct_schedule):
    correct_output = set()
    actual_output = correct_schedule.unused_vehicles()

    assert_semantically_equal(correct_output, actual_output)


@pytest.fixture()
def schedule_with_unused_vehicles():
    s = Schedule(epsg='epsg:27700', services=[
        Service(id='service',
                routes=[
                    Route(id = 'r1',route_short_name='route', mode='bus',
                          stops=[Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700'),
                                 Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700')],
                          trips={'trip_id': ['VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00'],
                                 'trip_departure_time': ['04:40:00'],
                                 'vehicle_id': ['veh_1_bus']},
                          arrival_offsets=['00:00:00', '00:02:00'],
                          departure_offsets=['00:00:00', '00:02:00'])
                ])
    ])

    s.vehicles = {'veh_2_bus': {'type': 'bus'}, 'veh_1_bus': {'type': 'bus'}}

    return s



def test_schedule_with_unused_vehicles(schedule_with_unused_vehicles):
    unused_correct = set({'veh_2_bus'})
    unused_actual = schedule_with_unused_vehicles.unused_vehicles()

    assert_semantically_equal(unused_correct, unused_actual)


def test_schedule_with_no_multiple_use_vehicles(correct_schedule):
    correct_output = {}
    actual_output = correct_schedule.check_vehicle_uniqueness()

    assert_semantically_equal(correct_output, actual_output)



@pytest.fixture()
def schedule_with_multiple_use_vehicles():
    s = Schedule(epsg='epsg:27700', services=[
        Service(id='service',
                routes=[
                    Route(route_short_name='route', mode='bus',
                          stops=[Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700'),
                                 Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700')],
                          trips={'trip_id': ['VJ00938baa194cee94700312812d208fe79f3297ee_044000'],
                                 'trip_departure_time': ['04:40:00'],
                                 'vehicle_id': ['veh_1_bus']},
                          arrival_offsets=['00:00:00', '00:02:00'],
                          departure_offsets=['00:00:00', '00:02:00']),
                    Route(route_short_name='route1', mode='bus',
                          stops=[Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700'),
                                 Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700')],
                          trips={'trip_id': ['Blep_044000'],
                                 'trip_departure_time': ['05:40:00'],
                                 'vehicle_id': ['veh_1_bus']},
                          arrival_offsets=['00:00:00', '00:03:00'],
                          departure_offsets=['00:00:00', '00:05:00'])
                ])
    ])
    return s


def test_schedule_with_multiple_use_vehicles(schedule_with_multiple_use_vehicles):
    correct_output = {}
    correct_output['veh_1_bus'] = []
    correct_output['veh_1_bus'].append('VJ00938baa194cee94700312812d208fe79f3297ee_044000')
    correct_output['veh_1_bus'].append('Blep_044000')
    actual_output = schedule_with_multiple_use_vehicles.check_vehicle_uniqueness()

    assert_semantically_equal(correct_output, actual_output)