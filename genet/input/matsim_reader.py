import logging
import re
import xml.etree.cElementTree as ET

import networkx as nx
from pyproj import Proj, Transformer

from genet.schedule_elements import Route, Service, Stop
from genet.utils import dict_support, java_dtypes, spatial


def read_node(elem, g, node_id_mapping, node_attribs, transformer):
    """
    Adds node elem of the stream to the network
    :param elem:
    :param g: nx.MultiDiGraph
    :param node_id_mapping:
    :param transformer:
    :return:
    """
    duplicated_node_id = {}
    attribs = elem.attrib
    attribs["x"], attribs["y"] = float(attribs["x"]), float(attribs["y"])

    if "z" in attribs:
        attribs["z"] = float(attribs["z"])

    lon, lat = spatial.change_proj(attribs["x"], attribs["y"], transformer)
    # ideally we would check if the transformer was created with always_xy=True and swap
    # lat and long values if so, but there is no obvious way to interrogate the transformer
    attribs["lon"], attribs["lat"] = lon, lat
    attribs["s2_id"] = spatial.generate_index_s2(lat, lon)

    if node_attribs:
        attribs["attributes"] = node_attribs

    node_id = attribs["id"]
    if node_id in node_id_mapping:
        logging.warning(
            "This MATSim network has a node that is not unique: {}. Generating a new id would"
            "be pointless as we don't know which links should be connected to this particular"
            "node. The node will cease to exist and the first encountered node with this id"
            "will be kept. Investigate the links connected to that node.".format(node_id)
        )
        duplicated_node_id[node_id] = attribs
    else:
        node_id_mapping[node_id] = attribs["s2_id"]
        g.add_node(node_id, **attribs)
    return g, duplicated_node_id


def read_link(elem, g, u, v, node_id_mapping, link_id_mapping, link_attribs):
    """
    Reads link elem of the stream to the network
    :param elem:
    :param g: nx.MultiDiGraph
    :param u: from node of the previous link
    :param v: to node of the previous link
    :param node_id_mapping:
    :param link_id_mapping:
    :param link_attribs: link attributes of the previous link
    :return:
    """
    duplicated_link_id = {}

    attribs = elem.attrib
    attribs["s2_from"] = node_id_mapping[attribs["from"]]
    attribs["s2_to"] = node_id_mapping[attribs["to"]]
    attribs["modes"] = set(attribs["modes"].split(","))

    link_id, duplicated_link_id = unique_link_id(attribs["id"], link_id_mapping)
    attribs["id"] = link_id
    link_id_mapping[link_id] = {"from": attribs["from"], "to": attribs["to"]}

    for key in ["freespeed", "capacity", "permlanes"]:
        try:
            attribs[key] = float(attribs[key])
        except KeyError:
            logging.warning(
                "Key: {} is not present in link: {}. This may lead to problems if using this"
                "network with MATSim."
            )

    length = float(attribs["length"])
    del attribs["length"]

    u = attribs["from"]
    v = attribs["to"]

    if link_attribs:
        if "geometry" in link_attribs:
            if link_attribs["geometry"]:
                attribs["geometry"] = spatial.decode_polyline_to_shapely_linestring(
                    link_attribs["geometry"]
                )
                del link_attribs["geometry"]
        if link_attribs:
            attribs["attributes"] = link_attribs

    if g.has_edge(u, v):
        link_id_mapping[link_id]["multi_edge_idx"] = len(g[u][v])
    else:
        link_id_mapping[link_id]["multi_edge_idx"] = 0
    g.add_weighted_edges_from([(u, v, length)], weight="length", **attribs)
    return g, u, v, link_id_mapping, duplicated_link_id


def update_additional_attrib(elem, attribs, force_long_form_attributes=False):
    """
    Reads additional attributes
    :param elem:
    :param attribs: current additional attributes
    :param force_long_form_attributes: Defaults to False, if True the additional attributes will be read into long form
    :return:
    """
    attribs[elem.attrib["name"]] = read_additional_attrib(
        elem, force_long_form_attributes=force_long_form_attributes
    )
    return attribs


def read_additional_attrib(elem, force_long_form_attributes=False):
    """
    :param elem:
    :param force_long_form_attributes: Defaults to False, if True the additional attributes will be read into long form
    :return:
    """
    if force_long_form_attributes:
        return _read_additional_attrib_to_long_form(elem)
    else:
        return _read_additional_attrib_to_short_form(elem)


def _read_additional_attrib_text(elem):
    if elem.text is None:
        t = ""
        logging.warning(
            f"Elem {elem.attrib['name']} is being read as None. Defaulting value to empty string."
        )
    elif ("," in elem.text) and elem.attrib["name"] != "geometry":
        t = set(elem.text.strip("{}").replace(("'"), "").replace(" ", "").split(","))
    else:
        t = elem.text
    return t


def _read_additional_attrib_class(elem):
    if "class" in elem.attrib:
        c = elem.attrib["class"]
    else:
        logging.warning(
            f"Elem {elem.attrib['name']} does not have a Java class declared. "
            "Defaulting type to string."
        )
        c = "java.lang.String"
    return c


def _read_additional_attrib_to_short_form(elem):
    t = _read_additional_attrib_text(elem)
    if t and isinstance(t, str):
        c = _read_additional_attrib_class(elem)
        return java_dtypes.java_to_python_dtype(c)(t)
    else:
        return t


def _read_additional_attrib_to_long_form(elem):
    return {
        "text": _read_additional_attrib_text(elem),
        "class": _read_additional_attrib_class(elem),
        "name": elem.attrib["name"],
    }


def unique_link_id(link_id, link_id_mapping):
    duplicated_link_id = {}
    if link_id in link_id_mapping:
        old_link_id = link_id
        logging.warning("This MATSim network has a link that is not unique: {}".format(old_link_id))
        i = 1
        link_id = old_link_id
        while link_id in link_id_mapping:
            link_id = "{}_{}".format(old_link_id, i)
            i += 1
        logging.warning("Generated new link_id: {}".format(link_id))
        duplicated_link_id[old_link_id] = link_id
    return link_id, duplicated_link_id


def read_network(network_path, transformer: Transformer, force_long_form_attributes=False):
    """
    Read MATSim network
    :param network_path: path to the network.xml file
    :param transformer: pyproj crs transformer
    :param force_long_form_attributes: Defaults to False, if True the additional attributes will be read into verbose
        format:
            {
                'additional_attrib': {'name': 'additional_attrib', 'class': 'java.lang.String', 'text': 'attrib_value'}
            }
        where 'attrib_value' is always a python string; instead of the default short form:
            {
                'additional_attrib': 'attrib_value'
            }
        where the type of attrib_value is mapped to a python type using the declared java class.
        NOTE! Network level attributes cannot be forced to be read into long form.
    :return: g (nx.MultiDiGraph representing the multimodal network),
        node_id_mapping (dict {matsim network node ids : s2 spatial ids}),
        link_id_mapping (dict {matsim network link ids : {'from': matsim id from node, ,'to': matsim id to
        node, 's2_from' : s2 spatial ids from node, 's2_to': s2 spatial ids to node}})
    """
    g = nx.MultiDiGraph()

    network_attributes = {}
    node_id_mapping = {}
    node_attribs = {}
    link_id_mapping = {}
    link_attribs = {}
    duplicated_link_ids = {}
    duplicated_node_ids = {}
    u, v = None, None

    elem_themes_for_additional_attributes = {"network", "nodes", "links"}
    elem_type_for_additional_attributes = None

    for event, elem in ET.iterparse(network_path, events=("start", "end")):
        if event == "start":
            if elem.tag in elem_themes_for_additional_attributes:
                elem_type_for_additional_attributes = elem.tag
        elif event == "end":
            if elem.tag == "node":
                g, duplicated_node_id = read_node(
                    elem, g, node_id_mapping, node_attribs, transformer
                )
                if duplicated_node_id:
                    for key, val in duplicated_node_id.items():
                        if key in duplicated_node_ids:
                            duplicated_node_ids[key].append(val)
                        else:
                            duplicated_node_ids[key] = [val]
                # reset node_attribs
                node_attribs = {}
            elif elem.tag == "link":
                g, u, v, link_id_mapping, duplicated_link_id = read_link(
                    elem, g, u, v, node_id_mapping, link_id_mapping, link_attribs
                )
                if duplicated_link_id:
                    for key, val in duplicated_link_id.items():
                        if key in duplicated_link_ids:
                            duplicated_link_ids[key].append(val)
                        else:
                            duplicated_link_ids[key] = [val]
                # reset link_attribs
                link_attribs = {}
            elif elem.tag == "attribute":
                if elem_type_for_additional_attributes == "links":
                    link_attribs = update_additional_attrib(
                        elem, link_attribs, force_long_form_attributes
                    )
                elif elem_type_for_additional_attributes == "network":
                    if force_long_form_attributes:
                        logging.warning(
                            "Network-level additional attributes are always read into short form."
                        )
                    network_attributes = update_additional_attrib(
                        elem, network_attributes, force_long_form_attributes=False
                    )
                elif elem_type_for_additional_attributes == "nodes":
                    node_attribs = update_additional_attrib(
                        elem, node_attribs, force_long_form_attributes
                    )
    return g, link_id_mapping, duplicated_node_ids, duplicated_link_ids, network_attributes


def read_schedule(schedule_path, epsg, force_long_form_attributes=False):
    """
    Read MATSim schedule
    :param schedule_path: path to the schedule.xml file
    :param epsg: 'epsg:12345'
    :param force_long_form_attributes: Defaults to False, if True the additional attributes will be read into verbose
        format:
            {
                'additional_attrib': {'name': 'additional_attrib', 'class': 'java.lang.String', 'text': 'attrib_value'}
            }
        where 'attrib_value' is always a python string; instead of the default short form:
            {
                'additional_attrib': 'attrib_value'
            }
        where the type of attrib_value is mapped to a python type using the declared java class.
        NOTE! Schedule level attributes cannot be forced to be read into long form.
    :return: list of Service objects
    """
    services = []
    transformer = Transformer.from_proj(Proj(epsg), Proj("epsg:4326"), always_xy=True)

    def write_transitLinesTransitRoute(transitLine, transitRoutes, transportMode):
        mode = transportMode["transportMode"]
        service_id = transitLine["transitLine_data"]["id"]
        service_routes = []
        for transitRoute, transitRoute_val in transitRoutes.items():
            stops = [
                Stop(
                    s["stop"]["refId"],
                    x=transit_stop_id_mapping[s["stop"]["refId"]]["x"],
                    y=transit_stop_id_mapping[s["stop"]["refId"]]["y"],
                    epsg=epsg,
                    transformer=transformer,
                )
                for s in transitRoute_val["stops"]
            ]
            for s in stops:
                s.add_additional_attributes(transit_stop_id_mapping[s.id])

            arrival_offsets = []
            departure_offsets = []
            await_departure = []
            for stop in transitRoute_val["stops"]:
                if "departureOffset" not in stop["stop"] and "arrivalOffset" not in stop["stop"]:
                    pass
                elif "departureOffset" not in stop["stop"]:
                    arrival_offsets.append(stop["stop"]["arrivalOffset"])
                    departure_offsets.append(stop["stop"]["arrivalOffset"])
                elif "arrivalOffset" not in stop["stop"]:
                    arrival_offsets.append(stop["stop"]["departureOffset"])
                    departure_offsets.append(stop["stop"]["departureOffset"])
                else:
                    arrival_offsets.append(stop["stop"]["arrivalOffset"])
                    departure_offsets.append(stop["stop"]["departureOffset"])

                if "awaitDeparture" in stop["stop"]:
                    await_departure.append(
                        str(stop["stop"]["awaitDeparture"]).lower() in ["true", "1"]
                    )

            route = [r_val["link"]["refId"] for r_val in transitRoute_val["links"]]

            trips = {"trip_id": [], "trip_departure_time": [], "vehicle_id": []}
            for dep in transitRoute_val["departure_list"]:
                trips["trip_id"].append(dep["departure"]["id"])
                trips["trip_departure_time"].append(dep["departure"]["departureTime"])
                trips["vehicle_id"].append(dep["departure"]["vehicleRefId"])

            r = Route(
                route_short_name=transitLine["transitLine_data"]["name"],
                mode=mode,
                stops=stops,
                route=route,
                trips=trips,
                arrival_offsets=arrival_offsets,
                departure_offsets=departure_offsets,
                id=transitRoute,
                await_departure=await_departure,
            )
            if transitRoute_val["attributes"]:
                r.add_additional_attributes({"attributes": transitRoute_val["attributes"]})
            service_routes.append(r)
        _service = Service(id=service_id, routes=service_routes)
        if transitLine["attributes"]:
            _service.add_additional_attributes({"attributes": transitLine["attributes"]})
        services.append(_service)

    transitLine = {}
    transitRoutes = {}
    transportMode = {}
    transit_stop_id_mapping = {}
    is_minimalTransferTimes = False
    minimalTransferTimes = (
        {}
    )  # {'stop_id_1': {'stop_id_2': 0.0}} seconds_to_transfer between stop_id_1 and stop_id_2

    elem_themes_for_additional_attributes = {
        "transitSchedule",
        "stopFacility",
        "transitLine",
        "transitRoute",
    }
    elem_type_for_additional_attributes = None
    schedule_attribs = {}
    # Track IDs through the stream
    current_stop_id = None
    current_route_id = None

    # transitLines
    for event, elem in ET.iterparse(schedule_path, events=("start", "end")):
        if event == "start":
            if elem.tag in elem_themes_for_additional_attributes:
                elem_type_for_additional_attributes = elem.tag

            if elem.tag == "stopFacility":
                attribs = elem.attrib
                attribs["epsg"] = epsg
                attribs["x"] = float(attribs["x"])
                attribs["y"] = float(attribs["y"])
                if attribs["id"] not in transit_stop_id_mapping:
                    transit_stop_id_mapping[attribs["id"]] = attribs
                current_stop_id = attribs["id"]

            elif elem.tag == "minimalTransferTimes":
                is_minimalTransferTimes = not is_minimalTransferTimes
            elif elem.tag == "relation":
                if is_minimalTransferTimes:
                    attribs = elem.attrib
                    minimalTransferTimes = dict_support.merge_complex_dictionaries(
                        minimalTransferTimes,
                        {attribs["fromStop"]: {attribs["toStop"]: float(attribs["transferTime"])}},
                    )
            elif elem.tag == "transitLine":
                if transitLine:
                    write_transitLinesTransitRoute(transitLine, transitRoutes, transportMode)
                transitLine = {"transitLine_data": elem.attrib, "attributes": {}}
                transitRoutes = {}

            elif elem.tag == "transitRoute":
                transitRoutes[elem.attrib["id"]] = {
                    "stops": [],
                    "links": [],
                    "departure_list": [],
                    "attributes": {},
                }
                current_route_id = elem.attrib["id"]

            # doesn't have any attribs
            # if elem.tag == 'routeProfile':
            #     routeProfile = {'routeProfile': elem.attrib}

            elif elem.tag == "stop":
                transitRoutes[current_route_id]["stops"].append({"stop": elem.attrib})

            # doesn't have any attribs
            # if elem.tag == 'route':
            #     route = {'route': elem.attrib}

            elif elem.tag == "link":
                transitRoutes[current_route_id]["links"].append({"link": elem.attrib})

            # doesn't have any attribs
            # if elem.tag == 'departures':
            #     departures = {'departures': elem.attrib}

            elif elem.tag == "departure":
                transitRoutes[current_route_id]["departure_list"].append({"departure": elem.attrib})

        elif event == "end":
            if elem.tag == "attribute":
                if elem_type_for_additional_attributes == "transitSchedule":
                    if force_long_form_attributes:
                        logging.warning(
                            "Schedule-level additional attributes are always read into short form."
                        )
                    schedule_attribs = update_additional_attrib(elem, schedule_attribs)
                elif elem_type_for_additional_attributes == "stopFacility":
                    current_stop_data = transit_stop_id_mapping[current_stop_id]
                    if "attributes" in current_stop_data:
                        current_stop_data["attributes"] = update_additional_attrib(
                            elem,
                            transit_stop_id_mapping[current_stop_id]["attributes"],
                            force_long_form_attributes=force_long_form_attributes,
                        )
                    else:
                        current_stop_data["attributes"] = update_additional_attrib(
                            elem, {}, force_long_form_attributes=force_long_form_attributes
                        )
                elif elem_type_for_additional_attributes == "transitLine":
                    transitLine["attributes"] = update_additional_attrib(
                        elem,
                        transitLine["attributes"],
                        force_long_form_attributes=force_long_form_attributes,
                    )
                elif elem_type_for_additional_attributes == "transitRoute":
                    transitRoutes[current_route_id]["attributes"] = update_additional_attrib(
                        elem,
                        transitRoutes[current_route_id]["attributes"],
                        force_long_form_attributes=force_long_form_attributes,
                    )
            elif elem.tag == "transportMode":
                transportMode = {"transportMode": elem.text}

    # add the last one
    write_transitLinesTransitRoute(transitLine, transitRoutes, transportMode)

    return services, minimalTransferTimes, transit_stop_id_mapping, schedule_attribs


def read_vehicles(vehicles_path):
    vehicles = {}
    vehicle_types = {}
    v = {"capacity": {}}
    read_capacity = False
    for event, elem in ET.iterparse(vehicles_path):
        tag = re.sub(r"{http://www\.matsim\.org/files/dtd}", "", elem.tag)
        if tag == "vehicle":
            _id = elem.attrib.pop("id")
            vehicles[_id] = elem.attrib
            read_capacity = False
        elif tag == "vehicleType":
            vehicle_types[elem.attrib["id"]] = v
            v = {"capacity": {}}
            read_capacity = False
        elif tag == "capacity":
            read_capacity = True
        elif read_capacity:
            v[tag] = elem.attrib
        else:
            v["capacity"][tag] = elem.attrib
    return vehicles, vehicle_types
