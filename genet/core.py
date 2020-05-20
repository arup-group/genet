import networkx as nx
from pyproj import Proj, Transformer
from genet.inputs_handler import matsim_reader


class Network:
    def __init__(self):
        self.graph = nx.MultiDiGraph()
        self.spatial_tree = SpatialTree()
        self.schedule = Schedule()
        self.modes = []

        self.epsg = ''
        self.transformer = ''

        self.node_id_mapping = {}
        self.link_id_mapping = {}
        self.transit_stop_id_mapping = {}

    def __repr__(self):
        return "<{} instance at {}: with \ngraph: {} and \nschedule {}".format(
            self.__class__.__name__,
            id(self),
            nx.info(self.graph),
            self.schedule.summarise()
        )

    def nodes(self, node=None):
        if node is None:
            return self.graph.nodes
        else:
            return self.graph.nodes[node]

    def edges(self, u=None, v=None):
        if (u is None) and (v is None):
            return self.graph[u][v]
        else:
            return self.graph[u][v]

    def initiate_crs_transformer(self, epsg):
        self.epsg = epsg
        self.transformer = Transformer.from_proj(Proj(init=epsg), Proj(init='epsg:4326'))

    def read_matsim_network(self, path, epsg):
        self.initiate_crs_transformer(epsg)
        self.graph, self.node_id_mapping, self.link_id_mapping = matsim_reader.read_network(path, self.transformer)

    def read_matsim_schedule(self, path, epsg=None):
        if epsg is None:
            assert self.epsg
            assert self.transformer
        elif self.epsg and (epsg != self.epsg):
                raise RuntimeError('The epsg you have given {} does not match the epsg currently stored for this network '
                                   '{}. Make sure you pass files with matching coordinate system.'.format(
                    epsg, self.epsg
                ))
        else:
            self.initiate_crs_transformer(epsg)
        self.schedule.read_matsim_schedule(path, self.epsg)


class SpatialTree(nx.DiGraph):
    """
    Class which represents a nx.MultiDiGraph as a spatial tree
    hierarchy based on s2 cell levels
    """
    def __init__(self):
        super().__init__()


class Schedule():
    def __init__(self, services=None):
        super().__init__()
        if services is None:
            self.services = {}
        else:
            self.services = services
        self.epsg = ''
        self.transformer = ''

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
        return self.summarise()

    def __len__(self):
        return len(self.services)

    def services(self):
        return list(self.services.keys())

    def routes(self):
        """
        Iterator for routes in the schedule, returns service_id and a route
        """
        for service_id, service in self.services.items():
            for route in service:
                yield service_id, route

    def stops(self):
        """
        Iterator for stops in the schedule, returns ...
        """
        pass

    def initiate_crs_transformer(self, epsg):
        self.epsg = epsg
        self.transformer = Transformer.from_proj(Proj(init=epsg), Proj(init='epsg:4326'))

    def read_matsim_schedule(self, path, epsg):
        self.initiate_crs_transformer(epsg)
        schedule, self.transit_stop_id_mapping = matsim_reader.read_schedule(path, self.transformer)
        self.add_services(schedule)

    def add_services(self, services: dict):
        """
        takes the services dictionary and adds them to the current
        servicess stored in the Schedule. Have to be separable!
        I.e. the keys in services cannot overlap with the ones already
        existing (TODO)
        :param services: (see tests for the dict schema)
        :return:
        """
        if set(services.keys()) & set(self.services.keys()) != set():
            raise NotImplementedError('This method only supports adding non overlapping services')
        else:
            self.services = {**self.services, **services}

    def summarise(self):
        pass