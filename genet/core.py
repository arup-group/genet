import networkx as nx
import pandas as pd
import uuid
import logging
import os
from copy import deepcopy
from typing import Union, List
from pyproj import Proj, Transformer
from genet.inputs_handler import matsim_reader, gtfs_reader
from genet.outputs_handler import matsim_xml_writer
from genet.modify import ChangeLog
from genet.utils import spatial, persistence, graph_operations
from genet.schedule_elements import Service

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)


class Network:
    def __init__(self):
        self.graph = nx.MultiDiGraph()
        self.schedule = Schedule()
        self.change_log = ChangeLog()
        self.spatial_tree = spatial.SpatialTree()

        self.epsg = ''
        self.transformer = ''
        # link_id_mapping maps between (usually string literal) index per edge to the from and to nodes that are
        # connected by the edge
        self.link_id_mapping = {}

    def __repr__(self):
        return "<{} instance at {}: with \ngraph: {} and \nschedule {}".format(
            self.__class__.__name__,
            id(self),
            nx.info(self.graph),
            self.schedule.info()
        )

    def __str__(self):
        return self.info()

    def add(self, other):
        """
        This is deliberately not a magic function to discourage `new_network = network_1 + network_2` (and memory
        goes out the window)
        :param other:
        :return:
        """
        # consolidate coordinate systems
        if other.epsg != self.epsg:
            logging.info('Attempting to merge two networks in different coordinate systems. '
                         'Reprojecting from {} to {}'.format(other.epsg, self.epsg))
            other.reproject(other.epsg)
        # consolidate node ids
        other = graph_operations.consolidate_node_indices(self, other)
        # consolidate link ids
        other = graph_operations.consolidate_link_indices(self, other)

        # finally, once the node and link ids have been sorted, combine the graphs
        # nx.compose(left, right) overwrites data in left with data in right under matching ids
        self.graph = nx.compose(other.graph, self.graph)
        # finally, combine link_id_mappings
        self.link_id_mapping = {**other.link_id_mapping, **self.link_id_mapping}

        # combine schedules
        self.schedule = self.schedule + other.schedule

        # merge change_log DataFrames
        self.change_log.log = self.change_log.log.append(other.change_log.log)
        self.change_log.log = self.change_log.log.sort_values(by='timestamp').reset_index(drop=True)

    def print(self):
        return self.info()

    def info(self):
        return "Graph info: {} \nSchedule info: {}".format(
            nx.info(self.graph),
            self.schedule.info()
        )

    def reproject(self, new_epsg):
        """
        Changes projection of the network to new_epsg
        :param new_epsg: 'epsg:1234'
        :return:
        """
        old_to_new_transformer = Transformer.from_proj(Proj(self.epsg), Proj(new_epsg))
        for node_id, node_attribs in self.nodes():
            x, y = spatial.change_proj(node_attribs['x'], node_attribs['y'], old_to_new_transformer)
            reprojected_node_attribs = {'x': x, 'y': y}
            self.apply_attributes_to_node(node_id, reprojected_node_attribs)
        if self.schedule:
            self.schedule.reproject(new_epsg)
        self.initiate_crs_transformer(new_epsg)

    def node_attribute_summary(self, data=False):
        """
        Is expensive. Parses through data stored on nodes and gives a summary tree of the data stored on the nodes.
        If data is True, shows also up to 5 unique values stored under such keys.
        :param data: bool, False by default
        :return:
        """
        root = graph_operations.get_attribute_schema(self.nodes(), data=data)
        graph_operations.render_tree(root, data)

    def node_attribute_data_under_key(self, key):
        """
        Generates a pandas.Series object index by node ids, with data stored on the nodes under `key`
        :param key: either a string e.g. 'x', or if accessing nested information, a dictionary
            e.g. {'attributes': {'osm:way:name': 'text'}}
        :return: pandas.Series
        """
        return pd.Series(graph_operations.get_attribute_data_under_key(self.nodes(), key))

    def node_attribute_data_under_keys(self, keys: list, index_name=None):
        """
        Generates a pandas.DataFrame object index by link ids, with data stored on the nodes under `key`
        :param keys: list of either a string e.g. 'x', or if accessing nested information, a dictionary
            e.g. {'attributes': {'osm:way:name': 'text'}}
        :param index_name: optional, gives the index_name to dataframes index
        :return: pandas.DataFrame
        """
        df = None
        for key in keys:
            if isinstance(key, dict):
                # consolidate nestedness to get a name for the column
                name = str(key)
                name = name.replace('{', '').replace('}', '').replace("'", '').replace(' ', ':')
            else:
                name = key

            col_series = self.node_attribute_data_under_key(key)
            col_series.name = name

            if df is not None:
                df = df.merge(pd.DataFrame(col_series), left_index=True, right_index=True, how='outer')
            else:
                df = pd.DataFrame(col_series)
        if index_name:
            df.index = df.index.set_names([index_name])
        return df

    def link_attribute_summary(self, data=False):
        """
        Is expensive. Parses through data stored on links and gives a summary tree of the data stored on the links.
        If data is True, shows also up to 5 unique values stored under such keys.
        :param data: bool, False by default
        :return:
        """
        root = graph_operations.get_attribute_schema(self.links(), data=data)
        graph_operations.render_tree(root, data)

    def link_attribute_data_under_key(self, key: Union[str, dict]):
        """
        Generates a pandas.Series object index by link ids, with data stored on the links under `key`
        :param key: either a string e.g. 'modes', or if accessing nested information, a dictionary
            e.g. {'attributes': {'osm:way:name': 'text'}}
        :return: pandas.Series
        """
        return pd.Series(graph_operations.get_attribute_data_under_key(self.links(), key))

    def link_attribute_data_under_keys(self, keys: list, index_name=None):
        """
        Generates a pandas.DataFrame object index by link ids, with data stored on the links under `key`
        :param keys: list of either a string e.g. 'modes', or if accessing nested information, a dictionary
            e.g. {'attributes': {'osm:way:name': 'text'}}
        :param index_name: optional, gives the index_name to dataframes index
        :return: pandas.DataFrame
        """
        df = None
        for key in keys:
            if isinstance(key, dict):
                # consolidate nestedness to get a name for the column
                name = str(key)
                name = name.replace('{', '').replace('}', '').replace("'", '').replace(' ', ':')
            else:
                name = key

            col_series = self.link_attribute_data_under_key(key)
            col_series.name = name

            if df is not None:
                df = df.merge(pd.DataFrame(col_series), left_index=True, right_index=True, how='outer')
            else:
                df = pd.DataFrame(col_series)
        if index_name:
            df.index = df.index.set_names([index_name])
        return df

    def add_node(self, node: Union[str, int], attribs: dict = None):
        if attribs is not None:
            self.graph.add_node(node, **attribs)
        else:
            self.graph.add_node(node)
        self.change_log.add(object_type='node', object_id=node, object_attributes=attribs)
        logging.info('Added Node with index `{}` and data={}'.format(node, attribs))
        return node

    def add_edge(self, u: Union[str, int], v: Union[str, int], multi_edge_idx: int = None, attribs: dict = None):
        """
        Adds an edge between u and v. If an edge between u and v already exists, adds an additional one. Generates
        link id. If you already have a link id, use the method to add_link.
        :param u: node in the graph
        :param v: node in the graph
        :param multi_edge_idx: you can specify which multi index to use if there are other edges between u and v.
        Will generate new index if already used.
        :param attribs:
        :return:
        """
        link_id = self.generate_index_for_edge()
        self.add_link(link_id, u, v, multi_edge_idx, attribs)
        logging.info('Added edge from `{}` to `{}` with link_id `{}`'.format(u, v, link_id))
        return link_id

    def add_link(self, link_id: Union[str, int], u: Union[str, int], v: Union[str, int], multi_edge_idx: int = None,
                 attribs: dict = None):
        """
        Adds an link between u and v with id link_id, if available. If a link between u and v already exists,
        adds an additional one.
        :param link_id:
        :param u: node in the graph
        :param v: node in the graph
        :param multi_edge_idx: you can specify which multi index to use if there are other edges between u and v.
        Will generate new index if already used.
        :param attribs:
        :return:
        """
        if link_id in self.link_id_mapping:
            new_link_id = self.generate_index_for_edge()
            logging.warning('This link_id=`{}` already exists. Generated a new unique_index: `{}`'.format(
                link_id, new_link_id))
            link_id = new_link_id

        if multi_edge_idx is None:
            multi_edge_idx = self.graph.new_edge_key(u, v)
        if self.graph.has_edge(u, v, multi_edge_idx):
            old_idx = multi_edge_idx
            multi_edge_idx = self.graph.new_edge_key(u, v)
            logging.warning('Changing passed multi_edge_idx: `{}` as there already exists an edge stored under that '
                            'index. New multi_edge_idx: `{}`'.format(old_idx, multi_edge_idx))
        if not isinstance(multi_edge_idx, int):
            raise RuntimeError('Multi index key needs to be an integer')

        self.link_id_mapping[link_id] = {'from': u, 'to': v, 'multi_edge_idx': multi_edge_idx}
        compulsory_attribs = {'from': u, 'to': v, 'id': link_id}
        if attribs is None:
            attribs = compulsory_attribs
        else:
            attribs = {**attribs, **compulsory_attribs}
        self.graph.add_edge(u, v, key=multi_edge_idx, **attribs)
        self.change_log.add(object_type='link', object_id=link_id, object_attributes=attribs)
        logging.info('Added Link with index {}, from node:{} to node:{}, under multi-index:{}, and data={}'.format(
            link_id, u, v, multi_edge_idx, attribs))
        return link_id

    def reindex_node(self, node_id, new_node_id):
        # check if new id is already occupied
        if self.node_id_exists(new_node_id):
            new_node_id = self.generate_index_for_node()
        # extract link ids which will be affected byt the node relabel and change the from anf to attributes
        from_links = graph_operations.extract_links_on_edge_attributes(self, conditions={'from': node_id})
        self.apply_attributes_to_links(from_links, {'from': new_node_id})
        to_links = graph_operations.extract_links_on_edge_attributes(self, conditions={'to': node_id})
        self.apply_attributes_to_links(to_links, {'to': new_node_id})
        # update link_id_mapping
        for k in from_links:
            self.link_id_mapping[k]['from'] = new_node_id
        for k in to_links:
            self.link_id_mapping[k]['to'] = new_node_id

        new_attribs = deepcopy(self.node(node_id))
        new_attribs['id'] = new_node_id
        self.change_log.modify(object_type='node', old_id=node_id, new_id=new_node_id,
                               old_attributes=self.node(node_id), new_attributes=new_attribs)
        self.apply_attributes_to_node(node_id, new_attribs)
        self.graph = nx.relabel_nodes(self.graph, {node_id: new_node_id})
        logging.info('Changed Node index from {} to {}'.format(node_id, new_node_id))

    def reindex_link(self, link_id, new_link_id):
        # check if new id is already occupied
        if self.link_id_exists(new_link_id):
            new_link_id = self.generate_index_for_edge()
        new_attribs = deepcopy(self.link(link_id))
        new_attribs['id'] = new_link_id
        self.change_log.modify(object_type='link', old_id=link_id, new_id=new_link_id,
                               old_attributes=self.link(link_id), new_attributes=new_attribs)
        self.apply_attributes_to_link(link_id, new_attribs)
        self.link_id_mapping[new_link_id] = self.link_id_mapping[link_id]
        del self.link_id_mapping[link_id]
        logging.info('Changed Link index from {} to {}'.format(link_id, new_link_id))

    def apply_attributes_to_node(self, node_id, new_attributes):
        """
        Adds, or changes if already present, the attributes in new_attributes. Doesn't replace the dictionary
        stored at the node currently so no data is lost, unless it is being overwritten.
        :param node_id: node id to perform the change to
        :param new_attributes: dictionary of data to add/replace if present
        :return:
        """
        old_attributes = deepcopy(self.node(node_id))

        # check if change is to nested part of node data
        if any(isinstance(v, dict) for v in new_attributes.values()):
            new_attributes = persistence.set_nested_value(old_attributes, new_attributes)
        else:
            new_attributes = {**old_attributes, **new_attributes}

        self.change_log.modify(
            object_type='node',
            old_id=node_id,
            new_id=node_id,
            old_attributes=self.node(node_id),
            new_attributes=new_attributes)
        nx.set_node_attributes(self.graph, {node_id: new_attributes})
        logging.info('Changed Node attributes under index: {}'.format(node_id))

    def apply_attributes_to_nodes(self, nodes: list, new_attributes: dict):
        """
        Adds, or changes if already present, the attributes in new_attributes. Doesn't replace the dictionary
        stored at the node currently so no data is lost, unless it is being overwritten.
        :param nodes: list of node ids
        :param new_attributes: dictionary of data to add/replace if present
        :return:
        """
        [self.apply_attributes_to_node(node, new_attributes) for node in nodes]

    def apply_attributes_to_link(self, link_id, new_attributes):
        """
        Adds, or changes if already present, the attributes in new_attributes. Doesn't replace the dictionary
        stored at the link currently so no data is lost, unless it is being overwritten.
        :param link_id: link id to perform the change to
        :param new_attributes: dictionary of data to add/replace if present
        :return:
        """
        u, v = self.link_id_mapping[link_id]['from'], self.link_id_mapping[link_id]['to']
        multi_idx = self.link_id_mapping[link_id]['multi_edge_idx']
        old_attributes = deepcopy(self.link(link_id))

        # check if change is to nested part of node data
        if any(isinstance(v, dict) for v in new_attributes.values()):
            new_attributes = persistence.set_nested_value(old_attributes, new_attributes)
        else:
            new_attributes = {**old_attributes, **new_attributes}

        self.change_log.modify(
            object_type='link',
            old_id=link_id,
            new_id=link_id,
            old_attributes=self.link(link_id),
            new_attributes=new_attributes)

        nx.set_edge_attributes(self.graph, {(u, v, multi_idx): new_attributes})
        logging.info('Changed Link attributes under index: {}'.format(link_id))

    def apply_attributes_to_links(self, links: list, new_attributes: dict):
        """
        Adds, or changes if already present, the attributes in new_attributes. Doesn't replace the dictionary
        stored at the link currently so no data is lost, unless it is being overwritten.
        :param links: list of link ids
        :param new_attributes: dictionary of data to add/replace if present
        :return:
        """
        [self.apply_attributes_to_link(link, new_attributes) for link in links]

    def remove_node(self, node_id):
        """
        Removes the node n and all adjacent edges
        :param node_id:
        :return:
        """
        self.change_log.remove(object_type='node', object_id=node_id, object_attributes=self.node(node_id))
        self.graph.remove_node(node_id)
        logging.info('Removed Node under index: {}'.format(node_id))

    def remove_nodes(self, nodes):
        """
        Removes several nodes and all adjacent edges
        :param nodes:
        :return:
        """
        [self.remove_node(node) for node in nodes]

    def remove_link(self, link_id):
        """
        Removes the multi edge pertaining to link given
        :param link_id:
        :return:
        """
        self.change_log.remove(object_type='link', object_id=link_id, object_attributes=self.link(link_id))
        u, v = self.link_id_mapping[link_id]['from'], self.link_id_mapping[link_id]['to']
        multi_idx = self.link_id_mapping[link_id]['multi_edge_idx']
        self.graph.remove_edge(u, v, multi_idx)
        del self.link_id_mapping[link_id]
        logging.info('Removed Link under index: {}'.format(link_id))

    def remove_links(self, links):
        """
        Removes the multi edges pertaining to links given
        :param links:
        :return:
        """
        [self.remove_link(link) for link in links]

    def number_of_multi_edges(self, u, v):
        """
        number of multi edges on edge from u to v
        :param u: from node
        :param v: to node
        :return:
        """
        if self.graph.has_edge(u, v):
            return len(self.graph.edges(u, v))
        else:
            return 0

    def nodes(self):
        """
        :return:  Iterator through each node and its attrib (two-tuple)
        """
        for id, attrib in self.graph.nodes(data=True):
            yield id, attrib

    def node(self, node_id):
        """
        :return:  attribs of the 'node_id'
        """
        return self.graph.nodes[node_id]

    def edges(self):
        """
        :return: Iterator through each edge's from, to nodes and its attrib (three-tuple)
        """
        for u, v, attrib in self.graph.edges(data=True):
            yield u, v, attrib

    def edge(self, u, v):
        """
        :param u: from node of self.graph
        :param v: to node of self.graph
        :return:  attribs of the edge from u to  v
        """
        return dict(self.graph[u][v])

    def links(self):
        """
        :return: Iterator through each link id its attrib (two-tuple)
        """
        for link_id in self.link_id_mapping.keys():
            yield link_id, self.link(link_id)

    def link(self, link_id):
        """
        :param link_id:
        :return:
        """
        u, v = self.link_id_mapping[link_id]['from'], self.link_id_mapping[link_id]['to']
        multi_idx = self.link_id_mapping[link_id]['multi_edge_idx']
        return dict(self.graph[u][v][multi_idx])

    def services(self):
        """
        Iterator returning services
        :return:
        """
        for id, service in self.schedule.services.items():
            yield service

    def initiate_crs_transformer(self, epsg):
        self.epsg = epsg
        if epsg != 'epsg:4326':
            self.transformer = Transformer.from_proj(Proj(epsg), Proj('epsg:4326'))
        else:
            self.transformer = None

    def read_matsim_network(self, path, epsg):
        self.initiate_crs_transformer(epsg)
        self.graph, self.link_id_mapping, duplicated_nodes, duplicated_links = \
            matsim_reader.read_network(path, self.transformer)

        for node_id, duplicated_node_attribs in duplicated_nodes.items():
            for duplicated_node_attrib in duplicated_node_attribs:
                self.change_log.remove(
                    object_type='node',
                    object_id=node_id,
                    object_attributes=duplicated_node_attrib
                )
        for link_id, reindexed_duplicated_links in duplicated_links.items():
            for duplicated_link in reindexed_duplicated_links:
                self.change_log.modify(
                    object_type='link',
                    old_id=link_id,
                    old_attributes=self.link(duplicated_link),
                    new_id=duplicated_link,
                    new_attributes=self.link(duplicated_link)
                )

    def read_matsim_schedule(self, path, epsg=None):
        if epsg is None:
            assert self.epsg
            assert self.transformer
        elif self.epsg and (epsg != self.epsg):
            raise RuntimeError('The epsg you have given {} does not match the epsg currently stored for this network '
                               '{}. Make sure you pass files with matching coordinate system.'.format(epsg, self.epsg))
        else:
            self.initiate_crs_transformer(epsg)
        self.schedule.read_matsim_schedule(path, self.epsg)

    def node_id_exists(self, node_id):
        if node_id in [i for i, attribs in self.nodes()]:
            logging.warning('This node_id={} already exists.'.format(node_id))
            return True
        return False

    def generate_index_for_node(self, avoid_keys: Union[list, set] = None):
        existing_keys = set([i for i, attribs in self.nodes()])
        if avoid_keys:
            existing_keys = existing_keys | set(avoid_keys)
        try:
            id = max([int(i) for i in existing_keys]) + 1
        except ValueError:
            id = len(existing_keys) + 1
        if (id in existing_keys) or (str(id) in existing_keys):
            id = uuid.uuid4()
        logging.info('Generated node id {}.'.format(id))
        return str(id)

    def link_id_exists(self, link_id):
        if link_id in self.link_id_mapping:
            logging.warning('This link_id={} already exists.'.format(link_id))
            return True
        return False

    def generate_index_for_edge(self, avoid_keys: Union[list, set] = None):
        existing_keys = set(self.link_id_mapping.keys())
        if avoid_keys:
            existing_keys = existing_keys | set(avoid_keys)
        try:
            id = max([int(i) for i in existing_keys]) + 1
        except ValueError:
            id = len(existing_keys) + 1
        if (id in existing_keys) or (str(id) in existing_keys):
            id = uuid.uuid4()
        logging.info('Generated link id {}.'.format(id))
        return str(id)

    def index_graph_edges(self):
        logging.warning('This method clears the existing link_id indexing')
        self.link_id_mapping = {}
        i = 0
        for u, v, multi_edge_idx in self.graph.edges:
            self.link_id_mapping[str(i)] = {'from': u, 'to': v, 'multi_edge_idx': multi_edge_idx}
            i += 1

    def write_to_matsim(self, output_dir):
        persistence.ensure_dir(output_dir)
        matsim_xml_writer.write_to_matsim_xmls(output_dir, self)
        self.change_log.export(os.path.join(output_dir, 'change_log.csv'))


class Schedule:
    """
    Takes services and stops_mapping in the correct format and provides method and structure for transit schedules

    Parameters
    ----------
    :param services: list of Service class objects
    :param stops_mapping: {'stop_id' : [service_id, service_id_2, ...]} for extracting services given a stop_id
    :param epsg: 'epsg:12345', projection for the schedule (each stop has its own epsg)
    """

    def __init__(self, services: List[Service] = None, epsg=''):
        super().__init__()
        if services is None:
            self.services = {}
            self.stops_mapping = pd.DataFrame(columns=['stop_id', 'stop', 'service_id', 'service'])
        else:
            assert epsg != '', 'You need to specify the coordinate system for the schedule'
            self.services = {}
            for service in services:
                self.services[service.id] = service
            self.build_stops_mapping()
        self.epsg = epsg
        self.transformer = ''
        self.minimal_transfer_times = {}

    def __nonzero__(self):
        return self.services

    def __getitem__(self, service_id):
        return self.services[service_id]

    def __contains__(self, service_id):
        return service_id in self.services

    def __repr__(self):
        return "<{} instance at {}: with {} services>".format(
            self.__class__.__name__,
            id(self),
            len(self))

    def __str__(self):
        return self.info()

    def __len__(self):
        return len(self.services)

    def __add__(self, other):
        """
        takes the services dictionary and adds them to the current
        services stored in the Schedule. Have to be separable!
        I.e. the keys in services cannot overlap with the ones already
        existing (TODO: add merging complicated schedules, parallels to the merging gtfs work)
        :param services: (see tests for the dict schema)
        :return:
        """
        if not self.is_separable_from(other):
            # have left and right indicies
            raise NotImplementedError('This method only supports adding non overlapping services.')
        elif self.epsg != other.epsg:
            other.reproject(self.epsg)
        return self.__class__(
            services=list(self.services.values()) + list(other.services.values()),
            epsg=self.epsg)

    def is_separable_from(self, other):
        return set(other.services.keys()) & set(self.services.keys()) == set()

    def print(self):
        return self.info()

    def info(self):
        return 'Number of services: {}\nNumber of unique routes: {}'.format(self.__len__(), self.number_of_routes())

    def reproject(self, new_epsg):
        """
        Changes projection of the schedule to new_epsg
        :param new_epsg: 'epsg:1234'
        :return:
        """
        old_to_new_transformer = Transformer.from_proj(Proj(self.epsg), Proj(new_epsg))
        # need to go through all instances of all the stops
        for service_id, route in self.routes():
            for stop in route.stops:
                stop.reproject(new_epsg, old_to_new_transformer)
        self.initiate_crs_transformer(new_epsg)

    def service_ids(self):
        return list(self.services.keys())

    def routes(self):
        """
        Iterator for routes in the schedule, returns service_id and a route
        """
        for service_id, service in self.services.items():
            for route in service.routes:
                yield service_id, route

    def number_of_routes(self):
        return len([r for id, r in self.routes()])

    def stops(self):
        """
        Iterator for stops_mapping in the schedule, returns two-tuple: stop_id and the Stop object
        """
        all_stops = set()
        for service in self.services.values():
            all_stops = all_stops | set(service.stops())
        for stop in all_stops:
            yield stop.id, stop

    def build_stops_mapping(self):
        service_to_stops = {}
        for service_id, service in self.services.items():
            service_to_stops[service_id] = [stop.id for stop in service.stops()]

        # ze old switcheroo
        self.stops_mapping = {}
        for key, value in service_to_stops.items():
            for item in value:
                if item in self.stops_mapping:
                    self.stops_mapping[item].append(key)
                else:
                    self.stops_mapping[item] = [key]

    def initiate_crs_transformer(self, epsg):
        self.epsg = epsg
        if epsg != 'epsg:4326':
            self.transformer = Transformer.from_proj(Proj(epsg), Proj('epsg:4326'))
        else:
            self.transformer = None

    def read_matsim_schedule(self, path, epsg):
        self.initiate_crs_transformer(epsg)
        services, self.minimal_transfer_times = matsim_reader.read_schedule(path, epsg)
        for service in services:
            self.services[service.id] = service
        self.build_stops_mapping()

    def read_gtfs_schedule(self, path, day):
        """
        Reads from GTFS. The resulting services will not have route lists. Assumes to be in lat lon epsg:4326
        :param path: to GTFS folder or a zip file
        :param day: 'YYYYMMDD' to use form the gtfs
        :return:
        """
        self.initiate_crs_transformer(epsg='epsg:4326')
        services = gtfs_reader.read_to_list_of_service_objects(path, day)
        for service in services:
            self.services[service.id] = service
        self.build_stops_mapping()

    def write_to_matsim(self, output_dir):
        persistence.ensure_dir(output_dir)
        vehicles = matsim_xml_writer.write_matsim_schedule(output_dir, self)
        matsim_xml_writer.write_vehicles(output_dir, vehicles)
