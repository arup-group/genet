from itertools import groupby
import genet.utils.spatial as spatial
import genet.inputs_handler.osm_reader as osm_reader
import networkx as nx
from math import ceil
from shapely.geometry import LineString, Point
import logging


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


def simplify_graph(n, strict=True, remove_rings=True):
    """
    MONKEY PATCH OF OSMNX'S GRAPH SIMPLIFICATION ALGO TOW ORK WITH OUR MESSED UP ATTRIBS

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
    import osmnx

    if osmnx.simplification._is_simplified(n.graph):
        raise Exception("This graph has already been simplified, cannot simplify it again.")

    logging.info("Begin topologically simplifying the graph...")
    G = n.graph.copy()
    initial_node_count = len(list(G.nodes()))
    initial_edge_count = len(list(G.edges()))
    all_nodes_to_remove = []
    all_edges_to_add = []

    used_indices = set()
    n.link_simplification_map = {}
    # generate each path that needs to be simplified
    for path in osmnx.simplification._get_paths_to_simplify(G, strict=strict):
        # add the interstitial edges we're removing to a list so we can retain
        # their spatial geometry
        edge_attributes = {}
        for u, v in zip(path[:-1], path[1:]):

            # there should rarely be multiple edges between interstitial nodes
            # usually happens if OSM has duplicate ways digitized for just one
            # street... we will keep only one of the edges (see below)
            number_of_edges = G.number_of_edges(u, v)
            if number_of_edges != 1:
                pass

            # get edge between these nodes: if multiple edges exist between
            # them (see above) - smoosh them
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

        edge_attributes['ids'] = edge_attributes['id']
        new_link_idx = n.generate_index_for_edge(avoid_keys=used_indices, silent=True)
        edge_attributes['id'] = new_link_idx
        used_indices |= {new_link_idx}
        n.link_simplification_map = {**n.link_simplification_map,
                                     **dict(zip(edge_attributes['ids'], [new_link_idx] * len(edge_attributes['ids'])))}

        edge_attributes['from'] = path[0]
        edge_attributes['to'] = path[-1]
        edge_attributes['s2_from'] = n.node(path[0])['s2_id']
        edge_attributes['s2_to'] = n.node(path[-1])['s2_id']

        edge_attributes['freespeed'] = sum(edge_attributes['freespeed']) / len(edge_attributes['freespeed'])
        edge_attributes['capacity'] = sum(edge_attributes['capacity']) / len(edge_attributes['capacity'])
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
            [Point((G.nodes[node]["x"], G.nodes[node]["y"])) for node in path]
        )

        # link ref id mapping update
        for link_id in edge_attributes['ids']:
            del n.link_id_mapping[link_id]
        n.link_id_mapping[new_link_idx] = {'from': edge_attributes['from'], 'to': edge_attributes['to'],
                                           'multi_edge_idx': 0}

        # add the nodes and edges to their lists for processing at the end
        all_nodes_to_remove.extend(path[1:-1])
        all_edges_to_add.append(
            {"origin": path[0], "destination": path[-1], "attr_dict": edge_attributes}
        )

    # for each edge to add in the list we assembled, create a new edge between
    # the origin and destination
    for edge in all_edges_to_add:
        G.add_edge(edge["origin"], edge["destination"], **edge["attr_dict"])

    # finally remove all the interstitial nodes between the new edges
    G.remove_nodes_from(set(all_nodes_to_remove))

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
    G.graph["simplified"] = True

    logging.info(f"Simplified graph: {initial_node_count} to {len(G)} nodes, {initial_edge_count} to {len(G.edges())} "
                 f"edges")
    n.graph = G

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
