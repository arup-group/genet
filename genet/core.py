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

    def initiate_crs_transformer(self, epsg):
        self.epsg = epsg
        self.transformer = Transformer.from_proj(Proj(init=epsg), Proj(init='epsg:4326'))

    def read_matsim_network(self, path, epsg):
        self.initiate_crs_transformer(epsg)
        self.graph, self.node_id_mapping, self.link_id_mapping = matsim_reader.read_network(path, self.transformer)

    def read_matsim_schedule(self, path):
        if not self.link_id_mapping:
            raise RuntimeError('You need to read the network file first. The schedule refers to its edges')
        schedule, self.transit_stop_id_mapping = matsim_reader.read_schedule(path, self.transformer)
        # t = matsim_reader.update_transit_stops(self.transit_stop_id_mapping, self.link_id_mapping)
        self.schedule.add_services(schedule)


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

    def __getitem__(self, service_id):
        return self.services[service_id]

    def __contains__(self, service_id):
        return service_id in self.services

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

    def routes(self):
        """
        Iterator for routes in the schedule, returns ...
        """
        pass

    def stops(self):
        """
        Iterator for stops in the schedule, returns ...
        """
        pass