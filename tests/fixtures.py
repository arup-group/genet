import json
import sys, os
import dictdiffer
import pytest
from collections import OrderedDict
from genet.schedule_elements import Stop, Route, Service, Schedule
from genet.core import Network
from genet.inputs_handler import osm_reader

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
pt2matsim_network_test_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "network.xml"))
pt2matsim_schedule_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "schedule.xml"))


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
    diffs = list(dictdiffer.diff(deep_sort(dict1), deep_sort(dict2), tolerance=0.00000000001))
    assert diffs == [], diffs


def assert_logging_warning_caught_with_message_containing(clog, message):
    for record in clog.records:
        if message in record.message:
            return True
    return False


###########################################################
# core data  structure examples
###########################################################

###########################################################
# networks
###########################################################
@pytest.fixture()
def network_object_from_test_data():
    n = Network('epsg:27700')
    n.read_matsim_network(pt2matsim_network_test_file)
    n.read_matsim_schedule(pt2matsim_schedule_file)
    return n


###########################################################
# schedule
###########################################################
@pytest.fixture()
def schedule_object_from_test_data():
    s = Schedule('epsg:27700')
    s.read_matsim_schedule(pt2matsim_schedule_file)
    return s


@pytest.fixture()
def stop_epsg_27700():
    return Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700')


@pytest.fixture()
def stop_epsg_4326():
    return Stop(id='0', x=-0.14910908709500162, y=51.52370573323939, epsg='epsg:4326')


@pytest.fixture()
def route():
    return Route(route_short_name='route', mode='bus',
                 stops=[Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700'),
                        Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700')],
                 trips={'VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00': '04:40:00'},
                 arrival_offsets=['00:00:00', '00:02:00'],
                 departure_offsets=['00:00:00', '00:02:00'])


@pytest.fixture()
def similar_non_exact_test_route():
    return Route(route_short_name='route', mode='bus',
                 stops=[Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700'),
                        Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700')],
                 trips={'Blep_04:40:00': '05:40:00'},
                 arrival_offsets=['00:00:00', '00:03:00'],
                 departure_offsets=['00:00:00', '00:05:00'])


@pytest.fixture()
def test_service():
    return Service(id='service',
                   routes=[
                       Route(route_short_name='route', mode='bus',
                        stops=[Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700'),
                            Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700')],
                        trips={'VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00': '04:40:00'},
                        arrival_offsets=['00:00:00', '00:02:00'],
                        departure_offsets=['00:00:00', '00:02:00']),
                       Route(route_short_name='route1', mode='bus',
                             stops=[Stop(id='1', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700'),
                                    Stop(id='2', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700')],
                             trips={'Blep_04:40:00': '05:40:00'},
                             arrival_offsets=['00:00:00', '00:03:00'],
                             departure_offsets=['00:00:00', '00:05:00'])
                   ])


@pytest.fixture()
def different_test_service():
    return Service(id='different_service',
                   routes=[
                       Route(route_short_name='route', mode='bus',
                             stops=[Stop(id='3', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700'),
                                    Stop(id='4', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700')],
                             trips={'VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00': '04:40:00'},
                             arrival_offsets=['00:00:00', '00:02:00'],
                             departure_offsets=['00:00:00', '00:02:00'])
                   ])


@pytest.fixture()
def correct_schedule():
    return Schedule(epsg='epsg:27700', services=[
        Service(id='service',
                routes=[
                    Route(id='1', route_short_name='route', mode='bus',
                          stops=[Stop(id='0', x=529455.7452394223, y=182401.37630677427, epsg='epsg:27700', linkRefId='1'),
                                 Stop(id='1', x=529350.7866124967, y=182388.0201078112, epsg='epsg:27700', linkRefId='2')],
                          trips={'VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00': '04:40:00'},
                          arrival_offsets=['00:00:00', '00:02:00'],
                          departure_offsets=['00:00:00', '00:02:00'],
                          route=['1', '2']),
                    Route(id='2', route_short_name='route1', mode='bus',
                          stops=[Stop(id='0', x=529455.7452394223, y=182401.37630677427, epsg='epsg:27700', linkRefId='1'),
                                 Stop(id='1', x=529350.7866124967, y=182388.0201078112, epsg='epsg:27700', linkRefId='2')],
                          trips={'Blep_04:40:00': '05:40:00'},
                          arrival_offsets=['00:00:00', '00:03:00'],
                          departure_offsets=['00:00:00', '00:05:00'],
                          route=['1', '2'])
                ])
    ])


@pytest.fixture()
def test_schedule():
    return Schedule(epsg='epsg:27700', services=[
        Service(id='service',
                routes=[
                    Route(route_short_name='route', mode='bus',
                          stops=[Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700'),
                                 Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700')],
                          trips={'VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00': '04:40:00'},
                          arrival_offsets=['00:00:00', '00:02:00'],
                          departure_offsets=['00:00:00', '00:02:00']),
                    Route(route_short_name='route1', mode='bus',
                          stops=[Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700'),
                                 Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700')],
                          trips={'Blep_04:40:00': '05:40:00'},
                          arrival_offsets=['00:00:00', '00:03:00'],
                          departure_offsets=['00:00:00', '00:05:00'])
                ])
    ])


###########################################################
# correct gtfs vars
###########################################################
@pytest.fixture()
def correct_stop_times():
    return [{'trip_id': 'BT1', 'arrival_time': '03:21:00', 'departure_time': '03:21:00', 'stop_id': 'BSE',
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


@pytest.fixture()
def correct_stop_times_db():
    return {'BT1': [
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


@pytest.fixture()
def correct_stops_db():
    return {
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


@pytest.fixture()
def correct_trips_db():
    return {
        'BT1': {'route_id': '1001', 'service_id': '6630', 'trip_id': 'BT1', 'trip_headsign': 'Bus Test trip',
                'block_id': '', 'wheelchair_accessible': '0', 'trip_direction_name': '', 'exceptional': ''},
        'RT1': {'route_id': '1002', 'service_id': '6631', 'trip_id': 'RT1', 'trip_headsign': 'Rail Test trip',
                'block_id': '', 'wheelchair_accessible': '0', 'trip_direction_name': '', 'exceptional': ''}}


@pytest.fixture()
def correct_routes_db():
    return {'1001': {'route_id': '1001', 'agency_id': 'OP550', 'route_short_name': 'BTR',
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
         'departure_offsets': ['0:00:00', '0:02:00'], 's2_stops': [5221390325135889957, 5221390684150342605]}],
        '1002': [
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
def correct_stops_to_service_mapping_from_test_gtfs():
    return {'BSN': ['1001'], 'BSE': ['1001'], 'RSE': ['1002'], 'RSN': ['1002']}


@pytest.fixture()
def correct_stops_to_route_mapping_from_test_gtfs():
    return {'BSE': ['1001_0'], 'BSN': ['1001_0'], 'RSE': ['1002_0'], 'RSN': ['1002_0']}


@pytest.fixture()
def correct_services_from_test_pt2matsim_schedule():
    stops = [Stop(id='26997928P', x='528464.1342843144', y='182179.7435136598', epsg='epsg:27700'),
             Stop(id='26997928P.link:1', x='528464.1342843144', y='182179.7435136598', epsg='epsg:27700')]

    stops[0].add_additional_attributes({'name': 'Brunswick Place (Stop P)', 'isBlocking': 'false'})
    stops[1].add_additional_attributes({'name': 'Brunswick Place (Stop P)', 'isBlocking': 'false'})

    services = [Service(id='10314', routes=[
        Route(
            route_short_name='12',
            mode='bus',
            stops=stops,
            route=['1'],
            trips={'VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00': '04:40:00'},
            arrival_offsets=['00:00:00', '00:02:00'],
            departure_offsets=['00:00:00', '00:02:00'],
            await_departure=[True, True]
        )
    ])
                ]
    return services


###########################################################
# OSM reading configs
###########################################################

@pytest.fixture()
def full_fat_default_config_path():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "configs", "default_config.yml"))

@pytest.fixture()
def full_fat_default_config():
    return osm_reader.Config(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "configs", "default_config.yml")))

@pytest.fixture()
def slim_default_config_path():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "configs", "slim_config.yml"))

@pytest.fixture()
def slim_default_config():
    return osm_reader.Config(os.path.join(os.path.dirname(__file__), "..", "configs", "slim_config.yml"))