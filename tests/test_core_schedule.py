import math

from shapely.geometry import Polygon, GeometryCollection, LineString
from pandas import DataFrame, Timestamp, Timedelta
from geopandas import GeoDataFrame
from pandas.testing import assert_frame_equal
from geopandas.testing import assert_geodataframe_equal

from genet.exceptions import ServiceIndexError, ConflictingStopData, InconsistentVehicleModeError
from genet.input import read, matsim_reader, gtfs_reader
from genet.schedule_elements import Schedule, Service, Route, Stop, read_vehicle_types, verify_graph_schema
from genet.utils import plot, spatial
from genet.validate import schedule as schedule_validation
from tests.fixtures import *
from tests.test_core_components_service import service
from tests.test_core_components_route import self_looping_route, route
from tests.test_core_schedule_elements import schedule_graph

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
pt2matsim_schedule_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "schedule.xml"))
pt2matsim_vehicles_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "vehicles.xml"))


@pytest.fixture()
def schedule():
    route_1 = Route(route_short_name='name',
                    mode='bus', id='1',
                    stops=[Stop(id='1', x=4, y=2, epsg='epsg:27700'), Stop(id='2', x=1, y=2, epsg='epsg:27700'),
                           Stop(id='3', x=3, y=3, epsg='epsg:27700'), Stop(id='4', x=7, y=5, epsg='epsg:27700')],
                    trips={'trip_id': ['1', '2'],
                           'trip_departure_time': ['13:00:00', '13:30:00'],
                           'vehicle_id': ['veh_1_bus', 'veh_2_bus']},
                    arrival_offsets=['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                    departure_offsets=['00:00:00', '00:05:00', '00:09:00', '00:15:00'])
    route_2 = Route(route_short_name='name_2',
                    mode='bus', id='2',
                    stops=[Stop(id='5', x=4, y=2, epsg='epsg:27700'), Stop(id='6', x=1, y=2, epsg='epsg:27700'),
                           Stop(id='7', x=3, y=3, epsg='epsg:27700'), Stop(id='8', x=7, y=5, epsg='epsg:27700')],
                    trips={'trip_id': ['1', '2'],
                           'trip_departure_time': ['11:00:00', '13:00:00'],
                           'vehicle_id': ['veh_3_bus', 'veh_4_bus']},
                    arrival_offsets=['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                    departure_offsets=['00:00:00', '00:05:00', '00:09:00', '00:15:00'])
    service = Service(id='service', routes=[route_1, route_2])
    return Schedule(epsg='epsg:27700', services=[service])


@pytest.fixture()
def strongly_connected_schedule():
    route_1 = Route(route_short_name='name',
                    mode='bus',
                    stops=[Stop(id='1', x=4, y=2, epsg='epsg:27700', name='Stop_1'),
                           Stop(id='2', x=1, y=2, epsg='epsg:27700', name='Stop_2'),
                           Stop(id='3', x=3, y=3, epsg='epsg:27700', name='Stop_3'),
                           Stop(id='4', x=7, y=5, epsg='epsg:27700', name='Stop_4'),
                           Stop(id='1', x=4, y=2, epsg='epsg:27700', name='Stop_1')],
                    trips={'trip_id': ['1', '2'], 'trip_departure_time': ['11:00:00', '13:00:00'],
                           'vehicle_id': ['veh_1_bus', 'veh_2_bus']},
                    arrival_offsets=['1', '2'], departure_offsets=['1', '2'],
                    id='1')
    route_2 = Route(route_short_name='name_2',
                    mode='bus',
                    stops=[Stop(id='5', x=4, y=2, epsg='epsg:27700', name='Stop_5'),
                           Stop(id='2', x=1, y=2, epsg='epsg:27700', name='Stop_2'),
                           Stop(id='7', x=3, y=3, epsg='epsg:27700', name='Stop_7'),
                           Stop(id='8', x=7, y=5, epsg='epsg:27700', name='Stop_8'),
                           Stop(id='5', x=4, y=2, epsg='epsg:27700', name='Stop_5')],
                    trips={'trip_id': ['1', '2'], 'trip_departure_time': ['11:00:00', '13:00:00'],
                           'vehicle_id': ['veh_3_bus', 'veh_4_bus']},
                    arrival_offsets=['1', '2', '3', '4', '5'],
                    departure_offsets=['1', '2', '3', '4', '5'],
                    id='2')
    service = Service(id='service', routes=[route_1, route_2])
    return Schedule(epsg='epsg:27700', services=[service])


def test_initiating_schedule(schedule):
    s = schedule
    assert_semantically_equal(dict(s._graph.nodes(data=True)), {
        '5': {'services': {'service'}, 'routes': {'2'}, 'id': '5', 'x': 4.0, 'y': 2.0, 'epsg': 'epsg:27700', 'name': '',
              'lat': 49.76682779861249, 'lon': -7.557106577683727, 's2_id': 5205973754090531959},
        '6': {'services': {'service'}, 'routes': {'2'}, 'id': '6', 'x': 1.0, 'y': 2.0, 'epsg': 'epsg:27700', 'name': '',
              'lat': 49.766825803756994, 'lon': -7.557148039524952, 's2_id': 5205973754090365183},
        '7': {'services': {'service'}, 'routes': {'2'}, 'id': '7', 'x': 3.0, 'y': 3.0, 'epsg': 'epsg:27700', 'name': '',
              'lat': 49.76683608549253, 'lon': -7.557121424907424, 's2_id': 5205973754090203369},
        '8': {'services': {'service'}, 'routes': {'2'}, 'id': '8', 'x': 7.0, 'y': 5.0, 'epsg': 'epsg:27700', 'name': '',
              'lat': 49.766856648946295, 'lon': -7.5570681956375, 's2_id': 5205973754097123809},
        '1': {'services': {'service'}, 'routes': {'1'}, 'id': '1', 'x': 4.0, 'y': 2.0, 'epsg': 'epsg:27700', 'name': '',
              'lat': 49.76682779861249, 'lon': -7.557106577683727, 's2_id': 5205973754090531959},
        '4': {'services': {'service'}, 'routes': {'1'}, 'id': '4', 'x': 7.0, 'y': 5.0, 'epsg': 'epsg:27700', 'name': '',
              'lat': 49.766856648946295, 'lon': -7.5570681956375, 's2_id': 5205973754097123809},
        '2': {'services': {'service'}, 'routes': {'1'}, 'id': '2', 'x': 1.0, 'y': 2.0, 'epsg': 'epsg:27700', 'name': '',
              'lat': 49.766825803756994, 'lon': -7.557148039524952, 's2_id': 5205973754090365183},
        '3': {'services': {'service'}, 'routes': {'1'}, 'id': '3', 'x': 3.0, 'y': 3.0, 'epsg': 'epsg:27700', 'name': '',
              'lat': 49.76683608549253, 'lon': -7.557121424907424, 's2_id': 5205973754090203369}})
    assert_semantically_equal(s._graph.edges(data=True)._adjdict,
                              {'5': {'6': {'services': {'service'}, 'routes': {'2'}}},
                               '6': {'7': {'services': {'service'}, 'routes': {'2'}}},
                               '7': {'8': {'services': {'service'}, 'routes': {'2'}}}, '8': {}, '4': {},
                               '1': {'2': {'services': {'service'}, 'routes': {'1'}}},
                               '3': {'4': {'services': {'service'}, 'routes': {'1'}}},
                               '2': {'3': {'services': {'service'}, 'routes': {'1'}}}})
    log = s._graph.graph.pop('change_log')
    assert log.empty
    assert_semantically_equal(s._graph.graph,
                              {'name': 'Schedule graph',
                               'routes': {'2': {'route_short_name': 'name_2', 'mode': 'bus',
                                                'trips': {'trip_id': ['1', '2'],
                                                          'trip_departure_time': ['11:00:00', '13:00:00'],
                                                          'vehicle_id': ['veh_3_bus', 'veh_4_bus']},
                                                'arrival_offsets': ['00:00:00', '00:03:00',
                                                                    '00:07:00', '00:13:00'],
                                                'departure_offsets': ['00:00:00', '00:05:00',
                                                                      '00:09:00', '00:15:00'],
                                                'route_long_name': '', 'id': '2', 'route': [],
                                                'await_departure': [],
                                                'ordered_stops': ['5', '6', '7', '8']},
                                          '1': {'route_short_name': 'name', 'mode': 'bus',
                                                'trips': {'trip_id': ['1', '2'],
                                                          'trip_departure_time': ['13:00:00', '13:30:00'],
                                                          'vehicle_id': ['veh_1_bus', 'veh_2_bus']},
                                                'arrival_offsets': ['00:00:00', '00:03:00',
                                                                    '00:07:00', '00:13:00'],
                                                'departure_offsets': ['00:00:00', '00:05:00',
                                                                      '00:09:00', '00:15:00'],
                                                'route_long_name': '', 'id': '1', 'route': [],
                                                'await_departure': [],
                                                'ordered_stops': ['1', '2', '3', '4']}},
                               'services': {'service': {'id': 'service', 'name': 'name'}},
                               'route_to_service_map': {'1': 'service', '2': 'service'},
                               'service_to_route_map': {'service': ['1', '2']},
                               'crs': 'epsg:27700'})


@pytest.fixture()
def non_uniquely_index_schedule():
    route_1 = Route(route_short_name='name',
                    mode='bus', id='route_id',
                    stops=[Stop(id='1', x=4, y=2, epsg='epsg:27700'), Stop(id='2', x=1, y=2, epsg='epsg:27700'),
                           Stop(id='3', x=3, y=3, epsg='epsg:27700'), Stop(id='4', x=7, y=5, epsg='epsg:27700')],
                    trips={'trip_id': ['1', '2'],
                           'trip_departure_time': ['13:00:00', '13:30:00'],
                           'vehicle_id': ['veh_1_bus', 'veh_2_bus']},
                    arrival_offsets=['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                    departure_offsets=['00:00:00', '00:05:00', '00:09:00', '00:15:00'])
    route_2 = Route(route_short_name='name_2',
                    mode='bus', id='route_id',
                    stops=[Stop(id='5', x=4, y=2, epsg='epsg:27700'), Stop(id='6', x=1, y=2, epsg='epsg:27700'),
                           Stop(id='7', x=3, y=3, epsg='epsg:27700'), Stop(id='8', x=7, y=5, epsg='epsg:27700')],
                    trips={'trip_id': ['1', '2'],
                           'trip_departure_time': ['11:00:00', '13:00:00'],
                           'vehicle_id': ['veh_2_bus', 'veh_3_bus']},
                    arrival_offsets=['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                    departure_offsets=['00:00:00', '00:05:00', '00:09:00', '00:15:00'])
    service1 = Service(id='service_id', routes=[route_1, route_2])
    service2 = Service(id='service_id', routes=[route_1, route_2])
    return Schedule(epsg='epsg:27700', services=[service1, service2])


def test_initiating_schedule_with_non_uniquely_indexed_objects_results_in_uniquely_defined_routes(
        non_uniquely_index_schedule):
    assert non_uniquely_index_schedule.number_of_routes() == 4
    assert set(non_uniquely_index_schedule.route_ids()) == {
        'route_id', 'service_id_1', 'service_id_0_service_id_1', 'service_id_0_route_id'}


def test_initiating_schedule_with_non_uniquely_indexed_objects_results_in_uniquely_defined_services(
        non_uniquely_index_schedule):
    assert len(non_uniquely_index_schedule) == 2
    assert set(non_uniquely_index_schedule.service_ids()) == {'service_id_0', 'service_id'}


@pytest.fixture()
def non_uniformly_projected_schedule():
    route_1 = Route(route_short_name='name',
                    mode='bus', id='',
                    stops=[Stop(id='1', x=4, y=2, epsg='epsg:4326'), Stop(id='2', x=1, y=2, epsg='epsg:4326'),
                           Stop(id='3', x=3, y=3, epsg='epsg:4326'), Stop(id='4', x=7, y=5, epsg='epsg:4326')],
                    trips={'trip_id': ['1', '2'],
                           'trip_departure_time': ['13:00:00', '13:30:00'],
                           'vehicle_id': ['veh_1_bus', 'veh_2_bus']},
                    arrival_offsets=['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                    departure_offsets=['00:00:00', '00:05:00', '00:09:00', '00:15:00'])
    route_2 = Route(route_short_name='name_2',
                    mode='bus', id='',
                    stops=[Stop(id='5', x=4, y=2, epsg='epsg:27700'), Stop(id='6', x=1, y=2, epsg='epsg:27700'),
                           Stop(id='7', x=3, y=3, epsg='epsg:27700'), Stop(id='8', x=7, y=5, epsg='epsg:27700')],
                    trips={'trip_id': ['1', '2'],
                           'trip_departure_time': ['11:00:00', '13:00:00'],
                           'vehicle_id': ['veh_2_bus', 'veh_3_bus']},
                    arrival_offsets=['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                    departure_offsets=['00:00:00', '00:05:00', '00:09:00', '00:15:00'])
    service1 = Service(id='service', routes=[route_1, route_2])
    service2 = Service(id='service', routes=[route_1, route_2])
    s = Schedule(epsg='epsg:3857', services=[service1, service2])
    return {
        'schedule': s,
        'unique_stop_projections': {'epsg:4326', 'epsg:27700'},
        'target_projection': s.epsg
    }


def test_schedule_with_non_uniformly_projected_objects_does_not_automatically_reproject(
        non_uniformly_projected_schedule):
    assert non_uniformly_projected_schedule['schedule'].stop('1').epsg == 'epsg:4326'
    assert non_uniformly_projected_schedule['schedule'].stop('5').epsg == 'epsg:27700'
    assert non_uniformly_projected_schedule['schedule'].epsg == 'epsg:3857'


def test_schedule_with_non_uniformly_projected_objects_lists_correct_stop_projections(non_uniformly_projected_schedule):
    assert non_uniformly_projected_schedule['schedule'].unique_stop_projections() == non_uniformly_projected_schedule[
        'unique_stop_projections']


def test_schedule_with_non_uniformly_projected_objects_fails_unique_stop_projects_test(
        non_uniformly_projected_schedule):
    assert not non_uniformly_projected_schedule['schedule'].has_uniformly_projected_stops()


def test_schedule_with_non_uniformly_projected_objects_can_be_projected_to_uniform_projection(
        non_uniformly_projected_schedule):
    assert non_uniformly_projected_schedule['schedule'].epsg == 'epsg:3857'
    assert non_uniformly_projected_schedule['schedule'].unique_stop_projections() != {'epsg:3857'}

    non_uniformly_projected_schedule['schedule'].reproject('epsg:3857')

    assert non_uniformly_projected_schedule['schedule'].epsg == 'epsg:3857'
    assert non_uniformly_projected_schedule['schedule'].unique_stop_projections() == {'epsg:3857'}


def test__getitem__returns_a_service(test_service):
    services = [test_service]
    schedule = Schedule(services=services, epsg='epsg:4326')
    assert schedule['service'] == services[0]


def test_accessing_route(schedule):
    assert schedule.route('1') == Route(route_short_name='name',
                                        mode='bus', id='1',
                                        stops=[Stop(id='1', x=4, y=2, epsg='epsg:27700'),
                                               Stop(id='2', x=1, y=2, epsg='epsg:27700'),
                                               Stop(id='3', x=3, y=3, epsg='epsg:27700'),
                                               Stop(id='4', x=7, y=5, epsg='epsg:27700')],
                                        trips={'trip_id': ['1', '2'],
                                               'trip_departure_time': ['1', '2'],
                                               'vehicle_id': ['veh_1_bus', 'veh_2_bus']},
                                        arrival_offsets=['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                                        departure_offsets=['00:00:00', '00:05:00', '00:09:00', '00:15:00'])


def test__repr__shows_number_of_services(mocker):
    mocker.patch.object(Schedule, '__len__', return_value=0)
    schedule = Schedule('epsg:27700')
    s = schedule.__repr__()
    assert 'instance at' in s
    assert 'services' in s
    Schedule.__len__.assert_called()


def test__str__shows_info():
    schedule = Schedule('epsg:27700')
    assert 'Number of services' in schedule.__str__()
    assert 'Number of routes' in schedule.__str__()


def test__len__returns_the_number_of_services(test_service):
    services = [test_service]
    schedule = Schedule(services=services, epsg='epsg:4326')
    assert len(schedule) == 1


def test_print_shows_info(mocker):
    mocker.patch.object(Schedule, 'info')
    schedule = Schedule('epsg:27700')
    schedule.print()
    Schedule.info.assert_called_once()


def test_info_shows_number_of_services_and_routes(mocker):
    mocker.patch.object(Schedule, '__len__', return_value=0)
    mocker.patch.object(Schedule, 'number_of_routes')
    schedule = Schedule('epsg:27700')
    schedule.print()
    Schedule.__len__.assert_called()
    Schedule.number_of_routes.assert_called_once()


def test_plot_delegates_to_util_plot_plot_graph_routes(mocker, schedule):
    mocker.patch.object(plot, 'plot_geodataframes_on_kepler_map')
    schedule.plot()
    plot.plot_geodataframes_on_kepler_map.assert_called_once()


def test_plot_saves_to_the_specified_directory(tmpdir, schedule):
    filename = 'schedule_map'
    expected_plot_path = os.path.join(tmpdir, filename + '.html')
    assert not os.path.exists(expected_plot_path)

    schedule.plot(output_dir=tmpdir)

    assert os.path.exists(expected_plot_path)


def test_reproject_changes_projection_for_all_stops_in_route():
    correct_x_y = {'x': -0.14967658860132668, 'y': 51.52393050617373}
    schedule = Schedule(
        'epsg:27700',
        [Service(id='10314', routes=[
            Route(
                route_short_name='12',
                mode='bus',
                stops=[Stop(id='26997928P', x='528464.1342843144', y='182179.7435136598', epsg='epsg:27700'),
                       Stop(id='26997928P.link:1', x='528464.1342843144', y='182179.7435136598', epsg='epsg:27700')],
                route=['1'],
                trips={'trip_id': ['VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00'],
                       'trip_departure_time': ['04:40:00'],
                       'vehicle_id': ['veh_1_bus']},
                arrival_offsets=['00:00:00', '00:02:00'],
                departure_offsets=['00:00:00', '00:02:00']
            )
        ])])
    schedule.reproject('epsg:4326')
    _stops = list(schedule.stops())
    stops = dict(zip([stop.id for stop in _stops], _stops))
    assert_semantically_equal({'x': stops['26997928P'].x, 'y': stops['26997928P'].y}, correct_x_y)
    assert_semantically_equal({'x': stops['26997928P.link:1'].x, 'y': stops['26997928P.link:1'].y}, correct_x_y)


def test_adding_merges_separable_schedules(route):
    schedule = Schedule(epsg='epsg:4326', services=[Service(id='1', routes=[route])])
    before_graph_nodes = schedule.reference_nodes()
    before_graph_edges = schedule.reference_edges()

    a = Stop(id='10', x=40, y=20, epsg='epsg:27700', linkRefId='1')
    b = Stop(id='20', x=10, y=20, epsg='epsg:27700', linkRefId='2')
    c = Stop(id='30', x=30, y=30, epsg='epsg:27700', linkRefId='3')
    d = Stop(id='40', x=70, y=50, epsg='epsg:27700', linkRefId='4')
    schedule_to_be_added = Schedule(epsg='epsg:4326', services=[Service(id='2', routes=[
        Route(
            route_short_name='name',
            mode='bus',
            stops=[a, b, c, d],
            trips={'trip_id': ['1', '2'],
                   'trip_departure_time': ['04:40:00', '05:40:00'],
                   'vehicle_id': ['veh_1_bus', 'veh_2_bus']},
            arrival_offsets=['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
            departure_offsets=['00:00:00', '00:05:00', '00:09:00', '00:15:00'],
            route=['1', '2', '3', '4'], id='2')
    ])])

    tba_graph_nodes = schedule_to_be_added.reference_nodes()
    tba_graph_edges = schedule_to_be_added.reference_edges()

    schedule.add(schedule_to_be_added)

    assert '1' in list(schedule.service_ids())
    assert '2' in list(schedule.service_ids())
    assert '1' in list(schedule.route_ids())
    assert '2' in list(schedule.route_ids())
    assert schedule.epsg == 'epsg:4326'
    assert schedule.epsg == schedule_to_be_added.epsg
    assert set(schedule._graph.nodes()) == set(before_graph_nodes) | set(tba_graph_nodes)
    assert set(schedule._graph.edges()) == set(before_graph_edges) | set(tba_graph_edges)
    assert schedule._graph.graph['route_to_service_map'] == {'1': '1', '2': '2'}
    assert schedule._graph.graph['service_to_route_map'] == {'1': ['1'], '2': ['2']}


def test_adding_throws_error_when_schedules_not_separable(test_service):
    schedule = Schedule(epsg='epsg:4326', services=[test_service])
    assert 'service' in schedule
    schedule_to_be_added = Schedule(epsg='epsg:4326', services=[test_service])

    with pytest.raises(NotImplementedError) as e:
        schedule.add(schedule_to_be_added)
    assert 'This method only supports adding non overlapping services' in str(e.value)


def test_adding_calls_on_reproject_when_schedules_dont_have_matching_epsg(test_service, different_test_service, mocker):
    mocker.patch.object(Schedule, 'reproject')
    schedule = Schedule(services=[test_service], epsg='epsg:27700')
    assert schedule.has_service('service')
    schedule_to_be_added = Schedule(services=[different_test_service], epsg='epsg:4326')

    schedule.add(schedule_to_be_added)
    schedule_to_be_added.reproject.assert_called_once_with('epsg:27700')


def test_service_ids_returns_keys_of_the_services_dict(test_service):
    services = [test_service]
    schedule = Schedule(services=services, epsg='epsg:4326')
    assert set(schedule.service_ids()) == {'service'}


def test_routes_returns_service_ids_with_unique_routes(route, similar_non_exact_test_route):
    services = [Service(id='1', routes=[route]), Service(id='2', routes=[similar_non_exact_test_route])]
    schedule = Schedule(services=services, epsg='epsg:4326')
    routes = list(schedule.routes())
    assert route in routes
    assert similar_non_exact_test_route in routes
    assert len(routes) == 2


def test_number_of_routes_counts_routes(test_service, different_test_service):
    schedule = Schedule(services=[test_service, different_test_service], epsg='epsg:4362')
    assert schedule.number_of_routes() == 3


def test_service_attribute_data_under_key(schedule):
    df = schedule.service_attribute_data(keys='name').sort_index()
    assert_frame_equal(df, DataFrame(
        {'name': {'service': 'name'}}
    ))


def test_service_attribute_data_under_keys(schedule):
    df = schedule.service_attribute_data(keys=['name', 'id']).sort_index()
    assert_frame_equal(df, DataFrame(
        {'name': {'service': 'name'}, 'id': {'service': 'service'}}
    ))


def test_route_attribute_data_under_key(schedule):
    df = schedule.route_attribute_data(keys='route_short_name').sort_index()
    assert_frame_equal(df, DataFrame(
        {'route_short_name': {'1': 'name', '2': 'name_2'}}
    ))


def test_route_attribute_data_under_keys(schedule):
    df = schedule.route_attribute_data(keys=['route_short_name', 'mode']).sort_index()
    assert_frame_equal(df, DataFrame(
        {'route_short_name': {'1': 'name', '2': 'name_2'}, 'mode': {'1': 'bus', '2': 'bus'}}
    ))


def test_stop_attribute_data_under_key(schedule):
    df = schedule.stop_attribute_data(keys='x').sort_index()
    assert_frame_equal(df, DataFrame(
        {'x': {'1': 4.0, '2': 1.0, '3': 3.0, '4': 7.0, '5': 4.0, '6': 1.0, '7': 3.0, '8': 7.0}}))


def test_stop_attribute_data_under_keys(schedule):
    df = schedule.stop_attribute_data(keys=['x', 'y']).sort_index()
    assert_frame_equal(df, DataFrame(
        {'x': {'1': 4.0, '2': 1.0, '3': 3.0, '4': 7.0, '5': 4.0, '6': 1.0, '7': 3.0, '8': 7.0},
         'y': {'1': 2.0, '2': 2.0, '3': 3.0, '4': 5.0, '5': 2.0, '6': 2.0, '7': 3.0, '8': 5.0}}))


def test_extracting_services_on_condition(schedule):
    ids = schedule.extract_service_ids_on_attributes(conditions={'name': 'name'})
    assert ids == ['service']


def test_extracting_routes_on_condition(schedule):
    ids = schedule.extract_route_ids_on_attributes(conditions=[{'mode': 'bus'}, {'route_short_name': 'name_2'}],
                                                   how=all)
    assert ids == ['2']


def test_extracting_stops_on_condition(schedule):
    ids = schedule.extract_stop_ids_on_attributes(conditions=[{'x': (0, 4)}, {'y': (0, 2)}], how=all)
    assert set(ids) == {'5', '6', '1', '2'}


def test_getting_services_on_modal_condition(schedule):
    service_ids = schedule.services_on_modal_condition(modes='bus')
    assert service_ids == ['service']


def test_getting_routes_on_modal_condition(schedule):
    route_ids = schedule.routes_on_modal_condition(modes='bus')
    assert set(route_ids) == {'1', '2'}


def test_getting_stops_on_modal_condition(schedule):
    stop_ids = schedule.stops_on_modal_condition(modes='bus')
    assert set(stop_ids) == {'5', '6', '7', '8', '3', '1', '4', '2'}


test_geojson = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "test_geojson.geojson"))


def test_getting_stops_on_spatial_condition_with_geojson(schedule, mocker):
    mocker.patch.object(spatial, 'read_geojson_to_shapely',
                        return_value=GeometryCollection(
                            [Polygon([(-7.6, 49.7), (-7.4, 49.7), (-7.4, 49.8), (-7.6, 49.8), (-7.6, 49.7)])]))
    stops = schedule.stops_on_spatial_condition(test_geojson)
    assert set(stops) == {'5', '6', '7', '8', '2', '4', '3', '1'}


def test_getting_stops_on_spatial_condition_with_shapely_polygon(schedule):
    p = Polygon([(-7.6, 49.7), (-7.4, 49.7), (-7.4, 49.8), (-7.6, 49.8), (-7.6, 49.7)])
    stops = schedule.stops_on_spatial_condition(p)
    assert set(stops) == {'5', '6', '7', '8', '2', '4', '3', '1'}


def test_getting_stops_on_spatial_condition_with_s2_hex_region(schedule):
    s2_region = '4837,4839,483f5,4844,4849'
    stops = schedule.stops_on_spatial_condition(s2_region)
    assert set(stops) == {'5', '6', '7', '8', '2', '4', '3', '1'}


def test_getting_routes_intersecting_spatial_region(schedule):
    p = Polygon([(-7.6, 49.7), (-7.4, 49.7), (-7.4, 49.8), (-7.6, 49.8), (-7.6, 49.7)])
    routes = schedule.routes_on_spatial_condition(p)
    assert set(routes) == {'1', '2'}


def test_getting_routes_contained_spatial_region(schedule):
    p = Polygon([(-7.6, 49.7), (-7.4, 49.7), (-7.4, 49.8), (-7.6, 49.8), (-7.6, 49.7)])
    routes = schedule.routes_on_spatial_condition(p, how='within')
    assert set(routes) == {'1', '2'}


def test_getting_services_intersecting_spatial_region(schedule):
    p = Polygon([(-7.6, 49.7), (-7.4, 49.7), (-7.4, 49.8), (-7.6, 49.8), (-7.6, 49.7)])
    routes = schedule.services_on_spatial_condition(p)
    assert set(routes) == {'service'}


def test_getting_services_contained_spatial_region(schedule):
    p = Polygon([(-7.6, 49.7), (-7.4, 49.7), (-7.4, 49.8), (-7.6, 49.8), (-7.6, 49.7)])
    routes = schedule.services_on_spatial_condition(p, how='within')
    assert set(routes) == {'service'}


@pytest.fixture()
def schedule_with_two_services():
    bus_route = Route(route_short_name='bus_route',
                      mode='bus', id='bus_route',
                      stops=[Stop(id='1', x=4, y=2, epsg='epsg:27700', linkRefId='1'),
                             Stop(id='2', x=1, y=2, epsg='epsg:27700', linkRefId='2'),
                             Stop(id='3', x=3, y=3, epsg='epsg:27700', linkRefId='3'),
                             Stop(id='4', x=7, y=5, epsg='epsg:27700', linkRefId='4')],
                      trips={'trip_id': ['1', '2'],
                             'trip_departure_time': ['13:00:00', '13:30:00'],
                             'vehicle_id': ['veh_1_bus', 'veh_2_bus']},
                      route=['1', '2', '3', '4'],
                      arrival_offsets=['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                      departure_offsets=['00:00:00', '00:05:00', '00:09:00', '00:15:00'])
    rail_route = Route(route_short_name='rail_route',
                       mode='rail', id='rail_route',
                       stops=[Stop(id='4', x=4, y=2, epsg='epsg:27700', linkRefId='4'),
                              Stop(id='5', x=1, y=2, epsg='epsg:27700', linkRefId='5'),
                              Stop(id='6', x=3, y=3, epsg='epsg:27700', linkRefId='6'),
                              Stop(id='7', x=7, y=5, epsg='epsg:27700', linkRefId='7')],
                       trips={'trip_id': ['1', '2'],
                              'trip_departure_time': ['11:00:00', '13:00:00'],
                              'vehicle_id': ['veh_3_bus', 'veh_4_bus']},
                       route=['4', '5', '6', '7'],
                       arrival_offsets=['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                       departure_offsets=['00:00:00', '00:05:00', '00:09:00', '00:15:00'])
    bus_service = Service(id='bus_service', routes=[bus_route])
    rail_service = Service(id='rail_service', routes=[rail_route])
    return Schedule(epsg='epsg:27700', services=[bus_service, rail_service],
                    minimal_transfer_times={'7': {'6': 0.0}, '2': {'1': 0.0}, '4': {'3': 0.0}})


def test_removing_service_from_copied_schedule_does_not_affect_services_in_original(schedule_with_two_services):
    assert set(schedule_with_two_services.service_ids()) == {'bus_service', 'rail_service'}

    subschedule = schedule_with_two_services.__copy__()
    subschedule.remove_service('rail_service')

    assert set(schedule_with_two_services.service_ids()) == {'bus_service', 'rail_service'}
    assert set(subschedule.service_ids()) == {'bus_service'}


def test_removing_service_from_copied_schedule_does_not_affect_graph_nodes_of_original(schedule_with_two_services):
    subschedule = schedule_with_two_services.__copy__()
    subschedule.remove_service('rail_service')

    assert_semantically_equal(
        dict(subschedule._graph.nodes(data=True)),
        {'4': {'services': {'bus_service'}, 'routes': {'bus_route'}, 'id': '4', 'x': 7.0, 'y': 5.0,
               'epsg': 'epsg:27700', 'name': '', 'lon': -7.557068195637501, 'lat': 49.766856648946295,
               's2_id': 5205973754097123809, 'linkRefId': '4'},
         '5': {'services': set(), 'routes': set(), 'id': '5', 'x': 1.0, 'y': 2.0, 'epsg': 'epsg:27700', 'name': '',
               'lon': -7.55714803952495, 'lat': 49.766825803756994, 's2_id': 5205973754090365183, 'linkRefId': '5'},
         '6': {'services': set(), 'routes': set(), 'id': '6', 'x': 3.0, 'y': 3.0, 'epsg': 'epsg:27700', 'name': '',
               'lon': -7.557121424907426, 'lat': 49.76683608549253, 's2_id': 5205973754090203369, 'linkRefId': '6'},
         '7': {'services': set(), 'routes': set(), 'id': '7', 'x': 7.0, 'y': 5.0, 'epsg': 'epsg:27700', 'name': '',
               'lon': -7.557068195637501, 'lat': 49.766856648946295, 's2_id': 5205973754097123809, 'linkRefId': '7'},
         '3': {'services': {'bus_service'}, 'routes': {'bus_route'}, 'id': '3', 'x': 3.0, 'y': 3.0,
               'epsg': 'epsg:27700', 'name': '', 'lon': -7.557121424907426, 'lat': 49.76683608549253,
               's2_id': 5205973754090203369, 'linkRefId': '3'},
         '1': {'services': {'bus_service'}, 'routes': {'bus_route'}, 'id': '1', 'x': 4.0, 'y': 2.0,
               'epsg': 'epsg:27700', 'name': '', 'lon': -7.5571065776837285, 'lat': 49.76682779861248,
               's2_id': 5205973754090531959, 'linkRefId': '1'},
         '2': {'services': {'bus_service'}, 'routes': {'bus_route'}, 'id': '2', 'x': 1.0, 'y': 2.0,
               'epsg': 'epsg:27700', 'name': '', 'lon': -7.55714803952495, 'lat': 49.766825803756994,
               's2_id': 5205973754090365183, 'linkRefId': '2'}}
    )
    assert_semantically_equal(
        dict(schedule_with_two_services._graph.nodes(data=True)),
        {'4': {'services': {'bus_service', 'rail_service'}, 'routes': {'bus_route', 'rail_route'}, 'id': '4', 'x': 7.0,
               'y': 5.0, 'epsg': 'epsg:27700', 'name': '', 'lon': -7.557068195637501, 'lat': 49.766856648946295,
               's2_id': 5205973754097123809, 'linkRefId': '4'},
         '5': {'services': {'rail_service'}, 'routes': {'rail_route'}, 'id': '5', 'x': 1.0, 'y': 2.0,
               'epsg': 'epsg:27700', 'name': '', 'lon': -7.55714803952495, 'lat': 49.766825803756994,
               's2_id': 5205973754090365183, 'linkRefId': '5'},
         '6': {'services': {'rail_service'}, 'routes': {'rail_route'}, 'id': '6', 'x': 3.0, 'y': 3.0,
               'epsg': 'epsg:27700', 'name': '', 'lon': -7.557121424907426, 'lat': 49.76683608549253,
               's2_id': 5205973754090203369, 'linkRefId': '6'},
         '7': {'services': {'rail_service'}, 'routes': {'rail_route'}, 'id': '7', 'x': 7.0, 'y': 5.0,
               'epsg': 'epsg:27700', 'name': '', 'lon': -7.557068195637501, 'lat': 49.766856648946295,
               's2_id': 5205973754097123809, 'linkRefId': '7'},
         '3': {'services': {'bus_service'}, 'routes': {'bus_route'}, 'id': '3', 'x': 3.0, 'y': 3.0,
               'epsg': 'epsg:27700', 'name': '', 'lon': -7.557121424907426, 'lat': 49.76683608549253,
               's2_id': 5205973754090203369, 'linkRefId': '3'},
         '1': {'services': {'bus_service'}, 'routes': {'bus_route'}, 'id': '1', 'x': 4.0, 'y': 2.0,
               'epsg': 'epsg:27700', 'name': '', 'lon': -7.5571065776837285, 'lat': 49.76682779861248,
               's2_id': 5205973754090531959, 'linkRefId': '1'},
         '2': {'services': {'bus_service'}, 'routes': {'bus_route'}, 'id': '2', 'x': 1.0, 'y': 2.0,
               'epsg': 'epsg:27700', 'name': '', 'lon': -7.55714803952495, 'lat': 49.766825803756994,
               's2_id': 5205973754090365183, 'linkRefId': '2'}}
    )


def test_removing_service_from_copied_schedule_does_not_affect_vehicles_of_original(schedule_with_two_services):
    subschedule = schedule_with_two_services.__copy__()
    subschedule.remove_service('rail_service')

    assert_semantically_equal(
        subschedule.vehicles,
        {'veh_1_bus': {'type': 'bus'}, 'veh_2_bus': {'type': 'bus'}}
    )
    assert_semantically_equal(
        schedule_with_two_services.vehicles,
        {'veh_3_bus': {'type': 'rail'}, 'veh_4_bus': {'type': 'rail'}, 'veh_1_bus': {'type': 'bus'},
         'veh_2_bus': {'type': 'bus'}}
    )


def test_changing_copied_schedule_does_not_affect_transfer_times_of_original(schedule_with_two_services):
    subschedule = schedule_with_two_services.__copy__()
    subschedule.remove_stops_from_minimal_transfer_times(['7'])

    assert_semantically_equal(
        subschedule.minimal_transfer_times,
        {'2': {'1': 0.0}, '4': {'3': 0.0}}
    )
    assert_semantically_equal(
        schedule_with_two_services.minimal_transfer_times,
        {'7': {'6': 0.0}, '2': {'1': 0.0}, '4': {'3': 0.0}}
    )


def test_creating_subschedule_results_in_correct_schedule_elems(schedule_with_two_services):
    assert set(schedule_with_two_services.service_ids()) == {'bus_service', 'rail_service'}
    assert set(schedule_with_two_services.route_ids()) == {'bus_route', 'rail_route'}
    assert {s.id for s in schedule_with_two_services.stops()} == {'4', '3', '5', '7', '2', '6', '1'}

    subschedule = schedule_with_two_services.subschedule(['bus_service'])

    assert set(subschedule.service_ids()) == {'bus_service'}
    assert set(subschedule.route_ids()) == {'bus_route'}
    # 6 and 7 are there because we keep unused stops if they have transfers
    assert {s.id for s in subschedule.stops()} == {'4', '3', '2', '1', '6', '7'}


def test_creating_subschedule_results_in_valid_schedule(schedule_with_two_services):
    assert schedule_with_two_services.is_valid_schedule()
    subschedule = schedule_with_two_services.subschedule(['bus_service'])
    assert subschedule.is_valid_schedule()


def test_subnetwork_on_spatial_condition_delagates_to_spatial_methods_to_get_subset_items(mocker,
                                                                                          schedule_with_two_services):
    mocker.patch.object(Schedule, 'services_on_spatial_condition', return_value={'service'})
    mocker.patch.object(Schedule, 'subschedule')

    schedule_with_two_services.subschedule_on_spatial_condition(region_input='region')

    Schedule.services_on_spatial_condition.assert_called_once_with(region_input='region', how='intersect')
    Schedule.subschedule.assert_called_once_with(service_ids={'service'})


def test_applying_attributes_to_service(schedule):
    assert schedule._graph.graph['services']['service']['name'] == 'name'
    assert schedule['service'].name == 'name'

    schedule.apply_attributes_to_services({'service': {'name': 'new_name'}})

    assert schedule._graph.graph['services']['service']['name'] == 'new_name'
    assert schedule['service'].name == 'new_name'


def test_applying_attributes_changing_id_to_service_throws_error(schedule):
    assert 'service' in schedule._graph.graph['services']
    assert schedule._graph.graph['services']['service']['id'] == 'service'
    assert schedule['service'].id == 'service'

    with pytest.raises(NotImplementedError) as e:
        schedule.apply_attributes_to_services({'service': {'id': 'new_id'}})
    assert 'Changing id can only be done via the `reindex` method' in str(e.value)


def test_applying_attributes_to_route(schedule):
    assert schedule._graph.graph['routes']['1']['route_short_name'] == 'name'
    assert schedule.route('1').route_short_name == 'name'

    schedule.apply_attributes_to_routes({'1': {'route_short_name': 'new_name'}})

    assert schedule._graph.graph['routes']['1']['route_short_name'] == 'new_name'
    assert schedule.route('1').route_short_name == 'new_name'


def test_applying_mode_attributes_to_route_results_in_correct_mode_methods(schedule):
    assert schedule.route('1').mode == 'bus'
    assert schedule.modes() == {'bus'}
    assert schedule.mode_graph_map() == {
        'bus': {('3', '4'), ('2', '3'), ('1', '2'), ('6', '7'), ('5', '6'), ('7', '8')}}

    schedule.apply_attributes_to_routes({'1': {'mode': 'new_bus'}})

    assert schedule.route('1').mode == 'new_bus'
    assert schedule.modes() == {'bus', 'new_bus'}
    assert schedule['service'].modes() == {'bus', 'new_bus'}
    assert schedule.mode_graph_map() == {'bus': {('7', '8'), ('6', '7'), ('5', '6')},
                                         'new_bus': {('3', '4'), ('1', '2'), ('2', '3')}}
    assert schedule['service'].mode_graph_map() == {'bus': {('6', '7'), ('7', '8'), ('5', '6')},
                                                    'new_bus': {('3', '4'), ('2', '3'), ('1', '2')}}


def test_applying_attributes_changing_id_to_route_throws_error(schedule):
    assert '1' in schedule._graph.graph['routes']
    assert schedule._graph.graph['routes']['1']['id'] == '1'
    assert schedule.route('1').id == '1'

    with pytest.raises(NotImplementedError) as e:
        schedule.apply_attributes_to_routes({'1': {'id': 'new_id'}})
    assert 'Changing id can only be done via the `reindex` method' in str(e.value)


def test_applying_attributes_changing_stop_ids_to_route_changes_node_and_edge_indexing(schedule):
    assert schedule._graph.graph['routes']['1']['ordered_stops'] == ['1', '2', '3', '4']
    schedule.apply_attributes_to_routes({'1': {'ordered_stops': ['5', '6', '7', '8']}})

    assert schedule.route('1').ordered_stops == ['5', '6', '7', '8']

    assert_semantically_equal(dict(schedule.graph().nodes(data=True)),
                              {'5': {'services': {'service'}, 'routes': {'1', '2'}, 'id': '5', 'x': 4.0, 'y': 2.0,
                                     'epsg': 'epsg:27700', 'name': '', 'lon': -7.557106577683727,
                                     'lat': 49.76682779861249, 's2_id': 5205973754090531959},
                               '6': {'services': {'service'}, 'routes': {'1', '2'}, 'id': '6', 'x': 1.0, 'y': 2.0,
                                     'epsg': 'epsg:27700', 'name': '', 'lon': -7.557148039524952,
                                     'lat': 49.766825803756994, 's2_id': 5205973754090365183},
                               '7': {'services': {'service'}, 'routes': {'1', '2'}, 'id': '7', 'x': 3.0, 'y': 3.0,
                                     'epsg': 'epsg:27700', 'name': '', 'lon': -7.557121424907424,
                                     'lat': 49.76683608549253, 's2_id': 5205973754090203369},
                               '8': {'services': {'service'}, 'routes': {'1', '2'}, 'id': '8', 'x': 7.0, 'y': 5.0,
                                     'epsg': 'epsg:27700', 'name': '', 'lon': -7.5570681956375,
                                     'lat': 49.766856648946295, 's2_id': 5205973754097123809},
                               '4': {'services': set(), 'routes': set(), 'id': '4', 'x': 7.0, 'y': 5.0,
                                     'epsg': 'epsg:27700', 'name': '', 'lon': -7.5570681956375,
                                     'lat': 49.766856648946295, 's2_id': 5205973754097123809},
                               '1': {'services': set(), 'routes': set(), 'id': '1', 'x': 4.0, 'y': 2.0,
                                     'epsg': 'epsg:27700', 'name': '', 'lon': -7.557106577683727,
                                     'lat': 49.76682779861249, 's2_id': 5205973754090531959},
                               '2': {'services': set(), 'routes': set(), 'id': '2', 'x': 1.0, 'y': 2.0,
                                     'epsg': 'epsg:27700', 'name': '', 'lon': -7.557148039524952,
                                     'lat': 49.766825803756994, 's2_id': 5205973754090365183},
                               '3': {'services': set(), 'routes': set(), 'id': '3', 'x': 3.0, 'y': 3.0,
                                     'epsg': 'epsg:27700', 'name': '', 'lon': -7.557121424907424,
                                     'lat': 49.76683608549253, 's2_id': 5205973754090203369}})
    assert_semantically_equal(schedule.graph().edges._adjdict,
                              {'5': {'6': {'services': {'service'}, 'routes': {'2', '1'}}},
                               '6': {'7': {'services': {'service'}, 'routes': {'2', '1'}}},
                               '7': {'8': {'services': {'service'}, 'routes': {'2', '1'}}}, '8': {},
                               '2': {'3': {'services': set(), 'routes': set()}},
                               '3': {'4': {'services': set(), 'routes': set()}},
                               '1': {'2': {'services': set(), 'routes': set()}}, '4': {}})


def test_applying_attributes_to_stop(schedule):
    assert schedule._graph.nodes['5']['name'] == ''
    assert schedule.stop('5').name == ''

    schedule.apply_attributes_to_stops({'5': {'name': 'new_name'}})

    assert schedule._graph.nodes['5']['name'] == 'new_name'
    assert schedule.stop('5').name == 'new_name'


def test_applying_attributes_changing_id_to_stop_throws_error(schedule):
    assert '5' in schedule._graph.nodes
    assert schedule._graph.nodes['5']['id'] == '5'
    assert schedule.stop('5').id == '5'

    with pytest.raises(NotImplementedError) as e:
        schedule.apply_attributes_to_stops({'5': {'id': 'new_id'}})
    assert 'Changing id can only be done via the `reindex` method' in str(e.value)


def change_name(attrib):
    return 'new_name'


def test_applying_function_to_services(schedule):
    schedule.apply_function_to_services(function=change_name, location='name')
    assert schedule._graph.graph['services']['service']['name'] == 'new_name'
    assert schedule['service'].name == 'new_name'


def test_applying_function_to_routes(schedule):
    schedule.apply_function_to_routes(function=change_name, location='route_short_name')
    for route in schedule.routes():
        assert schedule._graph.graph['routes'][route.id]['route_short_name'] == 'new_name'
        assert route.route_short_name == 'new_name'


def test_applying_function_to_stops(schedule):
    schedule.apply_function_to_stops(function=change_name, location='name')
    for stop in schedule.stops():
        assert stop.name == 'new_name'
        assert schedule._graph.nodes[stop.id]['name'] == 'new_name'


def test_adding_service(schedule, service):
    service.reindex('different_service')
    service.route('1').reindex('different_service_1')
    service.route('2').reindex('different_service_2')
    schedule.add_service(service)

    assert set(schedule.route_ids()) == {'1', '2', 'different_service_1', 'different_service_2'}
    assert set(schedule.service_ids()) == {'service', 'different_service'}
    assert_semantically_equal(schedule._graph.graph['route_to_service_map'],
                              {'1': 'service', '2': 'service',
                               'different_service_1': 'different_service', 'different_service_2': 'different_service'})
    assert_semantically_equal(schedule._graph.graph['service_to_route_map'],
                              {'service': ['1', '2'],
                               'different_service': ['different_service_1', 'different_service_2']})


@pytest.fixture()
def services_to_add():
    services = []
    for i in range(2):
        routes = []
        for j in range(2):
            routes.append(Route(route_short_name='name',
                                mode='bus', id=f'new_route_{i}_{j}',
                                stops=[Stop(id='1', x=4, y=2, epsg='epsg:27700'),
                                       Stop(id='2', x=1, y=2, epsg='epsg:27700'),
                                       Stop(id='3', x=3, y=3, epsg='epsg:27700'),
                                       Stop(id='4', x=7, y=5, epsg='epsg:27700')],
                                trips={'trip_id': ['1', '2'],
                                       'trip_departure_time': ['13:00:00', '13:30:00'],
                                       'vehicle_id': ['veh_1_bus', 'veh_2_bus']},
                                arrival_offsets=['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                                departure_offsets=['00:00:00', '00:05:00', '00:09:00', '00:15:00'])
                          )
        services.append(Service(id=f'new_service_{i}', routes=routes))
    return services


def test_multiple_services_are_present_in_schedule_after_adding(schedule, services_to_add):
    existing_routes = set(schedule.route_ids())
    expected_routes_after_adding = existing_routes | {r.id for s in services_to_add for r in s.routes()}
    existing_services = set(schedule.service_ids())
    expected_services_after_adding = existing_services | {s.id for s in services_to_add}

    schedule.add_services(services_to_add)

    assert set(schedule.service_ids()) == expected_services_after_adding
    assert set(schedule.route_ids()) == expected_routes_after_adding


def test_adding_multiple_services_updates_changelog(schedule, services_to_add):
    schedule.add_services(services_to_add)
    assert list(schedule.change_log().iloc[-len(services_to_add):][['change_event', 'new_id']].itertuples(
        index=False, name=None)) == [('add', s.id) for s in services_to_add]


def test_adding_service_with_clashing_route_ids(schedule, service):
    service.reindex('different_service')
    schedule.add_service(service)

    assert set(schedule.route_ids()) == {'1', '2', 'different_service_1', 'different_service_2'}
    assert set(schedule.service_ids()) == {'service', 'different_service'}
    assert_semantically_equal(schedule._graph.graph['route_to_service_map'],
                              {'1': 'service', '2': 'service',
                               'different_service_1': 'different_service', 'different_service_2': 'different_service'})
    assert_semantically_equal(schedule._graph.graph['service_to_route_map'],
                              {'service': ['1', '2'],
                               'different_service': ['different_service_1', 'different_service_2']})


def test_adding_service_with_clashing_id_throws_error(schedule, service):
    with pytest.raises(ServiceIndexError) as e:
        schedule.add_service(service)
    assert 'already exist' in str(e.value)


def test_adding_service_with_clashing_stops_data_does_not_overwrite_existing_stops(schedule):
    expected_stops_data = {
        '5': {'services': {'service', 'some_id'}, 'routes': {'2', '3'}, 'id': '5', 'x': 4.0, 'y': 2.0,
              'epsg': 'epsg:27700',
              'name': '',
              'lat': 49.76682779861249, 'lon': -7.557106577683727, 's2_id': 5205973754090531959},
        '1': {'services': {'service', 'some_id'}, 'routes': {'1', '3'}, 'id': '1', 'x': 4.0, 'y': 2.0,
              'epsg': 'epsg:27700',
              'name': '',
              'lat': 49.76682779861249, 'lon': -7.557106577683727, 's2_id': 5205973754090531959},
        '2': {'services': {'service', 'some_id'}, 'routes': {'1', '3'}, 'id': '2', 'x': 1.0, 'y': 2.0,
              'epsg': 'epsg:27700',
              'name': '',
              'lat': 49.766825803756994, 'lon': -7.557148039524952, 's2_id': 5205973754090365183}}

    r = Route(
        id='3',
        route_short_name='name',
        mode='bus',
        trips={'trip_id': ['1'], 'trip_departure_time': ['02:20:20'], 'vehicle_id': ['1']},
        arrival_offsets=[],
        departure_offsets=[],
        stops=[Stop(id='1', x=1, y=2, epsg='epsg:27700'),
               Stop(id='2', x=0, y=1, epsg='epsg:27700'),
               Stop(id='5', x=0, y=2, epsg='epsg:27700')]
    )
    assert r.ordered_stops == ['1', '2', '5']
    s = Service(id='some_id', routes=[r])

    schedule.add_service(s, force=True)

    assert_semantically_equal(dict(s.graph().nodes(data=True)), expected_stops_data)
    assert_semantically_equal(s.graph()['1']['2'], {'routes': {'1', '3'}, 'services': {'some_id', 'service'}})
    assert_semantically_equal(s.graph()['2']['5'], {'routes': {'3'}, 'services': {'some_id'}})


def test_adding_service_with_clashing_stops_data_without_force_flag_throws_error(schedule):
    r = Route(
        id='3',
        route_short_name='name',
        mode='bus',
        trips={'trip_id': ['1'], 'trip_departure_time': ['02:20:20'], 'vehicle_id': ['1']},
        arrival_offsets=[],
        departure_offsets=[],
        stops=[Stop(id='1', x=1, y=2, epsg='epsg:27700'),
               Stop(id='2', x=0, y=1, epsg='epsg:27700'),
               Stop(id='5', x=0, y=2, epsg='epsg:27700')]
    )

    with pytest.raises(ConflictingStopData) as e:
        schedule.add_service(Service(id='some_id', routes=[r]))
    assert 'The following stops would inherit data' in str(e.value)


def test_removing_service(schedule):
    schedule.remove_service('service')
    assert not set(schedule.route_ids())
    assert not set(schedule.service_ids())
    assert not schedule._graph.graph['route_to_service_map']
    assert not schedule._graph.graph['service_to_route_map']


def test_removing_service_updates_vehicles(schedule):
    assert schedule.has_service('service')
    schedule.remove_service('service')
    assert schedule.vehicles == {}


def test_multiple_services_are_no_longer_present_in_schedule_after_removing(schedule_graph):
    s = Schedule(_graph=schedule_graph)
    s.remove_services(list(s.service_ids()))
    assert set(s.service_ids()) == set()
    assert set(s.route_ids()) == set()


def test_removing_multiple_services_updates_changelog(schedule, schedule_graph):
    s = Schedule(_graph=schedule_graph)
    services_to_remove = list(s.service_ids())
    s.remove_services(services_to_remove)
    assert list(s.change_log().iloc[-len(services_to_remove):][['change_event', 'old_id']].itertuples(
        index=False, name=None)) == [('remove', s) for s in services_to_remove]


def test_adding_route(schedule, route):
    route.reindex('new_id')
    schedule.add_route('service', route)

    assert set(schedule.route_ids()) == {'1', '2', 'new_id'}
    assert set(schedule.service_ids()) == {'service'}
    assert_semantically_equal(schedule._graph.graph['route_to_service_map'],
                              {'1': 'service', '2': 'service', 'new_id': 'service'})
    assert_semantically_equal(schedule._graph.graph['service_to_route_map'],
                              {'service': ['1', '2', 'new_id']})


def test_adding_route_with_clashing_id(schedule, route):
    schedule.add_route('service', route)

    assert set(schedule.route_ids()) == {'1', '2', 'service_3'}
    assert set(schedule.service_ids()) == {'service'}
    assert_semantically_equal(schedule._graph.graph['route_to_service_map'],
                              {'1': 'service', '2': 'service', 'service_3': 'service'})
    assert_semantically_equal(schedule._graph.graph['service_to_route_map'],
                              {'service': ['1', '2', 'service_3']})


def test_adding_route_to_non_existing_service_throws_error(schedule, route):
    with pytest.raises(ServiceIndexError) as e:
        schedule.add_route('service_that_doesnt_exist', route)
    assert 'do not exist' in str(e.value)


@pytest.fixture()
def routes_to_add():
    route_1 = Route(route_short_name='name',
                    mode='bus', id='route_to_add1',
                    stops=[Stop(id='1', x=4, y=2, epsg='epsg:27700'), Stop(id='2', x=1, y=2, epsg='epsg:27700'),
                           Stop(id='3', x=3, y=3, epsg='epsg:27700'), Stop(id='4', x=7, y=5, epsg='epsg:27700')],
                    trips={'trip_id': ['1', '2'],
                           'trip_departure_time': ['13:00:00', '13:30:00'],
                           'vehicle_id': ['veh_1', 'veh_2']},
                    arrival_offsets=['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                    departure_offsets=['00:00:00', '00:05:00', '00:09:00', '00:15:00'])
    route_2 = Route(route_short_name='name_2',
                    mode='bus', id='route_to_add2',
                    stops=[Stop(id='5', x=4, y=2, epsg='epsg:27700'), Stop(id='6', x=1, y=2, epsg='epsg:27700'),
                           Stop(id='7', x=3, y=3, epsg='epsg:27700'), Stop(id='8', x=7, y=5, epsg='epsg:27700')],
                    trips={'trip_id': ['1', '2'],
                           'trip_departure_time': ['11:00:00', '13:00:00'],
                           'vehicle_id': ['veh_3', 'veh_4']},
                    arrival_offsets=['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                    departure_offsets=['00:00:00', '00:05:00', '00:09:00', '00:15:00'])
    return {'service': [route_1, route_2]}


def test_multiple_routes_are_present_in_schedule_after_adding(schedule, routes_to_add):
    existing_routes = set(schedule.route_ids())
    expected_routes_after_adding = existing_routes | {r.id for s, rs in routes_to_add.items() for r in rs}
    existing_services = set(schedule.service_ids())
    expected_services_after_adding = existing_services | set(routes_to_add)

    schedule.add_routes(routes_to_add)

    assert set(schedule.service_ids()) == expected_services_after_adding
    assert set(schedule.route_ids()) == expected_routes_after_adding


def test_adding_multiple_routes_updates_changelog(schedule, routes_to_add):
    schedule.add_routes(routes_to_add)
    assert list(schedule.change_log().iloc[-sum([len(rs) for s, rs in routes_to_add.items()]):][
        ['change_event', 'new_id']].itertuples(
        index=False, name=None)) == [('add', r.id) for s, rs in routes_to_add.items() for r in rs]


def test_creating_a_route_to_add_using_id_references_to_existing_stops_inherits_schedule_stops_data(schedule):
    expected_stops_data = {
        '5': {'services': {'service'}, 'routes': {'2', '3'}, 'id': '5', 'x': 4.0, 'y': 2.0, 'epsg': 'epsg:27700',
              'name': '',
              'lat': 49.76682779861249, 'lon': -7.557106577683727, 's2_id': 5205973754090531959},
        '1': {'services': {'service'}, 'routes': {'1', '3'}, 'id': '1', 'x': 4.0, 'y': 2.0, 'epsg': 'epsg:27700',
              'name': '',
              'lat': 49.76682779861249, 'lon': -7.557106577683727, 's2_id': 5205973754090531959},
        '2': {'services': {'service'}, 'routes': {'1', '3'}, 'id': '2', 'x': 1.0, 'y': 2.0, 'epsg': 'epsg:27700',
              'name': '',
              'lat': 49.766825803756994, 'lon': -7.557148039524952, 's2_id': 5205973754090365183}}

    r = Route(
        id='3',
        route_short_name='name',
        mode='bus',
        trips={'trip_id': ['1'], 'trip_departure_time': ['02:20:20'], 'vehicle_id': ['1']},
        arrival_offsets=[],
        departure_offsets=[],
        stops=['1', '2', '5']
    )
    assert r.ordered_stops == ['1', '2', '5']
    assert_semantically_equal(dict(r._graph.nodes(data=True)),
                              {'1': {'routes': {'3'}}, '2': {'routes': {'3'}}, '5': {'routes': {'3'}}})
    assert_semantically_equal(r._graph.edges(data=True)._adjdict,
                              {'1': {'2': {'routes': {'3'}}}, '2': {'5': {'routes': {'3'}}}, '5': {}})

    schedule.add_route('service', r)

    assert_semantically_equal(dict(r.graph().nodes(data=True)), expected_stops_data)
    assert_semantically_equal(r.graph()['1']['2'], {'routes': {'1', '3'}, 'services': {'service'}})
    assert_semantically_equal(r.graph()['2']['5'], {'routes': {'3'}, 'services': {'service'}})


def test_creating_a_route_to_add_giving_existing_schedule_stops(schedule):
    expected_stops_data = {
        '5': {'services': {'service'}, 'routes': {'2', '3'}, 'id': '5', 'x': 4.0, 'y': 2.0, 'epsg': 'epsg:27700',
              'name': '',
              'lat': 49.76682779861249, 'lon': -7.557106577683727, 's2_id': 5205973754090531959},
        '1': {'services': {'service'}, 'routes': {'1', '3'}, 'id': '1', 'x': 4.0, 'y': 2.0, 'epsg': 'epsg:27700',
              'name': '',
              'lat': 49.76682779861249, 'lon': -7.557106577683727, 's2_id': 5205973754090531959},
        '2': {'services': {'service'}, 'routes': {'1', '3'}, 'id': '2', 'x': 1.0, 'y': 2.0, 'epsg': 'epsg:27700',
              'name': '',
              'lat': 49.766825803756994, 'lon': -7.557148039524952, 's2_id': 5205973754090365183}}

    r = Route(
        id='3',
        route_short_name='name',
        mode='bus',
        trips={'trip_id': ['1'], 'trip_departure_time': ['02:20:20'], 'vehicle_id': ['1']},
        arrival_offsets=[],
        departure_offsets=[],
        stops=[schedule.stop('1'), schedule.stop('2'), schedule.stop('5')]
    )
    assert r.ordered_stops == ['1', '2', '5']
    assert_semantically_equal(dict(r._graph.nodes(data=True)),
                              {'1': {'routes': {'3'}, 'id': '1', 'x': 4.0, 'y': 2.0, 'epsg': 'epsg:27700', 'name': '',
                                     'lat': 49.76682779861249, 'lon': -7.557106577683727, 's2_id': 5205973754090531959},
                               '2': {'routes': {'3'}, 'id': '2', 'x': 1.0, 'y': 2.0, 'epsg': 'epsg:27700', 'name': '',
                                     'lat': 49.766825803756994, 'lon': -7.557148039524952,
                                     's2_id': 5205973754090365183},
                               '5': {'routes': {'3'}, 'id': '5', 'x': 4.0, 'y': 2.0, 'epsg': 'epsg:27700', 'name': '',
                                     'lat': 49.76682779861249, 'lon': -7.557106577683727,
                                     's2_id': 5205973754090531959}})
    assert_semantically_equal(r._graph.edges(data=True)._adjdict,
                              {'1': {'2': {'routes': {'3'}}}, '2': {'5': {'routes': {'3'}}}, '5': {}})

    schedule.add_route('service', r)

    assert_semantically_equal(dict(r.graph().nodes(data=True)), expected_stops_data)
    assert_semantically_equal(r.graph()['1']['2'], {'routes': {'1', '3'}, 'services': {'service'}})
    assert_semantically_equal(r.graph()['2']['5'], {'routes': {'3'}, 'services': {'service'}})


def test_adding_route_with_clashing_stops_data_does_not_overwrite_existing_stops(schedule):
    expected_stops_data = {
        '5': {'services': {'service'}, 'routes': {'2', '3'}, 'id': '5', 'x': 4.0, 'y': 2.0, 'epsg': 'epsg:27700',
              'name': '',
              'lat': 49.76682779861249, 'lon': -7.557106577683727, 's2_id': 5205973754090531959},
        '1': {'services': {'service'}, 'routes': {'1', '3'}, 'id': '1', 'x': 4.0, 'y': 2.0, 'epsg': 'epsg:27700',
              'name': '',
              'lat': 49.76682779861249, 'lon': -7.557106577683727, 's2_id': 5205973754090531959},
        '2': {'services': {'service'}, 'routes': {'1', '3'}, 'id': '2', 'x': 1.0, 'y': 2.0, 'epsg': 'epsg:27700',
              'name': '',
              'lat': 49.766825803756994, 'lon': -7.557148039524952, 's2_id': 5205973754090365183}}

    r = Route(
        id='3',
        route_short_name='name',
        mode='bus',
        trips={'trip_id': ['1'], 'trip_departure_time': ['02:20:20'], 'vehicle_id': ['1']},
        arrival_offsets=[],
        departure_offsets=[],
        stops=[Stop(id='1', x=1, y=2, epsg='epsg:27700'),
               Stop(id='2', x=0, y=1, epsg='epsg:27700'),
               Stop(id='5', x=0, y=2, epsg='epsg:27700')]
    )
    assert r.ordered_stops == ['1', '2', '5']

    schedule.add_route('service', r, force=True)

    assert_semantically_equal(dict(r.graph().nodes(data=True)), expected_stops_data)
    assert_semantically_equal(r.graph()['1']['2'], {'routes': {'1', '3'}, 'services': {'service'}})
    assert_semantically_equal(r.graph()['2']['5'], {'routes': {'3'}, 'services': {'service'}})


def test_adding_route_with_clashing_stops_data_only_flags_those_that_are_actually_different(schedule):
    r = Route(
        id='3',
        route_short_name='name',
        mode='bus',
        trips={'trip_id': ['1'], 'trip_departure_time': ['02:20:20'], 'vehicle_id': ['1']},
        arrival_offsets=[],
        departure_offsets=[],
        stops=[Stop(id='1', x=1, y=2, epsg='epsg:27700'),
               Stop(id='2', x=0, y=1, epsg='epsg:27700'),
               Stop(id='5', x=4, y=2, epsg='epsg:27700', name='')]
    )
    assert r.ordered_stops == ['1', '2', '5']

    with pytest.raises(ConflictingStopData) as e:
        schedule.add_route('service', r)
    assert "The following stops would inherit data currently stored under those Stop IDs in the Schedule: " \
           "['1', '2']" in str(e.value)


def test_adding_route_with_clashing_stops_data_without_force_flag_throws_error(schedule):
    r = Route(
        id='3',
        route_short_name='name',
        mode='bus',
        trips={'trip_id': ['1'], 'trip_departure_time': ['02:20:20'], 'vehicle_id': ['1']},
        arrival_offsets=[],
        departure_offsets=[],
        stops=[Stop(id='1', x=1, y=2, epsg='epsg:27700'),
               Stop(id='2', x=0, y=1, epsg='epsg:27700'),
               Stop(id='5', x=0, y=2, epsg='epsg:27700')]
    )

    with pytest.raises(ConflictingStopData) as e:
        schedule.add_route('service', r)
    assert 'The following stops would inherit data' in str(e.value)


def test_extracting_epsg_from_an_intermediate_route_gives_none():
    # intermediate meaning not belonging to a schedule yet but referring to stops in a schedule
    r = Route(
        route_short_name='name',
        mode='bus',
        trips={'trip_id': ['1'], 'trip_departure_time': ['02:20:20'], 'vehicle_id': ['1']},
        arrival_offsets=[],
        departure_offsets=[],
        stops=['S1', 'S2', 'S3']
    )

    assert r.epsg is None


def test_removing_route(schedule):
    schedule.remove_route('2')
    assert set(schedule.route_ids()) == {'1'}
    assert set(schedule.service_ids()) == {'service'}
    assert_semantically_equal(schedule._graph.graph['route_to_service_map'],
                              {'1': 'service'})
    assert_semantically_equal(schedule._graph.graph['service_to_route_map'],
                              {'service': ['1']})


def test_removing_route_updates_services_on_nodes_and_edges(schedule):
    schedule.remove_route('2')
    assert_semantically_equal(dict(schedule.graph().nodes(data=True)),
                              {'5': {'services': set(), 'routes': set(), 'id': '5', 'x': 4.0, 'y': 2.0,
                                     'epsg': 'epsg:27700',
                                     'name': '', 'lat': 49.76682779861249, 'lon': -7.557106577683727,
                                     's2_id': 5205973754090531959},
                               '6': {'services': set(), 'routes': set(), 'id': '6', 'x': 1.0, 'y': 2.0,
                                     'epsg': 'epsg:27700',
                                     'name': '', 'lat': 49.766825803756994, 'lon': -7.557148039524952,
                                     's2_id': 5205973754090365183},
                               '7': {'services': set(), 'routes': set(), 'id': '7', 'x': 3.0, 'y': 3.0,
                                     'epsg': 'epsg:27700',
                                     'name': '', 'lat': 49.76683608549253, 'lon': -7.557121424907424,
                                     's2_id': 5205973754090203369},
                               '8': {'services': set(), 'routes': set(), 'id': '8', 'x': 7.0, 'y': 5.0,
                                     'epsg': 'epsg:27700',
                                     'name': '', 'lat': 49.766856648946295, 'lon': -7.5570681956375,
                                     's2_id': 5205973754097123809},
                               '3': {'services': {'service'}, 'routes': {'1'}, 'id': '3', 'x': 3.0, 'y': 3.0,
                                     'epsg': 'epsg:27700', 'name': '', 'lat': 49.76683608549253,
                                     'lon': -7.557121424907424, 's2_id': 5205973754090203369},
                               '1': {'services': {'service'}, 'routes': {'1'}, 'id': '1', 'x': 4.0, 'y': 2.0,
                                     'epsg': 'epsg:27700', 'name': '', 'lat': 49.76682779861249,
                                     'lon': -7.557106577683727, 's2_id': 5205973754090531959},
                               '2': {'services': {'service'}, 'routes': {'1'}, 'id': '2', 'x': 1.0, 'y': 2.0,
                                     'epsg': 'epsg:27700', 'name': '', 'lat': 49.766825803756994,
                                     'lon': -7.557148039524952, 's2_id': 5205973754090365183},
                               '4': {'services': {'service'}, 'routes': {'1'}, 'id': '4', 'x': 7.0, 'y': 5.0,
                                     'epsg': 'epsg:27700', 'name': '', 'lat': 49.766856648946295,
                                     'lon': -7.5570681956375, 's2_id': 5205973754097123809}})
    assert_semantically_equal(schedule.graph().edges(data=True)._adjdict,
                              {'5': {'6': {'services': set(), 'routes': set()}},
                               '6': {'7': {'services': set(), 'routes': set()}},
                               '7': {'8': {'services': set(), 'routes': set()}}, '8': {},
                               '1': {'2': {'services': {'service'}, 'routes': {'1'}}},
                               '3': {'4': {'services': {'service'}, 'routes': {'1'}}},
                               '2': {'3': {'services': {'service'}, 'routes': {'1'}}}, '4': {}})


def test_removing_route_updates_vehicles(schedule):
    schedule.remove_route('2')
    assert_semantically_equal(schedule.vehicles,
                              {'veh_1_bus': {'type': 'bus'}, 'veh_2_bus': {'type': 'bus'}})


def test_removing_route_with_overlapping_vehicles_leaves_all_vehicles(schedule, route):
    schedule.add_route(route=route, service_id='service')
    schedule.remove_route('1')
    assert_semantically_equal(schedule.vehicles,
                              {'veh_1_bus': {'type': 'bus'}, 'veh_2_bus': {'type': 'bus'},
                               'veh_3_bus': {'type': 'bus'}, 'veh_4_bus': {'type': 'bus'}})


def test_multiple_routes_are_no_longer_present_in_schedule_after_removing(schedule_graph):
    s = Schedule(_graph=schedule_graph)
    assert set(s.service_ids()) == {'service1', 'service2'}
    assert set(s.route_ids()) == {'2', '1', '4', '3'}
    s.remove_routes(['1', '3'])
    assert set(s.service_ids()) == {'service1', 'service2'}
    assert set(s.route_ids()) == {'4', '2'}


def test_service_is_no_longer_present_after_removing_all_its_routes(schedule_graph):
    s = Schedule(_graph=schedule_graph)
    assert set(s.service_ids()) == {'service1', 'service2'}
    assert set(s.route_ids()) == {'2', '1', '4', '3'}
    s.remove_routes(['1', '2'])
    assert set(s.service_ids()) == {'service2'}
    assert set(s.route_ids()) == {'4', '3'}


def test_removing_multiple_routes_updates_changelog(schedule_graph):
    s = Schedule(_graph=schedule_graph)
    route_to_remove = ['1', '2']
    s.remove_routes(route_to_remove)
    assert list(
        s.change_log().iloc[-len(route_to_remove):][['change_event', 'old_id']].itertuples(index=False, name=None)) == [
               ('remove', r) for r in route_to_remove]


def test_removing_stop(schedule):
    schedule.remove_stop('5')
    assert {stop.id for stop in schedule.stops()} == {'1', '3', '4', '7', '8', '6', '2'}


def test_removing_multiple_stops(schedule):
    schedule.remove_stops(['5', '3'])
    assert {stop.id for stop in schedule.stops()} == {'1', '4', '7', '8', '6', '2'}


def test_removing_stop_updates_minimal_tranfer_times(schedule):
    schedule.minimal_transfer_times = {
        '5': {'2': 0.0},
        '2': {'5': 0.0, '3': 0.0},
        '3': {'2': 0.0},
    }
    schedule.remove_stop('5')
    assert_semantically_equal(schedule.minimal_transfer_times,
                              {
                                  '2': {'3': 0.0},
                                  '3': {'2': 0.0},
                              })


def test_removing_multiple_stops_updates_minimal_tranfer_times(schedule):
    schedule.minimal_transfer_times = {
        '5': {'2': 0.0},
        '2': {'5': 0.0, '3': 0.0},
        '3': {'2': 0.0},
    }
    schedule.remove_stops(['5', '3'])
    assert_semantically_equal(schedule.minimal_transfer_times, {})


def test_removing_key_stops_from_minimal_transfert_times(schedule):
    schedule.minimal_transfer_times = {
        '5': {'2': 0.0},
        '2': {'5': 0.0, '3': 0.0},
        '3': {'2': 0.0},
        '4': {'3': 0.0}
    }
    schedule.remove_stops_from_minimal_transfer_times(['4'])
    assert_semantically_equal(schedule.minimal_transfer_times,
                              {
                                  '5': {'2': 0.0},
                                  '2': {'5': 0.0, '3': 0.0},
                                  '3': {'2': 0.0},
                              })


def test_removing_val_stops_from_minimal_transfert_times(schedule):
    schedule.minimal_transfer_times = {
        '2': {'5': 0.0, '3': 0.0},
        '3': {'2': 0.0},
    }
    schedule.remove_stops_from_minimal_transfer_times(['5'])
    assert_semantically_equal(schedule.minimal_transfer_times,
                              {
                                  '2': {'3': 0.0},
                                  '3': {'2': 0.0},
                              })


def test_removing_stops_from_minimal_transfert_times_cleans_up_empties(schedule):
    schedule.minimal_transfer_times = {
        '4': {'5': 0.0, '3': 0.0},
        '3': {'2': 0.0},
    }
    schedule.remove_stops_from_minimal_transfer_times(['2'])
    assert_semantically_equal(schedule.minimal_transfer_times,
                              {
                                  '4': {'5': 0.0, '3': 0.0},
                              })


def test_removing_unused_stops(schedule):
    schedule.remove_route('1')
    schedule.remove_unused_stops()
    assert {stop.id for stop in schedule.stops()} == {'6', '8', '5', '7'}


def test_unused_stops_featured_in_minimal_transfer_times_are_kept(schedule):
    schedule.minimal_transfer_times = {
        '5': {'2': 0.0},
        '2': {'5': 0.0, '3': 0.0},
        '3': {'2': 0.0},
    }
    schedule.remove_route('1')
    schedule.remove_unused_stops()
    assert {stop.id for stop in schedule.stops()} == {'5', '2', '3', '6', '8', '7'}
    assert_semantically_equal(schedule.minimal_transfer_times,
                              {
                                  '5': {'2': 0.0},
                                  '2': {'5': 0.0, '3': 0.0},
                                  '3': {'2': 0.0},
                              })


def test_iter_stops_returns_stops_objects(test_service, different_test_service):
    schedule = Schedule(services=[test_service, different_test_service], epsg='epsg:4326')
    assert set([stop.id for stop in schedule.stops()]) == {'0', '1', '2', '3', '4'}
    assert all([isinstance(stop, Stop) for stop in schedule.stops()])


def test_read_matsim_schedule_delegates_to_matsim_reader_read_schedule(mocker, route):
    mocker.patch.object(
        matsim_reader,
        'read_schedule',
        return_value=([Service(id='1', routes=[route])], {}, {}, {'attributes': {}}))

    schedule = read.read_matsim_schedule(pt2matsim_schedule_file, epsg='epsg:27700')

    matsim_reader.read_schedule.assert_called_once_with(pt2matsim_schedule_file, schedule.epsg,
                                                        force_long_form_attributes=False)


def test_read_matsim_schedule_returns_expected_schedule():
    schedule = read.read_matsim_schedule(
        path_to_schedule=pt2matsim_schedule_file,
        epsg='epsg:27700')

    correct_services = Service(id='10314', routes=[
        Route(
            route_short_name='12', id='VJbd8660f05fe6f744e58a66ae12bd66acbca88b98',
            mode='bus',
            stops=[Stop(id='26997928P', x='528464.1342843144', y='182179.7435136598', epsg='epsg:27700'),
                   Stop(id='26997928P.link:1', x='528464.1342843144', y='182179.7435136598', epsg='epsg:27700')],
            route=['1'],
            trips={'trip_id': ['VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00'],
                   'trip_departure_time': ['04:40:00'],
                   'vehicle_id': ['veh_0_bus']},
            arrival_offsets=['00:00:00', '00:02:00'],
            departure_offsets=['00:00:00', '00:02:00']
        )
    ])
    for val in schedule.services():
        assert val == correct_services
    assert_semantically_equal(schedule.stop_to_service_ids_map(),
                              {'26997928P.link:1': {'10314'}, '26997928P': {'10314'}})
    assert_semantically_equal(schedule.stop_to_route_ids_map(),
                              {'26997928P': {'VJbd8660f05fe6f744e58a66ae12bd66acbca88b98'},
                               '26997928P.link:1': {'VJbd8660f05fe6f744e58a66ae12bd66acbca88b98'}})
    assert_semantically_equal(schedule.route('VJbd8660f05fe6f744e58a66ae12bd66acbca88b98').trips,
                              {'trip_id': ['VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00'],
                               'trip_departure_time': ['04:40:00'], 'vehicle_id': ['veh_0_bus']})
    assert_semantically_equal(schedule.minimal_transfer_times,
                              {'26997928P': {'26997928P.link:1': 0.0}, '26997928P.link:1': {'26997928P': 0.0}})


pt2matsim_schedule_extra_stop_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "schedule_extra_stop.xml"))


def test_reading_schedule_with_stops_unused_by_services():
    schedule = read.read_matsim_schedule(pt2matsim_schedule_extra_stop_file, 'epsg:27700')
    assert_semantically_equal(dict(schedule.graph().nodes(data=True)),
                              {'26997928P': {'services': {'10314'},
                                             'routes': {'VJbd8660f05fe6f744e58a66ae12bd66acbca88b98'},
                                             'id': '26997928P', 'x': 528464.1342843144, 'y': 182179.7435136598,
                                             'epsg': 'epsg:27700', 'name': 'Brunswick Place (Stop P)',
                                             'lat': 51.52393050617373, 'lon': -0.14967658860132668,
                                             's2_id': 5221390302759871369, 'isBlocking': 'false'},
                               '26997928P.link:1': {'services': {'10314'},
                                                    'routes': {'VJbd8660f05fe6f744e58a66ae12bd66acbca88b98'},
                                                    'id': '26997928P.link:1', 'x': 528464.1342843144,
                                                    'y': 182179.7435136598, 'epsg': 'epsg:27700',
                                                    'name': 'Brunswick Place (Stop P)', 'lon': -0.14967658860132668,
                                                    'lat': 51.52393050617373, 's2_id': 5221390302759871369,
                                                    'linkRefId': '1', 'isBlocking': 'false'},
                               'extra_stop': {'id': 'extra_stop', 'x': 528464.1342843144, 'y': 182179.7435136598,
                                              'epsg': 'epsg:27700', 'name': 'Brunswick Place (Stop P)',
                                              'lon': -0.14967658860132668, 'lat': 51.52393050617373,
                                              's2_id': 5221390302759871369,
                                              'isBlocking': 'false', 'routes': set(), 'services': set()}})
    assert_semantically_equal(schedule.minimal_transfer_times,
                              {'26997928P': {'extra_stop': 0.0}, 'extra_stop': {'26997928P': 0.0}})


def test_reading_vehicles_with_a_schedule():
    schedule = read.read_matsim_schedule(
        path_to_schedule=pt2matsim_schedule_file,
        path_to_vehicles=pt2matsim_vehicles_file,
        epsg='epsg:27700')

    assert_semantically_equal(schedule.vehicles, {'veh_0_bus': {'type': 'bus'}})
    assert_semantically_equal(schedule.vehicle_types['bus'], {
        'capacity': {'seats': {'persons': '71'}, 'standingRoom': {'persons': '1'}},
        'length': {'meter': '18.0'},
        'width': {'meter': '2.5'},
        'accessTime': {'secondsPerPerson': '0.5'},
        'egressTime': {'secondsPerPerson': '0.5'},
        'doorOperation': {'mode': 'serial'},
        'passengerCarEquivalents': {'pce': '2.8'}})


def test_reading_vehicles_after_reading_schedule():
    schedule = read.read_matsim_schedule(
        path_to_schedule=pt2matsim_schedule_file,
        path_to_vehicles=pt2matsim_vehicles_file,
        epsg='epsg:27700')

    assert_semantically_equal(schedule.vehicles, {'veh_0_bus': {'type': 'bus'}})
    assert_semantically_equal(schedule.vehicle_types['bus'], {
        'capacity': {'seats': {'persons': '71'}, 'standingRoom': {'persons': '1'}},
        'length': {'meter': '18.0'},
        'width': {'meter': '2.5'},
        'accessTime': {'secondsPerPerson': '0.5'},
        'egressTime': {'secondsPerPerson': '0.5'},
        'doorOperation': {'mode': 'serial'},
        'passengerCarEquivalents': {'pce': '2.8'}})


def test_is_strongly_connected_with_strongly_connected_schedule(strongly_connected_schedule):
    assert strongly_connected_schedule.is_strongly_connected()


def test_is_strongly_connected_with_not_strongly_connected_schedule(schedule):
    assert not schedule.is_strongly_connected()


def test_has_self_loops_with_self_has_self_looping_schedule(self_looping_route):
    s = Schedule('epsg:27700', [Service(id='service', routes=[self_looping_route])])
    assert s.has_self_loops()


def test_has_self_loops_returns_self_looping_stops(self_looping_route):
    s = Schedule('epsg:27700', [Service(id='service', routes=[self_looping_route])])
    loop_nodes = s.has_self_loops()
    assert loop_nodes == ['1']


def test_has_self_loops_with_non_looping_routes(schedule):
    assert not schedule.has_self_loops()


def test_validity_of_services(self_looping_route, route):
    s = Schedule('epsg:27700', [Service(id='1', routes=[self_looping_route]),
                                Service(id='2', routes=[route])])
    assert not s['1'].is_valid_service()
    assert s['2'].is_valid_service()
    assert set(s.validity_of_services()) == {False, True}


def test_has_valid_services(schedule):
    assert not schedule.has_valid_services()


def test_has_valid_services_with_only_valid_services(service):
    s = Schedule('epsg:27700', [service])
    assert s.has_valid_services()


def test_invalid_services_shows_invalid_services(service):
    for route_id in service.route_ids():
        service._graph.graph['routes'][route_id]['route'] = ['1']
    s = Schedule('epsg:27700', [service])
    assert s.invalid_services() == [service]


def test_is_valid_with_valid_schedule(service):
    s = Schedule('epsg:27700', [service])
    assert s.is_valid_schedule()


def test_generate_validation_report_delegates_to_method_in_schedule_operations(mocker, schedule):
    mocker.patch.object(schedule_validation, 'generate_validation_report')
    schedule.generate_validation_report()
    schedule_validation.generate_validation_report.assert_called_once()


def test_build_graph_builds_correct_graph(strongly_connected_schedule):
    g = strongly_connected_schedule.graph()

    assert_semantically_equal(dict(g.nodes(data=True)),
                              {'5': {'services': {'service'}, 'routes': {'2'}, 'id': '5', 'x': 4.0, 'y': 2.0,
                                     'epsg': 'epsg:27700', 'lat': 49.76682779861249, 'lon': -7.557106577683727,
                                     's2_id': 5205973754090531959, 'name': 'Stop_5'},
                               '2': {'services': {'service'}, 'routes': {'1', '2'}, 'id': '2', 'x': 1.0, 'y': 2.0,
                                     'epsg': 'epsg:27700', 'lat': 49.766825803756994, 'lon': -7.557148039524952,
                                     's2_id': 5205973754090365183, 'name': 'Stop_2'},
                               '7': {'services': {'service'}, 'routes': {'2'}, 'id': '7', 'x': 3.0, 'y': 3.0,
                                     'epsg': 'epsg:27700', 'lat': 49.76683608549253, 'lon': -7.557121424907424,
                                     's2_id': 5205973754090203369, 'name': 'Stop_7'},
                               '8': {'services': {'service'}, 'routes': {'2'}, 'id': '8', 'x': 7.0, 'y': 5.0,
                                     'epsg': 'epsg:27700', 'lat': 49.766856648946295, 'lon': -7.5570681956375,
                                     's2_id': 5205973754097123809, 'name': 'Stop_8'},
                               '3': {'services': {'service'}, 'routes': {'1'}, 'id': '3', 'x': 3.0, 'y': 3.0,
                                     'epsg': 'epsg:27700', 'lat': 49.76683608549253, 'lon': -7.557121424907424,
                                     's2_id': 5205973754090203369, 'name': 'Stop_3'},
                               '1': {'services': {'service'}, 'routes': {'1'}, 'id': '1', 'x': 4.0, 'y': 2.0,
                                     'epsg': 'epsg:27700', 'lat': 49.76682779861249, 'lon': -7.557106577683727,
                                     's2_id': 5205973754090531959, 'name': 'Stop_1'},
                               '4': {'services': {'service'}, 'routes': {'1'}, 'id': '4', 'x': 7.0, 'y': 5.0,
                                     'epsg': 'epsg:27700', 'lat': 49.766856648946295, 'lon': -7.5570681956375,
                                     's2_id': 5205973754097123809, 'name': 'Stop_4'}})
    assert_semantically_equal(g.edges(data=True)._adjdict,
                              {'5': {'2': {'services': {'service'}, 'routes': {'2'}}},
                               '2': {'7': {'services': {'service'}, 'routes': {'2'}},
                                     '3': {'services': {'service'}, 'routes': {'1'}}},
                               '7': {'8': {'services': {'service'}, 'routes': {'2'}}},
                               '8': {'5': {'services': {'service'}, 'routes': {'2'}}},
                               '4': {'1': {'services': {'service'}, 'routes': {'1'}}},
                               '1': {'2': {'services': {'service'}, 'routes': {'1'}}},
                               '3': {'4': {'services': {'service'}, 'routes': {'1'}}}})


def test_building_trips_dataframe_with_stops_accepts_backwards_compatibility(schedule, mocker, caplog):
    mocker.patch.object(Schedule, 'trips_with_stops_to_dataframe')
    schedule.trips_with_stops_to_dataframe(schedule.trips_to_dataframe())
    schedule.trips_with_stops_to_dataframe.assert_called_once()
    assert_logging_warning_caught_with_message_containing(caplog,
                                                          '`route_trips_with_stops_to_dataframe` method is deprecated')


def test_building_trips_dataframe_with_stops(schedule):
    df = schedule.trips_with_stops_to_dataframe()

    correct_df = DataFrame({'departure_time': {0: Timestamp('1970-01-01 13:00:00'), 1: Timestamp('1970-01-01 13:05:00'),
                                               2: Timestamp('1970-01-01 13:09:00'), 3: Timestamp('1970-01-01 13:30:00'),
                                               4: Timestamp('1970-01-01 13:35:00'), 5: Timestamp('1970-01-01 13:39:00'),
                                               6: Timestamp('1970-01-01 11:00:00'), 7: Timestamp('1970-01-01 11:05:00'),
                                               8: Timestamp('1970-01-01 11:09:00'), 9: Timestamp('1970-01-01 13:00:00'),
                                               10: Timestamp('1970-01-01 13:05:00'),
                                               11: Timestamp('1970-01-01 13:09:00')},
                            'arrival_time': {0: Timestamp('1970-01-01 13:03:00'), 1: Timestamp('1970-01-01 13:07:00'),
                                             2: Timestamp('1970-01-01 13:13:00'), 3: Timestamp('1970-01-01 13:33:00'),
                                             4: Timestamp('1970-01-01 13:37:00'), 5: Timestamp('1970-01-01 13:43:00'),
                                             6: Timestamp('1970-01-01 11:03:00'), 7: Timestamp('1970-01-01 11:07:00'),
                                             8: Timestamp('1970-01-01 11:13:00'), 9: Timestamp('1970-01-01 13:03:00'),
                                             10: Timestamp('1970-01-01 13:07:00'),
                                             11: Timestamp('1970-01-01 13:13:00')},
                            'from_stop': {0: '1', 1: '2', 2: '3', 3: '1', 4: '2', 5: '3', 6: '5', 7: '6', 8: '7',
                                          9: '5', 10: '6', 11: '7'},
                            'to_stop': {0: '2', 1: '3', 2: '4', 3: '2', 4: '3', 5: '4', 6: '6', 7: '7', 8: '8', 9: '6',
                                        10: '7', 11: '8'},
                            'trip_id': {0: '1', 1: '1', 2: '1', 3: '2', 4: '2', 5: '2', 6: '1', 7: '1', 8: '1', 9: '2',
                                        10: '2', 11: '2'},
                            'vehicle_id': {0: 'veh_1_bus', 1: 'veh_1_bus', 2: 'veh_1_bus', 3: 'veh_2_bus',
                                           4: 'veh_2_bus', 5: 'veh_2_bus', 6: 'veh_3_bus', 7: 'veh_3_bus',
                                           8: 'veh_3_bus', 9: 'veh_4_bus', 10: 'veh_4_bus', 11: 'veh_4_bus'},
                            'route_id': {0: '1', 1: '1', 2: '1', 3: '1', 4: '1', 5: '1', 6: '2', 7: '2', 8: '2', 9: '2',
                                         10: '2', 11: '2'},
                            'route_name': {0: 'name', 1: 'name', 2: 'name', 3: 'name', 4: 'name', 5: 'name',
                                           6: 'name_2', 7: 'name_2', 8: 'name_2', 9: 'name_2', 10: 'name_2',
                                           11: 'name_2'},
                            'mode': {0: 'bus', 1: 'bus', 2: 'bus', 3: 'bus', 4: 'bus', 5: 'bus', 6: 'bus', 7: 'bus',
                                     8: 'bus', 9: 'bus', 10: 'bus', 11: 'bus'},
                            'from_stop_name': {0: '', 1: '', 2: '', 3: '', 4: '', 5: '', 6: '', 7: '', 8: '', 9: '',
                                               10: '', 11: ''},
                            'to_stop_name': {0: '', 1: '', 2: '', 3: '', 4: '', 5: '', 6: '', 7: '', 8: '', 9: '',
                                             10: '', 11: ''},
                            'service_id': {0: 'service', 1: 'service', 2: 'service', 3: 'service', 4: 'service',
                                           5: 'service', 6: 'service', 7: 'service', 8: 'service', 9: 'service',
                                           10: 'service', 11: 'service'},
                            'service_name': {0: 'name', 1: 'name', 2: 'name', 3: 'name', 4: 'name', 5: 'name',
                                             6: 'name', 7: 'name', 8: 'name', 9: 'name', 10: 'name',
                                             11: 'name'}}).sort_values(
        by=['route_id', 'trip_id', 'departure_time']).reset_index(drop=True)

    assert_frame_equal(df.sort_index(axis=1), correct_df.sort_index(axis=1))


def test_generating_vehicles(schedule):
    schedule.generate_vehicles()
    assert_semantically_equal(schedule.vehicles, {'veh_3_bus': {'type': 'bus'}, 'veh_2_bus': {'type': 'bus'},
                                                  'veh_1_bus': {'type': 'bus'}, 'veh_4_bus': {'type': 'bus'}})


def test_generating_vehicles_with_shared_vehicles_and_consistent_modes(mocker, schedule):
    schedule.vehicles = {}
    mocker.patch.object(DataFrame, 'drop',
                        return_value=DataFrame({'vehicle_id': ['v_1', 'v_2', 'v_1', 'v_2', 'v_3'],
                                                'type': ['bus', 'bus', 'bus', 'bus', 'rail']}))
    schedule.generate_vehicles()
    assert_semantically_equal(schedule.vehicles, {'v_1': {'type': 'bus'}, 'v_2': {'type': 'bus'},
                                                  'v_3': {'type': 'rail'}})


def test_generating_additional_vehicles_by_default(schedule):
    r = Route(
        route_short_name='N55',
        mode='bus',
        trips={'trip_id': ['some_trip_1'],
               'trip_departure_time': ['16:23:00'],
               'vehicle_id': ['some_bus_2']},
        arrival_offsets=['00:00:00', '00:06:00'],
        departure_offsets=['00:00:00', '00:06:00'],
        id='new',
        stops=[schedule.stop('1'),
               schedule.stop('3')]
    )
    schedule.add_route('service', r)
    # change existing vehicle types to be different from mode to test whether they are regenerated with default
    # mode type
    schedule.vehicles = {'veh_3_bus': {'type': '_bus'}, 'veh_4_bus': {'type': '_bus'}, 'veh_1_bus': {'type': '_bus'},
                         'veh_2_bus': {'type': '_bus'}}
    schedule.generate_vehicles()
    assert_semantically_equal(schedule.vehicles, {'veh_3_bus': {'type': '_bus'}, 'veh_4_bus': {'type': '_bus'},
                                                  'veh_1_bus': {'type': '_bus'}, 'veh_2_bus': {'type': '_bus'},
                                                  'some_bus_2': {'type': 'bus'}})


def test_generating_new_vehicles_with_overwite_True(schedule):
    # change existing vehicle types to be different from mode to test whether they are regenerated with default
    # mode type
    schedule.vehicles = {'veh_3_bus': {'type': '_bus'}, 'veh_4_bus': {'type': '_bus'}, 'veh_1_bus': {'type': '_bus'},
                         'veh_2_bus': {'type': '_bus'}}
    schedule.generate_vehicles(overwrite=True)
    assert_semantically_equal(schedule.vehicles, {'veh_3_bus': {'type': 'bus'}, 'veh_4_bus': {'type': 'bus'},
                                                  'veh_1_bus': {'type': 'bus'}, 'veh_2_bus': {'type': 'bus'}})


def test_scale_vehicle_capacity(schedule, tmpdir):
    # assert the initial capacity before scaling
    assert_semantically_equal(schedule.vehicle_types['bus'], {
        'capacity': {'seats': {'persons': '70'}, 'standingRoom': {'persons': '0'}},
        'length': {'meter': '18.0'},
        'width': {'meter': '2.5'},
        'accessTime': {'secondsPerPerson': '0.5'},
        'egressTime': {'secondsPerPerson': '0.5'},
        'doorOperation': {'mode': 'serial'},
        'passengerCarEquivalents': {'pce': '2.8'}})

    # scale the vehicles by 50%
    schedule.scale_vehicle_capacity(0.5, 0.5, tmpdir)

    # assert the scaled capacity post scaling by 50%
    vehicles, vehicle_types = matsim_reader.read_vehicles(os.path.join(tmpdir, "50_perc_vehicles.xml"))
    assert_semantically_equal(vehicle_types['bus'], {
        'capacity': {'seats': {'persons': '35'}, 'standingRoom': {'persons': '0'}},
        'length': {'meter': '18.0'},
        'width': {'meter': '2.5'},
        'accessTime': {'secondsPerPerson': '0.5'},
        'egressTime': {'secondsPerPerson': '0.5'},
        'doorOperation': {'mode': 'serial'},
        'passengerCarEquivalents': {'pce': '1.4'}})


def test_scaling_vehicle_capacity_does_not_affect_original_values(schedule, tmpdir):
    # assert the initial capacity before scaling
    assert_semantically_equal(schedule.vehicle_types['bus'], {
        'capacity': {'seats': {'persons': '70'}, 'standingRoom': {'persons': '0'}},
        'length': {'meter': '18.0'},
        'width': {'meter': '2.5'},
        'accessTime': {'secondsPerPerson': '0.5'},
        'egressTime': {'secondsPerPerson': '0.5'},
        'doorOperation': {'mode': 'serial'},
        'passengerCarEquivalents': {'pce': '2.8'}})

    # scale the vehicles by 50%
    schedule.scale_vehicle_capacity(0.5, 0.5, tmpdir)

    # assert that vehicle scaling does not change the original values in the schedule
    assert_semantically_equal(schedule.vehicle_types['bus'], {
        'capacity': {'seats': {'persons': '70'}, 'standingRoom': {'persons': '0'}},
        'length': {'meter': '18.0'},
        'width': {'meter': '2.5'},
        'accessTime': {'secondsPerPerson': '0.5'},
        'egressTime': {'secondsPerPerson': '0.5'},
        'doorOperation': {'mode': 'serial'},
        'passengerCarEquivalents': {'pce': '2.8'}})


def test_rejects_inconsistent_modes_when_generating_vehicles(mocker, schedule):
    mocker.patch.object(DataFrame, 'drop',
                        return_value=DataFrame({'vehicle_id': ['v_1', 'v_2', 'v_1', 'v_3', 'v_3'],
                                                'type': ['bus', 'bus', 'rail', 'rail', 'rail']}))
    with pytest.raises(InconsistentVehicleModeError) as e:
        schedule.generate_vehicles()
    assert "{'v_1': ['bus', 'rail']}" in str(e.value)


def test_generating_route_trips_dataframe_is_backwards_compatible(schedule, mocker, caplog):
    mocker.patch.object(Schedule, 'trips_to_dataframe')
    schedule.route_trips_to_dataframe(gtfs_day='19700102')
    schedule.trips_to_dataframe.assert_called_once_with('19700102')
    assert_logging_warning_caught_with_message_containing(caplog, '`route_trips_to_dataframe` method is deprecated')


def test_generating_trips_dataframe(schedule):
    df = schedule.trips_to_dataframe(gtfs_day='19700102')
    assert_frame_equal(df.sort_index(axis=1), DataFrame(
        {'mode': {0: 'bus', 1: 'bus', 2: 'bus', 3: 'bus'},
         'service_id': {0: 'service', 1: 'service', 2: 'service', 3: 'service'},
         'route_id': {0: '2', 1: '2', 2: '1', 3: '1'}, 'trip_id': {0: '1', 1: '2', 2: '1', 3: '2'},
         'trip_departure_time': {0: Timestamp('1970-01-02 11:00:00'), 1: Timestamp('1970-01-02 13:00:00'),
                                 2: Timestamp('1970-01-02 13:00:00'), 3: Timestamp('1970-01-02 13:30:00')},
         'vehicle_id': {0: 'veh_3_bus', 1: 'veh_4_bus', 2: 'veh_1_bus', 3: 'veh_2_bus'}}
    ).sort_index(axis=1))


def test_applying_trips_dataframe_accepts_backwards_compatibility(schedule, mocker, caplog):
    mocker.patch.object(Schedule, 'set_trips_dataframe')
    schedule.set_route_trips_dataframe(schedule.trips_to_dataframe())
    schedule.set_trips_dataframe.assert_called_once()
    assert_logging_warning_caught_with_message_containing(caplog, '`set_route_trips_dataframe` method is deprecated')


def test_applying_trips_dataframe(schedule):
    df_to_change = DataFrame(
        {'service_id': {0: 'service', 1: 'service', 2: 'service'},
         'route_id': {0: '2', 1: '2', 2: '1'}, 'trip_id': {0: '2-1', 1: '2-2', 2: '1-1'},
         'trip_departure_time': {0: Timestamp('1970-01-01 10:00:00'), 1: Timestamp('1970-01-01 16:00:00'),
                                 2: Timestamp('1970-01-01 13:23:00')},
         'vehicle_id': {0: 'veh_3_bus', 1: 'veh_1_bus', 2: 'veh_1_bus'}}
    )
    schedule.set_trips_dataframe(df_to_change.copy())

    assert_frame_equal(
        df_to_change.sort_values(by=['route_id', 'trip_id']).sort_index(axis=1),
        schedule.trips_to_dataframe(gtfs_day='19700101').sort_values(by=['route_id', 'trip_id']).sort_index(
            axis=1).drop('mode', axis=1))


def test_generating_trips_headways(schedule):
    df = schedule.trips_headways(gtfs_day='19700102')
    assert_frame_equal(df.sort_index(axis=1), DataFrame(
        {'mode': {0: 'bus', 1: 'bus', 2: 'bus', 3: 'bus'},
         'service_id': {0: 'service', 1: 'service', 2: 'service', 3: 'service'},
         'route_id': {0: '1', 1: '1', 2: '2', 3: '2'}, 'trip_id': {0: '1', 1: '2', 2: '1', 3: '2'},
         'trip_departure_time': {0: Timestamp('1970-01-02 13:00:00'), 1: Timestamp('1970-01-02 13:30:00'),
                                 2: Timestamp('1970-01-02 11:00:00'), 3: Timestamp('1970-01-02 13:00:00')},
         'vehicle_id': {0: 'veh_1_bus', 1: 'veh_2_bus', 2: 'veh_3_bus', 3: 'veh_4_bus'},
         'headway': {0: pd.NaT, 1: Timedelta('0 days 00:30:00'), 2: pd.NaT,
                     3: Timedelta('0 days 02:00:00')},
         'headway_mins': {0: float('nan'), 1: 30.0, 2: float('nan'), 3: 120.0}}
    ).sort_index(axis=1))


def test_generating_route_trips_headways_with_a_time_bound_finds_only_one_trip(schedule):
    df = schedule.trips_headways(gtfs_day='19700102', from_time='10:00:00', to_time='12:00:00')
    assert_frame_equal(df.sort_index(axis=1), DataFrame(
        {'route_id': {2: '2'}, 'service_id': {2: 'service'}, 'mode': {2: 'bus'}, 'trip_id': {2: '1'},
         'trip_departure_time': {2: Timestamp('1970-01-02 11:00:00')}, 'vehicle_id': {2: 'veh_3_bus'},
         'headway': {2: pd.NaT}, 'headway_mins': {2: float('nan')}}
    ).sort_index(axis=1), check_dtype=False)


def test_generating_route_trips_headways_with_a_lower_time_bound_misses_one_trip(schedule):
    df = schedule.trips_headways(gtfs_day='19700102', from_time='12:00:00')
    assert_frame_equal(df.sort_index(axis=1), DataFrame(
        {'mode': {0: 'bus', 1: 'bus', 3: 'bus'},
         'service_id': {0: 'service', 1: 'service', 3: 'service'},
         'route_id': {0: '1', 1: '1', 3: '2'},
         'trip_id': {0: '1', 1: '2', 3: '2'},
         'trip_departure_time': {0: Timestamp('1970-01-02 13:00:00'), 1: Timestamp('1970-01-02 13:30:00'),
                                 3: Timestamp('1970-01-02 13:00:00')},
         'vehicle_id': {0: 'veh_1_bus', 1: 'veh_2_bus', 3: 'veh_4_bus'},
         'headway': {0: pd.NaT, 1: Timedelta('0 days 00:30:00'), 3: Timedelta('0 days 02:00:00')},
         'headway_mins': {0: float('nan'), 1: 30.0, 3: 120.0}}
    ).sort_index(axis=1))


def test_generating_route_trips_headways_with_an_upper_time_bound_misses_one_trip(schedule):
    df = schedule.trips_headways(gtfs_day='19700102', to_time='13:00:00')
    assert_frame_equal(df.sort_index(axis=1), DataFrame(
        {'mode': {0: 'bus', 2: 'bus', 3: 'bus'},
         'service_id': {0: 'service', 2: 'service', 3: 'service'},
         'route_id': {0: '1', 2: '2', 3: '2'},
         'trip_id': {0: '1', 2: '1', 3: '2'},
         'trip_departure_time': {0: Timestamp('1970-01-02 13:00:00'), 2: Timestamp('1970-01-02 11:00:00'),
                                 3: Timestamp('1970-01-02 13:00:00')},
         'vehicle_id': {0: 'veh_1_bus', 2: 'veh_3_bus', 3: 'veh_4_bus'},
         'headway': {0: pd.NaT, 2: pd.NaT, 3: Timedelta('0 days 02:00:00')},
         'headway_mins': {0: float('nan'), 2: float('nan'), 3: 120.0}}
    ).sort_index(axis=1))


def test_generating_headways_for_schedule(schedule):
    df = schedule.headway_stats(gtfs_day='19700102')
    assert_frame_equal(df.sort_index(axis=1), DataFrame(
        {'service_id': {0: 'service', 1: 'service'}, 'route_id': {0: '1', 1: '2'}, 'mode': {0: 'bus', 1: 'bus'},
         'mean_headway_mins': {0: 30.0, 1: 120.0}, 'std_headway_mins': {0: float('nan'), 1: float('nan')},
         'max_headway_mins': {0: 30.0, 1: 120.0}, 'min_headway_mins': {0: 30.0, 1: 120.0}, 'trip_count': {0: 2, 1: 2}}
    ).sort_index(axis=1))


def test_generating_headways_for_service(schedule):
    df = schedule['service'].headway_stats(gtfs_day='19700102')
    assert_frame_equal(df.sort_index(axis=1), DataFrame(
        {'service_id': {0: 'service', 1: 'service'}, 'route_id': {0: '1', 1: '2'}, 'mode': {0: 'bus', 1: 'bus'},
         'mean_headway_mins': {0: 30.0, 1: 120.0}, 'std_headway_mins': {0: float('nan'), 1: float('nan')},
         'max_headway_mins': {0: 30.0, 1: 120.0}, 'min_headway_mins': {0: 30.0, 1: 120.0}, 'trip_count': {0: 2, 1: 2}}
    ).sort_index(axis=1))


def test_generating_headways_for_route(schedule):
    df = schedule.route('1').headway_stats(gtfs_day='19700102')
    assert_frame_equal(df.sort_index(axis=1), DataFrame(
        {'route_id': {0: '1'}, 'mode': {0: 'bus'},
         'mean_headway_mins': {0: 30.0}, 'std_headway_mins': {0: float('nan')},
         'max_headway_mins': {0: 30.0}, 'min_headway_mins': {0: 30.0}, 'trip_count': {0: 2}}
    ).sort_index(axis=1))


def test_generating_headways_with_a_time_bound_finds_only_one_trip(schedule):
    df = schedule.headway_stats(gtfs_day='19700102', from_time='10:00:00', to_time='12:00:00')
    assert_frame_equal(df.sort_index(axis=1), DataFrame(
        {'service_id': {0: 'service'}, 'route_id': {0: '2'}, 'mode': {0: 'bus'}, 'mean_headway_mins': {0: float('nan')},
         'std_headway_mins': {0: float('nan')}, 'max_headway_mins': {0: float('nan')}, 'min_headway_mins': {0: float('nan')},
         'trip_count': {0: 1}}
    ).sort_index(axis=1))


def test_generating_headways_with_a_lower_time_bound_misses_one_trip(schedule):
    df = schedule.headway_stats(gtfs_day='19700102', from_time='12:00:00')
    assert_frame_equal(df.sort_index(axis=1), DataFrame(
        {'service_id': {0: 'service', 1: 'service'}, 'route_id': {0: '1', 1: '2'}, 'mode': {0: 'bus', 1: 'bus'},
         'mean_headway_mins': {0: 30.0, 1: 120.0}, 'std_headway_mins': {0: float('nan'), 1: float('nan')},
         'max_headway_mins': {0: 30.0, 1: 120.0}, 'min_headway_mins': {0: 30.0, 1: 120.0},
         'trip_count': {0: 2, 1: 1}}
    ).sort_index(axis=1))


def test_generating_headways_with_an_upper_time_bound_misses_one_trip(schedule):
    df = schedule.headway_stats(gtfs_day='19700102', to_time='13:00:00')
    assert_frame_equal(df.sort_index(axis=1), DataFrame(
        {'service_id': {0: 'service', 1: 'service'}, 'route_id': {0: '1', 1: '2'}, 'mode': {0: 'bus', 1: 'bus'},
         'mean_headway_mins': {0: float('nan'), 1: 120.0}, 'std_headway_mins': {0: float('nan'), 1: float('nan')},
         'max_headway_mins': {0: float('nan'), 1: 120.0}, 'min_headway_mins': {0: float('nan'), 1: 120.0},
         'trip_count': {0: 1, 1: 2}}
    ).sort_index(axis=1))


def test_generating_trip_departures():
    from genet.schedule_elements import generate_trip_departures_from_headway
    trip_deps = generate_trip_departures_from_headway(
        {('01:00:00', '02:00:00'): 20, ('02:00:00', '03:00:00'): 30}
    )
    assert {t.strftime("%H:%M:%S") for t in trip_deps} == {'01:20:00', '01:00:00', '01:40:00', '02:30:00', '03:00:00',
                                                           '02:00:00'}


def test_generating_trips_dataframe_from_headway(schedule):
    df = schedule.generate_trips_dataframe_from_headway(
        '1', {('01:00:00', '02:00:00'): 20, ('02:00:00', '03:00:00'): 30})
    assert_frame_equal(
        df.sort_values(by='trip_id').reset_index(drop=True),
        DataFrame(
            {'trip_id': {0: '1_01:20:00', 1: '1_02:00:00', 2: '1_03:00:00', 3: '1_02:30:00', 4: '1_01:40:00',
                         5: '1_01:00:00'},
             'trip_departure_time': {0: Timestamp('1970-01-01 01:20:00'), 1: Timestamp('1970-01-01 02:00:00'),
                                     2: Timestamp('1970-01-01 03:00:00'), 3: Timestamp('1970-01-01 02:30:00'),
                                     4: Timestamp('1970-01-01 01:40:00'), 5: Timestamp('1970-01-01 01:00:00')},
             'vehicle_id': {0: 'veh_bus_1_01:20:00', 1: 'veh_bus_1_02:00:00', 2: 'veh_bus_1_03:00:00',
                            3: 'veh_bus_1_02:30:00', 4: 'veh_bus_1_01:40:00', 5: 'veh_bus_1_01:00:00'},
             'route_id': {0: '1', 1: '1', 2: '1', 3: '1', 4: '1', 5: '1'},
             'service_id': {0: 'service', 1: 'service', 2: 'service', 3: 'service', 4: 'service', 5: 'service'}}
        ).sort_values(by='trip_id').reset_index(drop=True)
    )


def test_generating_trips_from_headway_creates_trips_with_vehicles(schedule):
    assert_semantically_equal(
        schedule.route('1').trips,
        {'trip_id': ['1', '2'],
         'trip_departure_time': ['13:00:00', '13:30:00'],
         'vehicle_id': ['veh_1_bus', 'veh_2_bus']}
    )

    schedule.generate_trips_from_headway('1', {('01:00:00', '02:00:00'): 20, ('02:00:00', '03:00:00'): 30})

    assert_semantically_equal(
        schedule.route('1').trips,
        {'trip_id': ['1_01:00:00', '1_01:20:00', '1_01:40:00', '1_02:00:00', '1_02:30:00', '1_03:00:00'],
         'trip_departure_time': ['01:00:00', '01:20:00', '01:40:00', '02:00:00', '02:30:00', '03:00:00'],
         'vehicle_id': ['veh_bus_1_01:00:00', 'veh_bus_1_01:20:00', 'veh_bus_1_01:40:00', 'veh_bus_1_02:00:00',
                        'veh_bus_1_02:30:00', 'veh_bus_1_03:00:00']}
    )


def test_generating_trips_from_headway_preserves_graph_schema(schedule):
    verify_graph_schema(schedule.graph())

    schedule.generate_trips_from_headway('1', {('01:00:00', '02:00:00'): 20, ('02:00:00', '03:00:00'): 30})

    verify_graph_schema(schedule.graph())


def test_generating_trips_from_headway_updates_vehicles(schedule):
    assert_semantically_equal(
        schedule.vehicles,
        {'veh_3_bus': {'type': 'bus'},
         'veh_4_bus': {'type': 'bus'},
         'veh_1_bus': {'type': 'bus'},
         'veh_2_bus': {'type': 'bus'}}
    )

    schedule.generate_trips_from_headway('1', {('01:00:00', '02:00:00'): 20, ('02:00:00', '03:00:00'): 30})

    assert_semantically_equal(
        schedule.vehicles,
        {'veh_bus_1_01:00:00': {'type': 'bus'},
         'veh_bus_1_02:00:00': {'type': 'bus'},
         'veh_bus_1_01:40:00': {'type': 'bus'},
         'veh_bus_1_01:20:00': {'type': 'bus'},
         'veh_bus_1_03:00:00': {'type': 'bus'},
         'veh_bus_1_02:30:00': {'type': 'bus'},
         'veh_3_bus': {'type': 'bus'},
         'veh_4_bus': {'type': 'bus'}}
    )


@pytest.fixture()
def schedule_for_speed_testing():
    return {
        'schedule': Schedule(epsg='epsg:27700', services=[
            Service(id='service',
                    routes=[
                        Route(route_short_name='route', mode='bus',
                              stops=[Stop(id='0', x=1, y=10, epsg='epsg:27700'),
                                     Stop(id='1', x=1, y=20, epsg='epsg:27700'),
                                     Stop(id='2', x=1, y=30, epsg='epsg:27700')],
                              trips={'trip_id': ['t1'], 'trip_departure_time': ['05:40:00'],
                                     'vehicle_id': ['veh_1_bus']},
                              arrival_offsets=['00:00:00', '00:00:01', '00:00:03'],
                              departure_offsets=['00:00:00', '00:00:01', '00:00:03'])
                    ])
        ]),
        'network_factor': 1.3,
        'stops_distance': 10 / (1.3),
        'expected_trips_with_stops_and_speed_df': GeoDataFrame(
            {'mode': {0: 'bus', 1: 'bus'}, 'service_id': {0: 'service', 1: 'service'},
             'route_name': {0: 'route', 1: 'route'}, 'route_id': {0: 'service_0', 1: 'service_0'},
             'to_stop': {0: '1', 1: '2'}, 'from_stop_name': {0: '', 1: ''}, 'from_stop': {0: '0', 1: '1'},
             'service_name': {0: 'route', 1: 'route'}, 'to_stop_name': {0: '', 1: ''},
             'speed': {0: 10.0, 1: 5.0}, 'routed_speed': {0: float('nan'), 1: float('nan')},
             'geometry': {0: LineString([(1,10),(1,20)]), 1: LineString([(1,20),(1,30)])}},
            crs='epsg:27700'
        ),
        'expected_route_speeds': {'service_0': 7.5},
        'expected_speed_report': {}
    }


@pytest.fixture()
def schedule_for_testing_0_speed_case():
    return {
        'schedule': Schedule(epsg='epsg:27700', services=[
            Service(id='service',
                    routes=[
                        Route(route_short_name='route', mode='bus',
                              stops=[Stop(id='0', x=1, y=10, epsg='epsg:27700'),
                                     Stop(id='1', x=1, y=10.001, epsg='epsg:27700')],
                              trips={'trip_id': ['t1'], 'trip_departure_time': ['05:40:00'],
                                     'vehicle_id': ['veh_1_bus']},
                              arrival_offsets=['00:00:00', '00:00:01'],
                              departure_offsets=['00:00:00', '00:00:01'])
                    ])
        ]),
        'network_factor': 1.3,
        'stops_distance': 0,
        'expected_trips_with_stops_and_speed_df': GeoDataFrame(
            {'mode': {0: 'bus'}, 'service_id': {0: 'service'},
             'route_name': {0: 'route'}, 'route_id': {0: 'service_0'},
             'to_stop': {0: '1'}, 'from_stop_name': {0: ''}, 'from_stop': {0: '0'},
             'service_name': {0: 'route'}, 'to_stop_name': {0: ''},
             'speed': {0: 0.0}, 'routed_speed': {0: float('nan')},
             'geometry': {0: LineString([(1, 10), (1, 10.001)])}},
            crs='epsg:27700'
        ),
        'expected_route_speeds': {'service_0': 0.0},
        'expected_speed_report': {'0_m/s': {'routes': ['service_0']}}
    }


@pytest.fixture()
def schedule_for_testing_inf_speed_case():
    return {
        'schedule': Schedule(epsg='epsg:27700', services=[
            Service(id='service',
                    routes=[
                        Route(route_short_name='route', mode='bus',
                              stops=[Stop(id='0', x=1, y=10, epsg='epsg:27700'),
                                     Stop(id='1', x=1, y=30, epsg='epsg:27700')],
                              trips={'trip_id': ['t1'], 'trip_departure_time': ['05:40:00'],
                                     'vehicle_id': ['veh_1_bus']},
                              arrival_offsets=['00:00:00', '00:00:00'],
                              departure_offsets=['00:00:00', '00:00:00'])
                    ])
        ]),
        'network_factor': 1.3,
        'stops_distance': 20,
        'expected_trips_with_stops_and_speed_df': GeoDataFrame(
            {'mode': {0: 'bus'}, 'service_id': {0: 'service'},
             'route_name': {0: 'route'}, 'route_id': {0: 'service_0'},
             'to_stop': {0: '1'}, 'from_stop_name': {0: ''}, 'from_stop': {0: '0'},
             'service_name': {0: 'route'}, 'to_stop_name': {0: ''},
             'speed': {0: math.inf}, 'routed_speed': {0: float('nan')},
             'geometry': {0: LineString([(1,10),(1,30)])}},
            crs='epsg:27700'
        ),
        'expected_route_speeds': {'service_0': math.inf},
        'expected_speed_report': {'inf_m/s': {'routes': ['service_0']}}
    }

@pytest.fixture()
def schedule_cases_for_speed_testing(schedule_for_speed_testing, schedule_for_testing_0_speed_case, schedule_for_testing_inf_speed_case):
    return {
        'normal_speeds': schedule_for_speed_testing,
        '0_speed': schedule_for_testing_0_speed_case,
        'inf_speed': schedule_for_testing_inf_speed_case
    }


@pytest.mark.parametrize("schedule_case", ['normal_speeds', '0_speed', 'inf_speed'])
def test_speed_calculation_for_schedule(schedule_case, schedule_cases_for_speed_testing, mocker):
    schedule_fixture = schedule_cases_for_speed_testing[schedule_case]
    network_factor = schedule_fixture['network_factor']
    mocker.patch.object(spatial, 'distance_between_s2cellids',
                        return_value=schedule_fixture['stops_distance'])
    assert_geodataframe_equal(
        schedule_fixture['schedule'].speed_geodataframe(network_factor=network_factor).sort_index(
            axis=1),
        schedule_fixture['expected_trips_with_stops_and_speed_df'].sort_index(axis=1)
    )


@pytest.mark.parametrize("schedule_case", ['normal_speeds', '0_speed', 'inf_speed'])
def test_average_speed_calculation_for_each_route_in_schedule(schedule_case, schedule_cases_for_speed_testing, mocker):
    schedule_fixture = schedule_cases_for_speed_testing[schedule_case]
    network_factor = schedule_fixture['network_factor']
    mocker.patch.object(spatial, 'distance_between_s2cellids',
                        return_value=schedule_fixture['stops_distance'])
    assert schedule_fixture['schedule'].average_route_speeds(network_factor=network_factor) == \
           schedule_fixture['expected_route_speeds']


@pytest.mark.parametrize("schedule_case", ['normal_speeds', '0_speed', 'inf_speed'])
def test_reporting_on_extreme_speed_values(schedule_case, schedule_cases_for_speed_testing, mocker):
    schedule_fixture = schedule_cases_for_speed_testing[schedule_case]
    network_factor = schedule_fixture['network_factor']
    mocker.patch.object(spatial, 'distance_between_s2cellids',
                        return_value=schedule_fixture['stops_distance'])
    assert schedule_fixture['schedule'].generate_validation_report()['schedule_level']['speeds'] == \
           schedule_fixture['expected_speed_report']


def test_overlapping_vehicles(schedule):
    overlapping_vehs = schedule.overlapping_vehicle_ids(vehicles={'veh_2_bus': {'type': 'bus'}})
    assert set(overlapping_vehs) == {'veh_2_bus'}


def test_overlapping_vehicle_types(schedule):
    overlapping_vehs = schedule.overlapping_vehicle_types(vehicle_types={'rail': {
        'capacity': {'seats': {'persons': '500'}, 'standingRoom': {'persons': '500'}},
        'length': {'meter': '36.0'}, 'width': {'meter': '2.4'},
        'accessTime': {'secondsPerPerson': '0.25'},
        'egressTime': {'secondsPerPerson': '0.25'},
        'doorOperation': {'mode': 'serial'},
        'passengerCarEquivalents': {'pce': '5.2'}}})
    assert set(overlapping_vehs) == {'rail'}


def test_updating_vehicles_with_no_overlap(schedule):
    schedule.update_vehicles(vehicles={'v_1': {'type': 'deathstar'}},
                             vehicle_types={'deathstar': {
                                 'capacity': {'seats': {'persons': '5'},
                                              'standingRoom': {'persons': '1000'}},
                                 'length': {'meter': '20000.0'},
                                 'width': {'meter': '20000'},
                                 'accessTime': {'secondsPerPerson': '0.25'},
                                 'egressTime': {'secondsPerPerson': '0.25'},
                                 'doorOperation': {'mode': 'serial'},
                                 'passengerCarEquivalents': {'pce': '1000'}}})
    assert_semantically_equal(schedule.vehicles, {'v_1': {'type': 'deathstar'},
                                                  'veh_4_bus': {'type': 'bus'},
                                                  'veh_3_bus': {'type': 'bus'},
                                                  'veh_2_bus': {'type': 'bus'},
                                                  'veh_1_bus': {'type': 'bus'}})
    assert_semantically_equal(schedule.vehicle_types, {
        'deathstar': {
            'capacity': {'seats': {'persons': '5'},
                         'standingRoom': {'persons': '1000'}},
            'length': {'meter': '20000.0'},
            'width': {'meter': '20000'},
            'accessTime': {'secondsPerPerson': '0.25'},
            'egressTime': {'secondsPerPerson': '0.25'},
            'doorOperation': {'mode': 'serial'},
            'passengerCarEquivalents': {'pce': '1000'}},
        'bus': {'capacity': {'seats': {'persons': '70'}, 'standingRoom': {'persons': '0'}}, 'length': {'meter': '18.0'},
                'width': {'meter': '2.5'}, 'accessTime': {'secondsPerPerson': '0.5'},
                'egressTime': {'secondsPerPerson': '0.5'}, 'doorOperation': {'mode': 'serial'},
                'passengerCarEquivalents': {'pce': '2.8'}},
        'rail': {'capacity': {'seats': {'persons': '1000'}, 'standingRoom': {'persons': '0'}},
                 'length': {'meter': '200.0'}, 'width': {'meter': '2.8'}, 'accessTime': {'secondsPerPerson': '0.25'},
                 'egressTime': {'secondsPerPerson': '0.25'}, 'doorOperation': {'mode': 'serial'},
                 'passengerCarEquivalents': {'pce': '27.1'}},
        'subway': {'capacity': {'seats': {'persons': '1000'}, 'standingRoom': {'persons': '0'}},
                   'length': {'meter': '30.0'}, 'width': {'meter': '2.45'}, 'accessTime': {'secondsPerPerson': '0.1'},
                   'egressTime': {'secondsPerPerson': '0.1'}, 'doorOperation': {'mode': 'serial'},
                   'passengerCarEquivalents': {'pce': '4.4'}},
        'ferry': {'capacity': {'seats': {'persons': '250'}, 'standingRoom': {'persons': '0'}},
                  'length': {'meter': '50.0'}, 'width': {'meter': '6.0'}, 'accessTime': {'secondsPerPerson': '0.5'},
                  'egressTime': {'secondsPerPerson': '0.5'}, 'doorOperation': {'mode': 'serial'},
                  'passengerCarEquivalents': {'pce': '7.1'}},
        'tram': {'capacity': {'seats': {'persons': '180'}, 'standingRoom': {'persons': '0'}},
                 'length': {'meter': '36.0'}, 'width': {'meter': '2.4'}, 'accessTime': {'secondsPerPerson': '0.25'},
                 'egressTime': {'secondsPerPerson': '0.25'}, 'doorOperation': {'mode': 'serial'},
                 'passengerCarEquivalents': {'pce': '5.2'}},
        'funicular': {'capacity': {'seats': {'persons': '180'}, 'standingRoom': {'persons': '0'}},
                      'length': {'meter': '36.0'}, 'width': {'meter': '2.4'},
                      'accessTime': {'secondsPerPerson': '0.25'}, 'egressTime': {'secondsPerPerson': '0.25'},
                      'doorOperation': {'mode': 'serial'}, 'passengerCarEquivalents': {'pce': '5.2'}},
        'gondola': {'capacity': {'seats': {'persons': '250'}, 'standingRoom': {'persons': '0'}},
                    'length': {'meter': '50.0'}, 'width': {'meter': '6.0'}, 'accessTime': {'secondsPerPerson': '0.5'},
                    'egressTime': {'secondsPerPerson': '0.5'}, 'doorOperation': {'mode': 'serial'},
                    'passengerCarEquivalents': {'pce': '7.1'}},
        'cablecar': {'capacity': {'seats': {'persons': '250'}, 'standingRoom': {'persons': '0'}},
                     'length': {'meter': '50.0'}, 'width': {'meter': '6.0'}, 'accessTime': {'secondsPerPerson': '0.5'},
                     'egressTime': {'secondsPerPerson': '0.5'}, 'doorOperation': {'mode': 'serial'},
                     'passengerCarEquivalents': {'pce': '7.1'}}})


def test_updating_vehicles_with_clashes_and_overwrite_on(schedule):
    schedule.update_vehicles(vehicles={'veh_2_bus': {'type': 'tram'}},
                             vehicle_types={'tram': {
                                 'capacity': {'seats': {'persons': '5000'}, 'standingRoom': {'persons': '5000'}},
                                 'length': {'meter': '36.0'}, 'width': {'meter': '2.4'},
                                 'accessTime': {'secondsPerPerson': '0.25'},
                                 'egressTime': {'secondsPerPerson': '0.25'},
                                 'doorOperation': {'mode': 'serial'},
                                 'passengerCarEquivalents': {'pce': '5.2'}}})
    assert_semantically_equal(schedule.vehicles, {'veh_4_bus': {'type': 'bus'},
                                                  'veh_3_bus': {'type': 'bus'},
                                                  'veh_2_bus': {'type': 'tram'},
                                                  'veh_1_bus': {'type': 'bus'}})
    assert_semantically_equal(schedule.vehicle_types['tram'],
                              {
                                  'capacity': {'seats': {'persons': '5000'}, 'standingRoom': {'persons': '5000'}},
                                  'length': {'meter': '36.0'}, 'width': {'meter': '2.4'},
                                  'accessTime': {'secondsPerPerson': '0.25'},
                                  'egressTime': {'secondsPerPerson': '0.25'},
                                  'doorOperation': {'mode': 'serial'},
                                  'passengerCarEquivalents': {'pce': '5.2'}})


def test_updating_vehicles_with_clashes_and_overwrite_off(schedule):
    schedule.update_vehicles(vehicles={'veh_2_bus': {'type': 'tram'}},
                             vehicle_types={'tram': {
                                 'capacity': {'seats': {'persons': '5000'}, 'standingRoom': {'persons': '5000'}},
                                 'length': {'meter': '36.0'}, 'width': {'meter': '2.4'},
                                 'accessTime': {'secondsPerPerson': '0.25'},
                                 'egressTime': {'secondsPerPerson': '0.25'},
                                 'doorOperation': {'mode': 'serial'},
                                 'passengerCarEquivalents': {'pce': '5.2'}}},
                             overwrite=False)
    assert_semantically_equal(schedule.vehicles, {'veh_4_bus': {'type': 'bus'},
                                                  'veh_3_bus': {'type': 'bus'},
                                                  'veh_2_bus': {'type': 'bus'},
                                                  'veh_1_bus': {'type': 'bus'}})
    assert_semantically_equal(schedule.vehicle_types['tram'],
                              {'capacity': {'seats': {'persons': '180'}, 'standingRoom': {'persons': '0'}},
                               'length': {'meter': '36.0'}, 'width': {'meter': '2.4'},
                               'accessTime': {'secondsPerPerson': '0.25'},
                               'egressTime': {'secondsPerPerson': '0.25'}, 'doorOperation': {'mode': 'serial'},
                               'passengerCarEquivalents': {'pce': '5.2'}})


def test_validating_vehicle_definitions(schedule):
    assert schedule.validate_vehicle_definitions()


def test_validate_vehicle_definitions_warns_of_missing_vehicle_types(schedule, caplog):
    del schedule.vehicle_types['bus']
    schedule.validate_vehicle_definitions()
    assert caplog.records[0].levelname == 'WARNING'
    assert 'bus' in caplog.records[0].message
    assert caplog.records[1].levelname == 'WARNING'
    for veh in {'veh_4_bus', 'veh_3_bus', 'veh_2_bus', 'veh_1_bus'}:
        assert veh in caplog.records[1].message
    assert "{'type': 'bus'}" in caplog.records[1].message


def test_correct_schedule_does_not_have_missing_vehicles(schedule):
    vehicle_information = schedule.get_missing_vehicle_information()
    assert vehicle_information == {
        'missing_vehicle_types': set(),
        'vehicles_affected': {}
    }


def test_schedule_with_missing_vehicle_type_returns_expected_information():
    route_1 = Route(route_short_name='name',
                    mode='bus', id='1',
                    stops=[Stop(id='1', x=4, y=2, epsg='epsg:27700'), Stop(id='2', x=1, y=2, epsg='epsg:27700'),
                           Stop(id='3', x=3, y=3, epsg='epsg:27700'), Stop(id='4', x=7, y=5, epsg='epsg:27700')],
                    trips={'trip_id': ['1', '2'],
                           'trip_departure_time': ['13:00:00', '13:30:00'],
                           'vehicle_id': ['veh_1_bus', 'veh_2_bus']},
                    arrival_offsets=['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                    departure_offsets=['00:00:00', '00:05:00', '00:09:00', '00:15:00'])
    route_2 = Route(route_short_name='name_2',
                    mode='bus', id='2',
                    stops=[Stop(id='5', x=4, y=2, epsg='epsg:27700'), Stop(id='6', x=1, y=2, epsg='epsg:27700'),
                           Stop(id='7', x=3, y=3, epsg='epsg:27700'), Stop(id='8', x=7, y=5, epsg='epsg:27700')],
                    trips={'trip_id': ['1', '2'],
                           'trip_departure_time': ['11:00:00', '13:00:00'],
                           'vehicle_id': ['veh_3_bus', 'veh_4_bus']},
                    arrival_offsets=['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                    departure_offsets=['00:00:00', '00:05:00', '00:09:00', '00:15:00'])
    service = Service(id='service', routes=[route_1, route_2])
    schedule = Schedule(epsg='epsg:27700', services=[service])
    del schedule.vehicle_types['bus']

    vehicle_information = schedule.get_missing_vehicle_information()
    assert vehicle_information == {
        'missing_vehicle_types': {'bus'},
        'vehicles_affected': {'veh_1_bus': {'type': 'bus'},
                              'veh_2_bus': {'type': 'bus'},
                              'veh_3_bus': {'type': 'bus'},
                              'veh_4_bus': {'type': 'bus'}}
    }


def test_reading_vehicle_types_from_a_yml_config(vehicle_definitions_config_path):
    vehicle_types = read_vehicle_types(vehicle_definitions_config_path)
    assert_semantically_equal(vehicle_types, {
        'bus': {'capacity': {'seats': {'persons': '70'}, 'standingRoom': {'persons': '0'}}, 'length': {'meter': '18.0'},
                'width': {'meter': '2.5'}, 'accessTime': {'secondsPerPerson': '0.5'},
                'egressTime': {'secondsPerPerson': '0.5'}, 'doorOperation': {'mode': 'serial'},
                'passengerCarEquivalents': {'pce': '2.8'}},
        'rail': {'capacity': {'seats': {'persons': '1000'}, 'standingRoom': {'persons': '0'}},
                 'length': {'meter': '200.0'}, 'width': {'meter': '2.8'}, 'accessTime': {'secondsPerPerson': '0.25'},
                 'egressTime': {'secondsPerPerson': '0.25'}, 'doorOperation': {'mode': 'serial'},
                 'passengerCarEquivalents': {'pce': '27.1'}},
        'subway': {'capacity': {'seats': {'persons': '1000'}, 'standingRoom': {'persons': '0'}},
                   'length': {'meter': '30.0'}, 'width': {'meter': '2.45'}, 'accessTime': {'secondsPerPerson': '0.1'},
                   'egressTime': {'secondsPerPerson': '0.1'}, 'doorOperation': {'mode': 'serial'},
                   'passengerCarEquivalents': {'pce': '4.4'}},
        'ferry': {'capacity': {'seats': {'persons': '250'}, 'standingRoom': {'persons': '0'}},
                  'length': {'meter': '50.0'}, 'width': {'meter': '6.0'}, 'accessTime': {'secondsPerPerson': '0.5'},
                  'egressTime': {'secondsPerPerson': '0.5'}, 'doorOperation': {'mode': 'serial'},
                  'passengerCarEquivalents': {'pce': '7.1'}},
        'tram': {'capacity': {'seats': {'persons': '180'}, 'standingRoom': {'persons': '0'}},
                 'length': {'meter': '36.0'}, 'width': {'meter': '2.4'}, 'accessTime': {'secondsPerPerson': '0.25'},
                 'egressTime': {'secondsPerPerson': '0.25'}, 'doorOperation': {'mode': 'serial'},
                 'passengerCarEquivalents': {'pce': '5.2'}},
        'funicular': {'capacity': {'seats': {'persons': '180'}, 'standingRoom': {'persons': '0'}},
                      'length': {'meter': '36.0'}, 'width': {'meter': '2.4'},
                      'accessTime': {'secondsPerPerson': '0.25'}, 'egressTime': {'secondsPerPerson': '0.25'},
                      'doorOperation': {'mode': 'serial'}, 'passengerCarEquivalents': {'pce': '5.2'}},
        'gondola': {'capacity': {'seats': {'persons': '250'}, 'standingRoom': {'persons': '0'}},
                    'length': {'meter': '50.0'}, 'width': {'meter': '6.0'}, 'accessTime': {'secondsPerPerson': '0.5'},
                    'egressTime': {'secondsPerPerson': '0.5'}, 'doorOperation': {'mode': 'serial'},
                    'passengerCarEquivalents': {'pce': '7.1'}},
        'cablecar': {'capacity': {'seats': {'persons': '250'}, 'standingRoom': {'persons': '0'}},
                     'length': {'meter': '50.0'}, 'width': {'meter': '6.0'}, 'accessTime': {'secondsPerPerson': '0.5'},
                     'egressTime': {'secondsPerPerson': '0.5'}, 'doorOperation': {'mode': 'serial'},
                     'passengerCarEquivalents': {'pce': '7.1'}}})


@pytest.fixture()
def json_schedule():
    return {'schedule': {'stops': {
        '5': {'y': 2.0, 'name': '', 'id': '5', 'x': 4.0, 'lon': -7.557106577683727, 'lat': 49.76682779861249,
              's2_id': 5205973754090531959},
        '6': {'y': 2.0, 'name': '', 'id': '6', 'x': 1.0, 'lon': -7.557148039524952, 'lat': 49.766825803756994,
              's2_id': 5205973754090365183},
        '7': {'y': 3.0, 'name': '', 'id': '7', 'x': 3.0, 'lon': -7.557121424907424, 'lat': 49.76683608549253,
              's2_id': 5205973754090203369},
        '8': {'y': 5.0, 'name': '', 'id': '8', 'x': 7.0, 'lon': -7.5570681956375, 'lat': 49.766856648946295,
              's2_id': 5205973754097123809},
        '3': {'y': 3.0, 'name': '', 'id': '3', 'x': 3.0, 'lon': -7.557121424907424, 'lat': 49.76683608549253,
              's2_id': 5205973754090203369},
        '4': {'y': 5.0, 'name': '', 'id': '4', 'x': 7.0, 'lon': -7.5570681956375, 'lat': 49.766856648946295,
              's2_id': 5205973754097123809},
        '1': {'y': 2.0, 'name': '', 'id': '1', 'x': 4.0, 'lon': -7.557106577683727, 'lat': 49.76682779861249,
              's2_id': 5205973754090531959},
        '2': {'y': 2.0, 'name': '', 'id': '2', 'x': 1.0, 'lon': -7.557148039524952, 'lat': 49.766825803756994,
              's2_id': 5205973754090365183}},
        'services': {'service': {'id': 'service', 'name': 'name', 'routes': {
            '1': {'route_short_name': 'name', 'mode': 'bus',
                  'trips': {'trip_id': ['1', '2'], 'trip_departure_time': ['13:00:00', '13:30:00'],
                            'vehicle_id': ['veh_1_bus', 'veh_2_bus']},
                  'arrival_offsets': ['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                  'departure_offsets': ['00:00:00', '00:05:00', '00:09:00', '00:15:00'], 'route_long_name': '',
                  'id': '1', 'route': [], 'await_departure': [], 'ordered_stops': ['1', '2', '3', '4']},
            '2': {'route_short_name': 'name_2', 'mode': 'bus',
                  'trips': {'trip_id': ['1', '2'], 'trip_departure_time': ['11:00:00', '13:00:00'],
                            'vehicle_id': ['veh_3_bus', 'veh_4_bus']},
                  'arrival_offsets': ['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                  'departure_offsets': ['00:00:00', '00:05:00', '00:09:00', '00:15:00'], 'route_long_name': '',
                  'id': '2', 'route': [], 'await_departure': [], 'ordered_stops': ['5', '6', '7', '8']}}}}},
        'vehicles': {'vehicle_types': {
            'bus': {'capacity': {'seats': {'persons': '70'}, 'standingRoom': {'persons': '0'}},
                    'length': {'meter': '18.0'}, 'width': {'meter': '2.5'}, 'accessTime': {'secondsPerPerson': '0.5'},
                    'egressTime': {'secondsPerPerson': '0.5'}, 'doorOperation': {'mode': 'serial'},
                    'passengerCarEquivalents': {'pce': '2.8'}},
            'rail': {'capacity': {'seats': {'persons': '1000'}, 'standingRoom': {'persons': '0'}},
                     'length': {'meter': '200.0'}, 'width': {'meter': '2.8'},
                     'accessTime': {'secondsPerPerson': '0.25'}, 'egressTime': {'secondsPerPerson': '0.25'},
                     'doorOperation': {'mode': 'serial'}, 'passengerCarEquivalents': {'pce': '27.1'}},
            'subway': {'capacity': {'seats': {'persons': '1000'}, 'standingRoom': {'persons': '0'}},
                       'length': {'meter': '30.0'}, 'width': {'meter': '2.45'},
                       'accessTime': {'secondsPerPerson': '0.1'}, 'egressTime': {'secondsPerPerson': '0.1'},
                       'doorOperation': {'mode': 'serial'}, 'passengerCarEquivalents': {'pce': '4.4'}},
            'ferry': {'capacity': {'seats': {'persons': '250'}, 'standingRoom': {'persons': '0'}},
                      'length': {'meter': '50.0'}, 'width': {'meter': '6.0'},
                      'accessTime': {'secondsPerPerson': '0.5'}, 'egressTime': {'secondsPerPerson': '0.5'},
                      'doorOperation': {'mode': 'serial'}, 'passengerCarEquivalents': {'pce': '7.1'}},
            'tram': {'capacity': {'seats': {'persons': '180'}, 'standingRoom': {'persons': '0'}},
                     'length': {'meter': '36.0'}, 'width': {'meter': '2.4'},
                     'accessTime': {'secondsPerPerson': '0.25'}, 'egressTime': {'secondsPerPerson': '0.25'},
                     'doorOperation': {'mode': 'serial'}, 'passengerCarEquivalents': {'pce': '5.2'}},
            'funicular': {'capacity': {'seats': {'persons': '180'}, 'standingRoom': {'persons': '0'}},
                          'length': {'meter': '36.0'}, 'width': {'meter': '2.4'},
                          'accessTime': {'secondsPerPerson': '0.25'}, 'egressTime': {'secondsPerPerson': '0.25'},
                          'doorOperation': {'mode': 'serial'}, 'passengerCarEquivalents': {'pce': '5.2'}},
            'gondola': {'capacity': {'seats': {'persons': '250'}, 'standingRoom': {'persons': '0'}},
                        'length': {'meter': '50.0'}, 'width': {'meter': '6.0'},
                        'accessTime': {'secondsPerPerson': '0.5'}, 'egressTime': {'secondsPerPerson': '0.5'},
                        'doorOperation': {'mode': 'serial'}, 'passengerCarEquivalents': {'pce': '7.1'}},
            'cablecar': {'capacity': {'seats': {'persons': '250'}, 'standingRoom': {'persons': '0'}},
                         'length': {'meter': '50.0'}, 'width': {'meter': '6.0'},
                         'accessTime': {'secondsPerPerson': '0.5'}, 'egressTime': {'secondsPerPerson': '0.5'},
                         'doorOperation': {'mode': 'serial'}, 'passengerCarEquivalents': {'pce': '7.1'}}},
            'vehicles': {'veh_3_bus': {'type': 'bus'}, 'veh_4_bus': {'type': 'bus'},
                         'veh_1_bus': {'type': 'bus'}, 'veh_2_bus': {'type': 'bus'}}}}


def test_transforming_schedule_to_json(schedule, json_schedule):
    assert_semantically_equal(schedule.to_json(), json_schedule)


def test_transforming_uneven_schedule_to_json():
    # the stops have different params, we expect only those with values in the json
    route_2 = Route(route_short_name='name',
                    mode='bus', id='2',
                    stops=[Stop(id='5', x=4, y=2, epsg='epsg:27700', linkRefId='1234'),
                           Stop(id='6', x=1, y=2, epsg='epsg:27700', name='stop'),
                           Stop(id='7', x=3, y=3, epsg='epsg:27700', isBlocking='false'),
                           Stop(id='8', x=7, y=5, epsg='epsg:27700')],
                    trips={'trip_id': ['1', '2'],
                           'trip_departure_time': ['11:00:00', '13:00:00'],
                           'vehicle_id': ['veh_3_bus', 'veh_4_bus']},
                    arrival_offsets=['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                    departure_offsets=['00:00:00', '00:05:00', '00:09:00', '00:15:00'])
    service = Service(id='service', routes=[route_2])
    schedule = Schedule(epsg='epsg:27700', services=[service])
    assert_semantically_equal(
        schedule.to_json()['schedule']['stops'],
        {
            '5': {'linkRefId': '1234', 'id': '5', 'name': '', 'y': 2.0, 'lon': -7.557106577683727,
                  's2_id': 5205973754090531959, 'x': 4.0, 'lat': 49.76682779861249},
            '6': {'id': '6', 'name': 'stop', 'y': 2.0, 'lon': -7.557148039524952,
                  's2_id': 5205973754090365183, 'x': 1.0, 'lat': 49.766825803756994},
            '7': {'isBlocking': 'false', 'id': '7', 'name': '', 'y': 3.0, 'lon': -7.557121424907424,
                  's2_id': 5205973754090203369, 'x': 3.0, 'lat': 49.76683608549253},
            '8': {'id': '8', 'name': '', 'y': 5.0, 'lon': -7.5570681956375,
                  's2_id': 5205973754097123809, 'x': 7.0, 'lat': 49.766856648946295}}
    )


def test_writing_schedule_to_json(schedule, json_schedule, tmpdir):
    schedule.write_to_json(tmpdir)
    expected_schedule_json = os.path.join(tmpdir, 'schedule.json')
    assert os.path.exists(expected_schedule_json)
    with open(expected_schedule_json) as json_file:
        output_json = json.load(json_file)
    assert_semantically_equal(output_json, json_schedule)


def test_transforming_schedule_to_gtfs(schedule):
    gtfs = schedule.to_gtfs(gtfs_day='19700101')
    expected_stops = {'stop_id': {'5': '5', '6': '6', '7': '7', '8': '8', '3': '3', '2': '2', '4': '4', '1': '1'},
                      'stop_name': {'5': '', '6': '', '7': '', '8': '', '3': '', '2': '', '4': '', '1': ''},
                      'stop_lat': {'5': 49.76682779861249, '6': 49.766825803756994, '7': 49.76683608549253,
                                   '8': 49.766856648946295,
                                   '3': 49.76683608549253, '2': 49.766825803756994, '4': 49.766856648946295,
                                   '1': 49.76682779861249},
                      'stop_lon': {'5': -7.557106577683727, '6': -7.557148039524952, '7': -7.557121424907424,
                                   '8': -7.5570681956375,
                                   '3': -7.557121424907424, '2': -7.557148039524952, '4': -7.5570681956375,
                                   '1': -7.557106577683727},
                      'stop_code': {'5': float('nan'), '6': float('nan'), '7': float('nan'), '8': float('nan'),
                                    '3': float('nan'),
                                    '2': float('nan'), '4': float('nan'), '1': float('nan')},
                      'stop_desc': {'5': float('nan'), '6': float('nan'), '7': float('nan'), '8': float('nan'),
                                    '3': float('nan'),
                                    '2': float('nan'), '4': float('nan'), '1': float('nan')},
                      'zone_id': {'5': float('nan'), '6': float('nan'), '7': float('nan'), '8': float('nan'),
                                  '3': float('nan'),
                                  '2': float('nan'), '4': float('nan'), '1': float('nan')},
                      'stop_url': {'5': float('nan'), '6': float('nan'), '7': float('nan'), '8': float('nan'),
                                   '3': float('nan'),
                                   '2': float('nan'), '4': float('nan'), '1': float('nan')},
                      'location_type': {'5': float('nan'), '6': float('nan'), '7': float('nan'), '8': float('nan'),
                                        '3': float('nan'), '2': float('nan'), '4': float('nan'), '1': float('nan')},
                      'parent_station': {'5': float('nan'), '6': float('nan'), '7': float('nan'), '8': float('nan'),
                                         '3': float('nan'), '2': float('nan'), '4': float('nan'), '1': float('nan')},
                      'stop_timezone': {'5': float('nan'), '6': float('nan'), '7': float('nan'), '8': float('nan'),
                                        '3': float('nan'), '2': float('nan'), '4': float('nan'), '1': float('nan')},
                      'wheelchair_boarding': {'5': float('nan'), '6': float('nan'), '7': float('nan'),
                                              '8': float('nan'),
                                              '3': float('nan'), '2': float('nan'), '4': float('nan'),
                                              '1': float('nan')},
                      'level_id': {'5': float('nan'), '6': float('nan'), '7': float('nan'), '8': float('nan'),
                                   '3': float('nan'),
                                   '2': float('nan'), '4': float('nan'), '1': float('nan')},
                      'platform_code': {'5': float('nan'), '6': float('nan'), '7': float('nan'), '8': float('nan'),
                                        '3': float('nan'), '2': float('nan'), '4': float('nan'), '1': float('nan')}}
    actual_stops = gtfs['stops'].to_dict()
    assert_semantically_equal(expected_stops, actual_stops)
    expected_routes = {'route_id': {0: 'service'}, 'route_short_name': {0: 'name_2'}, 'route_long_name': {0: ''},
                       'agency_id': {0: None}, 'route_desc': {0: None}, 'route_url': {0: None},
                       'route_type': {0: 3},
                       'route_color': {0: None}, 'route_text_color': {0: None}, 'route_sort_order': {0: None},
                       'continuous_pickup': {0: None}, 'continuous_drop_off': {0: None}}
    actual_routes = gtfs['routes'].to_dict()
    assert_semantically_equal(expected_routes, actual_routes)

    assert_semantically_equal(
        gtfs['trips'].to_dict(),
        {'route_id': {0: 'service', 1: 'service', 2: 'service', 3: 'service'},
         'service_id': {0: 'service', 1: 'service', 2: 'service', 3: 'service'},
         'trip_id': {0: '1', 1: '2', 2: '1', 3: '2'},
         'trip_headsign': {0: float('nan'), 1: float('nan'), 2: float('nan'), 3: float('nan')},
         'trip_short_name': {0: float('nan'), 1: float('nan'), 2: float('nan'), 3: float('nan')},
         'direction_id': {0: float('nan'), 1: float('nan'), 2: float('nan'), 3: float('nan')},
         'block_id': {0: float('nan'), 1: float('nan'), 2: float('nan'), 3: float('nan')},
         'shape_id': {0: float('nan'), 1: float('nan'), 2: float('nan'), 3: float('nan')},
         'wheelchair_accessible': {0: float('nan'), 1: float('nan'), 2: float('nan'), 3: float('nan')},
         'bikes_allowed': {0: float('nan'), 1: float('nan'), 2: float('nan'), 3: float('nan')}}
    )
    assert_semantically_equal(
        gtfs['stop_times'].to_dict(),
        {'trip_id': {0: '1', 1: '1', 2: '1', 3: '1', 4: '2', 5: '2', 6: '2', 7: '2', 8: '1', 9: '1', 10: '1', 11: '1',
                     12: '2', 13: '2', 14: '2', 15: '2'},
         'stop_id': {0: '5', 1: '6', 2: '7', 3: '8', 4: '5', 5: '6', 6: '7', 7: '8', 8: '1', 9: '2', 10: '3', 11: '4',
                     12: '1', 13: '2', 14: '3', 15: '4'},
         'stop_sequence': {0: 0, 1: 1, 2: 2, 3: 3, 4: 0, 5: 1, 6: 2, 7: 3, 8: 0, 9: 1, 10: 2, 11: 3, 12: 0, 13: 1,
                           14: 2, 15: 3},
         'departure_time': {0: '11:00:00', 1: '11:05:00', 2: '11:09:00', 3: '11:15:00', 4: '13:00:00', 5: '13:05:00',
                            6: '13:09:00', 7: '13:15:00', 8: '13:00:00', 9: '13:05:00', 10: '13:09:00', 11: '13:15:00',
                            12: '13:30:00', 13: '13:35:00', 14: '13:39:00', 15: '13:45:00'},
         'arrival_time': {0: '11:00:00', 1: '11:03:00', 2: '11:07:00', 3: '11:13:00', 4: '13:00:00', 5: '13:03:00',
                          6: '13:07:00', 7: '13:13:00', 8: '13:00:00', 9: '13:03:00', 10: '13:07:00', 11: '13:13:00',
                          12: '13:30:00', 13: '13:33:00', 14: '13:37:00', 15: '13:43:00'},
         'stop_headsign': {0: float('nan'), 1: float('nan'), 2: float('nan'), 3: float('nan'), 4: float('nan'),
                           5: float('nan'), 6: float('nan'), 7: float('nan'), 8: float('nan'), 9: float('nan'),
                           10: float('nan'),
                           11: float('nan'), 12: float('nan'), 13: float('nan'), 14: float('nan'), 15: float('nan')},
         'pickup_type': {0: float('nan'), 1: float('nan'), 2: float('nan'), 3: float('nan'), 4: float('nan'),
                         5: float('nan'), 6: float('nan'), 7: float('nan'), 8: float('nan'), 9: float('nan'),
                         10: float('nan'),
                         11: float('nan'), 12: float('nan'), 13: float('nan'), 14: float('nan'), 15: float('nan')},
         'drop_off_type': {0: float('nan'), 1: float('nan'), 2: float('nan'), 3: float('nan'), 4: float('nan'),
                           5: float('nan'), 6: float('nan'), 7: float('nan'), 8: float('nan'), 9: float('nan'),
                           10: float('nan'),
                           11: float('nan'), 12: float('nan'), 13: float('nan'), 14: float('nan'), 15: float('nan')},
         'continuous_pickup': {0: float('nan'), 1: float('nan'), 2: float('nan'), 3: float('nan'), 4: float('nan'),
                               5: float('nan'), 6: float('nan'), 7: float('nan'), 8: float('nan'), 9: float('nan'),
                               10: float('nan'),
                               11: float('nan'), 12: float('nan'), 13: float('nan'), 14: float('nan'),
                               15: float('nan')},
         'continuous_drop_off': {0: float('nan'), 1: float('nan'), 2: float('nan'), 3: float('nan'), 4: float('nan'),
                                 5: float('nan'), 6: float('nan'), 7: float('nan'), 8: float('nan'), 9: float('nan'),
                                 10: float('nan'), 11: float('nan'), 12: float('nan'), 13: float('nan'),
                                 14: float('nan'), 15: float('nan')},
         'shape_dist_traveled': {0: float('nan'), 1: float('nan'), 2: float('nan'), 3: float('nan'), 4: float('nan'),
                                 5: float('nan'), 6: float('nan'), 7: float('nan'), 8: float('nan'), 9: float('nan'),
                                 10: float('nan'), 11: float('nan'), 12: float('nan'), 13: float('nan'),
                                 14: float('nan'), 15: float('nan')},
         'timepoint': {0: float('nan'), 1: float('nan'), 2: float('nan'), 3: float('nan'), 4: float('nan'),
                       5: float('nan'), 6: float('nan'), 7: float('nan'), 8: float('nan'), 9: float('nan'),
                       10: float('nan'), 11: float('nan'),
                       12: float('nan'), 13: float('nan'), 14: float('nan'), 15: float('nan')}}
    )
    assert_semantically_equal(
        gtfs['calendar'].to_dict(),
        {'route_id': {0: 'service'}, 'monday': {0: 1}, 'tuesday': {0: 1}, 'wednesday': {0: 1}, 'thursday': {0: 1},
         'friday': {0: 1}, 'saturday': {0: 1}, 'sunday': {0: 1}, 'start_date': {0: '19700101'},
         'end_date': {0: '19700101'}}
    )


def test_writing_schedule_to_csv(schedule, tmpdir):
    schedule.write_to_csv(tmpdir)
    assert set(os.listdir(tmpdir)) == {'calendar.csv', 'routes.csv', 'stop_times.csv', 'stops.csv', 'trips.csv',
                                       'schedule_change_log.csv'}


def test_writing_schedule_to_gtfs(schedule, tmpdir):
    schedule.write_to_gtfs(tmpdir)
    assert set(os.listdir(tmpdir)) == {'calendar.txt', 'routes.txt', 'stop_times.txt', 'stops.txt', 'trips.txt',
                                       'schedule_change_log.csv'}
