import os
import sys
import pytest
from genet.inputs_handler import matsim_reader
from genet.core import Network, Schedule

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
pt2matsim_network_test_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_data", "network.xml"))
pt2matsim_schedule_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_data", "schedule.xml"))





def test_read_matsim_network_delegates_to_matsim_reader_read_network(mocker):
    mocker.patch.object(matsim_reader, 'read_network', return_value = (1,2,3))

    network = Network()
    network.read_matsim_network(pt2matsim_network_test_file, 'epsg:27700')

    matsim_reader.read_network.assert_called_once_with(pt2matsim_network_test_file, network.transformer)


def test_read_matsim_schedule_runs_schedule_read_matsim_schedule_using_epsg_from_earlier_network_run(mocker):
    mocker.patch.object(Schedule, 'read_matsim_schedule')
    network = Network()
    network.read_matsim_network(pt2matsim_network_test_file, 'epsg:27700')
    network.read_matsim_schedule(pt2matsim_schedule_file)

    Schedule.read_matsim_schedule.assert_called_once_with(pt2matsim_schedule_file, 'epsg:27700')


def test_read_matsim_schedule_runs_schedule_read_matsim_schedule_using_given_epsg_independent_of_network(mocker):
    mocker.patch.object(Schedule, 'read_matsim_schedule')
    network = Network()
    network.read_matsim_schedule(pt2matsim_schedule_file, 'epsg:27700')

    Schedule.read_matsim_schedule.assert_called_once_with(pt2matsim_schedule_file, 'epsg:27700')


def test_read_matsim_schedule_when_asked_to_use_different_epsg_than_stored():
    network = Network()
    network.epsg = 'blop'

    with pytest.raises(RuntimeError) as e:
        network.read_matsim_schedule(pt2matsim_schedule_file, 'epsg:27700')
    assert 'The epsg you have given epsg:27700 does not match the epsg currently stored for this network' in str(e.value)