import logging
import networkx as nx
import xml.etree.cElementTree as ET
from pyproj import Transformer, Proj
from genet.utils import spatial
from genet.variables import MODE_TYPES_MAP
from genet.schedule_elements import Route, Stop, Service


def read_network(network_path, TRANSFORMER: Transformer):
    """
    Read MATSim network
    :param network_path: path to the network.xml file
    :param TRANSFORMER: pyproj crs transformer
    :return: g (nx.MultiDiGraph representing the multimodal network),
        node_id_mapping (dict {matsim network node ids : s2 spatial ids}),
        link_id_mapping (dict {matsim network link ids : {'from': matsim id from node, ,'to': matsim id to
        node, 's2_from' : s2 spatial ids from node, 's2_to': s2 spatial ids to node}})
    """
    g = nx.MultiDiGraph()

    node_id_mapping = {}
    link_id_mapping = {}
    link_attribs = {}

    for event, elem in ET.iterparse(network_path, events=('start', 'end')):
        if event == 'start':
            if elem.tag == 'node':
                attribs = elem.attrib
                lat, lon = spatial.change_proj(attribs['x'], attribs['y'], TRANSFORMER)
                # ideally we would check if the transformer was created with always_xy=True and swap
                # lat and long values if so, but there is no obvious way to interrogate the transformer
                attribs['lon'], attribs['lat'] = lon, lat
                node_id = spatial.grab_index_s2(lat, lon)
                attribs['s2_id'] = node_id
                node_id_mapping[attribs['id']] = node_id
                g.add_node(attribs['id'], **attribs)
            elif elem.tag == 'link':
                # update old link by link attributes (osm tags etc.)
                if link_attribs:
                    # if multiple edges, add to the one added most recently
                    g[u][v][len(g[u][v]) - 1]['attributes'] = link_attribs  # noqa: F821

                attribs = elem.attrib
                attribs['s2_from'] = node_id_mapping[attribs['from']]
                attribs['s2_to'] = node_id_mapping[attribs['to']]
                attribs['modes'] = read_modes(attribs['modes'])

                link_id = attribs['id']
                if link_id in link_id_mapping:
                    logging.warning('This MATSim network has a link which that is not unique: {}'.format(link_id))
                    i = 1
                    _id = link_id + '_{}'
                    while link_id in link_id_mapping:
                        link_id = _id.format(i)
                        i += 1
                    logging.warning('Generated new link_id: {}'.format(link_id))
                link_id_mapping[link_id] = {
                    'from': attribs['from'],
                    'to': attribs['to']
                }

                try:
                    attribs['freespeed'] = float(attribs['freespeed'])
                    attribs['capacity'] = float(attribs['capacity'])
                    attribs['permlanes'] = float(attribs['permlanes'])
                except KeyError:
                    pass

                length = float(attribs['length'])
                del attribs['length']

                u = attribs['from']
                v = attribs['to']
                if g.has_edge(u, v):
                    link_id_mapping[link_id]['multi_edge_idx'] = len(g[u][v])
                else:
                    link_id_mapping[link_id]['multi_edge_idx'] = 0
                g.add_weighted_edges_from([(u, v, length)], weight='length', **attribs)
                # reset link_attribs
                link_attribs = {}
            elif elem.tag == 'attribute':
                d = elem.attrib
                d['text'] = elem.text
                link_attribs[elem.attrib['name']] = d
    # update the attributes of the last link
    if link_attribs:
        g[u][v][len(g[u][v]) - 1]['attributes'] = link_attribs
    return g, link_id_mapping


def read_modes(modes_string):
    modes = set()
    for m in modes_string.split(','):
        try:
            modes.add(MODE_TYPES_MAP[m.lower()])
        except KeyError:
            modes.add(m.lower())
    return list(modes)


def read_schedule(schedule_path, epsg):
    """
    Read MATSim schedule
    :param schedule_path: path to the schedule.xml file
    :param epsg: 'epsg:12345'
    :return: list of Service objects
    """
    services = []
    transformer = Transformer.from_proj(Proj(epsg), Proj('epsg:4326'))

    def write_transitLinesTransitRoute(transitLine, transitRoutes, transportMode):
        mode = transportMode['transportMode']
        service_id = transitLine['transitLine']['id']
        service_routes = []
        for transitRoute, transitRoute_val in transitRoutes.items():
            stops = [Stop(
                s['stop']['refId'],
                x=transit_stop_id_mapping[s['stop']['refId']]['x'],
                y=transit_stop_id_mapping[s['stop']['refId']]['y'],
                epsg=epsg,
                transformer=transformer
            ) for s in transitRoute_val['stops']]
            for s in stops:
                s.add_additional_attributes(transit_stop_id_mapping[s.id])

            arrival_offsets = []
            departure_offsets = []
            await_departure = []
            for stop in transitRoute_val['stops']:
                if 'departureOffset' not in stop['stop'] and 'arrivalOffset' not in stop['stop']:
                    pass
                elif 'departureOffset' not in stop['stop']:
                    arrival_offsets.append(stop['stop']['arrivalOffset'])
                    departure_offsets.append(stop['stop']['arrivalOffset'])
                elif 'arrivalOffset' not in stop['stop']:
                    arrival_offsets.append(stop['stop']['departureOffset'])
                    departure_offsets.append(stop['stop']['departureOffset'])
                else:
                    arrival_offsets.append(stop['stop']['arrivalOffset'])
                    departure_offsets.append(stop['stop']['departureOffset'])

                if 'awaitDeparture' in stop['stop']:
                    await_departure.append(str(stop['stop']['awaitDeparture']).lower() in ['true', '1'])

            route = [r_val['link']['refId'] for r_val in transitRoute_val['links']]

            trips = {}
            for dep in transitRoute_val['departure_list']:
                trips[dep['departure']['id']] = dep['departure']['departureTime']

            r = Route(
                route_short_name=transitLine['transitLine']['name'],
                mode=mode,
                stops=stops,
                route=route,
                trips=trips,
                arrival_offsets=arrival_offsets,
                departure_offsets=departure_offsets,
                id=transitRoute,
                await_departure=await_departure
            )
            service_routes.append(r)
        services.append(Service(id=service_id, routes=service_routes))

    transitLine = {}
    transitRoutes = {}
    transportMode = {}
    transitStops = {}
    transit_stop_id_mapping = {}
    is_minimalTransferTimes = False
    minimalTransferTimes = {}  # {'stop_id_1': {stop: 'stop_id_2', transfer_time: 0.0}}

    # transitLines
    for event, elem in ET.iterparse(schedule_path, events=('start', 'end')):
        if event == 'start':
            if elem.tag == 'stopFacility':
                attribs = elem.attrib
                if attribs['id'] not in transitStops:
                    transitStops[attribs['id']] = attribs
                if attribs['id'] not in transit_stop_id_mapping:
                    transit_stop_id_mapping[attribs['id']] = elem.attrib
            if elem.tag == 'minimalTransferTimes':
                is_minimalTransferTimes = not is_minimalTransferTimes
            if elem.tag == 'relation':
                if is_minimalTransferTimes:
                    if not elem.attrib['toStop'] in minimalTransferTimes:
                        attribs = elem.attrib
                        minimalTransferTimes[attribs['fromStop']] = {
                            'stop': attribs['toStop'],
                            'transferTime': float(attribs['transferTime'])
                        }
            if elem.tag == 'transitLine':
                if transitLine:
                    write_transitLinesTransitRoute(transitLine, transitRoutes, transportMode)
                transitLine = {"transitLine": elem.attrib}
                transitRoutes = {}

            if elem.tag == 'transitRoute':
                transitRoutes[elem.attrib['id']] = {'stops': [], 'links': [], 'departure_list': [],
                                                    'attribs': elem.attrib}
                transitRoute = elem.attrib['id']

            # doesn't have any attribs
            # if elem.tag == 'routeProfile':
            #     routeProfile = {'routeProfile': elem.attrib}

            if elem.tag == 'stop':
                transitRoutes[transitRoute]['stops'].append({'stop': elem.attrib})

            # doesn't have any attribs
            # if elem.tag == 'route':
            #     route = {'route': elem.attrib}

            if elem.tag == 'link':
                transitRoutes[transitRoute]['links'].append({'link': elem.attrib})

            # doesn't have any attribs
            # if elem.tag == 'departures':
            #     departures = {'departures': elem.attrib}

            if elem.tag == 'departure':
                transitRoutes[transitRoute]['departure_list'].append({'departure': elem.attrib})
        elif (event == 'end') and (elem.tag == "transportMode"):
            transportMode = {'transportMode': elem.text}

    # add the last one
    write_transitLinesTransitRoute(transitLine, transitRoutes, transportMode)

    return services, minimalTransferTimes
