import json
import os
import sys
from pandas import DataFrame
from pandas.testing import assert_frame_equal
from genet.inputs_handler import gtfs_reader
from tests.fixtures import *

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

def test_read_gtfs_calendar_with_spaces_fills_in_with_character():
    services = gtfs_reader.read_services_from_calendar(
        os.path.abspath(os.path.join(os.path.dirname(__file__), "test_data", "gtfs_with_spaces")),
        '20190604')
    assert services == ['663_0', '663_1']

def test_read_gtfs_with_spaces_fills_in_with_character():
    stop_times_db, stops_db, trips_db, routes_db = gtfs_reader.read_gtfs_to_db_like_tables(
        os.path.abspath(os.path.join(os.path.dirname(__file__), "test_data", "gtfs_with_spaces"))
    )

    assert_frame_equal(
        stop_times_db,
        DataFrame(
            {'trip_id': {0: 'BT_1', 1: 'BT_1', 2: 'RT_1', 3: 'RT_1'},
             'arrival_time': {0: '03:21:00', 1: '03:23:00', 2: '03:21:00', 3: '03:23:00'},
             'departure_time': {0: '03:21:00', 1: '03:23:00', 2: '03:21:00', 3: '03:23:00'},
             'stop_id': {0: 'BS_E', 1: 'BS_N', 2: 'RS_N', 3: 'RS_E'}, 'stop_sequence': {0: 0, 1: 1, 2: 0, 3: 1},
             'stop_headsign': {0: float('nan'), 1: float('nan'), 2: float('nan'), 3: float('nan')},
             'pickup_type': {0: 0, 1: 0, 2: 0, 3: 0},
             'drop_off_type': {0: 1, 1: 0, 2: 0, 3: 1}, 'timepoint': {0: 1, 1: 0, 2: 0, 3: 1},
             'stop_direction_name': {0: float('nan'), 1: float('nan'), 2: float('nan'), 3: float('nan')}}
        )
    )
    assert_frame_equal(
        stops_db,
        DataFrame(
            {'stop_id': {0: 'BS_E', 1: 'BS_N', 2: 'RS_E', 3: 'RS_N'},
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
    )
    assert_frame_equal(
        trips_db,
        DataFrame(
            {'route_id': {0: '100_1', 1: '100_2'}, 'service_id': {0: '663_0', 1: '663_1'},
             'trip_id': {0: 'BT_1', 1: 'RT_1'}, 'trip_headsign': {0: 'Bus Test trip', 1: 'Rail Test trip'},
             'block_id': {0: float('nan'), 1: float('nan')}, 'wheelchair_accessible': {0: 0, 1: 0},
             'trip_direction_name': {0: float('nan'), 1: float('nan')},
             'exceptional': {0: float('nan'), 1: float('nan')}}
        )
    )
    assert_frame_equal(
        routes_db,
        DataFrame(
            {'route_id': {0: '100_1', 1: '100_2'}, 'agency_id': {0: 'OP550', 1: 'OP550'},
             'route_short_name': {0: 'BTR', 1: 'RTR'}, 'route_long_name': {0: 'Bus Test Route', 1: 'Rail Test Route'},
             'route_type': {0: 3, 1: 2}, 'route_url': {0: float('nan'), 1: float('nan')},
             'route_color': {0: 'CE312D', 1: 'CE312D'},
             'route_text_color': {0: 'FFFFFF', 1: 'FFFFFF'},
             'checkin_duration': {0: float('nan'), 1: float('nan')}}
        )
    )


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
