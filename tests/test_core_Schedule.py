import os
import sys
import pytest
from genet.inputs_handler import matsim_reader
from genet.core import Network, Schedule

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
pt2matsim_network_test_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_data", "network.xml"))
pt2matsim_schedule_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_data", "schedule.xml"))


def test_Schedule_merges_seperable_schedules():
    schedule = Schedule(services={'1': [{}]})
    assert '1' in schedule
    schedule_to_be_added = {'2': [{}]}

    schedule.add_services(schedule_to_be_added)
    assert '2' in schedule


def test_Schedule_throws_error_when_schedules_not_separable():
    schedule = Schedule(services={'1': [{}]})
    assert '1' in schedule
    schedule_to_be_added = {'1': [{}]}

    with pytest.raises(NotImplementedError) as e:
        schedule.add_services(schedule_to_be_added)
    assert 'This method only supports adding non overlapping services' in str(e.value)


def test_Schedule_read_matsim_schedule_delegates_to_matsim_reader_read_schedule(mocker):
    mocker.patch.object(matsim_reader, 'read_schedule', return_value = ({'1': []}, {}))

    schedule = Schedule()
    schedule.read_matsim_schedule(pt2matsim_schedule_file, 'epsg:27700')

    matsim_reader.read_schedule.assert_called_once_with(pt2matsim_schedule_file, schedule.transformer)