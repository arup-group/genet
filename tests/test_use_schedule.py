import pytest
from datetime import datetime, timedelta
from pandas.testing import assert_frame_equal
from shapely.geometry import LineString
from pandas import DataFrame, Timestamp
from geopandas import GeoDataFrame
from geopandas.testing import assert_geodataframe_equal
from genet import Stop, Route, Service, Schedule
import genet.use.schedule as use_schedule
from genet.outputs_handler import geojson as gngeojson


@pytest.fixture()
def schedule():
    route_1 = Route(route_short_name='name',
                    mode='bus', id='1',
                    stops=[Stop(id='1', x=4, y=2, epsg='epsg:27700', name='Stop_1'),
                           Stop(id='2', x=1, y=2, epsg='epsg:27700', name='Stop_2'),
                           Stop(id='3', x=3, y=3, epsg='epsg:27700', name='Stop_3'),
                           Stop(id='4', x=7, y=5, epsg='epsg:27700')],
                    trips={'1': '17:00:00', '2': '18:30:00'},
                    arrival_offsets=['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                    departure_offsets=['00:00:00', '00:05:00', '00:09:00', '00:15:00'])
    route_2 = Route(route_short_name='name_2',
                    mode='bus', id='2',
                    stops=[Stop(id='4', x=7, y=5, epsg='epsg:27700'),
                           Stop(id='3', x=3, y=3, epsg='epsg:27700', name='Stop_3'),
                           Stop(id='2', x=1, y=2, epsg='epsg:27700', name='Stop_2'),
                           Stop(id='1', x=4, y=2, epsg='epsg:27700', name='Stop_1')],
                    trips={'1': '17:00:00', '2': '18:30:00'},
                    arrival_offsets=['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                    departure_offsets=['00:00:00', '00:05:00', '00:09:00', '00:15:00'])
    service = Service(id='service', routes=[route_1, route_2])
    return Schedule(epsg='epsg:27700', services=[service])


def test_sanitising_time_with_default_day():
    t = use_schedule.sanitise_time('12:46:20')
    assert t == datetime(year=1970, month=1, day=1, hour=12, minute=46, second=20)


def test_sanitising_time_going_over_24_hrs():
    t = use_schedule.sanitise_time('25:46:20')
    assert t == datetime(year=1970, month=1, day=2, hour=1, minute=46, second=20)


def test_sanitising_time_with_non_default_day():
    t = use_schedule.sanitise_time('15:46:20', gtfs_day='20200401')
    assert t == datetime(year=2020, month=4, day=1, hour=15, minute=46, second=20)


def test_offsets():
    t = use_schedule.get_offset('00:06:20')
    assert t == timedelta(minutes=6, seconds=20)


def test_offsets_going_over_24_hrs_why_not():
    t = use_schedule.get_offset('25:06:20')
    assert t == timedelta(hours=25, minutes=6, seconds=20)


def test_generating_trips_geodataframe_for_schedule(schedule):
    df = use_schedule.generate_trips_dataframe(schedule)

    correct_df = DataFrame({'departure_time': {0: Timestamp('1970-01-01 17:00:00'), 1: Timestamp('1970-01-01 17:05:00'),
                                               2: Timestamp('1970-01-01 17:09:00'), 3: Timestamp('1970-01-01 18:30:00'),
                                               4: Timestamp('1970-01-01 18:35:00'), 5: Timestamp('1970-01-01 18:39:00'),
                                               6: Timestamp('1970-01-01 17:00:00'), 7: Timestamp('1970-01-01 17:05:00'),
                                               8: Timestamp('1970-01-01 17:09:00'), 9: Timestamp('1970-01-01 18:30:00'),
                                               10: Timestamp('1970-01-01 18:35:00'),
                                               11: Timestamp('1970-01-01 18:39:00')},
                            'arrival_time': {0: Timestamp('1970-01-01 17:03:00'), 1: Timestamp('1970-01-01 17:07:00'),
                                             2: Timestamp('1970-01-01 17:13:00'), 3: Timestamp('1970-01-01 18:33:00'),
                                             4: Timestamp('1970-01-01 18:37:00'), 5: Timestamp('1970-01-01 18:43:00'),
                                             6: Timestamp('1970-01-01 17:03:00'), 7: Timestamp('1970-01-01 17:07:00'),
                                             8: Timestamp('1970-01-01 17:13:00'), 9: Timestamp('1970-01-01 18:33:00'),
                                             10: Timestamp('1970-01-01 18:37:00'),
                                             11: Timestamp('1970-01-01 18:43:00')},
                            'from_stop': {0: '1', 1: '2', 2: '3', 3: '1', 4: '2', 5: '3', 6: '4', 7: '3', 8: '2',
                                          9: '4', 10: '3', 11: '2'},
                            'to_stop': {0: '2', 1: '3', 2: '4', 3: '2', 4: '3', 5: '4', 6: '3', 7: '2', 8: '1', 9: '3',
                                        10: '2', 11: '1'},
                            'trip': {0: '1', 1: '1', 2: '1', 3: '2', 4: '2', 5: '2', 6: '1', 7: '1', 8: '1', 9: '2',
                                     10: '2', 11: '2'},
                            'route': {0: '1', 1: '1', 2: '1', 3: '1', 4: '1', 5: '1', 6: '2', 7: '2', 8: '2', 9: '2',
                                      10: '2', 11: '2'},
                            'service': {0: 'service', 1: 'service', 2: 'service', 3: 'service', 4: 'service',
                                        5: 'service', 6: 'service', 7: 'service', 8: 'service', 9: 'service',
                                        10: 'service', 11: 'service'},
                            'mode': {0: 'bus', 1: 'bus', 2: 'bus', 3: 'bus', 4: 'bus', 5: 'bus', 6: 'bus', 7: 'bus',
                                     8: 'bus', 9: 'bus', 10: 'bus', 11: 'bus'}})

    assert_frame_equal(df, correct_df)


def test_generating_trips_geodataframe_for_selected_route_ids_in_schedule(schedule):
    df = use_schedule.generate_trips_dataframe(schedule, route_ids=['2'])

    correct_df = DataFrame({'departure_time': {0: Timestamp('1970-01-01 17:00:00'), 1: Timestamp('1970-01-01 17:05:00'),
                                               2: Timestamp('1970-01-01 17:09:00'), 3: Timestamp('1970-01-01 18:30:00'),
                                               4: Timestamp('1970-01-01 18:35:00'),
                                               5: Timestamp('1970-01-01 18:39:00')},
                            'arrival_time': {0: Timestamp('1970-01-01 17:03:00'), 1: Timestamp('1970-01-01 17:07:00'),
                                             2: Timestamp('1970-01-01 17:13:00'), 3: Timestamp('1970-01-01 18:33:00'),
                                             4: Timestamp('1970-01-01 18:37:00'), 5: Timestamp('1970-01-01 18:43:00')},
                            'from_stop': {0: '4', 1: '3', 2: '2', 3: '4', 4: '3', 5: '2'},
                            'to_stop': {0: '3', 1: '2', 2: '1', 3: '3', 4: '2', 5: '1'},
                            'trip': {0: '1', 1: '1', 2: '1', 3: '2', 4: '2', 5: '2'},
                            'route': {0: '2', 1: '2', 2: '2', 3: '2', 4: '2', 5: '2'},
                            'service': {0: 'service', 1: 'service', 2: 'service', 3: 'service', 4: 'service',
                                        5: 'service'},
                            'mode': {0: 'bus', 1: 'bus', 2: 'bus', 3: 'bus', 4: 'bus', 5: 'bus'}})

    assert_frame_equal(df, correct_df)


def test_generating_edge_vph_geodataframe(schedule):
    nodes, links = gngeojson.generate_geodataframes(schedule.graph())
    df = use_schedule.generate_trips_dataframe(schedule)
    df = use_schedule.generate_edge_vph_geodataframe(df, nodes, links)

    correct_df = GeoDataFrame({'hour': {0: Timestamp('1970-01-01 17:00:00'), 1: Timestamp('1970-01-01 18:00:00'),
                                        2: Timestamp('1970-01-01 17:00:00'), 3: Timestamp('1970-01-01 19:00:00'),
                                        4: Timestamp('1970-01-01 17:00:00'), 5: Timestamp('1970-01-01 19:00:00'),
                                        6: Timestamp('1970-01-01 17:00:00'), 7: Timestamp('1970-01-01 19:00:00'),
                                        8: Timestamp('1970-01-01 17:00:00'), 9: Timestamp('1970-01-01 19:00:00'),
                                        10: Timestamp('1970-01-01 17:00:00'), 11: Timestamp('1970-01-01 18:00:00')},
                               'from_stop': {0: '1', 1: '1', 2: '2', 3: '2', 4: '2', 5: '2', 6: '3', 7: '3', 8: '3',
                                             9: '3', 10: '4', 11: '4'},
                               'to_stop': {0: '2', 1: '2', 2: '1', 3: '1', 4: '3', 5: '3', 6: '2', 7: '2', 8: '4',
                                           9: '4',
                                           10: '3', 11: '3'},
                               'vph': {0: 1, 1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 1, 8: 1, 9: 1, 10: 1, 11: 1},
                               'geometry': {
                                   0: LineString([(-7.557106577683727, 49.76682779861249),
                                                  (-7.557148039524952, 49.766825803756994)]),
                                   1: LineString([(-7.557106577683727, 49.76682779861249),
                                                  (-7.557148039524952, 49.766825803756994)]),
                                   2: LineString([(-7.557148039524952, 49.766825803756994),
                                                  (-7.557106577683727, 49.76682779861249)]),
                                   3: LineString([(-7.557148039524952, 49.766825803756994),
                                                  (-7.557106577683727, 49.76682779861249)]),
                                   4: LineString([(-7.557148039524952, 49.766825803756994),
                                                  (-7.557121424907424, 49.76683608549253)]),
                                   5: LineString([(-7.557148039524952, 49.766825803756994),
                                                  (-7.557121424907424, 49.76683608549253)]),
                                   6: LineString([(-7.557121424907424, 49.76683608549253),
                                                  (-7.557148039524952, 49.766825803756994)]),
                                   7: LineString([(-7.557121424907424, 49.76683608549253),
                                                  (-7.557148039524952, 49.766825803756994)]),
                                   8: LineString([(-7.557121424907424, 49.76683608549253),
                                                  (-7.5570681956375, 49.766856648946295)]),
                                   9: LineString([(-7.557121424907424, 49.76683608549253),
                                                  (-7.5570681956375, 49.766856648946295)]),
                                   10: LineString([(-7.5570681956375, 49.766856648946295),
                                                   (-7.557121424907424, 49.76683608549253)]),
                                   11: LineString([(-7.5570681956375, 49.766856648946295),
                                                   (-7.557121424907424, 49.76683608549253)])},
                               'from_stop_name': {0: 'Stop_1', 1: 'Stop_1', 2: 'Stop_2', 3: 'Stop_2', 4: 'Stop_2',
                                                  5: 'Stop_2',
                                                  6: 'Stop_3', 7: 'Stop_3', 8: 'Stop_3', 9: 'Stop_3', 10: float('nan'),
                                                  11: float('nan')},
                               'to_stop_name': {0: 'Stop_2', 1: 'Stop_2', 2: 'Stop_1', 3: 'Stop_1',
                                                4: 'Stop_3', 5: 'Stop_3', 6: 'Stop_2', 7: 'Stop_2',
                                                8: float('nan'), 9: float('nan'), 10: 'Stop_3', 11: 'Stop_3'}})

    assert_geodataframe_equal(df, correct_df, check_less_precise=True)


def test_generating_trips_geodataframe_for_service(schedule):
    df = use_schedule.generate_trips_dataframe(schedule['service'])

    correct_df = DataFrame({'departure_time': {0: Timestamp('1970-01-01 17:00:00'), 1: Timestamp('1970-01-01 17:05:00'),
                                               2: Timestamp('1970-01-01 17:09:00'), 3: Timestamp('1970-01-01 18:30:00'),
                                               4: Timestamp('1970-01-01 18:35:00'), 5: Timestamp('1970-01-01 18:39:00'),
                                               6: Timestamp('1970-01-01 17:00:00'), 7: Timestamp('1970-01-01 17:05:00'),
                                               8: Timestamp('1970-01-01 17:09:00'), 9: Timestamp('1970-01-01 18:30:00'),
                                               10: Timestamp('1970-01-01 18:35:00'),
                                               11: Timestamp('1970-01-01 18:39:00')},
                            'arrival_time': {0: Timestamp('1970-01-01 17:03:00'), 1: Timestamp('1970-01-01 17:07:00'),
                                             2: Timestamp('1970-01-01 17:13:00'), 3: Timestamp('1970-01-01 18:33:00'),
                                             4: Timestamp('1970-01-01 18:37:00'), 5: Timestamp('1970-01-01 18:43:00'),
                                             6: Timestamp('1970-01-01 17:03:00'), 7: Timestamp('1970-01-01 17:07:00'),
                                             8: Timestamp('1970-01-01 17:13:00'), 9: Timestamp('1970-01-01 18:33:00'),
                                             10: Timestamp('1970-01-01 18:37:00'),
                                             11: Timestamp('1970-01-01 18:43:00')},
                            'from_stop': {0: '1', 1: '2', 2: '3', 3: '1', 4: '2', 5: '3', 6: '4', 7: '3', 8: '2',
                                          9: '4', 10: '3', 11: '2'},
                            'to_stop': {0: '2', 1: '3', 2: '4', 3: '2', 4: '3', 5: '4', 6: '3', 7: '2', 8: '1', 9: '3',
                                        10: '2', 11: '1'},
                            'trip': {0: '1', 1: '1', 2: '1', 3: '2', 4: '2', 5: '2', 6: '1', 7: '1', 8: '1', 9: '2',
                                     10: '2', 11: '2'},
                            'route': {0: '1', 1: '1', 2: '1', 3: '1', 4: '1', 5: '1', 6: '2', 7: '2', 8: '2', 9: '2',
                                      10: '2', 11: '2'},
                            'service': {0: 'service', 1: 'service', 2: 'service', 3: 'service', 4: 'service',
                                        5: 'service', 6: 'service', 7: 'service', 8: 'service', 9: 'service',
                                        10: 'service', 11: 'service'},
                            'mode': {0: 'bus', 1: 'bus', 2: 'bus', 3: 'bus', 4: 'bus', 5: 'bus', 6: 'bus', 7: 'bus',
                                     8: 'bus', 9: 'bus', 10: 'bus', 11: 'bus'}})

    assert_frame_equal(df, correct_df)


def test_generating_trips_geodataframe_for_selected_route_ids_in_service(schedule):
    df = use_schedule.generate_trips_dataframe(schedule['service'], route_ids=['2'])

    correct_df = DataFrame({'departure_time': {0: Timestamp('1970-01-01 17:00:00'), 1: Timestamp('1970-01-01 17:05:00'),
                                               2: Timestamp('1970-01-01 17:09:00'), 3: Timestamp('1970-01-01 18:30:00'),
                                               4: Timestamp('1970-01-01 18:35:00'),
                                               5: Timestamp('1970-01-01 18:39:00')},
                            'arrival_time': {0: Timestamp('1970-01-01 17:03:00'), 1: Timestamp('1970-01-01 17:07:00'),
                                             2: Timestamp('1970-01-01 17:13:00'), 3: Timestamp('1970-01-01 18:33:00'),
                                             4: Timestamp('1970-01-01 18:37:00'), 5: Timestamp('1970-01-01 18:43:00')},
                            'from_stop': {0: '4', 1: '3', 2: '2', 3: '4', 4: '3', 5: '2'},
                            'to_stop': {0: '3', 1: '2', 2: '1', 3: '3', 4: '2', 5: '1'},
                            'trip': {0: '1', 1: '1', 2: '1', 3: '2', 4: '2', 5: '2'},
                            'route': {0: '2', 1: '2', 2: '2', 3: '2', 4: '2', 5: '2'},
                            'service': {0: 'service', 1: 'service', 2: 'service', 3: 'service', 4: 'service',
                                        5: 'service'},
                            'mode': {0: 'bus', 1: 'bus', 2: 'bus', 3: 'bus', 4: 'bus', 5: 'bus'}})

    assert_frame_equal(df, correct_df)


def test_generating_edge_vph_geodataframe_for_service(schedule):
    nodes, links = gngeojson.generate_geodataframes(schedule['service'].graph())
    df = use_schedule.generate_trips_dataframe(schedule['service'])
    df = use_schedule.generate_edge_vph_geodataframe(df, nodes, links)

    correct_df = GeoDataFrame({'hour': {0: Timestamp('1970-01-01 17:00:00'), 1: Timestamp('1970-01-01 18:00:00'),
                                        2: Timestamp('1970-01-01 17:00:00'), 3: Timestamp('1970-01-01 19:00:00'),
                                        4: Timestamp('1970-01-01 17:00:00'), 5: Timestamp('1970-01-01 19:00:00'),
                                        6: Timestamp('1970-01-01 17:00:00'), 7: Timestamp('1970-01-01 19:00:00'),
                                        8: Timestamp('1970-01-01 17:00:00'), 9: Timestamp('1970-01-01 19:00:00'),
                                        10: Timestamp('1970-01-01 17:00:00'), 11: Timestamp('1970-01-01 18:00:00')},
                               'from_stop': {0: '1', 1: '1', 2: '2', 3: '2', 4: '2', 5: '2', 6: '3', 7: '3', 8: '3',
                                             9: '3', 10: '4', 11: '4'},
                               'to_stop': {0: '2', 1: '2', 2: '1', 3: '1', 4: '3', 5: '3', 6: '2', 7: '2', 8: '4',
                                           9: '4',
                                           10: '3', 11: '3'},
                               'vph': {0: 1, 1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 1, 8: 1, 9: 1, 10: 1, 11: 1},
                               'geometry': {
                                   0: LineString([(-7.557106577683727, 49.76682779861249),
                                                  (-7.557148039524952, 49.766825803756994)]),
                                   1: LineString([(-7.557106577683727, 49.76682779861249),
                                                  (-7.557148039524952, 49.766825803756994)]),
                                   2: LineString([(-7.557148039524952, 49.766825803756994),
                                                  (-7.557106577683727, 49.76682779861249)]),
                                   3: LineString([(-7.557148039524952, 49.766825803756994),
                                                  (-7.557106577683727, 49.76682779861249)]),
                                   4: LineString([(-7.557148039524952, 49.766825803756994),
                                                  (-7.557121424907424, 49.76683608549253)]),
                                   5: LineString([(-7.557148039524952, 49.766825803756994),
                                                  (-7.557121424907424, 49.76683608549253)]),
                                   6: LineString([(-7.557121424907424, 49.76683608549253),
                                                  (-7.557148039524952, 49.766825803756994)]),
                                   7: LineString([(-7.557121424907424, 49.76683608549253),
                                                  (-7.557148039524952, 49.766825803756994)]),
                                   8: LineString([(-7.557121424907424, 49.76683608549253),
                                                  (-7.5570681956375, 49.766856648946295)]),
                                   9: LineString([(-7.557121424907424, 49.76683608549253),
                                                  (-7.5570681956375, 49.766856648946295)]),
                                   10: LineString([(-7.5570681956375, 49.766856648946295),
                                                   (-7.557121424907424, 49.76683608549253)]),
                                   11: LineString([(-7.5570681956375, 49.766856648946295),
                                                   (-7.557121424907424, 49.76683608549253)])},
                               'from_stop_name': {0: 'Stop_1', 1: 'Stop_1', 2: 'Stop_2', 3: 'Stop_2', 4: 'Stop_2',
                                                  5: 'Stop_2',
                                                  6: 'Stop_3', 7: 'Stop_3', 8: 'Stop_3', 9: 'Stop_3',
                                                  10: float('nan'),
                                                  11: float('nan')},
                               'to_stop_name': {0: 'Stop_2', 1: 'Stop_2', 2: 'Stop_1', 3: 'Stop_1',
                                                4: 'Stop_3', 5: 'Stop_3', 6: 'Stop_2', 7: 'Stop_2',
                                                8: float('nan'), 9: float('nan'), 10: 'Stop_3', 11: 'Stop_3'}})

    assert_geodataframe_equal(df, correct_df, check_less_precise=True)


def test_generating_trips_geodataframe_for_route(schedule):
    df = use_schedule.generate_trips_dataframe(schedule.route('2'), route_ids=['2'])

    correct_df = DataFrame({'departure_time': {0: Timestamp('1970-01-01 17:00:00'), 1: Timestamp('1970-01-01 17:05:00'),
                                               2: Timestamp('1970-01-01 17:09:00'), 3: Timestamp('1970-01-01 18:30:00'),
                                               4: Timestamp('1970-01-01 18:35:00'),
                                               5: Timestamp('1970-01-01 18:39:00')},
                            'arrival_time': {0: Timestamp('1970-01-01 17:03:00'), 1: Timestamp('1970-01-01 17:07:00'),
                                             2: Timestamp('1970-01-01 17:13:00'), 3: Timestamp('1970-01-01 18:33:00'),
                                             4: Timestamp('1970-01-01 18:37:00'), 5: Timestamp('1970-01-01 18:43:00')},
                            'from_stop': {0: '4', 1: '3', 2: '2', 3: '4', 4: '3', 5: '2'},
                            'to_stop': {0: '3', 1: '2', 2: '1', 3: '3', 4: '2', 5: '1'},
                            'trip': {0: '1', 1: '1', 2: '1', 3: '2', 4: '2', 5: '2'},
                            'route': {0: '2', 1: '2', 2: '2', 3: '2', 4: '2', 5: '2'},
                            'service': {0: None, 1: None, 2: None, 3: None, 4: None,
                                        5: None},
                            'mode': {0: 'bus', 1: 'bus', 2: 'bus', 3: 'bus', 4: 'bus', 5: 'bus'}})

    assert_frame_equal(df, correct_df)


def test_generating_trips_geodataframe_for_route_with_specifying_route_ids(schedule):
    df = use_schedule.generate_trips_dataframe(schedule.route('2'), route_ids=['2'])

    correct_df = DataFrame({'departure_time': {0: Timestamp('1970-01-01 17:00:00'), 1: Timestamp('1970-01-01 17:05:00'),
                                               2: Timestamp('1970-01-01 17:09:00'), 3: Timestamp('1970-01-01 18:30:00'),
                                               4: Timestamp('1970-01-01 18:35:00'),
                                               5: Timestamp('1970-01-01 18:39:00')},
                            'arrival_time': {0: Timestamp('1970-01-01 17:03:00'), 1: Timestamp('1970-01-01 17:07:00'),
                                             2: Timestamp('1970-01-01 17:13:00'), 3: Timestamp('1970-01-01 18:33:00'),
                                             4: Timestamp('1970-01-01 18:37:00'), 5: Timestamp('1970-01-01 18:43:00')},
                            'from_stop': {0: '4', 1: '3', 2: '2', 3: '4', 4: '3', 5: '2'},
                            'to_stop': {0: '3', 1: '2', 2: '1', 3: '3', 4: '2', 5: '1'},
                            'trip': {0: '1', 1: '1', 2: '1', 3: '2', 4: '2', 5: '2'},
                            'route': {0: '2', 1: '2', 2: '2', 3: '2', 4: '2', 5: '2'},
                            'service': {0: None, 1: None, 2: None, 3: None, 4: None,
                                        5: None},
                            'mode': {0: 'bus', 1: 'bus', 2: 'bus', 3: 'bus', 4: 'bus', 5: 'bus'}})

    assert_frame_equal(df, correct_df)


def test_generating_edge_vph_geodataframe_for_route(schedule):
    nodes, links = gngeojson.generate_geodataframes(schedule.route('2').graph())
    df = use_schedule.generate_trips_dataframe(schedule.route('2'))
    df = use_schedule.generate_edge_vph_geodataframe(df, nodes, links)

    correct_df = GeoDataFrame({'hour': {0: Timestamp('1970-01-01 17:00:00'), 1: Timestamp('1970-01-01 19:00:00'),
                                        2: Timestamp('1970-01-01 17:00:00'), 3: Timestamp('1970-01-01 19:00:00'),
                                        4: Timestamp('1970-01-01 17:00:00'), 5: Timestamp('1970-01-01 18:00:00')},
                               'from_stop': {0: '2', 1: '2', 2: '3', 3: '3', 4: '4', 5: '4'},
                               'to_stop': {0: '1', 1: '1', 2: '2', 3: '2', 4: '3', 5: '3'},
                               'vph': {0: 1, 1: 1, 2: 1, 3: 1, 4: 1, 5: 1},
                               'geometry': {0: LineString([(-7.557148039524952, 49.766825803756994),
                                                           (-7.557106577683727, 49.76682779861249)]),
                                            1: LineString([(-7.557148039524952, 49.766825803756994),
                                                           (-7.557106577683727, 49.76682779861249)]),
                                            2: LineString([(-7.557121424907424, 49.76683608549253),
                                                           (-7.557148039524952, 49.766825803756994)]),
                                            3: LineString([(-7.557121424907424, 49.76683608549253),
                                                           (-7.557148039524952, 49.766825803756994)]),
                                            4: LineString([(-7.5570681956375, 49.766856648946295),
                                                           (-7.557121424907424, 49.76683608549253)]),
                                            5: LineString([(-7.5570681956375, 49.766856648946295),
                                                           (-7.557121424907424, 49.76683608549253)])},
                               'from_stop_name': {0: 'Stop_2', 1: 'Stop_2', 2: 'Stop_3', 3: 'Stop_3', 4: float('nan'),
                                                  5: float('nan')},
                               'to_stop_name': {0: 'Stop_1', 1: 'Stop_1', 2: 'Stop_2', 3: 'Stop_2',
                                                4: 'Stop_3', 5: 'Stop_3'}})

    assert_geodataframe_equal(df, correct_df, check_less_precise=True)
