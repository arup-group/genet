import pytest
import itertools
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


def test_generating_edge_vph_geodataframe(schedule):
    nodes, links = gngeojson.generate_geodataframes(schedule.graph())
    df = schedule.generate_trips_dataframe()
    df = use_schedule.generate_edge_vph_geodataframe(df, links)

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
                               'route_name': {0: 1, 1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 1, 8: 1, 9: 1, 10: 1, 11: 1},
                               'from_stop_name': {0: 1, 1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 1, 8: 1, 9: 1, 10: 1,
                                                  11: 1},
                               'to_stop_name': {0: 1, 1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 1, 8: 1, 9: 1, 10: 1,
                                                11: 1},
                               'service_name': {0: 1, 1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 1, 8: 1, 9: 1, 10: 1,
                                                11: 1},
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
                                                   (-7.557121424907424, 49.76683608549253)])}})

    assert_geodataframe_equal(df, correct_df, check_less_precise=True)


def test_generating_edge_vph_geodataframe_for_service(schedule):
    nodes, links = gngeojson.generate_geodataframes(schedule['service'].graph())
    df = schedule['service'].generate_trips_dataframe()
    df = use_schedule.generate_edge_vph_geodataframe(df, links)

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
                               'route_name': {0: 1, 1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 1, 8: 1, 9: 1, 10: 1, 11: 1},
                               'from_stop_name': {0: 1, 1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 1, 8: 1, 9: 1, 10: 1,
                                                  11: 1},
                               'to_stop_name': {0: 1, 1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 1, 8: 1, 9: 1, 10: 1,
                                                11: 1},
                               'service_name': {0: 1, 1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 1, 8: 1, 9: 1, 10: 1,
                                                11: 1},
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
                                                   (-7.557121424907424, 49.76683608549253)])}})

    assert_geodataframe_equal(df, correct_df, check_less_precise=True)


def test_generating_edge_vph_geodataframe_for_route(schedule):
    nodes, links = gngeojson.generate_geodataframes(schedule.route('2').graph())
    df = schedule.route('2').generate_trips_dataframe()
    df = use_schedule.generate_edge_vph_geodataframe(df, links)

    correct_df = GeoDataFrame({'hour': {0: Timestamp('1970-01-01 17:00:00'), 1: Timestamp('1970-01-01 19:00:00'),
                                        2: Timestamp('1970-01-01 17:00:00'), 3: Timestamp('1970-01-01 19:00:00'),
                                        4: Timestamp('1970-01-01 17:00:00'), 5: Timestamp('1970-01-01 18:00:00')},
                               'from_stop': {0: '2', 1: '2', 2: '3', 3: '3', 4: '4', 5: '4'},
                               'to_stop': {0: '1', 1: '1', 2: '2', 3: '2', 4: '3', 5: '3'},
                               'route_name': {0: 1, 1: 1, 2: 1, 3: 1, 4: 1, 5: 1},
                               'from_stop_name': {0: 1, 1: 1, 2: 1, 3: 1, 4: 1, 5: 1},
                               'to_stop_name': {0: 1, 1: 1, 2: 1, 3: 1, 4: 1, 5: 1},
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
                                                           (-7.557121424907424, 49.76683608549253)])}})

    assert_geodataframe_equal(df, correct_df, check_less_precise=True)


def test_generating_trips_per_day_per_service(schedule):
    df_trips = use_schedule.trips_per_day_per_service(schedule.generate_trips_dataframe())

    correct_df = DataFrame(
        {'service': {0: 'service'},
         'service_name': {0: 'name'},
         'mode': {0: 'bus'},
         'number_of_trips': {0: 4}})

    assert_frame_equal(df_trips, correct_df)


def test_generating_trips_per_day_per_route(schedule):
    df_trips = use_schedule.trips_per_day_per_route(schedule.generate_trips_dataframe())

    correct_df = DataFrame(
        {'route': {0: '1', 1: '2'},
         'route_name': {0: 'name', 1: 'name_2'},
         'mode': {0: 'bus', 1: 'bus'},
         'number_of_trips': {0: 2, 1: 2}})

    assert_frame_equal(df_trips, correct_df)


@pytest.fixture()
def schedule_with_a_couple_services_that_overlap_stations():
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
                    stops=[Stop(id='04', x=7, y=5, epsg='epsg:27700'),
                           Stop(id='03', x=3, y=3, epsg='epsg:27700', name='Stop_3'),
                           Stop(id='02', x=1, y=2, epsg='epsg:27700', name='Stop_2'),
                           Stop(id='01', x=4, y=2, epsg='epsg:27700', name='Stop_1')],
                    trips={'1': '17:00:00', '2': '18:30:00'},
                    arrival_offsets=['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                    departure_offsets=['00:00:00', '00:05:00', '00:09:00', '00:15:00'])
    service = Service(id='service', routes=[route_1, route_2])

    route_11 = Route(route_short_name='name',
                     mode='bus', id='11',
                     stops=[Stop(id='1', x=4, y=2, epsg='epsg:27700', name='Stop_1'),
                            Stop(id='2', x=1, y=2, epsg='epsg:27700', name='Stop_2'),
                            Stop(id='3', x=3, y=3, epsg='epsg:27700', name='Stop_3'),
                            Stop(id='4', x=7, y=5, epsg='epsg:27700')],
                     trips={'1': '17:00:00'},
                     arrival_offsets=['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                     departure_offsets=['00:00:00', '00:05:00', '00:09:00', '00:15:00'])
    route_12 = Route(route_short_name='name_2',
                     mode='bus', id='012',
                     stops=[Stop(id='04', x=7, y=5, epsg='epsg:27700'),
                            Stop(id='03', x=3, y=3, epsg='epsg:27700', name='Stop_3'),
                            Stop(id='02', x=1, y=2, epsg='epsg:27700', name='Stop_2'),
                            Stop(id='01', x=4, y=2, epsg='epsg:27700', name='Stop_1')],
                     trips={'1': '17:00:00'},
                     arrival_offsets=['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                     departure_offsets=['00:00:00', '00:05:00', '00:09:00', '00:15:00'])
    service_2 = Service(id='service_2', routes=[route_11, route_12])

    return Schedule(epsg='epsg:27700', services=[service, service_2])


def test_aggregating_trips_per_day_per_route_by_end_stop_pairs(schedule_with_a_couple_services_that_overlap_stations,
                                                               mocker):
    mocker.patch.object(itertools, 'combinations',
                        return_value=[('01', '4'), ('01', '04'), ('01', '1'), ('4', '04'), ('4', '1'), ('04', '1')])

    trips_per_day_per_route = use_schedule.trips_per_day_per_route(
        schedule_with_a_couple_services_that_overlap_stations.generate_trips_dataframe())

    df = use_schedule.aggregate_trips_per_day_per_route_by_end_stop_pairs(
        schedule_with_a_couple_services_that_overlap_stations, trips_per_day_per_route)

    assert_frame_equal(df,
                       DataFrame(
                           {'station_A': {1: '01', 4: '4'}, 'station_B': {1: '04', 4: '1'},
                            'station_A_name': {1: 'Stop_1', 4: ''}, 'station_B_name': {1: '', 4: 'Stop_1'},
                            'mode': {1: 'bus', 4: 'bus'}, 'routes_in_common': {1: {'2', '012'}, 4: {'11', '1'}},
                            'number_of_trips': {1: 3, 4: 3}}
                       ))


def test_aggregating_further_by_station_name():
    df = DataFrame(
        {'station_A': {0: '4', 5: '01'}, 'station_B': {0: '1', 5: '04'}, 'station_A_name': {0: 'Stop_4', 5: 'Stop_1'},
         'station_B_name': {0: 'Stop_1', 5: 'Stop_4'}, 'mode': {0: 'bus', 5: 'bus'},
         'routes_in_common': {0: {'11', '1'}, 5: {'012', '2'}}, 'number_of_trips': {0: 3, 5: 3}})

    aggregated = use_schedule.aggregate_by_stop_names(df)

    assert_frame_equal(aggregated, DataFrame(
        {'station_A_name': {0: 'Stop_1'}, 'station_B_name': {0: 'Stop_4'}, 'mode': {0: 'bus'},
         'number_of_trips': {0: 6}}))


def test_aggregating_further_by_station_name_with_missing_names():
    df = DataFrame(
        {'station_A': {0: '4', 5: '01'}, 'station_B': {0: '1', 5: '04'}, 'station_A_name': {0: '', 5: 'Stop_1'},
         'station_B_name': {0: 'Stop_1', 5: ''}, 'mode': {0: 'bus', 5: 'bus'},
         'routes_in_common': {0: {'11', '1'}, 5: {'012', '2'}}, 'number_of_trips': {0: 3, 5: 3}})

    aggregated = use_schedule.aggregate_by_stop_names(df)

    assert aggregated.empty


def test_aggregating_trips_per_day_per_route_by_end_stop_pairs_with_different_modes():
    df = DataFrame(
        {'station_A': {0: '4', 1: '01', 2: 'a', 3: 'b'},
         'station_B': {0: '1', 1: '04', 2: 'b', 3: 'a'},
         'station_A_name': {0: 'Stop_4', 1: 'Stop_1', 2: 'A', 3: 'B'},
         'station_B_name': {0: 'Stop_1', 1: 'Stop_4', 2: 'B', 3: 'A'},
         'mode': {0: 'bus', 1: 'bus', 2: 'rail', 3: 'horse'},
         'routes_in_common': {0: {'11', '1'}, 1: {'012', '2'}, 2: {'lol'}, 3: {''}},
         'number_of_trips': {0: 3, 1: 3, 2: 4, 3: 10}})

    aggregated = use_schedule.aggregate_by_stop_names(df)

    assert_frame_equal(aggregated, DataFrame(
        {'station_A_name': {0: 'A', 1: 'A', 2: 'Stop_1'},
         'station_B_name': {0: 'B', 1: 'B', 2: 'Stop_4'},
         'mode': {0: 'horse', 1: 'rail', 2: 'bus'},
         'number_of_trips': {0: 10, 1: 4, 2: 6}}))
