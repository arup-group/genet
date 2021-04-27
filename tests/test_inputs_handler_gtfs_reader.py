import json
import os
import sys
from pandas.testing import assert_frame_equal
from tests.fixtures import *
from genet.inputs_handler import gtfs_reader

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
gtfs_test_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_data", "gtfs"))
gtfs_test_zip_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_data", "gtfs.zip"))


def test_read_services_from_calendar_correct():
    services = gtfs_reader.read_services_from_calendar(gtfs_test_file, '20190604')
    assert services == ['6630', '6631']


def test_read_gtfs_to_db_like_tables_correct(correct_stop_times_db, correct_stops_db, correct_trips_db, correct_routes_db):
    stop_times_db, stops_db, trips_db, routes_db = gtfs_reader.read_gtfs_to_db_like_tables(gtfs_test_file)

    assert_frame_equal(stop_times_db, correct_stop_times_db)
    assert_frame_equal(stops_db, correct_stops_db)
    assert_frame_equal(trips_db, correct_trips_db)
    assert_frame_equal(routes_db, correct_routes_db)


def test_get_mode_returns_mode_if_given_int():
    assert gtfs_reader.get_mode(3) == 'bus'


def test_get_mode_returns_mode_if_given_str():
    assert gtfs_reader.get_mode('3') == 'bus'


def test_get_mode_returns_other_if_doesnt_recognise():
    assert gtfs_reader.get_mode('99999999') == 'other'


def test_read_to_schedule_correct(correct_schedule_graph_nodes_from_test_gtfs,
                                  correct_schedule_graph_edges_from_test_gtfs,
                                  correct_schedule_graph_data_from_test_gtfs):
    schedule_graph = gtfs_reader.read_gtfs_to_schedule_graph(gtfs_test_file, '20190604')
    assert_semantically_equal(dict(schedule_graph.nodes(data=True)), correct_schedule_graph_nodes_from_test_gtfs)
    assert_semantically_equal(schedule_graph.edges._adjdict, correct_schedule_graph_edges_from_test_gtfs)
    del schedule_graph.graph['change_log']
    del correct_schedule_graph_data_from_test_gtfs['change_log']
    assert_semantically_equal(schedule_graph.graph, correct_schedule_graph_data_from_test_gtfs)


def test_zip_read_to_schedule_correct(correct_schedule_graph_nodes_from_test_gtfs,
                                      correct_schedule_graph_edges_from_test_gtfs,
                                      correct_schedule_graph_data_from_test_gtfs):
    schedule_graph = gtfs_reader.read_gtfs_to_schedule_graph(gtfs_test_file, '20190604')
    assert_semantically_equal(dict(schedule_graph.nodes(data=True)), correct_schedule_graph_nodes_from_test_gtfs)
    assert_semantically_equal(schedule_graph.edges._adjdict, correct_schedule_graph_edges_from_test_gtfs)
    del schedule_graph.graph['change_log']
    del correct_schedule_graph_data_from_test_gtfs['change_log']
    assert_semantically_equal(schedule_graph.graph, correct_schedule_graph_data_from_test_gtfs)


def test_reading_loopy_gtfs_removes_duplicated_stops():
    schedule_graph = gtfs_reader.read_gtfs_to_schedule_graph(
         os.path.abspath(os.path.join(os.path.dirname(__file__), "test_data", "loopy_gtfs")),
        '20190604')
    assert schedule_graph.graph['routes']['1001_0']['ordered_stops'] == ['BSE', 'BSN', 'BSE', 'BSN']
