import logging
import os
from lxml import etree
from pyproj import Proj, Transformer
from genet.outputs_handler import matsim_xml_values
from genet.validate.network_validation import validate_link_data
from genet.utils.spatial import change_proj
from genet.variables import NECESSARY_NETWORK_LINK_ATTRIBUTES


def sanitise_dictionary_for_xml(d):
    for k, v in d.items():
        if isinstance(v, list):
            d[k] = ','.join(v)
        if isinstance(v, (int, float)):
            d[k] = str(v)
    return d


def delete_redundant_link_attributes_for_xml(d):
    attrib_keys = set(d.keys())
    for attrib in attrib_keys - set(NECESSARY_NETWORK_LINK_ATTRIBUTES + ['attributes']):
        del d[attrib]
    return d


def write_matsim_network(output_dir, network):
    fname = os.path.join(output_dir, "network.xml")
    logging.info('Writing {}'.format(fname))

    with open(fname, "wb") as f, etree.xmlfile(f, encoding='utf-8') as xf:
        xf.write_declaration(doctype='<!DOCTYPE network SYSTEM "http://www.matsim.org/files/dtd/network_v2.dtd">')
        with xf.element("network"):
            with xf.element("nodes"):
                for node_id, node_attributes in network.nodes():
                    node_attrib = {'id': str(node_id), 'x': str(node_attributes['x']), 'y': str(node_attributes['y'])}
                    xf.write(etree.Element("node", node_attrib))

            links_attribs = {'capperiod': '01:00:00', 'effectivecellsize': '7.5', 'effectivelanewidth': '3.75'}
            with xf.element("links", links_attribs):
                for link_id, link_attributes in network.links():
                    link_attributes = delete_redundant_link_attributes_for_xml(link_attributes)
                    validate_link_data(link_attributes)
                    if 'attributes' in link_attributes:
                        attributes = link_attributes.pop('attributes')
                        with xf.element("link", sanitise_dictionary_for_xml(link_attributes)):
                            with xf.element("attributes"):
                                for k, attrib in attributes.items():
                                    text = attrib.pop('text')
                                    rec = etree.Element("attribute", attrib)
                                    rec.text = text
                                    xf.write(rec)
                    else:
                        xf.write(etree.Element("link", sanitise_dictionary_for_xml(link_attributes)))


def write_matsim_schedule(output_dir, schedule, epsg=''):
    fname = os.path.join(output_dir, "schedule.xml")
    if not epsg:
        epsg = schedule.epsg
    transformer = Transformer.from_proj(Proj('epsg:4326'), Proj(epsg))
    logging.info('Writing {}'.format(fname))

    # Also makes vehicles
    vehicles = {}

    with open(fname, "wb") as f, etree.xmlfile(f, encoding='utf-8') as xf:
        xf.write_declaration(doctype='<!DOCTYPE transitSchedule '
                                     'SYSTEM "http://www.matsim.org/files/dtd/transitSchedule_v2.dtd">')
        with xf.element("transitSchedule"):
            # transitStops first
            with xf.element("transitStops"):
                for stop_facility_id, stop_facility in schedule.stops():
                    transit_stop_attrib = {'id': str(stop_facility_id)}
                    if stop_facility.epsg == epsg:
                        x = stop_facility.x
                        y = stop_facility.y
                    else:
                        x, y = change_proj(
                            x=stop_facility.lat,
                            y=stop_facility.lon,
                            crs_transformer=transformer)
                    transit_stop_attrib['x'], transit_stop_attrib['y'] = str(x), str(y)
                    for k, v in stop_facility.iter_through_additional_attributes():
                        transit_stop_attrib[k] = str(v)
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
            v_id = 0  # generating some ids for vehicles
            for service_id, service in schedule.services.items():
                transit_line_attribs = {'id': service_id, 'name': str(service.name)}

                with xf.element("transitLine", transit_line_attribs):
                    for i in range(len(service.routes)):
                        route = service.routes[i]
                        id = route.id
                        if not id:
                            '{}_{}'.format(service.id, i)
                        transit_route_attribs = {'id': id}

                        with xf.element("transitRoute", transit_route_attribs):
                            rec = etree.Element("transportMode")
                            rec.text = route.mode
                            xf.write(rec)

                            with xf.element("routeProfile"):
                                for j in range(len(route.stops)):
                                    stop_attribs = {'refId': str(route.stops[j].id)}

                                    if not (route.departure_offsets and route.arrival_offsets):
                                        logging.warning(
                                            'The stop(s) along your route don\'t have arrival and departure offsets. '
                                            'This is likely a route with one stop - consider validating your schedule.'
                                        )
                                    else:
                                        if j == 0:
                                            stop_attribs['departureOffset'] = route.departure_offsets[j]
                                        elif j == len(route.stops) - 1:
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
                                for trip_id, trip_dep in route.trips.items():
                                    vehicle_id = 'veh_{}_{}'.format(v_id, route.mode)
                                    trip_attribs = {
                                        'id': trip_id,
                                        'departureTime': trip_dep,
                                        'vehicleRefId': vehicle_id
                                    }
                                    vehicles[vehicle_id] = matsim_xml_values.MODE_DICT[route.mode]
                                    v_id += 1
                                    xf.write(etree.Element("departure", trip_attribs))
    return vehicles


def write_vehicles(output_dir, vehicles):
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
            unique_veh_types = list(set(vehicles.values()))
            for vehicle_type in unique_veh_types:
                if vehicle_type in matsim_xml_values.VEHICLE_TYPES:
                    vehicle_type_attribs = {'id': vehicle_type}
                    veh_type_vals = matsim_xml_values.VEHICLE_TYPES[vehicle_type]
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
                    raise NotImplementedError('No Vehicle Type info available for mode {}, you will need to add it to '
                                              'matsim_xml_values.py'.format(vehicle_type))

            for veh_id, mode in vehicles.items():
                xf.write(etree.Element("vehicle", {'id': veh_id, 'type': mode}))
