import os
import yaml
import logging
import osmread
import genet.inputs_handler.osmnx_customised as osmnx_customised
import genet.utils.spatial as spatial
import genet.utils.parallel as parallel


class Config(object):
    def __init__(self, path):
        with open(path) as c:
            self.config = yaml.load(c, Loader=yaml.FullLoader)

        self.USEFUL_TAGS_NODE = self.config['OSM_TAGS']['USEFUL_TAGS_NODE']
        self.USEFUL_TAGS_PATH = self.config['OSM_TAGS']['USEFUL_TAGS_PATH']

        self.MODE_INDICATORS = self.config['MODES']['MODE_INDICATORS']
        self.DEFAULT_OSM_TAG_VALUE = self.config['MODES']['DEFAULT_OSM_TAG_VALUE']


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
    edges = parallel.multiprocess_wrap_function_processing_dict_data(
        osmnx_customised.return_edges,
        paths,
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
