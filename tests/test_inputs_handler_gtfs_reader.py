import json
import os
import sys
from tests.fixtures import *
from genet.inputs_handler import gtfs_reader

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
gtfs_test_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_data", "gtfs"))
gtfs_test_zip_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_data", "gtfs.zip"))


@pytest.fixture()
def correct_schedule_dict_from_test_gtfs():
    return {'1001': [
        {'route_short_name': 'BTR', 'route_long_name': 'Bus Test Route', 'mode': 'bus', 'route_color': '#CE312D',
         'trips': {'BT1': '03:21:00'}, 'stops': ['BSE', 'BSN'], 'arrival_offsets': ['0:00:00', '0:02:00'],
         'departure_offsets': ['0:00:00', '0:02:00'], 's2_stops': [5221390325135889957, 5221390684150342605]}],
            '1002': [{'route_short_name': 'RTR', 'route_long_name': 'Rail Test Route', 'mode': 'rail',
                      'route_color': '#CE312D', 'trips': {'RT1': '03:21:00'}, 'stops': ['RSN', 'RSE'],
                      'arrival_offsets': ['0:00:00', '0:02:00'], 'departure_offsets': ['0:00:00', '0:02:00'],
                      's2_stops': [5221390332291192399, 5221390324026756531]}]}


@pytest.fixture()
def correct_stopdb_from_test_gtfs():
    return {'BSE': {'stop_id': 'BSE', 'stop_code': '', 'stop_name': 'Bus Stop snap to edge', 'stop_lat': '51.5226864',
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


def test_read_services_from_calendar_correct():
    services = gtfs_reader.read_services_from_calendar(gtfs_test_file, '20190604')
    assert services == ['6630', '6631']


def test_read_gtfs_to_db_like_tables_correct(correct_stop_times, correct_stop_times_db, correct_stops_db,
                                             correct_trips_db, correct_routes_db):
    stop_times, stop_times_db, stops_db, trips_db, routes_db = gtfs_reader.read_gtfs_to_db_like_tables(gtfs_test_file)

    assert stop_times == correct_stop_times
    assert stop_times_db == correct_stop_times_db
    assert stops_db == correct_stops_db
    assert trips_db == correct_trips_db
    assert routes_db == correct_routes_db


def test_get_mode_returns_mode_if_given_int():
    assert gtfs_reader.get_mode(3) == 'bus'


def test_get_mode_returns_mode_if_given_str():
    assert gtfs_reader.get_mode('3') == 'bus'


def test_get_mode_returns_other_if_doesnt_recognise():
    assert gtfs_reader.get_mode('99999999') == 'other'


def test_parse_db_to_schedule_dict_correct(correct_schedule_dict, correct_stop_times_db, correct_stops_db,
                                           correct_trips_db, correct_routes_db):
    schedule = gtfs_reader.parse_db_to_schedule_dict(stop_times_db=correct_stop_times_db, stops_db=correct_stops_db,
                                                     trips_db=correct_trips_db, route_db=correct_routes_db,
                                                     services=['6630', '6631'])

    assert_semantically_equal(schedule, correct_schedule_dict)


def test_read_to_schedule_correct(correct_schedule_dict_from_test_gtfs, correct_stopdb_from_test_gtfs):
    schedule, stops_db = gtfs_reader.read_to_dict_schedule_and_stopd_db(gtfs_test_file, '20190604')

    assert_semantically_equal(schedule, correct_schedule_dict_from_test_gtfs)
    assert_semantically_equal(stops_db, correct_stopdb_from_test_gtfs)


def test_zip_read_to_schedule_correct(correct_schedule_dict_from_test_gtfs, correct_stopdb_from_test_gtfs):
    schedule, stops_db = gtfs_reader.read_to_dict_schedule_and_stopd_db(gtfs_test_zip_file, '20190604')

    assert_semantically_equal(schedule, correct_schedule_dict_from_test_gtfs)
    assert_semantically_equal(stops_db, correct_stopdb_from_test_gtfs)
