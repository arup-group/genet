import genet.utils.parallel as parallel
import networkx as nx
from math import ceil
from shapely.geometry import LineString, Point
import logging
import osmnx


# rip and monkey patch of a few functions from osmnx.simplification to customise graph simplification


def _process_path(indexed_edge_groups_to_simplify):
    links_to_add = {}
    for new_id, edge_group_data in indexed_edge_groups_to_simplify.items():
        path = edge_group_data['path']
        nodes_data = edge_group_data['node_data']
        edge_attributes = edge_group_data['link_data'].copy()

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
                if len(val['text']) == 1:
                    val['text'] = list(val['text'])[0]
            edge_attributes['attributes'] = new_attributes.copy()

        # construct the geometry
        edge_attributes["geometry"] = LineString(
            [Point((nodes_data[node]["x"], nodes_data[node]["y"])) for node in path]
        )

        edge_attributes['ids'] = edge_attributes['id']
        edge_attributes['id'] = new_id

        edge_attributes['from'] = path[0]
        edge_attributes['to'] = path[-1]
        edge_attributes['s2_from'] = nodes_data[path[0]]['s2_id']
        edge_attributes['s2_to'] = nodes_data[path[-1]]['s2_id']

        edge_attributes['freespeed'] = max(edge_attributes['freespeed'])
        edge_attributes['capacity'] = ceil(sum(edge_attributes['capacity']) / len(edge_attributes['capacity']))
        edge_attributes['permlanes'] = ceil(sum(edge_attributes['permlanes']) / len(edge_attributes['permlanes']))
        edge_attributes['length'] = sum(edge_attributes['length'])

        modes = set()
        for mode_list in edge_attributes['modes']:
            modes |= set(mode_list)
        edge_attributes['modes'] = modes

        for key in set(edge_attributes) - {'s2_to', 'freespeed', 'attributes', 'to', 'permlanes', 'from', 'id', 'ids',
                                           'capacity', 'length', 'modes', 's2_from', 'geometry'}:
            if len(set(edge_attributes[key])) == 1:
                # if there's only 1 unique value in this attribute list,
                # consolidate it to the single value (the zero-th)
                edge_attributes[key] = edge_attributes[key][0]
            else:
                # otherwise, if there are multiple values, keep one of each value
                edge_attributes[key] = list(set(edge_attributes[key]))

        links_to_add[new_id] = edge_attributes
    return links_to_add


def _extract_edge_data(G, path):
    edge_attributes = {}
    for u, v in zip(path[:-1], path[1:]):
        # get edge between these nodes: if multiple edges exist between
        # them - smoosh them
        # TODO this shouldn't be the case anymore, multiple edges will result in a non simplified edge
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
    return [node for node, data in node_neighbours.items() if (len(data['successors'] | data['predecessors']) > 2) or
            (len(data['successors']) == 0 or len(data['predecessors']) == 0)]


def _build_path(edge_group, endpoints):
    # find first node
    first_edge = ()
    nodes = set(sum(edge_group, ()))
    groups_endpts = endpoints & nodes

    for _edge in edge_group:
        if _edge[0] in groups_endpts:
            first_edge = _edge
            break

    if not first_edge:
        # is disconnected, don't mess with it
        return []

    # build the path
    ordered_edge_group = [first_edge]
    edge_group -= {first_edge}
    for i in range(len(edge_group)):
        for _edge in edge_group:
            if _edge[0] == ordered_edge_group[-1][1]:
                ordered_edge_group.append(_edge)
    path = [_edge[0] for _edge in ordered_edge_group]
    path.append(ordered_edge_group[-1][1])
    return path


def _build_paths(edge_groups_to_simplify, endpoints):
    paths = []
    for edge_group in edge_groups_to_simplify:
        path = _build_path(edge_group, endpoints)
        if path:
            paths.append(path)
    return paths


def _get_edge_groups_to_simplify(G, no_processes=1):
    # first identify all the nodes that are endpoints
    endpoints = set(
        parallel.multiprocess_wrap(
            data={node: {'successors': set(G.successors(node)), 'predecessors': set(G.predecessors(node))}
                  for node in G.nodes},
            split=parallel.split_dict,
            apply=_is_endpoint,
            combine=parallel.combine_list,
            processes=no_processes)
    )

    logging.info(f"Identified {len(endpoints)} edge endpoints")
    path_start_points = G.out_edges(endpoints)

    paths = []
    for path_start_point in path_start_points:
        if path_start_point[1] not in endpoints:
            path = list(path_start_point)
            end_node = path[-1]
            while end_node not in endpoints:
                next_nodes = list(G.neighbors(end_node))
                if len(next_nodes) > 1:
                    next_nodes = list(set(next_nodes) - set(path))
                    if len(next_nodes) > 1:
                        raise RuntimeError('Path building found additional branching. Simplification failed to find'
                                           'all of the correct end points.')
                    if not next_nodes:
                        # is a loop, build the rest of the path except the end point i.e. from [1,2,3] to [1,2,3,3,2]
                        path += path[::-1][:-1]
                        next_nodes = [path[0]]
                end_node = next_nodes[0]
                path.append(end_node)
            if path:
                paths.append(path)

    return paths


def simplify_graph(n, no_processes=1):
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
    edges_to_simplify = _get_edge_groups_to_simplify(G, no_processes=no_processes)

    indexed_paths_to_simplify = dict(zip(n.generate_indices_for_n_edges(len(edges_to_simplify)), edges_to_simplify))
    indexed_paths_to_simplify = {
        k: {'path': path,
            'link_data': _extract_edge_data(G, path),
            'node_data': {node: n.node(node) for node in path}
            }
        for k, path in indexed_paths_to_simplify.items()
    }

    logging.info('Processing links for all paths to be simplified')
    links_to_add = parallel.multiprocess_wrap(
        data=indexed_paths_to_simplify,
        split=parallel.split_dict,
        apply=_process_path,
        combine=parallel.combine_dict,
        processes=no_processes
    )

    logging.info('Adding new simplified links')
    # add links
    reindexing_dict, links_and_attributes = n.add_links(links_to_add)

    # collect all links and nodes to remove, generate link simplification map between old indices and new
    nodes_to_remove = set()
    n.link_simplification_map = {}
    for new_id, path_data in indexed_paths_to_simplify.items():
        ids = set(path_data['link_data']['id'])
        try:
            new_id = reindexing_dict[new_id]
        except KeyError:
            pass
        n.link_simplification_map = {**n.link_simplification_map,
                                     **dict(zip(ids, [new_id] * len(ids)))}
        nodes_to_remove |= set(path_data['path'][1:-1])
    links_to_remove = set(n.link_simplification_map.keys())

    logging.info('Removing links which have now been replaced by simplified links')
    # remove links
    n.remove_links(links_to_remove)

    logging.info('Removing nodes')
    # finally, remove nodes
    n.remove_nodes(nodes_to_remove)

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

        # update schedule routes
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
