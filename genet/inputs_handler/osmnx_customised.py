from itertools import groupby
import genet.utils.spatial as spatial
import genet.inputs_handler.osm_reader as osm_reader
import genet.utils.parallel as parallel
import networkx as nx
from math import ceil
from shapely.geometry import LineString, Point
import logging
import osmnx


# rip and monkey patch of a few functions from osmnx.core to customise the tags being saved to the graph


def parse_osm_nodes_paths(osm_data, config):
    """
    function from osmnx, adding our own spin on this - need extra tags

    Construct dicts of nodes and paths with key=osmid and value=dict of
    attributes.

    Parameters
    ----------
    osm_data : dict
        JSON response from from the Overpass API

    Returns
    -------
    nodes, paths : tuple
    """

    nodes = {}
    paths = {}
    for element in osm_data['elements']:
        if element['type'] == 'node':
            key = element['id']
            nodes[key] = get_node(element, config)
        elif element['type'] == 'way':  # osm calls network paths 'ways'
            key = element['id']
            path = get_path(element, config)
            if path['modes']:
                # only proceed with edges that have found a mode (that's why it's important to define them in
                # MODE_INDICATORS in the config
                paths[key] = path

    return nodes, paths


def get_node(element, config):
    """
    Convert an OSM node element into the format for a networkx node.

    Parameters
    ----------
    element : dict
        an OSM node element

    Returns
    -------
    dict
    """

    node = {}
    node['osmid'] = element['id']
    node['s2id'] = spatial.grab_index_s2(element['lat'], element['lon'])
    node['x'], node['y'] = element['lat'], element['lon']
    if 'tags' in element:
        for useful_tag in config.USEFUL_TAGS_NODE:
            if useful_tag in element['tags']:
                node[useful_tag] = element['tags'][useful_tag]
    return node


def get_path(element, config):
    """
    function from osmnx, adding our own spin on this - need extra tags

    Convert an OSM way element into the format for a networkx graph path.

    Parameters
    ----------
    element : dict
        an OSM way element

    Returns
    -------
    dict
    """

    path = {}
    path['osmid'] = element['id']

    # remove any consecutive duplicate elements in the list of nodes
    grouped_list = groupby(element['nodes'])
    path['nodes'] = [group[0] for group in grouped_list]

    if 'tags' in element:
        for useful_tag in config.USEFUL_TAGS_PATH:
            if useful_tag in element['tags']:
                path[useful_tag] = element['tags'][useful_tag]

    path['modes'] = osm_reader.assume_travel_modes(path, config)
    return path


def return_edges(paths, config, bidirectional=False):
    """
    Makes graph edges from osm paths
    :param paths: dictionary {osm_way_id: {osmid: x, nodes:[a,b], osmtags: vals}}
    :param config: genet.inputs_handler.osm_reader.Config object
    :param bidirectional: bool value if True, reads all paths as both ways
    :return:
    """

    def extract_osm_data(data, es):
        d = {}
        for tag in (set(config.USEFUL_TAGS_PATH) | {'osmid', 'modes'}) - {'oneway'}:
            if tag in data:
                d[tag] = data[tag]
        return [(es[i], d) for i in range(len(es))]

    # the list of values OSM uses in its 'oneway' tag to denote True
    osm_oneway_values = ['yes', 'true', '1', '-1', 'reverse']

    edges = []

    for data in paths.values():

        # if this path is tagged as one-way and if it is not a walking network,
        # then we'll add the path in one direction only
        if ('oneway' in data and data['oneway'] in osm_oneway_values) and not bidirectional:
            if data['oneway'] in ['-1', 'reverse']:
                # paths with a one-way value of -1 are one-way, but in the
                # reverse direction of the nodes' order, see osm documentation
                data['nodes'] = list(reversed(data['nodes']))
            # add this path (in only one direction) to the graph
            es = return_edge(data, one_way=True)
            edges.extend(extract_osm_data(data, es))

        elif ('junction' in data and data['junction'] == 'roundabout') and not bidirectional:
            # roundabout are also oneway but not tagged as is
            es = return_edge(data, one_way=True)
            edges.extend(extract_osm_data(data, es))

        # else, this path is not tagged as one-way or it is a walking network
        # (you can walk both directions on a one-way street)
        else:
            # add this path (in both directions) to the graph and set its
            # 'oneway' attribute to False. if this is a walking network, this
            # may very well be a one-way street (as cars/bikes go), but in a
            # walking-only network it is a bi-directional edge
            es = return_edge(data, one_way=False)
            edges.extend(extract_osm_data(data, es))

    return edges


def return_edge(data, one_way):
    # extract the ordered list of nodes from this path element, then delete it
    # so we don't add it as an attribute to the edge later
    path_nodes = data['nodes']
    del data['nodes']

    # set the oneway attribute to the passed-in value, to make it consistent
    # True/False values
    data['oneway'] = one_way

    # zip together the path nodes so you get tuples like (0,1), (1,2), (2,3)
    # and so on
    path_edges = list(zip(path_nodes[:-1], path_nodes[1:]))

    # if the path is NOT one-way
    if not one_way:
        # reverse the direction of each edge and add this path going the
        # opposite direction
        path_edges_opposite_direction = [(v, u) for u, v in path_edges]
        path_edges.extend(path_edges_opposite_direction)
    return path_edges


def process_path(indexed_links_paths_to_simplify):
    links_to_add = {}
    for new_id, link_path_data in indexed_links_paths_to_simplify.items():
        path = link_path_data['path']
        nodes_data = link_path_data['node_data']
        edge_attributes = link_path_data['link_data'].copy()

        edge_attributes['ids'] = edge_attributes['id']
        edge_attributes['id'] = new_id

        edge_attributes['from'] = link_path_data['path'][0]
        edge_attributes['to'] = link_path_data['path'][-1]
        edge_attributes['s2_from'] = nodes_data[path[0]]['s2_id']
        edge_attributes['s2_to'] = nodes_data[path[-1]]['s2_id']

        edge_attributes['freespeed'] = max(edge_attributes['freespeed'])
        edge_attributes['capacity'] = ceil(sum(edge_attributes['capacity']) / len(edge_attributes['capacity']))
        edge_attributes['permlanes'] = ceil(sum(edge_attributes['permlanes']) / len(edge_attributes['permlanes']))
        edge_attributes['length'] = sum(edge_attributes['length'])

        modes = set()
        for mode_list in edge_attributes['modes']:
            modes |= set(mode_list)
        edge_attributes['modes'] = list(modes)

        if 'attributes' in edge_attributes:
            new_attributes = {}
            for attribs_dict in edge_attributes['attributes']:
                for key, val in attribs_dict.items():
                    if key in new_attributes:
                        new_attributes[key]['text'] |= {val["text"]}
                    else:
                        new_attributes[key] = val.copy()
                        new_attributes[key]['text'] = {new_attributes[key]['text']}
            for key, val in new_attributes.items():
                val['text'] -= {None}
                val['text'] = ','.join(val['text'])
            edge_attributes['attributes'] = new_attributes.copy()

        for key in set(edge_attributes) - {'s2_to', 'freespeed', 'attributes', 'to', 'permlanes', 'from', 'id', 'ids',
                                           'capacity', 'length', 'modes', 's2_from'}:
            # don't touch the length attribute, we'll sum it at the end
            if len(set(edge_attributes[key])) == 1:
                # if there's only 1 unique value in this attribute list,
                # consolidate it to the single value (the zero-th)
                edge_attributes[key] = edge_attributes[key][0]
            else:
                # otherwise, if there are multiple values, keep one of each value
                edge_attributes[key] = list(set(edge_attributes[key]))

        # construct the geometry
        edge_attributes["geometry"] = LineString(
            [Point((nodes_data[node]["x"], nodes_data[node]["y"])) for node in path]
        )
        links_to_add[new_id] = edge_attributes
    return links_to_add


def extract_edge_data(G, path):
    edge_attributes = {}
    for u, v in zip(path[:-1], path[1:]):
        # get edge between these nodes: if multiple edges exist between
        # them - smoosh them
        for multi_idx, edge in G[u][v].items():
            for key in edge:
                if key in edge_attributes:
                    # if this key already exists in the dict, append it to the
                    # value list
                    edge_attributes[key].append(edge[key])
                else:
                    # if this key doesn't already exist, set the value to a list
                    # containing the one value
                    edge_attributes[key] = [edge[key]]
    return edge_attributes


def _is_endpoint(node_neighbours):
    """
    :param node_neighbours: dict {node_id: {successors: in_degree, out_degree)
    :return:
    """
    return [node for node, data in node_neighbours.items() if
            (len(data['successors']) != 1) or (len(data['predecessors']) != 1)]


def _build_path(data_to_simplify, endpoints):
    # find first node
    first_edge = ''
    nodes = set(sum(data_to_simplify['edges'], ()))
    for node in nodes:
        associated_edges = [_edge for _edge in data_to_simplify['edges'] if (_edge[0] == node) or (_edge[1] == node)]
        if len(associated_edges) == 1:
            if associated_edges[0][0] == node:
                first_edge = associated_edges[0]
                break

    node_len = len(data_to_simplify['edges'])
    if not first_edge:
        # no obvious starting point, it is a loop
        # find the end point in the loop
        endpt = endpoints & nodes
        if len(endpt) > 1:
            raise RuntimeError('There should be just one end point in the loop')
        if len(endpt) != 0:
            first_node = list(endpt)[0]
            first_edge = [_edge for _edge in data_to_simplify['edges'] if _edge[0] == first_node][0]
            node_len = node_len - 2
        else:
            return []

    # build the path
    path = [first_edge[0], first_edge[1]]
    for i in range(node_len):
        for _edge in data_to_simplify['edges']:
            if path[-1] == _edge[0]:
                path.append(_edge[1])
                break
    return path


def _build_paths(node_sets_to_simplify, endpoints):
    paths = []
    for node_set in node_sets_to_simplify:
        path = _build_path(node_set, endpoints)
        if path:
            paths.append(path)
    return paths


def _get_paths_to_simplify(G, no_processes=1):
    # first identify all the nodes that are endpoints
    endpoints = set(
        parallel.multiprocess_wrap(
            data={node: {'successors': list(G.successors(node)), 'predecessors': list(G.predecessors(node))}
                  for node in G.nodes},
            split=parallel.split_dict,
            apply=_is_endpoint,
            combine=parallel.combine_list,
            processes=no_processes)
    )

    logging.info(f"Identified {len(endpoints)} edge endpoints")

    working_graph = G.copy()
    working_graph.remove_nodes_from(endpoints)
    nodes_to_simplify = nx.weakly_connected_components(working_graph)

    return parallel.multiprocess_wrap(
        data=[{'nodes': node_set, 'edges': set(G.out_edges(node_set)) | set(G.in_edges(node_set))} for node_set in
              nodes_to_simplify],
        split=parallel.split_list,
        apply=_build_paths,
        combine=parallel.combine_list,
        processes=no_processes,
        endpoints=endpoints
    )


def simplify_graph(n, no_processes=1, strict=True, remove_rings=True):
    """
    MONKEY PATCH OF OSMNX'S GRAPH SIMPLIFICATION ALGO

    Simplify a graph's topology by removing interstitial nodes.

    Simplify graph topology by removing all nodes that are not intersections
    or dead-ends. Create an edge directly between the end points that
    encapsulate them, but retain the geometry of the original edges, saved as
    attribute in new edge.

    Parameters
    ----------
    G : genet.Network object
    strict : bool
        if False, allow nodes to be end points even if they fail all other
        rules but have incident edges with different OSM IDs. Lets you keep
        nodes at elbow two-way intersections, but sometimes individual blocks
        have multiple OSM IDs within them too.
    remove_rings : bool
        if True, remove isolated self-contained rings that have no endpoints

    Returns
    -------
    None, updates n.graph, indexing and schedule routes. Adds a new attribute to n that records map between old
    and new link indices
    """
    if osmnx.simplification._is_simplified(n.graph):
        raise Exception("This graph has already been simplified, cannot simplify it again.")

    logging.info("Begin simplifying the graph")
    G = n.graph.copy()
    initial_node_count = len(list(G.nodes()))
    initial_edge_count = len(list(G.edges()))

    logging.info('Generating paths to be simplified')
    # generate each path that needs to be simplified
    paths_to_simplify = list(_get_paths_to_simplify(G))

    indexed_paths_to_simplify = dict(zip(n.generate_indices_for_n_edges(len(paths_to_simplify)), paths_to_simplify))
    indexed_paths_to_simplify = {
        k: {'path': path, 'link_data': extract_edge_data(G, path), 'node_data': {node: n.node(node) for node in path}}
        for k, path in indexed_paths_to_simplify.items()
    }

    logging.info('Processing links for all paths to be simplified')
    links_to_add = parallel.multiprocess_wrap(
        data=indexed_paths_to_simplify,
        split=parallel.split_dict,
        apply=process_path,
        combine=parallel.combine_dict,
        processes=no_processes
    )

    logging.info('Adding new simplified links')
    # add links
    reindexing_dict, links_and_attributes = n.add_links(links_to_add)

    # collect all links and nodes to remove, generate link simplification map between old indices and new
    links_to_remove = set()
    nodes_to_remove = set()
    n.link_simplification_map = {}
    for new_id, path_data in indexed_paths_to_simplify.items():
        links_to_remove |= set(path_data['link_data']['id'])
        if new_id in reindexing_dict:
            new_id = reindexing_dict[new_id]
        n.link_simplification_map = {**n.link_simplification_map,
                                     **dict(zip(path_data['link_data']['id'],
                                                [new_id] * len(path_data['link_data']['id'])))}
        nodes_to_remove |= set(path_data['path'][1:-1])

    logging.info('Removing links which have now been replaced by simplified links')
    # remove links
    n.remove_links(links_to_remove, silent=True)

    logging.info('Removing nodes')
    # finally, remove nodes
    n.remove_nodes(nodes_to_remove, silent=True)

    # TODO
    # if remove_rings:
    #     # remove any connected components that form a self-contained ring
    #     # without any endpoints
    #     wccs = nx.weakly_connected_components(G)
    #     nodes_in_rings = set()
    #     for wcc in wccs:
    #         if all([not osmnx.simplification._is_endpoint(G, n) for n in wcc]):
    #             nodes_in_rings.update(wcc)
    #     G.remove_nodes_from(nodes_in_rings)

    # mark graph as having been simplified
    n.graph.graph["simplified"] = True

    logging.info(
        f"Simplified graph: {initial_node_count} to {len(n.graph)} nodes, {initial_edge_count} to "
        f"{len(n.graph.edges())} edges")

    if n.schedule:
        logging.info("Updating the Schedule")
    # update stop's link reference ids
    new_stops_attribs = {}
    for node, link_ref_id in n.schedule._graph.nodes(data='linkRefId'):
        try:
            new_stops_attribs[node] = {'linkRefId': n.link_simplification_map[link_ref_id]}
        except KeyError:
            # Not all linkref ids would have changed
            pass
    nx.set_node_attributes(n.schedule._graph, new_stops_attribs)
    logging.info("Updated Stop Link Reference Ids")

    # TODO update schedule routes
    for service_id, route in n.schedule.routes():
        new_route = []
        for link in route.route:
            updated_route_link = link
            if link in n.link_simplification_map:
                updated_route_link = n.link_simplification_map[link]
            if not new_route:
                new_route = [updated_route_link]
            elif new_route[-1] != updated_route_link:
                new_route.append(updated_route_link)
        route.route = new_route
    logging.info("Updated Network Routes")
