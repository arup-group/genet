import logging
import os
from copy import deepcopy

from lxml import etree
from pandas import DataFrame

import genet.utils.java_dtypes as java_dtypes
import genet.variables as variables
from genet.exceptions import MalformedAdditionalAttributeError
from genet.output import sanitiser
from genet.schedule_elements import Schedule
from genet.utils.spatial import encode_shapely_linestring_to_polyline
from genet.validate.network import validate_attribute_data

EXPECTED_FORMAT_FOR_ADDITIONAL_ATTRIBUTES_MESSAGE = (
    "The expected format is either a nested dictionary: "
    '`{"attribute_name": {"name": "attribute_name", "class": "java.lang.DTYPE", '
    '"text": attribute_value}}`, or'
    '`{"attribute_name": attribute_value}` with `attribute_value` of supported python format:'
    f"{list(java_dtypes.PYTHON_DTYPE_MAP)}"
)


def get_allowable_attributes(elem_type):
    if elem_type == "node":
        return (
            variables.OPTIONAL_NETWORK_NODE_ATTRIBUTES + variables.NECESSARY_NETWORK_NODE_ATTRIBUTES
        )
    elif elem_type == "link":
        return (
            variables.OPTIONAL_NETWORK_LINK_ATTRIBUTES
            + variables.NECESSARY_NETWORK_LINK_ATTRIBUTES
            + ["geometry"]
        )
    elif elem_type == "stopFacility":
        return (
            variables.OPTIONAL_STOP_FACILITY_ATTRIBUTES
            + variables.NECESSARY_STOP_FACILITY_ATTRIBUTES
        )


def get_necessary_attributes(elem_type):
    if elem_type == "node":
        return variables.NECESSARY_NETWORK_NODE_ATTRIBUTES
    elif elem_type == "link":
        return variables.NECESSARY_NETWORK_LINK_ATTRIBUTES
    elif elem_type == "stopFacility":
        return variables.NECESSARY_STOP_FACILITY_ATTRIBUTES


def retain_allowed_attributes_for_xml(d, elem_type):
    attrib_keys = set(d.keys())
    allowable_attributes = get_allowable_attributes(elem_type)
    for attrib in attrib_keys - set(allowable_attributes):
        del d[attrib]
    return d


def is_of_matsim_format(attribute_value):
    if isinstance(attribute_value, dict):
        if {"name", "class", "text"}.issubset(set(attribute_value.keys())):
            return True
    return False


def can_be_put_in_matsim_format(attrib_value):
    return type(attrib_value) in java_dtypes.PYTHON_DTYPE_MAP


def put_in_matsim_format(attrib_name, attrib_value):
    return {
        "name": attrib_name,
        "class": java_dtypes.python_to_java_dtype(type(attrib_value)),
        "text": attrib_value,
    }


def format_to_matsim(k, _attrib):
    if is_of_matsim_format(_attrib):
        return deepcopy(_attrib)
    elif can_be_put_in_matsim_format(_attrib):
        return put_in_matsim_format(k, _attrib)
    else:
        raise MalformedAdditionalAttributeError(
            f"Attribute: {k} with data: {_attrib} is not of the required "
            f"format. {EXPECTED_FORMAT_FOR_ADDITIONAL_ATTRIBUTES_MESSAGE}"
        )


def check_additional_attributes(attribs):
    if "attributes" in attribs:
        if isinstance(attribs["attributes"], dict):
            attribs_to_delete = []
            for attrib, value in attribs["attributes"].items():
                if not (is_of_matsim_format(value) or can_be_put_in_matsim_format(value)):
                    logging.warning(
                        f'Data under "attributes:{attrib}" key is not of supported format. '
                        f"{EXPECTED_FORMAT_FOR_ADDITIONAL_ATTRIBUTES_MESSAGE}"
                    )
                    attribs_to_delete.append(attrib)
            for attrib in attribs_to_delete:
                logging.warning(f'Deleting malformed {attrib} under key "attributes"')
                del attribs["attributes"][attrib]
            if not attribs["attributes"]:
                logging.warning(
                    f"Attributes are not formatted correctly and will be deleted: {attribs}"
                )
                del attribs["attributes"]
        else:
            logging.warning(f"Attributes are not a dictionary: {attribs}")
            del attribs["attributes"]
    return attribs


def save_attributes(attributes, xf, elem_type):
    if "attributes" in attributes:
        save_with_additional_attributes(attributes, xf, elem_type)
    else:
        xf.write(etree.Element(elem_type, sanitiser.sanitise_dictionary_for_xml(attributes)))


def save_with_additional_attributes(_attributes, xf, elem_type):
    attributes = deepcopy(_attributes)
    additional_attributes = attributes.pop("attributes")
    attributes = sanitiser.sanitise_dictionary_for_xml(attributes)
    with xf.element(elem_type, attributes):
        save_additional_attributes(additional_attributes, xf)


def save_additional_attributes(attributes, xf):
    with xf.element("attributes"):
        for k, _attrib in attributes.items():
            attrib = format_to_matsim(k, _attrib)
            text = attrib.pop("text")
            rec = etree.Element("attribute", attrib)
            rec.text = str(text)
            xf.write(rec)


def prepare_attributes(attribs, elem_type):
    d = deepcopy(attribs)
    d = check_additional_attributes(d)
    d = retain_allowed_attributes_for_xml(d, elem_type)
    validate_attribute_data(d, get_necessary_attributes(elem_type))
    return d


def prepare_link_geometry_attribute(link_attribs):
    link_attributes = deepcopy(link_attribs)
    if "geometry" in link_attribs:
        geom_attribute = {
            "name": "geometry",
            "class": "java.lang.String",
            "text": encode_shapely_linestring_to_polyline(link_attributes["geometry"]),
        }
        if "attributes" in link_attributes:
            link_attributes["attributes"]["geometry"] = geom_attribute
        else:
            link_attributes["attributes"] = {"geometry": geom_attribute}
        del link_attributes["geometry"]
    return link_attributes


def write_matsim_network(output_dir, network):
    fname = os.path.join(output_dir, "network.xml")
    logging.info("Writing {}".format(fname))

    with open(fname, "wb") as f, etree.xmlfile(f, encoding="utf-8") as xf:
        xf.write_declaration(
            doctype='<!DOCTYPE network SYSTEM "http://www.matsim.org/files/dtd/network_v2.dtd">'
        )
        with xf.element("network"):
            save_additional_attributes(network.attributes, xf)

            with xf.element("nodes"):
                for node_id, node_attribs in network.nodes():
                    node_attributes = prepare_attributes(node_attribs, elem_type="node")
                    save_attributes(node_attributes, xf, elem_type="node")

            with xf.element(
                "links",
                {"capperiod": "01:00:00", "effectivecellsize": "7.5", "effectivelanewidth": "3.75"},
            ):
                for link_id, link_attribs in network.links():
                    link_attributes = prepare_attributes(link_attribs, elem_type="link")
                    link_attributes = prepare_link_geometry_attribute(link_attributes)
                    save_attributes(link_attributes, xf, elem_type="link")


def write_matsim_schedule(output_dir: str, schedule: Schedule, reproj_processes: int = 1):
    """Save to MATSim XML format.

    Args:
        output_dir (str): path to output directory.
        schedule (Schedule): Schedule object to write.
        reproj_processes (int, optional):
            You can set this in case you have a lot of stops and your stops need to be reprojected.
            It splits the process across given number of processes.
            Defaults to 1.
    """
    fname = os.path.join(output_dir, "schedule.xml")
    logging.info("Writing {}".format(fname))

    with open(fname, "wb") as f, etree.xmlfile(f, encoding="utf-8") as xf:
        xf.write_declaration(
            doctype="<!DOCTYPE transitSchedule "
            'SYSTEM "http://www.matsim.org/files/dtd/transitSchedule_v2.dtd">'
        )
        with xf.element("transitSchedule"):
            save_additional_attributes(schedule.attributes, xf)

            with xf.element("transitStops"):
                if not schedule.stops_have_this_projection(schedule.epsg):
                    logging.warning(
                        "Stops did not have a uniform projection, they will be projected to the Schedule "
                        f"projection: {schedule.epsg}. Re-projection can be ran in parallel, if you have "
                        "a lot of stops consider using `reproj_processes` parameter."
                    )
                    schedule.reproject(schedule.epsg, processes=reproj_processes)
                for stop_facility in schedule.stops():
                    transit_stop_attrib = prepare_attributes(
                        stop_facility.__dict__, elem_type="stopFacility"
                    )
                    save_attributes(transit_stop_attrib, xf, elem_type="stopFacility")

            # minimalTransferTimes, if present
            if schedule.minimal_transfer_times:
                with xf.element("minimalTransferTimes"):
                    for from_stop, val in schedule.minimal_transfer_times.items():
                        for to_stop, transfer_time in val.items():
                            minimal_transfer_times_attribs = {
                                "fromStop": str(from_stop),
                                "toStop": str(to_stop),
                                "transferTime": str(transfer_time),
                            }
                            xf.write(etree.Element("relation", minimal_transfer_times_attribs))

            for service in schedule.services():
                transit_line_attribs = {"id": service.id, "name": str(service.name)}

                with xf.element("transitLine", transit_line_attribs):
                    if service.has_attrib("attributes"):
                        save_additional_attributes(service.attributes, xf)
                    for route in service.routes():
                        transit_route_attribs = {"id": route.id}

                        with xf.element("transitRoute", transit_route_attribs):
                            if route.has_attrib("attributes"):
                                save_additional_attributes(route.attributes, xf)

                            rec = etree.Element("transportMode")
                            rec.text = route.mode
                            xf.write(rec)

                            with xf.element("routeProfile"):
                                for j in range(len(route.ordered_stops)):
                                    stop_attribs = {"refId": str(route.ordered_stops[j])}

                                    if not (route.departure_offsets and route.arrival_offsets):
                                        logging.warning(
                                            "The stop(s) along your route don't have arrival and departure offsets. "
                                            "This is likely a route with one stop - consider validating your schedule."
                                        )
                                    else:
                                        if j == 0:
                                            stop_attribs["departureOffset"] = (
                                                route.departure_offsets[j]
                                            )
                                        elif j == len(route.ordered_stops) - 1:
                                            stop_attribs["arrivalOffset"] = route.arrival_offsets[j]
                                        else:
                                            stop_attribs["departureOffset"] = (
                                                route.departure_offsets[j]
                                            )
                                            stop_attribs["arrivalOffset"] = route.arrival_offsets[j]

                                        if route.await_departure:
                                            stop_attribs["awaitDeparture"] = str(
                                                route.await_departure[j]
                                            ).lower()
                                    xf.write(etree.Element("stop", stop_attribs))

                            if not route.network_links:
                                logging.warning(
                                    "Route needs to have a network route composed of a list of network links that "
                                    "the vehicle on this route traverses. If read the Schedule from GTFS, the "
                                    "resulting Route objects will not have reference to the network route taken."
                                )
                            else:
                                with xf.element("route"):
                                    for link_id in route.network_links:
                                        route_attribs = {"refId": str(link_id)}
                                        xf.write(etree.Element("link", route_attribs))

                            with xf.element("departures"):
                                for trip_id, trip_dep_time, veh_id in zip(
                                    route.trips["trip_id"],
                                    route.trips["trip_departure_time"],
                                    route.trips["vehicle_id"],
                                ):
                                    trip_attribs = {
                                        "id": trip_id,
                                        "departureTime": trip_dep_time,
                                        "vehicleRefId": veh_id,
                                    }
                                    xf.write(etree.Element("departure", trip_attribs))


def write_vehicles(output_dir, vehicles, vehicle_types, file_name="vehicles.xml"):
    fname = os.path.join(output_dir, file_name)
    logging.info("Writing {}".format(fname))

    with open(fname, "wb") as f, etree.xmlfile(f, encoding="utf-8") as xf:
        xf.write_declaration()
        vehicleDefinitions_attribs = {
            "xmlns": "http://www.matsim.org/files/dtd",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:schemaLocation": "http://www.matsim.org/files/dtd "
            "http://www.matsim.org/files/dtd/vehicleDefinitions_v1.0.xsd",
        }
        with xf.element("vehicleDefinitions", vehicleDefinitions_attribs):
            unique_veh_types = DataFrame(vehicles).T["type"].unique()
            for vehicle_type in unique_veh_types:
                if vehicle_type in vehicle_types:
                    vehicle_type_attribs = {"id": vehicle_type}
                    veh_type_vals = vehicle_types[vehicle_type]
                    with xf.element("vehicleType", vehicle_type_attribs):
                        with xf.element("capacity"):
                            xf.write(etree.Element("seats", veh_type_vals["capacity"]["seats"]))
                            xf.write(
                                etree.Element(
                                    "standingRoom", veh_type_vals["capacity"]["standingRoom"]
                                )
                            )
                        xf.write(etree.Element("length", veh_type_vals["length"]))
                        xf.write(etree.Element("width", veh_type_vals["width"]))
                        xf.write(etree.Element("accessTime", veh_type_vals["accessTime"]))
                        xf.write(etree.Element("egressTime", veh_type_vals["egressTime"]))
                        xf.write(etree.Element("doorOperation", veh_type_vals["doorOperation"]))
                        xf.write(
                            etree.Element(
                                "passengerCarEquivalents", veh_type_vals["passengerCarEquivalents"]
                            )
                        )
                else:
                    raise NotImplementedError(
                        f"No Vehicle Type info available for mode {vehicle_type}, "
                        f"you will need to add it to configs/vehicles/vehicle_definitions.yml, "
                        f"or the schedule"
                    )
            for veh_id, data in vehicles.items():
                xf.write(etree.Element("vehicle", {"id": veh_id, "type": data["type"]}))
