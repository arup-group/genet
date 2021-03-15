from itertools import groupby
import genet.utils.spatial as spatial
import genet.inputs_handler.osm_reader as osm_reader


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
    node['s2id'] = spatial.generate_index_s2(lat=element['lat'], lng=element['lon'])
    node['x'], node['y'] = element['lon'], element['lat']
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
