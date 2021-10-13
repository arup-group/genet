import pytest

from genet import Schedule, Service, Route, Stop
from genet.validate import schedule_validation
from tests.fixtures import correct_schedule, test_schedule, assert_semantically_equal


def test_generate_validation_report_with_correct_schedule(correct_schedule):
    correct_report = {
        'schedule_level': {'is_valid_schedule': True, 'invalid_stages': [], 'has_valid_services': True,
                           'invalid_services': []},
        'service_level': {
            'service': {'is_valid_service': True, 'invalid_stages': [],
                        'has_valid_routes': True, 'invalid_routes': []}},
        'route_level': {
            'service': {'1': {'is_valid_route': True, 'invalid_stages': []},
                        '2': {'is_valid_route': True, 'invalid_stages': []}}},
        'vehicle_level': {
            'vehicle_definitions_valid': True,
            'missing_vehicle_types': set(),
            'vehicles_affected': {},
            'unused_vehicles': set(),
            'multiple_use_vehicles': {}}}

    report = schedule_validation.generate_validation_report(correct_schedule)
    assert_semantically_equal(report, correct_report)


def test_generate_validation_report_with_incorrect_schedule(test_schedule):
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
        'vehicle_level': {
            'vehicle_definitions_valid': True,
            'missing_vehicle_types': set(),
            'vehicles_affected': {},
            'unused_vehicles': set(),
            'multiple_use_vehicles': {}}}
    report = schedule_validation.generate_validation_report(test_schedule)
    assert_semantically_equal(report, correct_report)


@pytest.fixture()
def schedule_with_missing_vehicle_information():
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


def test_generate_validation_report_with_schedule_missing_vehicle_definitions(schedule_with_missing_vehicle_information):
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
        'vehicle_level': {
            'vehicle_definitions_valid': False,
            'missing_vehicle_types': {'bus'},
            'vehicles_affected': {'veh_2_bus': {'type': 'bus'}, 'veh_1_bus': {'type': 'bus'}},
            'unused_vehicles': set(),
            'multiple_use_vehicles': {}}}

    report = schedule_validation.generate_validation_report(schedule_with_missing_vehicle_information)
    assert_semantically_equal(report, correct_report)


