from genet.inputs_handler import gtfs_reader
from tests.fixtures import *

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
gtfs_test_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_data", "gtfs"))
gtfs_test_zip_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_data", "gtfs.zip"))


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

def test_read_gtfs_calendar_with_spaces_fills_in_with_character():
    services = gtfs_reader.read_services_from_calendar(
        os.path.abspath(os.path.join(os.path.dirname(__file__), "test_data", "gtfs_with_spaces")),
        '20190604')
    assert services == ['663_0', '663_1']

def test_read_gtfs_with_spaces_fills_in_with_character():
    stop_times, stop_times_db, stops_db, trips_db, routes_db = gtfs_reader.read_gtfs_to_db_like_tables(
        os.path.abspath(os.path.join(os.path.dirname(__file__), "test_data", "gtfs_with_spaces"))
    )

    assert stop_times == [
        {'trip_id': 'BT_1', 'arrival_time': '03:21:00', 'departure_time': '03:21:00', 'stop_id': 'BS_E',
         'stop_sequence': '0', 'stop_headsign': '', 'pickup_type': '0', 'drop_off_type': '1', 'timepoint': '1',
         'stop_direction_name': ''},
        {'trip_id': 'BT_1', 'arrival_time': '03:23:00', 'departure_time': '03:23:00', 'stop_id': 'BS_N',
         'stop_sequence': '1', 'stop_headsign': '', 'pickup_type': '0', 'drop_off_type': '0', 'timepoint': '0',
         'stop_direction_name': ''},
        {'trip_id': 'RT_1', 'arrival_time': '03:21:00', 'departure_time': '03:21:00', 'stop_id': 'RS_N',
         'stop_sequence': '0', 'stop_headsign': '', 'pickup_type': '0', 'drop_off_type': '0', 'timepoint': '0',
         'stop_direction_name': ''},
        {'trip_id': 'RT_1', 'arrival_time': '03:23:00', 'departure_time': '03:23:00', 'stop_id': 'RS_E',
         'stop_sequence': '1', 'stop_headsign': '', 'pickup_type': '0', 'drop_off_type': '1', 'timepoint': '1',
         'stop_direction_name': ''}]
    assert_semantically_equal(
        stop_times_db,
        {'BT_1': [{'trip_id': 'BT_1', 'arrival_time': '03:21:00', 'departure_time': '03:21:00', 'stop_id': 'BS_E',
                   'stop_sequence': '0', 'stop_headsign': '', 'pickup_type': '0', 'drop_off_type': '1',
                   'timepoint': '1', 'stop_direction_name': ''},
                  {'trip_id': 'BT_1', 'arrival_time': '03:23:00', 'departure_time': '03:23:00', 'stop_id': 'BS_N',
                   'stop_sequence': '1', 'stop_headsign': '', 'pickup_type': '0', 'drop_off_type': '0',
                   'timepoint': '0', 'stop_direction_name': ''}], 'RT_1': [
            {'trip_id': 'RT_1', 'arrival_time': '03:21:00', 'departure_time': '03:21:00', 'stop_id': 'RS_N',
             'stop_sequence': '0', 'stop_headsign': '', 'pickup_type': '0', 'drop_off_type': '0', 'timepoint': '0',
             'stop_direction_name': ''},
            {'trip_id': 'RT_1', 'arrival_time': '03:23:00', 'departure_time': '03:23:00', 'stop_id': 'RS_E',
             'stop_sequence': '1', 'stop_headsign': '', 'pickup_type': '0', 'drop_off_type': '1', 'timepoint': '1',
             'stop_direction_name': ''}]}
    )
    assert_semantically_equal(
        stops_db,
        {'BS_E': {'stop_id': 'BS_E', 'stop_code': '', 'stop_name': 'Bus Stop snap to edge', 'stop_lat': '51.5226864',
                  'stop_lon': '-0.1413621', 'wheelchair_boarding': '', 'stop_timezone': '', 'location_type': '0.0',
                  'parent_station': '210G433', 'platform_code': ''},
         'BS_N': {'stop_id': 'BS_N', 'stop_code': '', 'stop_name': 'Bus Stop snap to node', 'stop_lat': '51.5216199',
                  'stop_lon': '-0.140053', 'wheelchair_boarding': '', 'stop_timezone': '', 'location_type': '0.0',
                  'parent_station': '210G432', 'platform_code': ''},
         'RS_E': {'stop_id': 'RS_E', 'stop_code': '', 'stop_name': 'Rail Stop snap to edge', 'stop_lat': '51.5192615',
                  'stop_lon': '-0.1421595', 'wheelchair_boarding': '', 'stop_timezone': '', 'location_type': '0.0',
                  'parent_station': '210G431', 'platform_code': ''},
         'RS_N': {'stop_id': 'RS_N', 'stop_code': '', 'stop_name': 'Rail Stop snap to node', 'stop_lat': '51.5231335',
                  'stop_lon': '-0.1410946', 'wheelchair_boarding': '', 'stop_timezone': '', 'location_type': '0.0',
                  'parent_station': '210G430', 'platform_code': ''}}
    )
    assert_semantically_equal(
        trips_db,
        {'BT_1': {'route_id': '100_1', 'service_id': '663_0', 'trip_id': 'BT_1', 'trip_headsign': 'Bus Test trip',
                  'block_id': '', 'wheelchair_accessible': '0', 'trip_direction_name': '', 'exceptional': ''},
         'RT_1': {'route_id': '100_2', 'service_id': '663_1', 'trip_id': 'RT_1', 'trip_headsign': 'Rail Test trip',
                  'block_id': '', 'wheelchair_accessible': '0', 'trip_direction_name': '', 'exceptional': ''}}
    )
    assert_semantically_equal(
        routes_db,
        {'100_1': {'route_id': '100_1', 'agency_id': 'OP550', 'route_short_name': 'BTR',
                   'route_long_name': 'Bus Test Route', 'route_type': '3', 'route_url': '', 'route_color': 'CE312D',
                   'route_text_color': 'FFFFFF', 'checkin_duration': ''},
         '100_2': {'route_id': '100_2', 'agency_id': 'OP550', 'route_short_name': 'RTR',
                   'route_long_name': 'Rail Test Route', 'route_type': '2', 'route_url': '', 'route_color': 'CE312D',
                   'route_text_color': 'FFFFFF', 'checkin_duration': ''}}
    )


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
