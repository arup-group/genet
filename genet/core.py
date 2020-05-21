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
            self.schedule.info()
        )

    def __str__(self):
        return self.info()

    def print(self):
        return self.info()

    def info(self):
        pass

    def nodes(self, node_id=None):
        if node_id is None:
            return self.graph.nodes
        else:
            return self.graph.nodes[node_id]

    def edges(self, link_id=None):
        if link_id is None:
            return self.link_id_mapping.keys()
        else:
            u, v = self.link_id_mapping[link_id]['from'], self.link_id_mapping[link_id]['to']
            return dict(self.graph[u][v])

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
    def __init__(self, services: dict = None, stops: dict = None, epsg = ''):
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
            return self.__class__({**self.services, **other.services}, stops={**self.stops, **other.stops}, epsg=self.epsg)

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
        self.services, self.transit_stop_id_mapping = matsim_reader.read_schedule(path, self.transformer)
