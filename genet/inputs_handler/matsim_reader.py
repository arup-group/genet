import networkx as nx
import xml.etree.cElementTree as ET
from pyproj import Transformer
from genet.utils import spatial
from genet.variables import MODE_TYPES_MAP


def read_network(network_path, TRANSFORMER: Transformer.from_proj):
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
                lon, lat = spatial.change_proj(attribs['x'], attribs['y'], TRANSFORMER)
                attribs['lon'], attribs['lat'] = lon, lat
                node_id = spatial.grab_index_s2(lat, lon)
                attribs['s2_id'] = node_id
                node_id_mapping[attribs['id']] = node_id
                g.add_node(attribs['id'], **attribs)
            elif elem.tag == 'link':
                # update old link by link attributes (osm tags etc.)
                if link_attribs:
                    # if multiple edges, add to the one added most recently
                    g[u][v][len(g[u][v])-1]['attributes'] = link_attribs

                attribs = elem.attrib
                attribs['s2_from'] = node_id_mapping[attribs['from']]
                attribs['s2_to'] = node_id_mapping[attribs['to']]
                link_id_mapping[attribs['id']] = {
                    'from': attribs['from'],
                    'to': attribs['to'],
                    's2_from': attribs['s2_from'],
                    's2_to': attribs['s2_to']
                }
                attribs['modes'] = read_modes(attribs['modes'])

                length = float(attribs['length'])
                del attribs['length']

                u = link_id_mapping[elem.attrib['id']]['from']
                v = link_id_mapping[elem.attrib['id']]['to']
                g.add_weighted_edges_from([(u,v,length)], weight='length', **attribs)
                # reset link_attribs
                link_attribs = {}
            elif elem.tag == 'attribute':
                d = elem.attrib
                d['text'] = elem.text
                link_attribs[elem.attrib['name']] = d
    # update the attributes of the last link
    if link_attribs:
        g[u][v][len(g[u][v])-1]['attributes'] = link_attribs
    return g, node_id_mapping, link_id_mapping


def read_modes(modes_string):
    modes = set()
    for m in modes_string.split(','):
        try:
            modes.add(MODE_TYPES_MAP[m.lower()])
        except KeyError:
            modes.add(m.lower())
    return list(modes)


def read_schedule(schedule_path, TRANSFORMER):
    """
    Read MATSim schedule
    :param schedule_path: path to the schedule.xml file
    :param TRANSFORMER: pyproj crs transformer
    :return: schedule (dict {service_id : list(of unique route services, each is a dict
    {   'route_short_name': string,
        'mode': string,
        'stops': list,
        'route': ['1'],
        'trips': {'VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00': '04:40:00'},
        'arrival_offsets': ['00:00:00', '00:02:00'],
        'departure_offsets': ['00:00:00', '00:02:00'] }
    )}),
        transit_stop_id_mapping (dict {
        matsim schedule transit stop id : dict {
            'node_id' : s2 spatial id,
            'attribs' : dict of matsim schedule attributes attached to that transit stop
        }})
    """
    def write_transitLinesTransitRoute(transitLine, transitRoutes, transportMode):
        mode = transportMode['transportMode']
        schedule[transitLine['transitLine']['id']] = []
        for transitRoute, transitRoute_val in transitRoutes.items():
            stops = [s['stop']['refId'] for s in transitRoute_val['stops']]
            s2_stops = [transit_stop_id_mapping[s['stop']['refId']]['s2_node_id'] for s in transitRoute_val['stops']]

            arrival_offsets = []
            departure_offsets = []
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

            route = [r_val['link']['refId'] for r_val in transitRoute_val['links']]

            trips = {}
            for dep in transitRoute_val['departure_list']:
                trips[dep['departure']['id']] = dep['departure']['departureTime']

            d = {
                'route_short_name': transitLine['transitLine']['name'],
                'mode': mode,
                'stops': stops,
                's2_stops': s2_stops,
                'route': route,
                'trips': trips,
                'arrival_offsets': arrival_offsets,
                'departure_offsets': departure_offsets
            }
            schedule[transitLine['transitLine']['id']].append(d)

    schedule = {}
    transitLine = {}
    transitRoutes = {}
    transportMode = {}
    transitStops = {}
    transit_stop_id_mapping = {}

    # transitLines
    for event, elem in ET.iterparse(schedule_path, events=('start', 'end')):
        if event == 'start':
            if elem.tag == 'stopFacility':
                attribs = elem.attrib
                if attribs['id'] not in transitStops:
                    transitStops[attribs['id']] = attribs
                if attribs['id'] not in transit_stop_id_mapping:
                    attribs = elem.attrib
                    lon, lat = spatial.change_proj(attribs['x'], attribs['y'], TRANSFORMER)
                    node_id = spatial.grab_index_s2(lat, lon)
                    transit_stop_id_mapping[attribs['id']] = {'s2_node_id': node_id, 'attribs': attribs}
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
            #     routeProfile = {'routeProfile': elem.attrib}

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

    return schedule, transit_stop_id_mapping
