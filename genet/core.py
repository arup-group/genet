import networkx as nx
import pandas as pd
import uuid
import warnings
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


class Network:
    def __init__(self):
        self.graph = nx.MultiDiGraph()
        self.schedule = Schedule()
        self.change_log = ChangeLog()
        self.spatial_tree = spatial.SpatialTree()
        self.modes = []

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

    def print(self):
        return self.info()

    def info(self):
        return "Graph info: {} \nSchedule info: {}".format(
            nx.info(self.graph),
            self.schedule.info()
        )

    def node_attribute_summary(self, data=False):
        """
        Is expensive. Parses through data stored on nodes and gives a summary tree of the data stored on the nodes.
        If data is True, shows also up to 5 unique values stored under such keys.
        :param data: bool, False by default
        :return:
        """
        root = graph_operations.get_attribute_schema(self.nodes(), data=data)
        graph_operations.render_tree(root, data)

    def link_attribute_summary(self, data=False):
        """
        Is expensive. Parses through data stored on links and gives a summary tree of the data stored on the links.
        If data is True, shows also up to 5 unique values stored under such keys.
        :param data: bool, False by default
        :return:
        """
        root = graph_operations.get_attribute_schema(self.links(), data=data)
        graph_operations.render_tree(root, data)

    def add_node(self, node: Union[str, int], attribs: dict = None):
        if attribs is not None:
            self.graph.add_node(node, **attribs)
        else:
            self.graph.add_node(node)
        self.change_log.add(object_type='node', object_id=node, object_attributes=attribs)

    def add_edge(self, u: Union[str, int], v: Union[str, int], attribs: dict = None):
        link_id = self.generate_index_for_edge()
        self.add_link(link_id, u, v, attribs)
        logging.info('Added edge from {} to {} with link_id {}'.format(u, v, link_id))
        return link_id

    def add_link(self, link_id: Union[str, int], u: Union[str, int], v: Union[str, int], attribs: dict = None):
        if link_id in self.link_id_mapping:
            new_link_id = self.generate_index_for_edge()
            warnings.warn('This link_id={} already exists. Generated a new unique_index: {}'.format(
                link_id, new_link_id))
            link_id = new_link_id

        self.link_id_mapping[link_id] = {'from': u, 'to': v, 'multi_edge_idx': self.number_of_multi_edges(u, v)}
        if attribs is not None:
            self.graph.add_edge(u, v, **attribs)
        else:
            self.graph.add_edge(u, v)
        self.change_log.add(object_type='link', object_id=link_id, object_attributes=attribs)

    def modify_node(self, node_id, new_attributes):
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

    def modify_nodes(self, nodes: list, new_attributes: dict):
        """
        Adds, or changes if already present, the attributes in new_attributes. Doesn't replace the dictionary
        stored at the node currently so no data is lost, unless it is being overwritten.
        :param nodes: list of node ids
        :param new_attributes: dictionary of data to add/replace if present
        :return:
        """
        for node in nodes:
            self.modify_node(node, new_attributes)

    def modify_link(self, link_id, new_attributes):
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

    def modify_links(self, links: list, new_attributes: dict):
        """
        Adds, or changes if already present, the attributes in new_attributes. Doesn't replace the dictionary
        stored at the link currently so no data is lost, unless it is being overwritten.
        :param links: list of link ids
        :param new_attributes: dictionary of data to add/replace if present
        :return:
        """
        for link in links:
            self.modify_link(link, new_attributes)

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
        self.transformer = Transformer.from_proj(Proj(init=epsg), Proj(init='epsg:4326'))

    def read_matsim_network(self, path, epsg):
        self.initiate_crs_transformer(epsg)
        self.graph, self.link_id_mapping = matsim_reader.read_network(path, self.transformer)

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

    def generate_index_for_edge(self):
        try:
            id = max([int(i) for i in self.link_id_mapping.keys()]) + 1
        except ValueError:
            id = len(self.link_id_mapping) + 1
        if (id in self.link_id_mapping) or (str(id) in self.link_id_mapping):
            id = uuid.uuid4()
        return str(id)

    def index_graph_edges(self):
        warnings.warn('This method clears the existing link_id indexing')
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
            raise NotImplementedError('This method only supports adding non overlapping services.')
        elif self.epsg != other.epsg:
            raise RuntimeError('You are merging two schedules with different coordinate systems.')
        else:
            return self.__class__(
                services=list(self.services.values()) + list(other.services.values()),
                epsg=self.epsg)

    def is_separable_from(self, other):
        return set(other.services.keys()) & set(self.services.keys()) == set()

    def print(self):
        return self.info()

    def info(self):
        return 'Number of services: {}\nNumber of unique routes: {}'.format(self.__len__(), self.number_of_routes())

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
        self.transformer = Transformer.from_proj(Proj(init=epsg), Proj(init='epsg:4326'))

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
