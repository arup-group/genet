import yaml
import logging
import osmread
import genet.inputs_handler.osmnx_customised as osmnx_customised
import genet.utils.spatial as spatial
import genet.utils.parallel as parallel
from genet.outputs_handler.matsim_xml_values import MATSIM_JOSM_DEFAULTS


class Config(object):
    def __init__(self, path):
        with open(path) as c:
            self.config = yaml.load(c, Loader=yaml.FullLoader)

        self.USEFUL_TAGS_NODE = self.config['OSM_TAGS']['USEFUL_TAGS_NODE']
        self.USEFUL_TAGS_PATH = self.config['OSM_TAGS']['USEFUL_TAGS_PATH']

        self.MODE_INDICATORS = self.config['MODES']['MODE_INDICATORS']
        self.DEFAULT_OSM_TAG_VALUE = self.config['MODES']['DEFAULT_OSM_TAG_VALUE']


def assume_travel_modes(edge, config):
    modes = []
    for key, val in edge.items():
        if key in config.MODE_INDICATORS:
            if isinstance(config.MODE_INDICATORS[key], dict):
                if val == 'road':
                    edge['highway'] = 'unclassified'
                    modes.extend(config.MODE_INDICATORS['highway']['unclassified'])
                elif val not in ['construction', 'proposed']:
                    if val in config.MODE_INDICATORS[key]:
                        modes.extend(config.MODE_INDICATORS[key][val])
                    else:
                        logging.debug('Value {} for key {} does not have a mode assignment'.format(val, key))
            else:
                modes.extend(config.MODE_INDICATORS[key])
        elif key not in ['osmid', 'nodes', 'name', 'maxspeed', 'oneway', 'lanes', 'access']:
            logging.debug('Key {} is not present in OSM mode definitions'.format(key))
    return list(set(modes))


def find_matsim_link_values(edge_data, config):
    matsim_vals = {}
    if (set(edge_data.keys()) | set(MATSIM_JOSM_DEFAULTS.keys())) or ('highway' in edge_data):
        if 'highway' in edge_data:
            # highway is the one allowed 'nested' osm tag, the values of the tags are flattened in MATSIM_JOSM_DEFAULTS
            if edge_data['highway'] in MATSIM_JOSM_DEFAULTS:
                matsim_vals = MATSIM_JOSM_DEFAULTS[edge_data['highway']]
            else:
                logging.info('{} is highway but has no value defaults'.format(edge_data['highway']))
        else:
            for key in edge_data.keys():
                if key in MATSIM_JOSM_DEFAULTS:
                    # checks the non nested tags, at the time of writing that is just railway
                    matsim_vals = MATSIM_JOSM_DEFAULTS[key]

    if not matsim_vals:
        # check the modes as a last resort and look at the defaults in the config
        for mode in edge_data['modes']:
            # if more than one mode, there may have been a capacity already assumed for the link, go for the values
            # with bigger capacity
            if 'capacity' in matsim_vals:
                if mode in config.DEFAULT_OSM_TAG_VALUE:
                    new_matsim_vals = MATSIM_JOSM_DEFAULTS[config.DEFAULT_OSM_TAG_VALUE[mode]]
                    # decide which one is better on lane capacity
                    if float(new_matsim_vals['capacity']) > float(matsim_vals['capacity']):
                        matsim_vals = new_matsim_vals
            elif mode in config.DEFAULT_OSM_TAG_VALUE:
                matsim_vals = MATSIM_JOSM_DEFAULTS[config.DEFAULT_OSM_TAG_VALUE[mode]]
            else:
                logging.info('Mode {} not in the config\'s DEFAULT_OSM_TAG_VALUE\'s. '
                             'Defaulting to {}'.format(mode, 'secondary'))
                matsim_vals = MATSIM_JOSM_DEFAULTS['secondary']
    return matsim_vals


def generate_osm_graph_edges_from_file(osm_file, config, num_processes):
    logging.info("Building OSM graph from file {}".format(osm_file))
    response_jsons = file_converter(osm_file)
    nodes, edges = create_s2_indexed_osm_graph(response_jsons, config, num_processes, bidirectional=False)
    logging.info('Created OSM edges')
    return nodes, edges


def create_s2_indexed_osm_graph(response_jsons, config, num_processes, bidirectional):
    logging.info('Creating networkx graph from OSM data')

    elements = []
    for response_json in response_jsons:
        elements.extend(response_json['elements'])

    logging.info('OSM: Extract Nodes and Paths from OSM data')
    nodes = {}
    paths = {}
    for osm_data in response_jsons:
        nodes_temp, paths_temp = osmnx_customised.parse_osm_nodes_paths(osm_data, config)
        for key, value in nodes_temp.items():
            nodes[key] = value
        for key, value in paths_temp.items():
            paths[key] = value

    logging.info('OSM: Add each OSM way (aka, path) to the OSM graph')
    edges = parallel.multiprocess_wrap(
        data=paths,
        split=parallel.split_dict,
        apply=osmnx_customised.return_edges,
        combine=parallel.combine_list,
        processes=num_processes,
        config=config,
        bidirectional=bidirectional)

    logging.info('OSM: add length (great circle distance between nodes) attribute to each edge and index by s2')
    for edge, attr in edges:
        from_n = nodes[edge[0]]['s2id']
        to_n = nodes[edge[1]]['s2id']
        attr['length'] = spatial.distance_between_s2cellids(from_n, to_n)
    return nodes, edges


def read_node(entity):
    json_data = {'type': 'node',
                 'id': entity.id,
                 'version': entity.version,
                 'timestamp': entity.timestamp,
                 'uid': entity.uid,
                 'tags': entity.tags,
                 'lon': entity.lon,
                 'lat': entity.lat
                 }
    return json_data


def read_way(entity):
    json_data = {'type': 'way',
                 'id': entity.id,
                 'version': entity.version,
                 'timestamp': entity.timestamp,
                 'uid': entity.uid,
                 'tags': entity.tags,
                 'nodes': entity.nodes
                 }
    return json_data


def read_relation(entity):
    json_data = {'type': 'relation',
                 'id': entity.id,
                 'version': entity.version,
                 'timestamp': entity.timestamp,
                 'uid': entity.uid,
                 'tags': entity.tags,
                 'members': entity.members
                 }
    return json_data


def file_converter(osm_file):
    elements = []

    # Extract the nodes and the ways
    for entity in osmread.parse_file(osm_file):
        json_data = {}

        if isinstance(entity, osmread.Node):
            json_data = read_node(entity)

        elif isinstance(entity, osmread.Way):
            json_data = read_way(entity)

        elif isinstance(entity, osmread.Relation):
            json_data = read_relation(entity)

        elements.append(json_data)

    # response_jsons
    return [{'elements': elements}]
