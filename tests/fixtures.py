import json
import sys, os
import dictdiffer
import pytest
import pandas as pd
from collections import OrderedDict
from genet.schedule_elements import Stop, Route, Service, Schedule
from genet.inputs_handler import osm_reader
import genet.modify.change_log as change_log
from genet.inputs_handler import read

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
pt2matsim_network_test_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "network.xml"))
pt2matsim_schedule_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "schedule.xml"))
pt2matsim_vehicles_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "vehicles.xml"))


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
    return read.read_matsim(path_to_network=pt2matsim_network_test_file, path_to_schedule=pt2matsim_schedule_file,
                            path_to_vehicles=pt2matsim_vehicles_file, epsg='epsg:27700')


###########################################################
# schedule
###########################################################
@pytest.fixture()
def schedule_object_from_test_data():
    return read.read_matsim_schedule(path_to_schedule=pt2matsim_schedule_file, path_to_vehicles=pt2matsim_vehicles_file,
                                     epsg='epsg:27700')


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
                 trips={'trip_id': ['VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00'],
                        'trip_departure_time': ['04:40:00'],
                        'vehicle_id': ['veh_1_bus']},
                 arrival_offsets=['00:00:00', '00:02:00'],
                 departure_offsets=['00:00:00', '00:02:00'])


trips = {'trip_id': ['1', '2'],
         'trip_departure_time': ['13:00:00', '13:30:00'],
         'vehicle_id': ['veh_1_bus', 'veh_2_bus']},


@pytest.fixture()
def similar_non_exact_test_route():
    return Route(route_short_name='route', mode='bus',
                 stops=[Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700'),
                        Stop(id='0', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700')],
                 trips={'trip_id': ['Blep_04:40:00'],
                        'trip_departure_time': ['05:40:00'],
                        'vehicle_id': ['veh_1_bus']},
                 arrival_offsets=['00:00:00', '00:03:00'],
                 departure_offsets=['00:00:00', '00:05:00'])


@pytest.fixture()
def test_service():
    return Service(id='service',
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
                             stops=[Stop(id='1', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700'),
                                    Stop(id='2', x=528504.1342843144, y=182155.7435136598, epsg='epsg:27700')],
                             trips={'trip_id': ['Blep_04:40:00'],
                                    'trip_departure_time': ['05:40:00'],
                                    'vehicle_id': ['veh_2_bus']},
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
                             trips={'trip_id': ['VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00'],
                                    'trip_departure_time': ['04:40:00'],
                                    'vehicle_id': ['veh_1_bus']},
                             arrival_offsets=['00:00:00', '00:02:00'],
                             departure_offsets=['00:00:00', '00:02:00'])
                   ])


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


@pytest.fixture()
def test_schedule():
    return Schedule(epsg='epsg:27700', services=[
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


###########################################################
# correct gtfs vars
###########################################################
@pytest.fixture()
def correct_stop_times_db():
    return pd.DataFrame(
        {'trip_id': {0: 'BT1', 1: 'BT1', 2: 'RT1', 3: 'RT1'},
         'arrival_time': {0: '03:21:00', 1: '03:23:00', 2: '03:21:00', 3: '03:23:00'},
         'departure_time': {0: '03:21:00', 1: '03:23:00', 2: '03:21:00', 3: '03:23:00'},
         'stop_id': {0: 'BSE', 1: 'BSN', 2: 'RSN', 3: 'RSE'}, 'stop_sequence': {0: 0, 1: 1, 2: 0, 3: 1},
         'stop_headsign': {0: float('nan'), 1: float('nan'), 2: float('nan'), 3: float('nan')},
         'pickup_type': {0: 0, 1: 0, 2: 0, 3: 0},
         'drop_off_type': {0: 1, 1: 0, 2: 0, 3: 1}, 'timepoint': {0: 1, 1: 0, 2: 0, 3: 1},
         'stop_direction_name': {0: float('nan'), 1: float('nan'), 2: float('nan'), 3: float('nan')}}
    )


@pytest.fixture()
def correct_stops_db():
    return pd.DataFrame(
        {'stop_id': {0: 'BSE', 1: 'BSN', 2: 'RSE', 3: 'RSN'},
         'stop_code': {0: float('nan'), 1: float('nan'), 2: float('nan'), 3: float('nan')},
         'stop_name': {0: 'Bus Stop snap to edge', 1: 'Bus Stop snap to node', 2: 'Rail Stop snap to edge',
                       3: 'Rail Stop snap to node'},
         'stop_lat': {0: 51.5226864, 1: 51.5216199, 2: 51.5192615, 3: 51.5231335},
         'stop_lon': {0: -0.14136210000000002, 1: -0.140053, 2: -0.1421595, 3: -0.14109460000000001},
         'wheelchair_boarding': {0: float('nan'), 1: float('nan'), 2: float('nan'), 3: float('nan')},
         'stop_timezone': {0: float('nan'), 1: float('nan'), 2: float('nan'), 3: float('nan')},
         'location_type': {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0},
         'parent_station': {0: '210G433', 1: '210G432', 2: '210G431', 3: '210G430'},
         'platform_code': {0: float('nan'), 1: float('nan'), 2: float('nan'), 3: float('nan')}}
    )


@pytest.fixture()
def correct_trips_db():
    return pd.DataFrame(
        {'route_id': {0: '1001', 1: '1002'}, 'service_id': {0: '6630', 1: '6631'}, 'trip_id': {0: 'BT1', 1: 'RT1'},
         'trip_headsign': {0: 'Bus Test trip', 1: 'Rail Test trip'}, 'block_id': {0: float('nan'), 1: float('nan')},
         'wheelchair_accessible': {0: 0, 1: 0}, 'trip_direction_name': {0: float('nan'), 1: float('nan')},
         'exceptional': {0: float('nan'), 1: float('nan')}}
    )


@pytest.fixture()
def correct_routes_db():
    return pd.DataFrame(
        {'route_id': {0: '1001', 1: '1002'}, 'agency_id': {0: 'OP550', 1: 'OP550'},
         'route_short_name': {0: 'BTR', 1: 'RTR'}, 'route_long_name': {0: 'Bus Test Route', 1: 'Rail Test Route'},
         'route_type': {0: 3, 1: 2}, 'route_url': {0: float('nan'), 1: float('nan')},
         'route_color': {0: 'CE312D', 1: 'CE312D'},
         'route_text_color': {0: 'FFFFFF', 1: 'FFFFFF'}, 'checkin_duration': {0: float('nan'), 1: float('nan')}}
    )


@pytest.fixture()
def correct_schedule_dict():
    return {'1001': [
        {'route_short_name': 'BTR', 'route_long_name': 'Bus Test Route', 'mode': 'bus', 'route_color': '#CE312D',
         'trips': {'trip_id': ['BT1'], 'trip_departure_time': ['03:21:00'], 'vehicle_id': ['veh_0_bus']},
         'stops': ['BSE', 'BSN'], 'arrival_offsets': ['0:00:00', '0:02:00'],
         'departure_offsets': ['0:00:00', '0:02:00'], 's2_stops': [5221390325135889957, 5221390684150342605]}],
        '1002': [
            {'route_short_name': 'RTR', 'route_long_name': 'Rail Test Route', 'mode': 'rail', 'route_color': '#CE312D',
             'trips': {'trip_id': ['RT1'], 'trip_departure_time': ['03:21:00'], 'vehicle_id': ['veh_1_rail']},
             'stops': ['RSN', 'RSE'], 'arrival_offsets': ['0:00:00', '0:02:00'],
             'departure_offsets': ['0:00:00', '0:02:00'], 's2_stops': [5221390332291192399, 5221390324026756531]}]}


@pytest.fixture()
def correct_schedule_graph_nodes_from_test_gtfs():
    return {'BSN': {'stop_code': float('nan'), 'name': 'Bus Stop snap to node', 'lat': 51.5216199, 'lon': -0.140053,
                    'wheelchair_boarding': float('nan'), 'stop_timezone': float('nan'), 'location_type': 0.0,
                    'parent_station': '210G432',
                    'platform_code': float('nan'), 'id': 'BSN', 'x': -0.140053, 'y': 51.5216199, 'epsg': 'epsg:4326',
                    's2_id': 5221390684150342605, 'routes': {'1001_0'}, 'services': {'1001'}},
            'RSE': {'stop_code': float('nan'), 'name': 'Rail Stop snap to edge', 'lat': 51.5192615, 'lon': -0.1421595,
                    'wheelchair_boarding': float('nan'), 'stop_timezone': float('nan'), 'location_type': 0.0,
                    'parent_station': '210G431',
                    'platform_code': float('nan'), 'id': 'RSE', 'x': -0.1421595, 'y': 51.5192615, 'epsg': 'epsg:4326',
                    's2_id': 5221390324026756531, 'routes': {'1002_0'}, 'services': {'1002'}},
            'RSN': {'stop_code': float('nan'), 'name': 'Rail Stop snap to node', 'lat': 51.5231335,
                    'lon': -0.14109460000000001,
                    'wheelchair_boarding': float('nan'), 'stop_timezone': float('nan'), 'location_type': 0.0,
                    'parent_station': '210G430',
                    'platform_code': float('nan'), 'id': 'RSN', 'x': -0.14109460000000001, 'y': 51.5231335,
                    'epsg': 'epsg:4326',
                    's2_id': 5221390332291192399, 'routes': {'1002_0'}, 'services': {'1002'}},
            'BSE': {'stop_code': float('nan'), 'name': 'Bus Stop snap to edge', 'lat': 51.5226864,
                    'lon': -0.14136210000000002,
                    'wheelchair_boarding': float('nan'), 'stop_timezone': float('nan'), 'location_type': 0.0,
                    'parent_station': '210G433',
                    'platform_code': float('nan'), 'id': 'BSE', 'x': -0.14136210000000002, 'y': 51.5226864,
                    'epsg': 'epsg:4326',
                    's2_id': 5221390325135889957, 'routes': {'1001_0'}, 'services': {'1001'}}}


@pytest.fixture()
def correct_schedule_graph_edges_from_test_gtfs():
    return {'BSN': {}, 'RSE': {}, 'RSN': {'RSE': {'routes': {'1002_0'}, 'services': {'1002'}}},
            'BSE': {'BSN': {'routes': {'1001_0'}, 'services': {'1001'}}}}


@pytest.fixture()
def correct_schedule_graph_data_from_test_gtfs():
    return {'name': 'Schedule graph', 'crs': {'init': 'epsg:4326'},
            'route_to_service_map': {'1001_0': '1001', '1002_0': '1002'},
            'service_to_route_map': {'1001': ['1001_0'], '1002': ['1002_0']}, 'change_log': change_log.ChangeLog(),
            'routes': {'1001_0': {'arrival_offsets': ['00:00:00', '00:02:00'], 'route_color': 'CE312D',
                                  'ordered_stops': ['BSE', 'BSN'], 'mode': 'bus', 'route_type': 3,
                                  'departure_offsets': ['00:00:00', '00:02:00'],
                                  'route_long_name': 'Bus Test Route', 'route_short_name': 'BTR',
                                  'trips': {'trip_id': ['BT1'], 'trip_departure_time': ['03:21:00'],
                                            'vehicle_id': ['veh_0']}, 'service_id': '1001', 'id': '1001_0'},
                       '1002_0': {'arrival_offsets': ['00:00:00', '00:02:00'], 'route_color': 'CE312D',
                                  'ordered_stops': ['RSN', 'RSE'], 'mode': 'rail', 'route_type': 2,
                                  'departure_offsets': ['00:00:00', '00:02:00'],
                                  'route_long_name': 'Rail Test Route', 'route_short_name': 'RTR',
                                  'trips': {'trip_id': ['RT1'], 'trip_departure_time': ['03:21:00'],
                                            'vehicle_id': ['veh_1']}, 'service_id': '1002',
                                  'id': '1002_0'}},
            'services': {'1001': {'id': '1001', 'name': 'BTR'}, '1002': {'id': '1002', 'name': 'RTR'}}}


@pytest.fixture()
def correct_stops_to_service_mapping_from_test_gtfs():
    return {'BSN': {'1001'}, 'BSE': {'1001'}, 'RSE': {'1002'}, 'RSN': {'1002'}}


@pytest.fixture()
def correct_stops_to_route_mapping_from_test_gtfs():
    return {'BSE': {'1001_0'}, 'BSN': {'1001_0'}, 'RSE': {'1002_0'}, 'RSN': {'1002_0'}}


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
            trips={
                'trip_id': ['VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00'],
                'trip_departure_time': ['04:40:00'],
                'vehicle_id': ['veh_bus_1']
            },
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
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "genet", "configs", "OSM", "default_config.yml"))


@pytest.fixture()
def full_fat_default_config():
    return osm_reader.Config(
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "genet", "configs", "OSM", "default_config.yml")))


@pytest.fixture()
def slim_default_config_path():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "genet", "configs", "OSM", "slim_config.yml"))


@pytest.fixture()
def slim_default_config():
    return osm_reader.Config(
        os.path.join(os.path.dirname(__file__), "..", "genet", "configs", "OSM", "slim_config.yml"))


###########################################################
# vehicle types configs
###########################################################

@pytest.fixture()
def vehicle_definitions_config_path():
    return os.path.abspath(os.path.join(os.path.dirname(__file__),
                                        "..", "genet", "configs", "vehicles", "vehicle_definitions.yml"))
