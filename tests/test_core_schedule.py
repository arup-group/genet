import os
import sys
import pytest
from tests.fixtures import *
from genet.inputs_handler import matsim_reader, gtfs_reader
from genet.core import Schedule

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
pt2matsim_schedule_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_data", "matsim", "schedule.xml"))
gtfs_test_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_data", "gtfs"))


def test_schedule_rejects_partial_attributes_epsg_missing():
    with pytest.raises(AssertionError) as e:
        Schedule(services=[test_service])
    assert 'You need to specify the coordinate system for the schedule' in str(e.value)


def test__getitem__returns_a_service(test_service):
    services = [test_service]
    schedule = Schedule(services=services, epsg='1234')
    assert schedule['service'] == services[0]


def test__repr__shows_number_of_services(mocker):
    mocker.patch.object(Schedule, '__len__')
    schedule = Schedule()
    s = schedule.__repr__()
    assert 'instance at' in s
    assert 'services' in s
    Schedule.__len__.assert_called_once()


def test__str__shows_info():
    schedule = Schedule()
    assert 'Number of services' in schedule.__str__()
    assert 'Number of unique routes' in schedule.__str__()


def test__len__returns_the_number_of_services(test_service):
    services = [test_service]
    schedule = Schedule(services=services, epsg='1234')
    assert len(schedule) == 1


def test_print_shows_info(mocker):
    mocker.patch.object(Schedule, 'info')
    schedule = Schedule()
    schedule.print()
    Schedule.info.assert_called_once()


def test_info_shows_number_of_services_and_routes(mocker):
    mocker.patch.object(Schedule, '__len__')
    mocker.patch.object(Schedule, 'number_of_routes')
    schedule = Schedule()
    schedule.print()
    Schedule.__len__.assert_called_once()
    Schedule.number_of_routes.assert_called_once()


def test_adding_merges_separable_schedules(route):
    schedule = Schedule([Service(id='1', routes=[route])], epsg='epsg:1234')
    schedule_to_be_added = Schedule([Service(id='2', routes=[route])], epsg='epsg:1234')

    new_schedule = schedule + schedule_to_be_added

    assert new_schedule.services == {
        '1': Service(id='1', routes=[route]),
        '2': Service(id='2', routes=[route])}
    assert new_schedule.epsg == schedule.epsg
    assert new_schedule.epsg == schedule_to_be_added.epsg


def test_adding_throws_error_when_schedules_not_separable(test_service):
    schedule = Schedule(services=[test_service], epsg='1234')
    assert 'service' in schedule
    schedule_to_be_added = Schedule(services=[test_service], epsg='1234')

    with pytest.raises(NotImplementedError) as e:
        schedule + schedule_to_be_added
    assert 'This method only supports adding non overlapping services' in str(e.value)


def test_adding_throws_error_when_schedules_dont_have_matching_epsg(test_service, different_test_service):
    schedule = Schedule(services=[test_service], epsg='1234')
    assert 'service' in schedule.services
    schedule_to_be_added = Schedule(services=[different_test_service], epsg='2')

    with pytest.raises(RuntimeError) as e:
        schedule + schedule_to_be_added
    assert 'You are merging two schedules with different coordinate systems' in str(e.value)


def test_service_ids_returns_keys_of_the_services_dict(test_service):
    services = [test_service]
    schedule = Schedule(services=services, epsg='1234')
    assert set(schedule.service_ids()) == {'service'}


def test_routes_returns_service_ids_with_unique_routes(route, similar_non_exact_test_route):
    services = [Service(id='1', routes=[route]), Service(id='2', routes=[similar_non_exact_test_route])]
    schedule = Schedule(services=services, epsg='1234')
    assert [service_id for service_id, route in schedule.routes()] == ['1', '2']
    assert [route for service_id, route in schedule.routes()] == [route, similar_non_exact_test_route]


def test_number_of_routes_counts_routes(test_service, different_test_service):
    schedule = Schedule(services=[test_service, different_test_service], epsg='1234')
    assert schedule.number_of_routes() == 3


def test_iter_stops_returns_stops_with_attribs(test_service, different_test_service, stop_epsg_27700):
    schedule = Schedule(services=[test_service, different_test_service], epsg='1234')
    assert [stop for stop, attrib in schedule.iter_stops()] == ['0']
    assert [attrib for stop, attrib in schedule.iter_stops()] == [stop_epsg_27700]


def test_read_matsim_schedule_delegates_to_matsim_reader_read_schedule(mocker):
    mocker.patch.object(matsim_reader, 'read_schedule', return_value = ({'1': []}, {}))

    schedule = Schedule()
    schedule.read_matsim_schedule(pt2matsim_schedule_file, 'epsg:27700')

    matsim_reader.read_schedule.assert_called_once_with(pt2matsim_schedule_file, schedule.transformer)


def test_read_matsim_schedule_delegates_to_matsim_reader_read_schedule(mocker, test_service):
    mocker.patch.object(gtfs_reader, 'read_to_list_of_service_objects', return_value = [test_service])

    schedule = Schedule()
    schedule.read_gtfs_schedule(gtfs_test_file, '20190604')

    gtfs_reader.read_to_list_of_service_objects.assert_called_once_with(gtfs_test_file, '20190604')


def test_read_matsim_schedule_returns_expected_schedule():
    schedule = Schedule()
    schedule.read_matsim_schedule(pt2matsim_schedule_file, 'epsg:27700')

    correct_services = Service(id='10314', routes=[
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
    ])

    for key, val in schedule.services.items():
        assert val == correct_services
    assert_semantically_equal(schedule.stops_mapping, {'26997928P.link:1': ['10314'], '26997928P': ['10314']})


def test_read_gtfs_returns_expected_schedule(correct_stops_mapping_from_test_gtfs):
    schedule = Schedule()
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
    assert_semantically_equal(schedule.stops_mapping, correct_stops_mapping_from_test_gtfs)