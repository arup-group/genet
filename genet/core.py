import networkx as nx
import uuid
import warnings
from typing import Union
from pyproj import Proj, Transformer
from genet.inputs_handler import matsim_reader, gtfs_reader
from genet.modify import ChangeLog


class Network:
    def __init__(self):
        self.graph = nx.MultiDiGraph()
        self.schedule = Schedule()
        self.change_log = ChangeLog()
        self.spatial_tree = SpatialTree()
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
        pass

    def add_node(self, node: Union[str, int], attribs: dict = None):
        if attribs is not None:
            self.graph.add_node(node, **attribs)
        else:
            self.graph.add_node(node)
        self.change_log.add(object_type = 'node', object_id = node, object_attributes = attribs)

    def add_edge(self, u: Union[str, int], v: Union[str, int], attribs: dict = None):
        link_id = self.generate_index_for_edge()
        self.add_link(link_id, u, v, attribs)

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
        self.change_log.add(object_type = 'link', object_id = link_id, object_attributes = attribs)

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
        if id not in self.link_id_mapping and str(id) not in self.link_id_mapping:
            pass
        else:
            id = uuid.uuid4()
        return str(id)

    def index_graph_edges(self):
        warnings.warn('This method clears the existing link_id indexing')
        self.link_id_mapping = {}
        i = 0
        for u, v, multi_edge_idx in self.graph.edges:
            self.link_id_mapping[str(i)] = {'from': u, 'to': v, 'multi_edge_idx': multi_edge_idx}
            i += 1


class Schedule():
    """
    Takes services and stops in the correct format and provides method and structure for transit schedules

    Parameters
    ----------
    :param services:
        {'service_id : list(of unique route services, each is a dict
                      {'route_short_name': string,
                       'mode': string,
                       'stops': list,
        # optional     'route': list of network links,
                       'trips': {'VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00': '04:40:00'},
                       'arrival_offsets': ['00:00:00', '00:02:00'],
                       'departure_offsets': ['00:00:00', '00:02:00'] }
         )})
    :param stops: spatial information for the transit stops, at least x,y attributes
        {'stop_id'  (which feature in services stops lists) : {'x': float, 'y': float x,y in given epsg}
        }
    :param epsg: 'epsg:12345'
    """

    def __init__(self, services: dict = None, stops: dict = None, epsg=''):
        super().__init__()
        if (services is None) and (stops is None):
            self.services = {}
            self.stops = {}
        elif (services is None) and (stops is not None):
            raise AssertionError('{} expects all or none of the attributes'.format(self.__class__.__name__))
        elif (services is not None) and (stops is None):
            raise AssertionError('You need to provide spatial information for the stops')
        else:
            assert epsg != '', 'You need to specify the coordinate system for the schedule'
            self.services = services
            self.stops = stops
        self.epsg = epsg
        self.transformer = ''
        # TODO minimal transfer times for MATSim schedules

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
        existing (TODO)
        :param services: (see tests for the dict schema)
        :return:
        """
        if not self.is_separable_from(other):
            raise NotImplementedError('This method only supports adding non overlapping services.')
        elif self.epsg != other.epsg:
            raise RuntimeError('You are merging two schedules with different coordinate systems.')
        else:
            return self.__class__({**self.services, **other.services}, stops={**self.stops, **other.stops},
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
            for route in service:
                yield service_id, route

    def number_of_routes(self):
        return len([r for id, r in self.routes()])

    def iter_stops(self):
        """
        Iterator for stops in the schedule, returns ...
        """
        for stop_id, attribs in self.stops.items():
            yield stop_id, attribs

    def initiate_crs_transformer(self, epsg):
        self.epsg = epsg
        self.transformer = Transformer.from_proj(Proj(init=epsg), Proj(init='epsg:4326'))

    def read_matsim_schedule(self, path, epsg):
        self.initiate_crs_transformer(epsg)
        self.services, self.stops = matsim_reader.read_schedule(path, self.transformer)

    def read_gtfs_schedule(self, path, day):
        """
        Reads from GTFS. The resulting services will not have route lists. Assumes to be in lat lon epsg:4326
        :param path: to GTFS folder or a zip file
        :param day: 'YYYYMMDD' to use form the gtfs
        :return:
        """
        self.initiate_crs_transformer(epsg='epsg:4326')
        self.services, self.stops = gtfs_reader.read_to_schedule(path, day)


class SpatialTree(nx.DiGraph):
    """
    Class which represents a nx.MultiDiGraph as a spatial tree
    hierarchy based on s2 cell levels
    """

    def __init__(self):
        super().__init__()
