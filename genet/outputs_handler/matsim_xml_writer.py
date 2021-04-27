import logging
import os
from lxml import etree
from copy import deepcopy
from pyproj import Proj, Transformer
from pandas import DataFrame
from genet.outputs_handler import sanitiser
from genet.validate.network_validation import validate_link_data
from genet.utils.spatial import change_proj, encode_shapely_linestring_to_polyline
from genet.variables import NECESSARY_NETWORK_LINK_ATTRIBUTES, \
    OPTIONAL_NETWORK_LINK_ATTRIBUTES, ADDITIONAL_STOP_FACILITY_ATTRIBUTES


def delete_redundant_link_attributes_for_xml(d):
    attrib_keys = set(d.keys())
    allowable_attributes = OPTIONAL_NETWORK_LINK_ATTRIBUTES + NECESSARY_NETWORK_LINK_ATTRIBUTES
    for attrib in attrib_keys - set(allowable_attributes + ['attributes']):
        del d[attrib]
    return d


def check_link_attributes(link_attribs):
    if 'attributes' in link_attribs:
        if isinstance(link_attribs['attributes'], dict):
            attribs_to_delete = []
            for attrib, value in link_attribs['attributes'].items():
                try:
                    link_attribs['attributes'][attrib]['name']
                    link_attribs['attributes'][attrib]['class']
                    link_attribs['attributes'][attrib]['text']
                except Exception as e:
                    logging.warning(f'Attempt to access required keys in link data under "attributes:{attrib}" key '
                                    f'resulted in {type(e)} with message "{e}".')
                    attribs_to_delete.append(attrib)
            for attrib in attribs_to_delete:
                logging.warning(f'Deleting {attrib} under key "attributes"')
                del link_attribs['attributes'][attrib]
            if not link_attribs['attributes']:
                logging.warning(f'Attributes on link are not formatted correctly and will be deleted: {link_attribs}')
                del link_attribs['attributes']
        else:
            logging.warning(f'Attributes on link are not a dictionary: {link_attribs}')
            del link_attribs['attributes']
    return link_attribs


def prepare_link_attributes(link_attribs):
    link_attributes = check_link_attributes(link_attribs)
    if 'geometry' in link_attributes:
        geom_attribute = {
            'name': 'geometry',
            'class': 'java.lang.String',
            'text': encode_shapely_linestring_to_polyline(link_attributes['geometry'])
        }
        if 'attributes' in link_attributes:
            link_attributes['attributes']['geometry'] = geom_attribute
        else:
            link_attributes['attributes'] = {'geometry': geom_attribute}
    link_attributes = delete_redundant_link_attributes_for_xml(link_attributes)
    validate_link_data(link_attributes)
    return link_attributes


def write_matsim_network(output_dir, network):
    fname = os.path.join(output_dir, "network.xml")
    logging.info('Writing {}'.format(fname))

    with open(fname, "wb") as f, etree.xmlfile(f, encoding='utf-8') as xf:
        xf.write_declaration(doctype='<!DOCTYPE network SYSTEM "http://www.matsim.org/files/dtd/network_v2.dtd">')
        with xf.element("network"):
            if network.graph.graph:
                with xf.element("attributes"):
                    for key in set(network.graph.graph.keys()) - {'name'}:
                        rec = etree.Element("attribute", {'name': key, 'class': 'java.lang.String'})
                        rec.text = str(network.graph.graph[key])
                        xf.write(rec)

            with xf.element("nodes"):
                for node_id, node_attributes in network.nodes():
                    node_attrib = {'id': str(node_id), 'x': str(node_attributes['x']), 'y': str(node_attributes['y'])}
                    xf.write(etree.Element("node", node_attrib))

            links_attribs = {'capperiod': '01:00:00', 'effectivecellsize': '7.5', 'effectivelanewidth': '3.75'}
            with xf.element("links", links_attribs):
                for link_id, link_attribs in network.links():
                    link_attributes = prepare_link_attributes(deepcopy(link_attribs))
                    if 'attributes' in link_attributes:
                        attributes = link_attributes.pop('attributes')
                        with xf.element("link", sanitiser.sanitise_dictionary_for_xml(link_attributes)):
                            with xf.element("attributes"):
                                for k, attrib in attributes.items():
                                    attrib = sanitiser.sanitise_dictionary_for_xml(attrib)
                                    text = attrib.pop('text')
                                    rec = etree.Element("attribute", attrib)
                                    rec.text = text
                                    xf.write(rec)
                    else:
                        xf.write(etree.Element("link", sanitiser.sanitise_dictionary_for_xml(link_attributes)))


def write_matsim_schedule(output_dir, schedule, epsg=''):
    fname = os.path.join(output_dir, "schedule.xml")
    if not epsg:
        epsg = schedule.epsg
    transformer = Transformer.from_proj(Proj('epsg:4326'), Proj(epsg), always_xy=True)
    logging.info('Writing {}'.format(fname))

    with open(fname, "wb") as f, etree.xmlfile(f, encoding='utf-8') as xf:
        xf.write_declaration(doctype='<!DOCTYPE transitSchedule '
                                     'SYSTEM "http://www.matsim.org/files/dtd/transitSchedule_v2.dtd">')
        with xf.element("transitSchedule"):
            # transitStops first
            with xf.element("transitStops"):
                for stop_facility in schedule.stops():
                    transit_stop_attrib = {'id': str(stop_facility.id)}
                    if stop_facility.epsg == epsg:
                        x = stop_facility.x
                        y = stop_facility.y
                    else:
                        x, y = change_proj(
                            x=stop_facility.lon,
                            y=stop_facility.lat,
                            crs_transformer=transformer)
                    transit_stop_attrib['x'], transit_stop_attrib['y'] = str(x), str(y)
                    for k in ADDITIONAL_STOP_FACILITY_ATTRIBUTES:
                        if stop_facility.has_attrib(k):
                            transit_stop_attrib[k] = str(stop_facility.additional_attribute(k))
                    xf.write(etree.Element("stopFacility", transit_stop_attrib))

            # minimalTransferTimes, if present
            if schedule.minimal_transfer_times:
                with xf.element("minimalTransferTimes"):
                    for stop_1_id, val in schedule.minimal_transfer_times.items():
                        minimal_transfer_times_attribs = {
                            'fromStop': str(stop_1_id),
                            'toStop': str(val['stop']),
                            'transferTime': str(val['transferTime'])
                        }
                        xf.write(etree.Element("relation", minimal_transfer_times_attribs))

                        minimal_transfer_times_attribs['fromStop'] = str(val['stop'])
                        minimal_transfer_times_attribs['toStop'] = str(stop_1_id)
                        xf.write(etree.Element("relation", minimal_transfer_times_attribs))

            # transitLine
            for service in schedule.services():
                transit_line_attribs = {'id': service.id, 'name': str(service.name)}

                with xf.element("transitLine", transit_line_attribs):
                    for route in service.routes():
                        transit_route_attribs = {'id': route.id}

                        with xf.element("transitRoute", transit_route_attribs):
                            rec = etree.Element("transportMode")
                            rec.text = route.mode
                            xf.write(rec)

                            with xf.element("routeProfile"):
                                for j in range(len(route.ordered_stops)):
                                    stop_attribs = {'refId': str(route.ordered_stops[j])}

                                    if not (route.departure_offsets and route.arrival_offsets):
                                        logging.warning(
                                            'The stop(s) along your route don\'t have arrival and departure offsets. '
                                            'This is likely a route with one stop - consider validating your schedule.'
                                        )
                                    else:
                                        if j == 0:
                                            stop_attribs['departureOffset'] = route.departure_offsets[j]
                                        elif j == len(route.ordered_stops) - 1:
                                            stop_attribs['arrivalOffset'] = route.arrival_offsets[j]
                                        else:
                                            stop_attribs['departureOffset'] = route.departure_offsets[j]
                                            stop_attribs['arrivalOffset'] = route.arrival_offsets[j]

                                        if route.await_departure:
                                            stop_attribs['awaitDeparture'] = str(route.await_departure[j]).lower()
                                    xf.write(etree.Element("stop", stop_attribs))

                            with xf.element("route"):
                                if not route.route:
                                    logging.warning(
                                        "Route needs to have a network route composed of a list of network links that "
                                        "the vehicle on this route traverses. If read the Schedule from GTFS, the "
                                        "resulting Route objects will not have reference to the network route taken."
                                    )
                                for link_id in route.route:
                                    route_attribs = {'refId': str(link_id)}
                                    xf.write(etree.Element("link", route_attribs))

                            with xf.element("departures"):
                                for trip_id, trip_dep_time, veh_id in zip(route.trips['trip_id'],
                                                                          route.trips['trip_departure_time'],
                                                                          route.trips['vehicle_id']):
                                    trip_attribs = {
                                        'id': trip_id,
                                        'departureTime': trip_dep_time,
                                        'vehicleRefId': veh_id
                                    }
                                    xf.write(etree.Element("departure", trip_attribs))


def write_vehicles(output_dir, vehicles, vehicle_types):
    fname = os.path.join(output_dir, "vehicles.xml")
    logging.info('Writing {}'.format(fname))

    with open(fname, "wb") as f, etree.xmlfile(f, encoding='utf-8') as xf:
        xf.write_declaration()
        vehicleDefinitions_attribs = {
            'xmlns': "http://www.matsim.org/files/dtd",
            'xmlns:xsi': "http://www.w3.org/2001/XMLSchema-instance",
            'xsi:schemaLocation': "http://www.matsim.org/files/dtd "
                                  "http://www.matsim.org/files/dtd/vehicleDefinitions_v1.0.xsd"}
        with xf.element("vehicleDefinitions", vehicleDefinitions_attribs):
            unique_veh_types = DataFrame(vehicles).T['type'].unique()
            for vehicle_type in unique_veh_types:
                if vehicle_type in vehicle_types:
                    vehicle_type_attribs = {'id': vehicle_type}
                    veh_type_vals = vehicle_types[vehicle_type]
                    with xf.element("vehicleType", vehicle_type_attribs):
                        with xf.element("capacity"):
                            xf.write(etree.Element("seats", veh_type_vals['capacity']['seats']))
                            xf.write(etree.Element("standingRoom", veh_type_vals['capacity']['standingRoom']))
                        xf.write(etree.Element("length", veh_type_vals['length']))
                        xf.write(etree.Element("width", veh_type_vals['width']))
                        xf.write(etree.Element("accessTime", veh_type_vals['accessTime']))
                        xf.write(etree.Element("egressTime", veh_type_vals['egressTime']))
                        xf.write(etree.Element("doorOperation", veh_type_vals['doorOperation']))
                        xf.write(etree.Element("passengerCarEquivalents", veh_type_vals['passengerCarEquivalents']))
                else:
                    raise NotImplementedError(f'No Vehicle Type info available for mode {vehicle_type}, '
                                              f'you will need to add it to configs/vehicles/vehicle_definitions.yml, '
                                              f'or the schedule')
            for veh_id, data in vehicles.items():
                xf.write(etree.Element("vehicle", {'id': veh_id, 'type': data['type']}))
