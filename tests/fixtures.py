import json
import dictdiffer
import pytest
from collections import OrderedDict
from genet.schedule_elements import Stop, Route, Service
from genet.core import Schedule


###########################################################
# helper functions
###########################################################
def deep_sort(obj):
    if isinstance(obj, dict):
        obj = OrderedDict(sorted(obj.items()))
        for k, v in obj.items():
            if isinstance(v, dict) or isinstance(v, list):
                obj[k] = deep_sort(v)

    if isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, dict) or isinstance(v, list):
                obj[i] = deep_sort(v)
        obj = sorted(obj, key=lambda x: json.dumps(x))

    return obj


def assert_semantically_equal(dict1, dict2):
    # the tiny permissible tolerance is to account for cross-platform differences in
    # floating point lat/lon values, as witnessed in our CI build running on Ubuntu
    # Vs our own OSX laptops - lat/lon values within this tolerance can and should
    # be considered the same in practical terms
    assert list(dictdiffer.diff(deep_sort(dict1), deep_sort(dict2), tolerance=0.00000000000001)) == []


###########################################################
# core data  structure examples
###########################################################
@pytest.fixture()
def stop_epsg_27700():
    return Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700')


@pytest.fixture()
def stop_epsg_4326():
    return Stop(id='0', x=-0.14910908709500162, y=51.52370573323939, epsg='epsg:4326')


@pytest.fixture()
def route(stop_epsg_27700):
    return Route(route_short_name='route', mode='bus',
                 stops=[stop_epsg_27700, stop_epsg_27700],
                 trips={'VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00': '04:40:00'},
                 arrival_offsets=['00:00:00', '00:02:00'],
                 departure_offsets=['00:00:00', '00:02:00'])


@pytest.fixture()
def similar_non_exact_test_route(stop_epsg_27700):
    return Route(route_short_name='route', mode='bus',
                 stops=[stop_epsg_27700, stop_epsg_27700],
                 trips={'Blep_04:40:00': '05:40:00'},
                 arrival_offsets=['00:00:00', '00:03:00'],
                 departure_offsets=['00:00:00', '00:05:00'])


@pytest.fixture()
def test_service(route, similar_non_exact_test_route):
    return Service(id='service',
                   routes=[route, similar_non_exact_test_route])


@pytest.fixture()
def different_test_service(route):
    return Service(id='different_service',
                   routes=[route])


@pytest.fixture()
def test_schedule(test_service):
    return Schedule(services=[test_service])


###########################################################
# correct gtfs vars
###########################################################
correct_stop_times = [{'trip_id': 'BT1', 'arrival_time': '03:21:00', 'departure_time': '03:21:00', 'stop_id': 'BSE',
                       'stop_sequence': '0', 'stop_headsign': '', 'pickup_type': '0', 'drop_off_type': '1',
                       'timepoint': '1', 'stop_direction_name': ''},
                      {'trip_id': 'BT1', 'arrival_time': '03:23:00', 'departure_time': '03:23:00', 'stop_id': 'BSN',
                       'stop_sequence': '1', 'stop_headsign': '', 'pickup_type': '0', 'drop_off_type': '0',
                       'timepoint': '0', 'stop_direction_name': ''},
                      {'trip_id': 'RT1', 'arrival_time': '03:21:00', 'departure_time': '03:21:00', 'stop_id': 'RSN',
                       'stop_sequence': '0', 'stop_headsign': '', 'pickup_type': '0', 'drop_off_type': '0',
                       'timepoint': '0', 'stop_direction_name': ''},
                      {'trip_id': 'RT1', 'arrival_time': '03:23:00', 'departure_time': '03:23:00', 'stop_id': 'RSE',
                       'stop_sequence': '1', 'stop_headsign': '', 'pickup_type': '0', 'drop_off_type': '1',
                       'timepoint': '1', 'stop_direction_name': ''}]
correct_stop_times_db = {'BT1': [
    {'trip_id': 'BT1', 'arrival_time': '03:21:00', 'departure_time': '03:21:00', 'stop_id': 'BSE',
     'stop_sequence': '0', 'stop_headsign': '', 'pickup_type': '0', 'drop_off_type': '1', 'timepoint': '1',
     'stop_direction_name': ''},
    {'trip_id': 'BT1', 'arrival_time': '03:23:00', 'departure_time': '03:23:00', 'stop_id': 'BSN',
     'stop_sequence': '1', 'stop_headsign': '', 'pickup_type': '0', 'drop_off_type': '0', 'timepoint': '0',
     'stop_direction_name': ''}], 'RT1': [
    {'trip_id': 'RT1', 'arrival_time': '03:21:00', 'departure_time': '03:21:00', 'stop_id': 'RSN',
     'stop_sequence': '0', 'stop_headsign': '', 'pickup_type': '0', 'drop_off_type': '0', 'timepoint': '0',
     'stop_direction_name': ''},
    {'trip_id': 'RT1', 'arrival_time': '03:23:00', 'departure_time': '03:23:00', 'stop_id': 'RSE',
     'stop_sequence': '1', 'stop_headsign': '', 'pickup_type': '0', 'drop_off_type': '1', 'timepoint': '1',
     'stop_direction_name': ''}]}
correct_stops_db = {
    'BSE': {'stop_id': 'BSE', 'stop_code': '', 'stop_name': 'Bus Stop snap to edge', 'stop_lat': '51.5226864',
            'stop_lon': '-0.1413621', 'wheelchair_boarding': '', 'stop_timezone': '', 'location_type': '0.0',
            'parent_station': '210G433', 'platform_code': ''},
    'BSN': {'stop_id': 'BSN', 'stop_code': '', 'stop_name': 'Bus Stop snap to node', 'stop_lat': '51.5216199',
            'stop_lon': '-0.140053', 'wheelchair_boarding': '', 'stop_timezone': '', 'location_type': '0.0',
            'parent_station': '210G432', 'platform_code': ''},
    'RSE': {'stop_id': 'RSE', 'stop_code': '', 'stop_name': 'Rail Stop snap to edge', 'stop_lat': '51.5192615',
            'stop_lon': '-0.1421595', 'wheelchair_boarding': '', 'stop_timezone': '', 'location_type': '0.0',
            'parent_station': '210G431', 'platform_code': ''},
    'RSN': {'stop_id': 'RSN', 'stop_code': '', 'stop_name': 'Rail Stop snap to node', 'stop_lat': '51.5231335',
            'stop_lon': '-0.1410946', 'wheelchair_boarding': '', 'stop_timezone': '', 'location_type': '0.0',
            'parent_station': '210G430', 'platform_code': ''}}
correct_trips_db = {
    'BT1': {'route_id': '1001', 'service_id': '6630', 'trip_id': 'BT1', 'trip_headsign': 'Bus Test trip',
            'block_id': '', 'wheelchair_accessible': '0', 'trip_direction_name': '', 'exceptional': ''},
    'RT1': {'route_id': '1002', 'service_id': '6631', 'trip_id': 'RT1', 'trip_headsign': 'Rail Test trip',
            'block_id': '', 'wheelchair_accessible': '0', 'trip_direction_name': '', 'exceptional': ''}}
correct_routes_db = {'1001': {'route_id': '1001', 'agency_id': 'OP550', 'route_short_name': 'BTR',
                              'route_long_name': 'Bus Test Route', 'route_type': '3', 'route_url': '',
                              'route_color': 'CE312D', 'route_text_color': 'FFFFFF', 'checkin_duration': ''},
                     '1002': {'route_id': '1002', 'agency_id': 'OP550', 'route_short_name': 'RTR',
                              'route_long_name': 'Rail Test Route', 'route_type': '2', 'route_url': '',
                              'route_color': 'CE312D', 'route_text_color': 'FFFFFF', 'checkin_duration': ''}}


@pytest.fixture()
def correct_schedule_dict():
    return {'1001': [
    {'route_short_name': 'BTR', 'route_long_name': 'Bus Test Route', 'mode': 'bus', 'route_color': '#CE312D',
     'trips': {'BT1': '03:21:00'}, 'stops': ['BSE', 'BSN'], 'arrival_offsets': ['0:00:00', '0:02:00'],
     'departure_offsets': ['0:00:00', '0:02:00'], 's2_stops': [5221390325135889957, 5221390684150342605]}], '1002': [
    {'route_short_name': 'RTR', 'route_long_name': 'Rail Test Route', 'mode': 'rail', 'route_color': '#CE312D',
     'trips': {'RT1': '03:21:00'}, 'stops': ['RSN', 'RSE'], 'arrival_offsets': ['0:00:00', '0:02:00'],
     'departure_offsets': ['0:00:00', '0:02:00'], 's2_stops': [5221390332291192399, 5221390324026756531]}]}


@pytest.fixture()
def correct_services_from_test_gtfs():
    services = []
    services.append(Service(
        '1001',
        [Route(
            route_short_name='BTR',
            mode='bus',
            stops=[Stop(id='BSE', x=-0.1413621, y=51.5226864, epsg='epsg:4326'),
                   Stop(id='BSN', x=-0.140053, y=51.5216199, epsg='epsg:4326')],
            trips={'BT1': '03:21:00'},
            arrival_offsets=['0:00:00', '0:02:00'],
            departure_offsets=['0:00:00', '0:02:00']
        )]))
    services.append(Service(
        '1002',
        [Route(
            route_short_name='RTR',
            mode='rail',
            stops=[Stop(id='RSN', x=-0.1410946, y=51.5231335, epsg='epsg:4326'),
                   Stop(id='RSE', x=-0.1421595, y=51.5192615, epsg='epsg:4326')],
            trips={'RT1': '03:21:00'},
            arrival_offsets=['0:00:00', '0:02:00'],
            departure_offsets=['0:00:00', '0:02:00']
        )]))
    return services


@pytest.fixture()
def correct_stops_mapping_from_test_gtfs():
    return {'BSN': ['1001'], 'BSE': ['1001'], 'RSE': ['1002'], 'RSN': ['1002']}


