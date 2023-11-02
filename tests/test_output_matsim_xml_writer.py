import os
import xml.etree.cElementTree as ET
from collections import OrderedDict
from copy import deepcopy

import lxml
import pytest
import xmltodict
from shapely.geometry import LineString

from genet.core import Network
from genet.exceptions import MalformedAdditionalAttributeError
from genet.input import read
from genet.output import matsim_xml_writer
from genet.schedule_elements import read_vehicle_types

MATSIM_DATA_DIR = pytest.test_data_dir / "matsim"
pt2matsim_network_test_file = MATSIM_DATA_DIR / "network.xml"
pt2matsim_schedule_file = MATSIM_DATA_DIR / "schedule.xml"
pt2matsim_vehicles_file = MATSIM_DATA_DIR / "vehicles.xml"


@pytest.fixture
def vehicle_types(vehicle_definitions_config_path):
    return read_vehicle_types(vehicle_definitions_config_path)


@pytest.fixture
def vehicles_xsd():
    xsd_path = (pytest.test_data_dir / "dtd" / "matsim" / "vehicleDefinitions_v1.0.xsd").absolute()

    xml_schema_doc = lxml.etree.parse(xsd_path)
    yield lxml.etree.XMLSchema(xml_schema_doc)


@pytest.fixture
def schedule_dtd():
    dtd_path = (pytest.test_data_dir / "dtd" / "matsim" / "transitSchedule_v2.dtd").absolute()
    yield lxml.etree.DTD(dtd_path)


def test_generates_valid_matsim_network_xml_file(
    network_object_from_test_data, network_dtd, tmpdir
):
    matsim_xml_writer.write_matsim_network(tmpdir, network_object_from_test_data)

    generated_network_file_path = os.path.join(tmpdir, "network.xml")
    xml_obj = lxml.etree.parse(generated_network_file_path)
    assert network_dtd.validate(
        xml_obj
    ), "Doc generated at {} is not valid against DTD due to {}".format(
        generated_network_file_path, network_dtd.error_log.filter_from_errors()
    )


def test_network_from_test_osm_data_produces_valid_matsim_network_xml_file(
    full_fat_default_config_path, network_dtd, tmpdir, osm_test_file
):
    network = read.read_osm(osm_test_file, full_fat_default_config_path, 1, "epsg:27700")
    network.write_to_matsim(tmpdir)

    generated_network_file_path = os.path.join(tmpdir, "network.xml")
    xml_obj = lxml.etree.parse(generated_network_file_path)
    assert network_dtd.validate(
        xml_obj
    ), "Doc generated at {} is not valid against DTD due to {}".format(
        generated_network_file_path, network_dtd.error_log.filter_from_errors()
    )


@pytest.fixture()
def network_with_extra_attrib():
    network = Network("epsg:27700")
    network.add_node("0", attribs={"id": "0", "x": 1, "y": 2, "lat": 1, "lon": 2})
    network.add_node("1", attribs={"id": "1", "x": 2, "y": 2, "lat": 2, "lon": 2})
    network.add_link(
        "0",
        "0",
        "1",
        attribs={
            "id": "0",
            "from": "0",
            "to": "1",
            "length": 1,
            "freespeed": 1,
            "capacity": 20,
            "permlanes": 1,
            "oneway": "1",
            "modes": ["car"],
            "extra_Special_attrib": 12,
        },
    )
    return network


def test_network_with_extra_attribs_produces_valid_matsim_network_xml_file(
    network_with_extra_attrib, tmpdir, network_dtd
):
    network_with_extra_attrib.write_to_matsim(tmpdir)
    generated_network_file_path = os.path.join(tmpdir, "network.xml")
    xml_obj = lxml.etree.parse(generated_network_file_path)
    assert network_dtd.validate(
        xml_obj
    ), "Doc generated at {} is not valid against DTD due to {}".format(
        generated_network_file_path, network_dtd.error_log.filter_from_errors()
    )


def test_network_with_extra_attribs_saves_all_data_to_xml(
    assert_semantically_equal, network_with_extra_attrib, tmpdir, network_dtd
):
    network_with_extra_attrib.write_to_matsim(tmpdir)
    generated_network_file_path = os.path.join(tmpdir, "network.xml")
    _network_from_file = read.read_matsim(
        path_to_network=generated_network_file_path, epsg="epsg:27700"
    )
    assert_semantically_equal(
        dict(_network_from_file.nodes()),
        {
            "0": {
                "id": "0",
                "x": 1.0,
                "y": 2.0,
                "lon": -7.557148039524952,
                "lat": 49.766825803756994,
                "s2_id": 5205973754090365183,
            },
            "1": {
                "id": "1",
                "x": 2.0,
                "y": 2.0,
                "lon": -7.557134218911724,
                "lat": 49.766826468710484,
                "s2_id": 5205973754090480551,
            },
        },
    )
    assert_semantically_equal(
        dict(_network_from_file.links()),
        {
            "0": {
                "id": "0",
                "from": "0",
                "to": "1",
                "freespeed": 1.0,
                "capacity": 20.0,
                "permlanes": 1.0,
                "oneway": "1",
                "modes": {"car"},
                "s2_from": 5205973754090365183,
                "s2_to": 5205973754090480551,
                "length": 1.0,
            }
        },
    )


def test_tolerates_networks_with_no_oneway_flag_on_links(
    assert_semantically_equal, tmpdir, network_dtd
):
    network = Network("epsg:27700")
    network.add_node("0", attribs={"id": "0", "x": 1, "y": 2, "lat": 1, "lon": 2})
    network.add_node("1", attribs={"id": "1", "x": 2, "y": 2, "lat": 2, "lon": 2})
    network.add_link(
        "0",
        "0",
        "1",
        attribs={
            "id": "0",
            "from": "0",
            "to": "1",
            "length": 1,
            "freespeed": 1,
            "capacity": 20,
            "permlanes": 1,
            "modes": ["car"],
        },
    )
    network.write_to_matsim(tmpdir)

    generated_network_file_path = os.path.join(tmpdir, "network.xml")
    xml_obj = lxml.etree.parse(generated_network_file_path)
    assert network_dtd.validate(
        xml_obj
    ), "Doc generated at {} is not valid against DTD due to {}".format(
        generated_network_file_path, network_dtd.error_log.filter_from_errors()
    )

    _network_from_file = read.read_matsim(
        path_to_network=generated_network_file_path, epsg="epsg:27700"
    )
    assert_semantically_equal(
        dict(_network_from_file.nodes()),
        {
            "0": {
                "id": "0",
                "x": 1.0,
                "y": 2.0,
                "lon": -7.557148039524952,
                "lat": 49.766825803756994,
                "s2_id": 5205973754090365183,
            },
            "1": {
                "id": "1",
                "x": 2.0,
                "y": 2.0,
                "lon": -7.557134218911724,
                "lat": 49.766826468710484,
                "s2_id": 5205973754090480551,
            },
        },
    )
    assert_semantically_equal(
        dict(_network_from_file.links()),
        {
            "0": {
                "id": "0",
                "from": "0",
                "to": "1",
                "freespeed": 1.0,
                "capacity": 20.0,
                "permlanes": 1.0,
                "modes": {"car"},
                "s2_from": 5205973754090365183,
                "s2_to": 5205973754090480551,
                "length": 1.0,
            }
        },
    )


def test_network_with_attribs_doesnt_loose_any_attributes_after_saving(
    assert_semantically_equal, tmpdir
):
    network = Network("epsg:27700")
    network.add_node("0", attribs={"id": "0", "x": 1, "y": 2, "lat": 1, "lon": 2})
    network.add_node("1", attribs={"id": "1", "x": 2, "y": 2, "lat": 2, "lon": 2})
    network.add_link(
        "0",
        "0",
        "1",
        attribs={
            "id": "0",
            "from": "0",
            "to": "1",
            "length": 1,
            "freespeed": 1,
            "capacity": 20,
            "permlanes": 1,
            "oneway": "1",
            "modes": ["car"],
        },
    )
    network.add_link(
        "0",
        "0",
        "1",
        attribs={
            "id": "0",
            "from": "0",
            "to": "1",
            "length": 1,
            "freespeed": 1,
            "capacity": 20,
            "permlanes": 1,
            "oneway": "1",
            "modes": ["car"],
            "attributes": {
                "osm:way:lanes": {"name": "osm:way:lanes", "class": "java.lang.String", "text": "3"}
            },
        },
    )

    link_attributes = deepcopy(dict(network.links()))
    node_attributes = deepcopy(dict(network.nodes()))

    network.write_to_matsim(tmpdir)

    link_attributes_post_save = dict(network.links())
    node_attributes_post_save = dict(network.nodes())

    assert_semantically_equal(link_attributes_post_save, link_attributes)
    assert_semantically_equal(node_attributes_post_save, node_attributes)


def test_saving_network_with_geometry_doesnt_change_data_on_the_network(
    assert_semantically_equal, tmpdir
):
    network = Network("epsg:27700")
    network.add_node("0", attribs={"id": "0", "x": 1, "y": 2, "lat": 1, "lon": 2})
    network.add_node("1", attribs={"id": "1", "x": 2, "y": 2, "lat": 2, "lon": 2})
    network.add_link(
        "0",
        "0",
        "1",
        attribs={
            "id": "0",
            "from": "0",
            "to": "1",
            "length": 1,
            "freespeed": 1,
            "capacity": 20,
            "permlanes": 1,
            "oneway": "1",
            "modes": ["car"],
            "geometry": LineString([(1, 2), (2, 3), (3, 4)]),
        },
    )
    network.add_link(
        "0",
        "0",
        "1",
        attribs={
            "id": "0",
            "from": "0",
            "to": "1",
            "length": 1,
            "freespeed": 1,
            "capacity": 20,
            "permlanes": 1,
            "oneway": "1",
            "modes": ["car"],
            "geometry": LineString([(1, 2), (2, 3), (3, 4)]),
            "attributes": {
                "osm:way:lanes": {"name": "osm:way:lanes", "class": "java.lang.String", "text": "3"}
            },
        },
    )

    link_attributes = deepcopy(dict(network.links()))
    node_attributes = deepcopy(dict(network.nodes()))

    network.write_to_matsim(tmpdir)

    link_attributes_post_save = dict(network.links())
    node_attributes_post_save = dict(network.nodes())

    assert_semantically_equal(link_attributes_post_save, link_attributes)
    assert_semantically_equal(node_attributes_post_save, node_attributes)


def test_saving_network_with_geometry_produces_correct_polyline_in_link_attributes(tmpdir):
    network = Network("epsg:27700")
    network.add_node("0", attribs={"id": "0", "x": 1, "y": 2, "lat": 1, "lon": 2})
    network.add_node("1", attribs={"id": "1", "x": 2, "y": 2, "lat": 2, "lon": 2})
    network.add_link(
        "0",
        "0",
        "1",
        attribs={
            "id": "0",
            "from": "0",
            "to": "1",
            "length": 1,
            "freespeed": 1,
            "capacity": 20,
            "permlanes": 1,
            "oneway": "1",
            "modes": ["car"],
            "geometry": LineString([(1, 2), (2, 3), (3, 4)]),
            "extra_Special_attrib": 12,
        },
    )

    network.write_to_matsim(tmpdir)

    found_geometry_attrib = False
    for event, elem in ET.iterparse(os.path.join(tmpdir, "network.xml"), events=("start", "end")):
        if event == "start":
            if elem.tag == "attribute":
                if elem.attrib["name"] == "geometry":
                    assert elem.text == "_ibE_seK_ibE_ibE_ibE_ibE"
                    found_geometry_attrib = True
    assert found_geometry_attrib


@pytest.fixture()
def network_with_badly_formatted_attributes_and_geometry():
    # attributes are assumed to be a dictionary of format: key = name of attribute, value = value under that named
    # attribute. Due to the fact that user can do virtually anything to edge attributes, or due to calculation error,
    # this may not be the case. If it's not of correct format, we don't expect it to get saved to the matsim network.xml
    network = Network("epsg:27700")
    network.add_node("0", attribs={"id": "0", "x": 1, "y": 2, "lat": 1, "lon": 2})
    network.add_node("1", attribs={"id": "1", "x": 2, "y": 2, "lat": 2, "lon": 2})

    link_attribs = {
        "id": "0",
        "from": "0",
        "to": "1",
        "length": 1,
        "freespeed": 1,
        "capacity": 20,
        "permlanes": 1,
        "oneway": "1",
        "modes": ["car"],
        "geometry": LineString([(1, 2), (2, 3), (3, 4)]),
        "attributes": "heyo",
    }

    network.add_link("0", "0", "1", attribs=link_attribs)
    return {
        "network": network,
        "encoded_geometry": "_ibE_seK_ibE_ibE_ibE_ibE",
        "original_link_attributes": link_attribs,
    }


def test_saving_network_with_wrongly_formatted_attributes_with_geometry_does_not_alter_attributes_data(
    assert_semantically_equal, tmpdir, network_with_badly_formatted_attributes_and_geometry
):
    network_with_badly_formatted_attributes_and_geometry["network"].write_to_matsim(tmpdir)

    assert_semantically_equal(
        network_with_badly_formatted_attributes_and_geometry["network"].link("0"),
        network_with_badly_formatted_attributes_and_geometry["original_link_attributes"],
    )


def test_saving_network_with_wrongly_formatted_attributes_with_geometry_removes_bad_attribute_for_saving_to_xml(
    assert_semantically_equal, network_with_badly_formatted_attributes_and_geometry
):
    assert_semantically_equal(
        matsim_xml_writer.check_additional_attributes(
            network_with_badly_formatted_attributes_and_geometry["original_link_attributes"]
        ),
        {
            k: v
            for k, v in network_with_badly_formatted_attributes_and_geometry[
                "original_link_attributes"
            ].items()
            if k != "attributes"
        },
    )


def test_saving_network_with_badly_formatted_attributes_with_geometry_saves_correct_geometry(
    tmpdir, network_with_badly_formatted_attributes_and_geometry
):
    network_with_badly_formatted_attributes_and_geometry["network"].write_to_matsim(tmpdir)

    found_geometry_attrib = False
    for event, elem in ET.iterparse(os.path.join(tmpdir, "network.xml"), events=("start", "end")):
        if event == "start":
            if elem.tag == "attribute":
                if elem.attrib["name"] == "geometry":
                    assert (
                        elem.text
                        == network_with_badly_formatted_attributes_and_geometry["encoded_geometry"]
                    )
                    found_geometry_attrib = True
    assert found_geometry_attrib


def test_saving_network_with_bonkers_attributes_with_geometry(assert_semantically_equal, tmpdir):
    # attributes are assumed to be a nested dictionary of very specific format. Due to the fact that user can
    # do virtually anything to edge attributes, or due to calculation error, this may not be the case. If it's not
    # of correct format, we don't expect it to get saved to the matsim network.xml
    network = Network("epsg:27700")
    network.add_node("0", attribs={"id": "0", "x": 1, "y": 2, "lat": 1, "lon": 2})
    network.add_node("1", attribs={"id": "1", "x": 2, "y": 2, "lat": 2, "lon": 2})

    link_attribs = {
        "id": "0",
        "from": "0",
        "to": "1",
        "length": 1,
        "freespeed": 1,
        "capacity": 20,
        "permlanes": 1,
        "oneway": "1",
        "modes": ["car"],
        "geometry": LineString([(1, 2), (2, 3), (3, 4)]),
        "attributes": float("nan"),
    }

    network.add_link("0", "0", "1", attribs=link_attribs)
    network.write_to_matsim(tmpdir)

    assert_semantically_equal(dict(network.links()), {"0": link_attribs})

    assert_semantically_equal(
        matsim_xml_writer.check_additional_attributes(link_attribs),
        {
            "id": "0",
            "from": "0",
            "to": "1",
            "length": 1,
            "freespeed": 1,
            "capacity": 20,
            "permlanes": 1,
            "oneway": "1",
            "modes": ["car"],
            "geometry": LineString([(1, 2), (2, 3), (3, 4)]),
        },
    )

    found_geometry_attrib = False
    for event, elem in ET.iterparse(os.path.join(tmpdir, "network.xml"), events=("start", "end")):
        if event == "start":
            if elem.tag == "attribute":
                if elem.attrib["name"] == "geometry":
                    assert elem.text == "_ibE_seK_ibE_ibE_ibE_ibE"
                    found_geometry_attrib = True
    assert found_geometry_attrib


def test_saving_network_with_correct_attributes_and_geometry(assert_semantically_equal, tmpdir):
    # attributes are assumed to be a nested dictionary of very specific format. Due to the fact that user can
    # do virtually anything to edge attributes, or due to calculation error, this may not be the case. If it's not
    # of correct format, we don't expect it to get saved to the matsim network.xml
    network = Network("epsg:27700")
    network.add_node("0", attribs={"id": "0", "x": 1, "y": 2, "lat": 1, "lon": 2})
    network.add_node("1", attribs={"id": "1", "x": 2, "y": 2, "lat": 2, "lon": 2})

    link_attribs = {
        "id": "0",
        "from": "0",
        "to": "1",
        "length": 1,
        "freespeed": 1,
        "capacity": 20,
        "permlanes": 1,
        "oneway": "1",
        "modes": ["car"],
        "geometry": LineString([(1, 2), (2, 3), (3, 4)]),
        "attributes": {
            "osm:way:lanes": {"name": "osm:way:lanes", "class": "java.lang.String", "text": "3"}
        },
    }

    network.add_link("0", "0", "1", attribs=link_attribs)
    network.write_to_matsim(tmpdir)

    assert_semantically_equal(dict(network.links()), {"0": link_attribs})

    assert_semantically_equal(
        matsim_xml_writer.check_additional_attributes(link_attribs), link_attribs
    )

    found_geometry_attrib = False
    for event, elem in ET.iterparse(os.path.join(tmpdir, "network.xml"), events=("start", "end")):
        if event == "start":
            if elem.tag == "attribute":
                if elem.attrib["name"] == "geometry":
                    assert elem.text == "_ibE_seK_ibE_ibE_ibE_ibE"
                    found_geometry_attrib = True
    assert found_geometry_attrib


def test_saving_network_with_geometry_produces_polyline_if_link_already_has_other_attributes(
    tmpdir,
):
    network = Network("epsg:27700")
    network.add_node("0", attribs={"id": "0", "x": 1, "y": 2, "lat": 1, "lon": 2})
    network.add_node("1", attribs={"id": "1", "x": 2, "y": 2, "lat": 2, "lon": 2})
    network.add_link(
        "0",
        "0",
        "1",
        attribs={
            "id": "0",
            "from": "0",
            "to": "1",
            "length": 1,
            "freespeed": 1,
            "capacity": 20,
            "permlanes": 1,
            "oneway": "1",
            "modes": ["car"],
            "geometry": LineString([(1, 2), (2, 3), (3, 4)]),
            "attributes": {
                "osm:way:lanes": {"name": "osm:way:lanes", "class": "java.lang.String", "text": "3"}
            },
        },
    )

    network.write_to_matsim(tmpdir)

    found_geometry_attrib = False
    for event, elem in ET.iterparse(os.path.join(tmpdir, "network.xml"), events=("start", "end")):
        if event == "start":
            if elem.tag == "attribute":
                if elem.attrib["name"] == "geometry":
                    assert elem.text == "_ibE_seK_ibE_ibE_ibE_ibE"
                    found_geometry_attrib = True
    assert found_geometry_attrib


@pytest.fixture()
def attribute_in_different_forms():
    return {
        "long_form": {"attrib": {"name": "attrib", "class": "java.lang.String", "text": "3"}},
        "short_form": {"attrib": "3"},
    }


def test_long_form_is_of_matsim_format(attribute_in_different_forms):
    assert matsim_xml_writer.is_of_matsim_format(
        attribute_in_different_forms["long_form"]["attrib"]
    )


def test_short_form_is_not_of_matsim_format(attribute_in_different_forms):
    assert not matsim_xml_writer.is_of_matsim_format(
        attribute_in_different_forms["short_form"]["attrib"]
    )


def test_short_form_can_be_put_in_matsim_format(attribute_in_different_forms):
    assert matsim_xml_writer.can_be_put_in_matsim_format(
        attribute_in_different_forms["short_form"]["attrib"]
    )


def test_the_value_of_short_form_being_put_in_matsim_format(
    assert_semantically_equal, attribute_in_different_forms
):
    assert_semantically_equal(
        matsim_xml_writer.format_to_matsim(
            "attrib", attribute_in_different_forms["short_form"]["attrib"]
        ),
        attribute_in_different_forms["long_form"]["attrib"],
    )


def test_malformed_attrib_throws_exception_when_requested_to_put_in_matsim_format(mocker):
    mocker.patch.object(matsim_xml_writer, "can_be_put_in_matsim_format", return_value=False)
    with pytest.raises(MalformedAdditionalAttributeError) as e:
        matsim_xml_writer.format_to_matsim("", "")
    assert matsim_xml_writer.EXPECTED_FORMAT_FOR_ADDITIONAL_ATTRIBUTES_MESSAGE in str(e.value)


def test_particular_attribute_is_deleted_if_deemed_malformed(assert_semantically_equal, mocker):
    mocker.patch.object(matsim_xml_writer, "can_be_put_in_matsim_format", side_effect=[True, False])
    link_attribs = {
        "id": "0",
        "from": "0",
        "to": "1",
        "length": 1,
        "freespeed": 1,
        "capacity": 20,
        "permlanes": 1,
        "oneway": "1",
        "modes": ["car"],
        "attributes": OrderedDict({"attrib1": "1", "malformed_attrib2": "2"}),
    }
    assert_semantically_equal(
        matsim_xml_writer.check_additional_attributes(link_attribs),
        {
            "id": "0",
            "from": "0",
            "to": "1",
            "length": 1,
            "freespeed": 1,
            "capacity": 20,
            "permlanes": 1,
            "oneway": "1",
            "modes": ["car"],
            "attributes": OrderedDict({"attrib1": "1"}),
        },
    )


def test_attributes_are_deleted_if_all_are_deemed_malformed(assert_semantically_equal, mocker):
    mocker.patch.object(matsim_xml_writer, "can_be_put_in_matsim_format", return_value=False)
    link_attribs = {
        "id": "0",
        "from": "0",
        "to": "1",
        "length": 1,
        "freespeed": 1,
        "capacity": 20,
        "permlanes": 1,
        "oneway": "1",
        "modes": ["car"],
        "attributes": {"malformed_attrib1": "1", "malformed_attrib2": "2"},
    }
    assert_semantically_equal(
        matsim_xml_writer.check_additional_attributes(link_attribs),
        {
            "id": "0",
            "from": "0",
            "to": "1",
            "length": 1,
            "freespeed": 1,
            "capacity": 20,
            "permlanes": 1,
            "oneway": "1",
            "modes": ["car"],
        },
    )


def test_network_with_additional_node_attribs_produces_valid_matsim_xml_file(
    network_with_additional_node_attrib, tmpdir, network_dtd
):
    network_with_additional_node_attrib.write_to_matsim(tmpdir)
    generated_network_file_path = os.path.join(tmpdir, "network.xml")
    xml_obj = lxml.etree.parse(generated_network_file_path)
    assert network_dtd.validate(
        xml_obj
    ), "Doc generated at {} is not valid against DTD due to {}".format(
        generated_network_file_path, network_dtd.error_log.filter_from_errors()
    )


def test_network_with_additional_node_attribs_saves_all_data_to_xml(
    assert_xml_semantically_equal,
    network_with_additional_node_attrib,
    tmpdir,
    network_dtd,
    network_with_additional_node_attrib_xml_file,
):
    network_with_additional_node_attrib.write_to_matsim(tmpdir)

    generated_network_file_path = os.path.join(tmpdir, "network.xml")
    assert_xml_semantically_equal(
        generated_network_file_path, network_with_additional_node_attrib_xml_file
    )


def test_saving_network_with_additional_node_attribs_does_not_change_data_post_save(
    network_with_additional_node_attrib, tmpdir
):
    network_with_additional_node_attrib.write_to_matsim(tmpdir)
    assert network_with_additional_node_attrib.node("0")["attributes"] == {"osm:node:data": 3}


@pytest.fixture()
def network_with_additional_simple_form_node_attrib():
    network = Network("epsg:27700")
    network.add_node("0", attribs={"id": "0", "x": 1, "y": 2, "attributes": {"osm:node:data": 3}})
    network.add_node("1", attribs={"id": "1", "x": 2, "y": 2})
    network.add_link(
        "0",
        "0",
        "1",
        attribs={
            "id": "0",
            "from": "0",
            "to": "1",
            "length": 1,
            "freespeed": 1,
            "capacity": 20,
            "permlanes": 1,
            "oneway": "1",
            "modes": ["car"],
        },
    )
    return network


def test_simple_form_additional_attributes_are_indistinguishable_in_xml(
    assert_xml_semantically_equal,
    tmpdir,
    network_with_additional_simple_form_node_attrib,
    network_with_additional_node_attrib_xml_file,
):
    network_with_additional_simple_form_node_attrib.write_to_matsim(tmpdir)

    generated_network_file_path = tmpdir.join("network.xml")
    assert_xml_semantically_equal(
        generated_network_file_path, network_with_additional_node_attrib_xml_file
    )


def test_non_string_simple_form_additional_attribute_saves_to_xml_correctly(tmpdir):
    network = Network("epsg:27700")
    network.add_node("0", attribs={"id": "0", "x": 1, "y": 2, "attributes": {"osm:node:data": 3}})

    network.write_to_matsim(tmpdir)

    xml_data = xmltodict.parse(tmpdir.join("network.xml").read())
    assert (
        xml_data["network"]["nodes"]["node"]["attributes"]["attribute"]["@name"] == "osm:node:data"
    )
    assert (
        xml_data["network"]["nodes"]["node"]["attributes"]["attribute"]["@class"]
        == "java.lang.Integer"
    )
    assert xml_data["network"]["nodes"]["node"]["attributes"]["attribute"]["#text"] == "3"


def test_write_matsim_network_produces_semantically_equal_xml_to_input_matsim_xml(
    assert_xml_semantically_equal, network_object_from_test_data, tmpdir
):
    matsim_xml_writer.write_matsim_network(tmpdir, network_object_from_test_data)

    assert_xml_semantically_equal(os.path.join(tmpdir, "network.xml"), pt2matsim_network_test_file)


def test_generates_valid_matsim_schedule_xml_file(
    network_object_from_test_data, schedule_dtd, tmpdir
):
    matsim_xml_writer.write_matsim_schedule(tmpdir, network_object_from_test_data.schedule)

    generated_file_path = os.path.join(tmpdir, "schedule.xml")
    xml_obj = lxml.etree.parse(generated_file_path)
    assert schedule_dtd.validate(
        xml_obj
    ), "Doc generated at {} is not valid against DTD due to {} errors - first error {}".format(
        generated_file_path,
        len(schedule_dtd.error_log.filter_from_errors()),
        schedule_dtd.error_log.filter_from_errors()[0],
    )


def test_write_matsim_schedule_produces_semantically_equal_xml_to_input_matsim_xml(
    assert_xml_semantically_equal, network_object_from_test_data, tmpdir
):
    matsim_xml_writer.write_matsim_schedule(tmpdir, network_object_from_test_data.schedule)

    assert_xml_semantically_equal(os.path.join(tmpdir, "schedule.xml"), pt2matsim_schedule_file)


def test_write_matsim_schedule_produces_semantically_equal_xml_to_input_matsim_xml_if_stops_need_to_reprojected(
    assert_xml_semantically_equal, network_object_from_test_data, tmpdir
):
    # we change all the stops in the one service and one route that exists in the test data
    network_object_from_test_data.schedule.route(
        "VJbd8660f05fe6f744e58a66ae12bd66acbca88b98"
    ).reproject("epsg:3035")

    matsim_xml_writer.write_matsim_schedule(tmpdir, network_object_from_test_data.schedule)

    assert_xml_semantically_equal(os.path.join(tmpdir, "schedule.xml"), pt2matsim_schedule_file)


def test_schedule_with_additional_stop_attribs_produces_valid_matsim_xml_file(
    schedule_with_additional_attrib_stop, tmpdir, schedule_dtd
):
    schedule_with_additional_attrib_stop.write_to_matsim(tmpdir)
    generated_schedule_file_path = os.path.join(tmpdir, "schedule.xml")
    xml_obj = lxml.etree.parse(generated_schedule_file_path)
    assert schedule_dtd.validate(
        xml_obj
    ), "Doc generated at {} is not valid against DTD due to {}".format(
        generated_schedule_file_path, schedule_dtd.error_log.filter_from_errors()
    )


def test_schedule_with_additional_stop_attribs_saves_all_data_to_xml(
    assert_xml_semantically_equal,
    schedule_with_additional_attrib_stop,
    tmpdir,
    schedule_with_additional_attrib_stop_xml_file,
):
    schedule_with_additional_attrib_stop.write_to_matsim(tmpdir)

    generated_schedule_file_path = os.path.join(tmpdir, "schedule.xml")
    assert_xml_semantically_equal(
        generated_schedule_file_path, schedule_with_additional_attrib_stop_xml_file
    )


def test_saving_schedule_with_additional_stop_attribs_does_not_change_data_post_save(
    schedule_with_additional_attrib_stop, tmpdir
):
    schedule_with_additional_attrib_stop.write_to_matsim(tmpdir)
    assert schedule_with_additional_attrib_stop.stop("s1").attributes == {
        "carAccessible": "true",
        "accessLinkId_car": "linkID",
    }


def test_schedule_with_additional_route_attribs_produces_valid_matsim_xml_file(
    schedule_with_additional_route_attrib, tmpdir, schedule_dtd
):
    schedule_with_additional_route_attrib.write_to_matsim(tmpdir)
    generated_schedule_file_path = os.path.join(tmpdir, "schedule.xml")
    xml_obj = lxml.etree.parse(generated_schedule_file_path)
    assert schedule_dtd.validate(
        xml_obj
    ), "Doc generated at {} is not valid against DTD due to {}".format(
        generated_schedule_file_path, schedule_dtd.error_log.filter_from_errors()
    )


def test_schedule_with_additional_route_attribs_saves_all_data_to_xml(
    assert_xml_semantically_equal,
    schedule_with_additional_route_attrib,
    tmpdir,
    schedule_with_additional_route_attribs_xml_file,
):
    schedule_with_additional_route_attrib.write_to_matsim(tmpdir)

    generated_schedule_file_path = os.path.join(tmpdir, "schedule.xml")
    assert_xml_semantically_equal(
        generated_schedule_file_path, schedule_with_additional_route_attribs_xml_file
    )


def test_saving_schedule_with_additional_route_attribs_does_not_change_data_post_save(
    schedule_with_additional_route_attrib, tmpdir
):
    schedule_with_additional_route_attrib.write_to_matsim(tmpdir)
    assert (
        schedule_with_additional_route_attrib.route("r1").attributes["additional_attrib"]
        == "attrib_value"
    )


def test_schedule_with_additional_service_attribs_produces_valid_matsim_xml_file(
    schedule_with_additional_service_attrib, tmpdir, schedule_dtd
):
    schedule_with_additional_service_attrib.write_to_matsim(tmpdir)
    generated_schedule_file_path = os.path.join(tmpdir, "schedule.xml")
    xml_obj = lxml.etree.parse(generated_schedule_file_path)
    assert schedule_dtd.validate(
        xml_obj
    ), "Doc generated at {} is not valid against DTD due to {}".format(
        generated_schedule_file_path, schedule_dtd.error_log.filter_from_errors()
    )


def test_schedule_with_additional_service_attribs_saves_all_data_to_xml(
    assert_xml_semantically_equal,
    schedule_with_additional_service_attrib,
    tmpdir,
    schedule_with_additional_service_attribs_xml_file,
):
    schedule_with_additional_service_attrib.write_to_matsim(tmpdir)

    generated_schedule_file_path = os.path.join(tmpdir, "schedule.xml")
    assert_xml_semantically_equal(
        generated_schedule_file_path, schedule_with_additional_service_attribs_xml_file
    )


def test_saving_schedule_with_additional_service_attribs_does_not_change_data_post_save(
    schedule_with_additional_service_attrib, tmpdir
):
    schedule_with_additional_service_attrib.write_to_matsim(tmpdir)
    assert (
        schedule_with_additional_service_attrib["s1"].attributes["additional_attrib"]
        == "attrib_value"
    )


def test_schedule_with_additional_attribs_produces_valid_matsim_xml_file(
    schedule_with_additional_attrib, tmpdir, schedule_dtd
):
    schedule_with_additional_attrib.write_to_matsim(tmpdir)
    generated_schedule_file_path = os.path.join(tmpdir, "schedule.xml")
    xml_obj = lxml.etree.parse(generated_schedule_file_path)
    assert schedule_dtd.validate(
        xml_obj
    ), "Doc generated at {} is not valid against DTD due to {}".format(
        generated_schedule_file_path, schedule_dtd.error_log.filter_from_errors()
    )


def test_schedule_with_additional_attribs_saves_all_data_to_xml(
    assert_xml_semantically_equal,
    schedule_with_additional_attrib,
    tmpdir,
    schedule_with_additional_attribs_xml_file,
):
    schedule_with_additional_attrib.write_to_matsim(tmpdir)

    generated_schedule_file_path = os.path.join(tmpdir, "schedule.xml")
    assert_xml_semantically_equal(
        generated_schedule_file_path, schedule_with_additional_attribs_xml_file
    )


def test_saving_schedule_with_additional_attribs_does_not_change_data_post_save(
    schedule_with_additional_attrib, tmpdir
):
    schedule_with_additional_attrib.write_to_matsim(tmpdir)
    assert schedule_with_additional_attrib.attributes["additional_attrib"] == "attrib_value"


def test_generates_valid_matsim_vehicles_xml_file(tmpdir, vehicles_xsd, vehicle_types):
    vehicle_dict = {
        "veh_1": {"type": "bus"},
        "veh_2": {"type": "bus"},
        "veh_3": {"type": "bus"},
        "veh_4": {"type": "tram"},
        "veh_5": {"type": "rail"},
        "veh_6": {"type": "subway"},
    }
    matsim_xml_writer.write_vehicles(tmpdir, vehicle_dict, vehicle_types)

    generated_file_path = os.path.join(tmpdir, "vehicles.xml")
    xml_obj = lxml.etree.parse(generated_file_path)
    vehicles_xsd.assertValid(xml_obj)


def test_generates_matsim_vehicles_xml_file_containing_expected_vehicle_types(
    tmpdir, vehicle_types
):
    vehicle_dict = {
        "veh_1": {"type": "bus"},
        "veh_2": {"type": "bus"},
        "veh_3": {"type": "bus"},
        "veh_4": {"type": "tram"},
        "veh_5": {"type": "rail"},
        "veh_6": {"type": "subway"},
    }
    matsim_xml_writer.write_vehicles(tmpdir, vehicle_dict, vehicle_types)

    generated_file_path = os.path.join(tmpdir, "vehicles.xml")
    xml_obj = lxml.etree.parse(generated_file_path)

    vehicle_types = xml_obj.findall("{http://www.matsim.org/files/dtd}vehicleType")
    expected_vehicle_types = {v["type"] for k, v in vehicle_dict.items()}
    actual_vehicle_types = set()
    for vehicle_type in vehicle_types:
        actual_vehicle_types.add(vehicle_type.get("id"))
    assert expected_vehicle_types == actual_vehicle_types


def test_generates_matsim_vehicles_xml_file_containing_expected_vehicles(tmpdir, vehicle_types):
    vehicle_dict = {
        "veh_1": {"type": "bus"},
        "veh_2": {"type": "bus"},
        "veh_3": {"type": "bus"},
        "veh_4": {"type": "tram"},
        "veh_5": {"type": "rail"},
        "veh_6": {"type": "subway"},
    }
    matsim_xml_writer.write_vehicles(tmpdir, vehicle_dict, vehicle_types)

    generated_file_path = os.path.join(tmpdir, "vehicles.xml")
    xml_obj = lxml.etree.parse(generated_file_path)

    vehicles = xml_obj.findall("{http://www.matsim.org/files/dtd}vehicle")
    assert len(vehicles) == len(vehicle_dict)
    for vehicle in vehicles:
        assert vehicle_dict[vehicle.get("id")]["type"] == vehicle.get("type")


def test_throws_exception_when_generating_vehicles_xml_from_unrecognised_vehicle_types(
    tmpdir, vehicle_types
):
    vehicle_dict = {
        "veh_1": {"type": "bus"},
        "veh_4": {"type": "tram"},
        "veh_5": {"type": "rocket ship"},
    }
    with pytest.raises(NotImplementedError) as e:
        matsim_xml_writer.write_vehicles(tmpdir, vehicle_dict, vehicle_types)
    assert "No Vehicle Type info available for mode rocket ship" in str(e.value)


def test_write_matsim_vehicles_produces_semantically_equal_xml_to_input_matsim_xml(
    assert_xml_semantically_equal, network_object_from_test_data, tmpdir
):
    network = network_object_from_test_data
    matsim_xml_writer.write_matsim_schedule(tmpdir, network.schedule)
    matsim_xml_writer.write_vehicles(
        tmpdir, network.schedule.vehicles, network.schedule.vehicle_types
    )

    assert_xml_semantically_equal(os.path.join(tmpdir, "vehicles.xml"), pt2matsim_vehicles_file)


def test_network_with_elevation_data_produces_valid_matsim_network_xml_file(tmpdir, network_dtd):
    network = Network("epsg:27700")
    network.add_node("0", attribs={"id": "0", "x": 1, "y": 2, "z": 3, "lat": 1, "lon": 2})
    network.add_node("1", attribs={"id": "1", "x": 2, "y": 2, "z": 0, "lat": 2, "lon": 2})
    network.add_link(
        "0",
        "0",
        "1",
        attribs={
            "id": "0",
            "from": "0",
            "to": "1",
            "length": 1,
            "freespeed": 1,
            "capacity": 20,
            "permlanes": 1,
            "oneway": "1",
            "modes": ["car"],
        },
    )
    network.write_to_matsim(tmpdir)
    generated_network_file_path = os.path.join(tmpdir, "network.xml")
    xml_obj = lxml.etree.parse(generated_network_file_path)
    assert network_dtd.validate(
        xml_obj
    ), "Doc generated at {} is not valid against DTD due to {}".format(
        generated_network_file_path, network_dtd.error_log.filter_from_errors()
    )


def test_nodes_with_elevation_written_correctly_to_xml_network(assert_semantically_equal, tmpdir):
    network = Network("epsg:27700")
    network.add_node("0", attribs={"id": "0", "x": 1, "y": 2, "z": 3, "lat": 1, "lon": 2})
    network.add_node("1", attribs={"id": "1", "x": 2, "y": 2, "z": 0, "lat": 2, "lon": 2})
    network.add_link(
        "0",
        "0",
        "1",
        attribs={
            "id": "0",
            "from": "0",
            "to": "1",
            "length": 1,
            "freespeed": 1,
            "capacity": 20,
            "permlanes": 1,
            "oneway": "1",
            "modes": ["car"],
        },
    )
    network.write_to_matsim(tmpdir)
    generated_network_file_path = os.path.join(tmpdir, "network.xml")

    _network_from_file = read.read_matsim(
        path_to_network=generated_network_file_path, epsg="epsg:27700"
    )
    assert_semantically_equal(
        dict(_network_from_file.nodes()),
        {
            "0": {
                "id": "0",
                "x": 1.0,
                "y": 2.0,
                "z": 3.0,
                "lon": -7.557148039524952,
                "lat": 49.766825803756994,
                "s2_id": 5205973754090365183,
            },
            "1": {
                "id": "1",
                "x": 2.0,
                "y": 2.0,
                "z": 0.0,
                "lon": -7.557134218911724,
                "lat": 49.766826468710484,
                "s2_id": 5205973754090480551,
            },
        },
    )
