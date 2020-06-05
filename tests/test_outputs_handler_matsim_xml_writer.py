import os, sys
import pytest
import lxml
from tests.fixtures import network_object_from_test_data
from tests import xml_diff
from genet.outputs_handler import matsim_xml_writer
from genet.schedule_elements import Stop
from genet.utils import spatial
from pyproj import Proj, Transformer

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
pt2matsim_network_test_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "network.xml"))
pt2matsim_schedule_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "schedule.xml"))
pt2matsim_vehicles_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "vehicles.xml"))


@pytest.fixture
def network_dtd():
    dtd_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            "test_data", "dtd", "matsim", "network_v2.dtd"))
    yield lxml.etree.DTD(dtd_path)


@pytest.fixture
def schedule_dtd():
    dtd_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            "test_data", "dtd", "matsim", "transitSchedule_v2.dtd"))
    yield lxml.etree.DTD(dtd_path)


@pytest.fixture
def vehicles_xsd():
    xsd_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            "test_data", "dtd", "matsim", "vehicleDefinitions_v1.0.xsd"))

    xml_schema_doc = lxml.etree.parse(xsd_path)
    yield lxml.etree.XMLSchema(xml_schema_doc)


def test_generates_valid_matsim_network_xml_file(network_object_from_test_data, network_dtd, tmpdir):
    matsim_xml_writer.write_matsim_network(tmpdir, network_object_from_test_data)

    generated_network_file_path = os.path.join(tmpdir, 'network.xml')
    xml_obj = lxml.etree.parse(generated_network_file_path)
    assert network_dtd.validate(xml_obj), \
        'Doc generated at {} is not valid against DTD due to {}'.format(generated_network_file_path,
                                                                        network_dtd.error_log.filter_from_errors())


def test_write_matsim_network_produces_symantically_equal_xml_to_input_matsim_xml(network_object_from_test_data, tmpdir):
    matsim_xml_writer.write_matsim_network(tmpdir, network_object_from_test_data)

    xml_diff.assert_semantically_equal(os.path.join(tmpdir, 'network.xml'), pt2matsim_network_test_file)


def test_generates_valid_matsim_schedule_xml_file(network_object_from_test_data, schedule_dtd, tmpdir):
    matsim_xml_writer.write_matsim_schedule(tmpdir, network_object_from_test_data.schedule)

    generated_file_path = os.path.join(tmpdir, 'schedule.xml')
    xml_obj = lxml.etree.parse(generated_file_path)
    assert schedule_dtd.validate(xml_obj), \
        'Doc generated at {} is not valid against DTD due to {} errors - first error {}'\
            .format(generated_file_path,
                    len(schedule_dtd.error_log.filter_from_errors()),
                        schedule_dtd.error_log.filter_from_errors()[0])


def test_write_matsim_schedule_produces_symantically_equal_xml_to_input_matsim_xml(network_object_from_test_data, tmpdir):
    matsim_xml_writer.write_matsim_schedule(tmpdir, network_object_from_test_data.schedule)

    xml_diff.assert_semantically_equal(os.path.join(tmpdir, 'schedule.xml'), pt2matsim_schedule_file)


def test_write_matsim_schedule_produces_symantically_equal_xml_to_input_matsim_xml_if_stops_need_to_reprojected(network_object_from_test_data, tmpdir):
    # we change all the stops in the one service and one route that exists in the test data
    stops = network_object_from_test_data.schedule['10314'].routes[0].stops
    transformer = Transformer.from_proj(Proj('epsg:27700'), Proj('epsg:3035'))
    reprojected_stops = []
    for stop in stops:
        x, y = spatial.change_proj(stop.x, stop.y, transformer)
        new_stop = Stop(id=stop.id, x=x, y=y, epsg='epsg:3035')
        additional_attributes = {}
        for k, v in stop.iter_through_additional_attributes():
            additional_attributes[k] = v
        new_stop.add_additional_attributes(additional_attributes)
        reprojected_stops.append(new_stop)

    network_object_from_test_data.schedule['10314'].routes[0].stops = reprojected_stops

    matsim_xml_writer.write_matsim_schedule(tmpdir, network_object_from_test_data.schedule)

    xml_diff.assert_semantically_equal(os.path.join(tmpdir, 'schedule.xml'), pt2matsim_schedule_file)


def test_generates_valid_matsim_vehicles_xml_file(tmpdir, vehicles_xsd):
    vehicle_dict = {
        'veh_1': 'Bus',
        'veh_2': 'Bus',
        'veh_3': 'Bus',
        'veh_4': 'Tram',
        'veh_5': 'Rail',
        'veh_6': 'Underground Service'
    }
    matsim_xml_writer.write_vehicles(tmpdir, vehicle_dict)

    generated_file_path = os.path.join(tmpdir, 'vehicles.xml')
    xml_obj = lxml.etree.parse(generated_file_path)
    vehicles_xsd.assertValid(xml_obj)


def test_generates_matsim_vehicles_xml_file_containing_expected_vehicle_types(tmpdir):
    vehicle_dict = {
        'veh_1': 'Bus',
        'veh_2': 'Bus',
        'veh_3': 'Bus',
        'veh_4': 'Tram',
        'veh_5': 'Rail',
        'veh_6': 'Underground Service'
    }
    matsim_xml_writer.write_vehicles(tmpdir, vehicle_dict)

    generated_file_path = os.path.join(tmpdir, 'vehicles.xml')
    xml_obj = lxml.etree.parse(generated_file_path)

    vehicle_types = xml_obj.findall('{http://www.matsim.org/files/dtd}vehicleType')
    expected_vehicle_types = set(vehicle_dict.values())
    actual_vehicle_types = set()
    for vehicle_type in vehicle_types:
        actual_vehicle_types.add(vehicle_type.get('id'))
    assert expected_vehicle_types == actual_vehicle_types


def test_generates_matsim_vehicles_xml_file_containing_expected_vehicles(tmpdir):
    vehicle_dict = {
        'veh_1': 'Bus',
        'veh_2': 'Bus',
        'veh_3': 'Bus',
        'veh_4': 'Tram',
        'veh_5': 'Rail',
        'veh_6': 'Underground Service'
    }
    matsim_xml_writer.write_vehicles(tmpdir, vehicle_dict)

    generated_file_path = os.path.join(tmpdir, 'vehicles.xml')
    xml_obj = lxml.etree.parse(generated_file_path)

    vehicles = xml_obj.findall('{http://www.matsim.org/files/dtd}vehicle')
    assert len(vehicles) == len(vehicle_dict)
    for vehicle in vehicles:
        assert vehicle_dict[vehicle.get('id')] == vehicle.get('type')


def test_throws_exception_when_generating_vehicles_xml_from_unrecognised_vehicle_types(tmpdir):
    vehicle_dict = {
        'veh_1': 'Bus',
        'veh_4': 'Tram',
        'veh_5': 'Rocket ship'
    }
    with pytest.raises(NotImplementedError) as e:
        matsim_xml_writer.write_vehicles(tmpdir, vehicle_dict)
    assert 'No Vehicle Type info available for mode Rocket ship, you will need to add it to matsim_xml_values.py' \
           in str(e.value)


def test_write_matsim_vehicles_produces_symantically_equal_xml_to_input_matsim_xml(network_object_from_test_data, tmpdir):
    network = network_object_from_test_data
    vehicles = matsim_xml_writer.write_matsim_schedule(tmpdir, network.schedule)
    matsim_xml_writer.write_vehicles(tmpdir, vehicles)

    xml_diff.assert_semantically_equal(os.path.join(tmpdir, 'vehicles.xml'), pt2matsim_vehicles_file)