import os
import sys
import pytest
from tests.fixtures import *
from tests.test_core_components_route import self_looping_route, route
from tests.test_core_components_service import service
from genet.inputs_handler import matsim_reader, gtfs_reader
from genet.schedule_elements import Schedule, Service, Route, Stop
from genet.utils import plot
from genet.validate import schedule_validation

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
pt2matsim_schedule_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "schedule.xml"))
gtfs_test_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_data", "gtfs"))


@pytest.fixture()
def schedule():
    route_1 = Route(route_short_name='name',
                    mode='bus', id='1',
                    stops=[Stop(id='1', x=4, y=2, epsg='epsg:27700'), Stop(id='2', x=1, y=2, epsg='epsg:27700'),
                           Stop(id='3', x=3, y=3, epsg='epsg:27700'), Stop(id='4', x=7, y=5, epsg='epsg:27700')],
                    trips={'1': '1', '2': '2'},
                    arrival_offsets=['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                    departure_offsets=['00:00:00', '00:05:00', '00:09:00', '00:15:00'])
    route_2 = Route(route_short_name='name_2',
                    mode='bus', id='2',
                    stops=[Stop(id='5', x=4, y=2, epsg='epsg:27700'), Stop(id='6', x=1, y=2, epsg='epsg:27700'),
                           Stop(id='7', x=3, y=3, epsg='epsg:27700'), Stop(id='8', x=7, y=5, epsg='epsg:27700')],
                    trips={'1': '1', '2': '2'},
                    arrival_offsets=['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                    departure_offsets=['00:00:00', '00:05:00', '00:09:00', '00:15:00'])
    service = Service(id='service', routes=[route_1, route_2])
    return Schedule(epsg='epsg:27700', services=[service])


@pytest.fixture()
def strongly_connected_schedule():
    route_1 = Route(route_short_name='name',
                    mode='bus',
                    stops=[Stop(id='1', x=4, y=2, epsg='epsg:27700'), Stop(id='2', x=1, y=2, epsg='epsg:27700'),
                           Stop(id='3', x=3, y=3, epsg='epsg:27700'), Stop(id='4', x=7, y=5, epsg='epsg:27700'),
                           Stop(id='1', x=4, y=2, epsg='epsg:27700')],
                    trips={'1': '1', '2': '2'}, arrival_offsets=['1', '2'], departure_offsets=['1', '2'])
    route_2 = Route(route_short_name='name_2',
                    mode='bus',
                    stops=[Stop(id='5', x=4, y=2, epsg='epsg:27700'), Stop(id='2', x=1, y=2, epsg='epsg:27700'),
                           Stop(id='7', x=3, y=3, epsg='epsg:27700'), Stop(id='8', x=7, y=5, epsg='epsg:27700'),
                           Stop(id='5', x=4, y=2, epsg='epsg:27700')],
                    trips={'1': '1', '2': '2'}, arrival_offsets=['1', '2', '3', '4', '5'],
                    departure_offsets=['1', '2', '3', '4', '5'])
    service = Service(id='service', routes=[route_1, route_2])
    return Schedule(epsg='epsg:27700', services=[service])


def test__getitem__returns_a_service(test_service):
    services = [test_service]
    schedule = Schedule(services=services, epsg='epsg:4326')
    assert schedule['service'] == services[0]


def test_accessing_route(schedule):
    assert schedule.route('1') == Route(route_short_name='name',
                    mode='bus', id='1',
                    stops=[Stop(id='1', x=4, y=2, epsg='epsg:27700'), Stop(id='2', x=1, y=2, epsg='epsg:27700'),
                           Stop(id='3', x=3, y=3, epsg='epsg:27700'), Stop(id='4', x=7, y=5, epsg='epsg:27700')],
                    trips={'1': '1', '2': '2'},
                    arrival_offsets=['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                    departure_offsets=['00:00:00', '00:05:00', '00:09:00', '00:15:00'])


def test__repr__shows_number_of_services(mocker):
    mocker.patch.object(Schedule, '__len__')
    schedule = Schedule('epsg:27700')
    s = schedule.__repr__()
    assert 'instance at' in s
    assert 'services' in s
    Schedule.__len__.assert_called_once()


def test__str__shows_info():
    schedule = Schedule('epsg:27700')
    assert 'Number of services' in schedule.__str__()
    assert 'Number of unique routes' in schedule.__str__()


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
    mocker.patch.object(Schedule, '__len__')
    mocker.patch.object(Schedule, 'number_of_routes')
    schedule = Schedule('epsg:27700')
    schedule.print()
    Schedule.__len__.assert_called_once()
    Schedule.number_of_routes.assert_called_once()


def test_plot_delegates_to_util_plot_plot_graph_routes(mocker, schedule):
    mocker.patch.object(plot, 'plot_graph')
    schedule.plot()
    plot.plot_graph.assert_called_once()


def test_reproject_changes_projection_for_all_stops_in_route():
    correct_x_y = {'x': 51.52393050617373, 'y': -0.14967658860132668}
    schedule = Schedule(
        'epsg:27700',
        [Service(id='10314', routes=[
            Route(
                route_short_name='12',
                mode='bus',
                stops=[Stop(id='26997928P', x='528464.1342843144', y='182179.7435136598', epsg='epsg:27700'),
                       Stop(id='26997928P.link:1', x='528464.1342843144', y='182179.7435136598', epsg='epsg:27700')],
                route=['1'],
                trips={'VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00': '04:40:00'},
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
    before_graph_nodes = schedule.reference_nodes
    before_graph_edges = schedule.reference_edges

    a = Stop(id='10', x=40, y=20, epsg='epsg:27700', linkRefId='1')
    b = Stop(id='20', x=10, y=20, epsg='epsg:27700', linkRefId='2')
    c = Stop(id='30', x=30, y=30, epsg='epsg:27700', linkRefId='3')
    d = Stop(id='40', x=70, y=50, epsg='epsg:27700', linkRefId='4')
    schedule_to_be_added = Schedule(epsg='epsg:4326', services=[Service(id='2', routes=[
        Route(
            route_short_name='name',
            mode='bus',
            stops=[a, b, c, d],
            trips={'1': '1', '2': '2'},
            arrival_offsets=['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
            departure_offsets=['00:00:00', '00:05:00', '00:09:00', '00:15:00'],
            route=['1', '2', '3', '4'], id='1')
    ])])

    tba_graph_nodes = schedule_to_be_added.reference_nodes
    tba_graph_edges = schedule_to_be_added.reference_edges

    schedule.add(schedule_to_be_added)

    assert schedule.services == {
        '1': Service(id='1', routes=[route]),
        '2': Service(id='2', routes=[route])}
    assert schedule.epsg == 'epsg:4326'
    assert schedule.epsg == schedule_to_be_added.epsg
    assert set(schedule._graph.nodes()) == set(before_graph_nodes) | set(tba_graph_nodes)
    assert set(schedule._graph.edges()) == set(before_graph_edges) | set(tba_graph_edges)


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
    assert 'service' in schedule.services
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
    assert [service_id for service_id, route in schedule.routes()] == ['1', '2']
    assert [route for service_id, route in schedule.routes()] == [route, similar_non_exact_test_route]


def test_number_of_routes_counts_routes(test_service, different_test_service):
    schedule = Schedule(services=[test_service, different_test_service], epsg='epsg:4362')
    assert schedule.number_of_routes() == 3


def test_iter_stops_returns_stops_objects(test_service, different_test_service):
    schedule = Schedule(services=[test_service, different_test_service], epsg='epsg:4326')
    assert set([stop.id for stop in schedule.stops()]) == {'0', '1', '2', '3', '4'}
    assert all([isinstance(stop, Stop) for stop in schedule.stops()])


def test_read_matsim_schedule_delegates_to_matsim_reader_read_schedule(mocker):
    mocker.patch.object(matsim_reader, 'read_schedule', return_value=([Service(id='1', routes=[])], {}))

    schedule = Schedule('epsg:27700')
    schedule.read_matsim_schedule(pt2matsim_schedule_file)

    matsim_reader.read_schedule.assert_called_once_with(pt2matsim_schedule_file, schedule.epsg)


def test_read_matsim_schedule_returns_expected_schedule():
    schedule = Schedule('epsg:27700')
    schedule.read_matsim_schedule(pt2matsim_schedule_file)

    correct_services = Service(id='10314', routes=[
        Route(
            route_short_name='12', id='VJbd8660f05fe6f744e58a66ae12bd66acbca88b98',
            mode='bus',
            stops=[Stop(id='26997928P', x='528464.1342843144', y='182179.7435136598', epsg='epsg:27700'),
                   Stop(id='26997928P.link:1', x='528464.1342843144', y='182179.7435136598', epsg='epsg:27700')],
            route=['1'],
            trips={'VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00': '04:40:00'},
            arrival_offsets=['00:00:00', '00:02:00'],
            departure_offsets=['00:00:00', '00:02:00']
        )
    ])

    for key, val in schedule.services.items():
        assert val == correct_services
    assert_semantically_equal(schedule.stop_to_service_ids_map(),
                              {'26997928P.link:1': ['10314'], '26997928P': ['10314']})
    assert_semantically_equal(schedule.stop_to_route_ids_map(),
                              {'26997928P': ['VJbd8660f05fe6f744e58a66ae12bd66acbca88b98'],
                               '26997928P.link:1': ['VJbd8660f05fe6f744e58a66ae12bd66acbca88b98']})


def test_read_gtfs_returns_expected_schedule(correct_stops_to_service_mapping_from_test_gtfs, correct_stops_to_route_mapping_from_test_gtfs):
    schedule = Schedule('epsg:4326')
    schedule.read_gtfs_schedule(gtfs_test_file, '20190604')

    assert schedule.services['1001'] == Service(
        '1001',
        [Route(
            route_short_name='BTR',
            mode='bus',
            stops=[Stop(id='BSE', x=-0.1413621, y=51.5226864, epsg='epsg:4326'),
                   Stop(id='BSN', x=-0.140053, y=51.5216199, epsg='epsg:4326')],
            trips={'BT1': '03:21:00'},
            arrival_offsets=['0:00:00', '0:02:00'],
            departure_offsets=['0:00:00', '0:02:00']
        )])
    assert schedule.services['1002'] == Service(
        '1002',
        [Route(
            route_short_name='RTR',
            mode='rail',
            stops=[Stop(id='RSN', x=-0.1410946, y=51.5231335, epsg='epsg:4326'),
                   Stop(id='RSE', x=-0.1421595, y=51.5192615, epsg='epsg:4326')],
            trips={'RT1': '03:21:00'},
            arrival_offsets=['0:00:00', '0:02:00'],
            departure_offsets=['0:00:00', '0:02:00']
        )])
    assert_semantically_equal(schedule.stop_to_service_ids_map(), correct_stops_to_service_mapping_from_test_gtfs)
    assert_semantically_equal(schedule.stop_to_route_ids_map(), correct_stops_to_route_mapping_from_test_gtfs)


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
    assert s.validity_of_services() == [False, True]


def test_has_valid_services(schedule):
    assert not schedule.has_valid_services()


def test_has_valid_services_with_only_valid_services(service):
    s = Schedule('epsg:27700', [service])
    assert s.has_valid_services()


def test_invalid_services_shows_invalid_services(service):
    for route in service.routes.values():
        route.route = ['1']
    s = Schedule('epsg:27700', [service])
    assert s.invalid_services() == [service]


def test_has_uniquely_indexed_routes_with_uniquely_indexed_service(schedule):
    assert schedule.has_uniquely_indexed_services()


def test_is_valid_with_valid_schedule(service):
    s = Schedule('epsg:27700', [service])
    assert s.is_valid_schedule()


def test_generate_validation_report_delegates_to_method_in_schedule_operations(mocker, schedule):
    mocker.patch.object(schedule_validation, 'generate_validation_report')
    schedule.generate_validation_report()
    schedule_validation.generate_validation_report.assert_called_once()
