import os
import sys
import pytest
from genet.inputs_handler import matsim_reader
from genet.core import Schedule

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
pt2matsim_schedule_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_data", "schedule.xml"))


def test_Schedule_needs_all_attribs_filled_or_none__services_missing():
    with pytest.raises(AssertionError) as e:
        Schedule(stops={'1': {}})
    assert 'expects all or none of the attributes' in str(e.value)


def test_Schedule_needs_all_attribs_filled_or_none__stops_missing():
    with pytest.raises(AssertionError) as e:
        Schedule(services={'1': []})
    assert 'You need to provide spatial information for the stops' in str(e.value)


def test_Schedule_needs_all_attribs_filled_or_none__epsg_missing():
    with pytest.raises(AssertionError) as e:
        Schedule(services={'1': []}, stops={})
    assert 'You need to specify the coordinate system for the schedule' in str(e.value)


def test__getitem__returns_a_service():
    services = dict(zip(range(10), range(10)))
    stops = dict(zip(range(10),{'x': 1, 'y': 2}))
    schedule = Schedule(services=services, stops=stops, epsg='1234')
    assert schedule[5] == services[5]


def test__repr__shows_number_of_services(mocker):
    mocker.patch.object(Schedule, '__len__')
    schedule = Schedule()
    schedule.__repr__()
    Schedule.__len__.assert_called_once()


def test__str__shows_info(mocker):
    mocker.patch.object(Schedule, 'info')
    schedule = Schedule()
    schedule.__str__()
    Schedule.info.assert_called_once()


def test__len__returns_the_number_of_services():
    services = dict(zip(range(10), range(10)))
    stops = dict(zip(range(10),{'x': 1, 'y': 2}))
    schedule = Schedule(services=services, stops=stops, epsg='1234')
    assert len(schedule) == 10


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


def test_adding_merges_separable_schedules():
    schedule = Schedule(services={'1': [{}]}, stops={}, epsg='1234')
    schedule_to_be_added = Schedule(services={'2': [{}]}, stops={}, epsg='1234')

    new_schedule = schedule + schedule_to_be_added

    assert new_schedule.services == {'1': [{}], '2': [{}]}
    assert new_schedule.epsg == schedule.epsg
    assert new_schedule.epsg == schedule_to_be_added.epsg


def test_adding_throws_error_when_schedules_not_separable():
    schedule = Schedule(services={'1': [{}]}, stops={}, epsg='1234')
    assert '1' in schedule
    schedule_to_be_added = Schedule(services={'1': [{}]}, stops={}, epsg='1234')

    with pytest.raises(NotImplementedError) as e:
        schedule + schedule_to_be_added
    assert 'This method only supports adding non overlapping services' in str(e.value)


def test_adding_throws_error_when_schedules_dont_have_matching_epsg():
    schedule = Schedule(services={'1': [{}]}, stops={}, epsg='1234')
    assert '1' in schedule
    schedule_to_be_added = Schedule(services={'2': [{}]}, stops={}, epsg='2')

    with pytest.raises(RuntimeError) as e:
        schedule + schedule_to_be_added
    assert 'You are merging two schedules with different coordinate systems' in str(e.value)


def test_service_ids_returns_keys_of_the_services_dict():
    services = {'1': [{}], '2': [{}]}
    schedule = Schedule(services=services, stops={}, epsg='1234')
    assert set(schedule.service_ids()) == {'1', '2'}


def test_routes_returns_service_ids_with_unique_routes():
    services = {'1': [{'route_short_name': '12a'},{'route_short_name': '12b'}],
                '2': [{'route_short_name': '6a'}]}
    schedule = Schedule(services=services, stops={}, epsg='1234')
    assert [service_id for service_id, route in schedule.routes()] == ['1', '1', '2']
    assert [route for service_id, route in schedule.routes()] == [{'route_short_name': '12a'},{'route_short_name': '12b'},{'route_short_name': '6a'}]


def test_number_of_routes_counts_routes():
    services = {'1': [{'route_short_name': '12a'},{'route_short_name': '12b'}],
                '2': [{'route_short_name': '6a'}]}
    schedule = Schedule(services=services, stops={}, epsg='1234')
    assert schedule.number_of_routes() == 3


def test_iter_stops_returns_stops_with_attribs():
    services = {'1': [{}]}
    schedule = Schedule(services=services, stops={'1': {'x': 1, 'y': 2}}, epsg='1234')
    assert [stop for stop, attrib in schedule.iter_stops()] == ['1']
    assert [attrib for stop, attrib in schedule.iter_stops()] == [{'x': 1, 'y': 2}]


def test_read_matsim_schedule_delegates_to_matsim_reader_read_schedule(mocker):
    mocker.patch.object(matsim_reader, 'read_schedule', return_value = ({'1': []}, {}))

    schedule = Schedule()
    schedule.read_matsim_schedule(pt2matsim_schedule_file, 'epsg:27700')

    matsim_reader.read_schedule.assert_called_once_with(pt2matsim_schedule_file, schedule.transformer)