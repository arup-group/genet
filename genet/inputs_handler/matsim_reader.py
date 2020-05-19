import networkx as nx
import xml.etree.cElementTree as ET
from genet.utils import spatial
from genet.variables import MODE_TYPES_MAP


def read_network(network_path, TRANSFORMER):
    g = nx.MultiDiGraph()

    node_id_mapping = {}
    link_id_mapping = {}
    link_attribs = {}

    for event, elem in ET.iterparse(network_path, events=('start', 'end')):
        if event == 'start':
            if elem.tag == 'node':
                attribs = elem.attrib
                lon, lat = spatial.change_proj(attribs['x'], attribs['y'], TRANSFORMER)
                node_id = spatial.grab_index_s2(lat, lon)
                node_id_mapping[attribs['id']] = node_id
                g.add_node(node_id, **attribs)
            elif elem.tag == 'link':
                # update old link by link attributes (osm tags etc.)
                if link_attribs:
                    # if multiple edges, add to the one added most recently
                    g[u][v][len(g[u][v])-1]['attributes'] = link_attribs

                attribs = elem.attrib
                link_id_mapping[attribs['id']] = {
                    'from': node_id_mapping[attribs['from']],
                    'to': node_id_mapping[attribs['to']],
                    's2_id': '{}_{}'.format(node_id_mapping[attribs['from']], node_id_mapping[attribs['to']])
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


def read_schedule(schedule_path, link_id_mapping, TRANSFORMER):
    def write_transitLinesTransitRoute(transitLine, transitRoutes, transportMode):
        mode = transportMode['transportMode']
        schedule[transitLine['transitLine']['id']] = []
        for transitRoute, transitRoute_val in transitRoutes.items():
            stops = [transit_stop_id_mapping[s['stop']['refId']]['node_id'] for s in transitRoute_val['stops']]

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

            # build up the pt routing dict
            i = 0
            pt_route = []
            pt_routing_link_dict = {}
            transit_stops_ids = [s['stop']['refId'] for s in transitRoute_val['stops']]
            for link in transitRoute_val['links']:
                link_id = link['link']['refId']
                prev_stop = transitStops[transit_stops_ids[i]]['linkRefId']
                next_stop = transitStops[transit_stops_ids[i + 1]]['linkRefId']

                if link_id != next_stop:
                    pt_route.append(link_id)
                else:
                    pt_route.append(link_id)
                    pt_routing_link_dict[
                        (transit_stop_id_mapping[transit_stops_ids[i]]['node_id'],
                         transit_stop_id_mapping[transit_stops_ids[i + 1]]['node_id'],
                         mode)] = pt_route
                    pt_route = [link_id]
                    i += 1
                    if i < len(transit_stops_ids) - 1:
                        prev_stop = transitStops[transit_stops_ids[i]]['linkRefId']
                        next_stop = transitStops[transit_stops_ids[i + 1]]['linkRefId']
                        if prev_stop == next_stop:
                            pt_routing_link_dict[
                                (transit_stop_id_mapping[transit_stops_ids[i]]['node_id'],
                                 transit_stop_id_mapping[transit_stops_ids[i + 1]]['node_id'],
                                 mode)] = pt_route.copy()
                            i += 1
            # convert the linkid pt route to node based as travered in the graph
            for key, val in pt_routing_link_dict.items():
                pt_route = []
                for link_id in val:
                    link = link_id_mapping[link_id]
                    link_from_n, link_to_n = link['from'], link['to']
                    if pt_route:
                        if pt_route[-1] != link_from_n:
                            pt_route.append(link_from_n)
                        if pt_route[-1] != link_to_n:
                            pt_route.append(link_to_n)
                    else:
                        pt_route.append(link_from_n)
                        if link_from_n != link_to_n:
                            pt_route.append(link_to_n)

                pt_routing_dict[key] = pt_route

            trips = {}
            for dep in transitRoute_val['departure_list']:
                trips[dep['departure']['id']] = dep['departure']['departureTime']

            d = {
                'route_short_name': transitLine['transitLine']['name'],
                'mode': mode,
                'stops': stops,
                'trips': trips,
                'arrival_offsets': arrival_offsets,
                'departure_offsets': departure_offsets
            }
            schedule[transitLine['transitLine']['id']].append(d)

    schedule = {}
    pt_routing_dict = {}
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
                    transit_stop_id_mapping[attribs['id']] = {'node_id': node_id, 'attribs': attribs}
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

    return schedule, pt_routing_dict, transit_stop_id_mapping


def update_transit_stops(transit_stop_id_mapping, link_id_mapping):
    dict_to_return = {}

    for transit_stop_id, transit_stop_id_val in transit_stop_id_mapping.items():
        attribs = transit_stop_id_val['attribs']
        attribs['id'] = str(transit_stop_id_val['node_id'])
        try:
            attribs['linkRefId'] = link_id_mapping[attribs['linkRefId']]['puma_id']
            dict_to_return[transit_stop_id_val['node_id']] = attribs
        except KeyError:
            dict_to_return[transit_stop_id_val['node_id']] = attribs

    return dict_to_return

#
# if __name__ == '__main__':
#     arg_parser = argparse.ArgumentParser(description='Read MATSim network into puma-ish objects')
#
#     arg_parser.add_argument('-n',
#                             '--network',
#                             help='Input MATSim network',
#                             required=False)
#
#     arg_parser.add_argument('-s',
#                             '--schedule',
#                             help='Input MATSim schedule',
#                             required=False)
#
#     arg_parser.add_argument('-p',
#                             '--projection',
#                             help='EPSG projection of the inputs',
#                             default='epsg:27700',
#                             required=False)
#
#     arg_parser.add_argument('-c',
#                             '--config',
#                             help='Config for puma. Look at the default config: src/configs/default_config.yml',
#                             default=os.path.abspath(os.path.join(os.path.dirname(__file__),
#                                                                  '../configs/default_config.yml')))
#
#     arg_parser.add_argument('-o',
#                             '--output_dir',
#                             help='Output directory',
#                             required=True)
#
#     args = vars(arg_parser.parse_args())
#     network_path = args['network']
#     schedule_path = args['schedule']
#     config = Config(args['config'])
#     output_dir = args['output_dir']
#     persistence.ensure_dir(output_dir)
#     TRANSFORMER = Transformer.from_proj(Proj(init=args['projection']), Proj(init='epsg:4326'))
#
#     if network_path:
#         network, node_id_mapping, link_id_mapping = read_network(network_path, TRANSFORMER)
#
#     if schedule_path:
#         if not network_path:
#             raise RuntimeError('You need the network to understand the PT routes')
#         schedule, pt_routing_dict, transit_stop_id_mapping = read_schedule(
#             schedule_path,
#             link_id_mapping,
#             TRANSFORMER)
#
#         osm_indexing_tree = tree_operations.build_s2_indexing_tree(network.edges, {})
#
#         transit_stops = update_transit_stops(transit_stop_id_mapping, link_id_mapping)
#
#         matsim_xml_writer.write_to_matsim_xmls(
#             output_dir,
#             osm_indexing_tree,
#             transit_stops,
#             pt_routing_dict,
#             schedule,
#             config,
#             re_write=True
#         )
