import json
import os
import sys
from tests.fixtures import *
from genet.inputs_handler import gtfs_reader

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


def test_read_to_schedule_correct(correct_services_from_test_gtfs):
    services = gtfs_reader.read_to_dict_schedule_and_stopd_db(gtfs_test_file, '20190604')

    assert services == correct_services_from_test_gtfs


def test_zip_read_to_schedule_correct(correct_services_from_test_gtfs):
    services = gtfs_reader.read_to_dict_schedule_and_stopd_db(gtfs_test_zip_file, '20190604')

    assert services == correct_services_from_test_gtfs
