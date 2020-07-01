from typing import Union, Dict, List
from pyproj import Transformer
from genet.utils import spatial
import networkx as nx
from genet.utils import plot

# number of decimal places to consider when comparing lat lons
SPATIAL_TOLERANCE = 8


class Stop:
    """
    A transit stop that features in a Route object

    Parameters
    ----------
    :param id: unique identifier
    :param x: x coordinate or lat if using 'epsg:4326'
    :param y: y coordinate or lon if using 'epsg:4326'
    :param epsg: 'epsg:12345'
    :param transformer: optional but makes things MUCH faster if you're reading through a lot of stops in the same
            projection
    """

    def __init__(self, id: Union[str, int], x: Union[str, int, float], y: Union[str, int, float], epsg: str,
                 transformer: Transformer = None):
        self.id = id
        self.x = float(x)
        self.y = float(y)
        self.initiate_crs_transformer(epsg, transformer)

        if self.epsg == 'epsg:4326':
            self.lat, self.lon = float(x), float(y)
        else:
            self.lat, self.lon = spatial.change_proj(x, y, self.transformer)

        self.additional_attributes = []

    def __eq__(self, other):
        return (self._round_lat() == other._round_lat()) and (self._round_lon() == other._round_lon())

    def __hash__(self):
        return hash((self.id, self._round_lat(), self._round_lon()))

    def __repr__(self):
        return "<{} instance at {}: in {}>".format(
            self.__class__.__name__,
            id(self),
            self.epsg)

    def __str__(self):
        return self.info()

    def _round_lat(self):
        return round(self.lat, SPATIAL_TOLERANCE)

    def _round_lon(self):
        return round(self.lon, SPATIAL_TOLERANCE)

    def print(self):
        print(self.info())

    def info(self):
        return '{} ID: {}\nProjection: {}\nLat, Lon: {}, {}'.format(
            self.__class__.__name__, self.id, self.epsg, self._round_lat(), self._round_lon())

    def initiate_crs_transformer(self, epsg, transformer):
        self.epsg = epsg
        if transformer is None:
            if epsg != 'epsg:4326':
                self.transformer = Transformer.from_crs(epsg, 'epsg:4326')
            else:
                self.transformer = None
        else:
            self.transformer = transformer

    def reproject(self, new_epsg, transformer: Transformer = None):
        """
        Changes projection of a stop. If doing many stops, it's much quicker to pass the transformer as well as epsg.
        :param new_epsg: 'epsg:12345'
        :param transformer:
        :return:
        """
        if transformer is None:
            transformer = Transformer.from_crs(self.epsg, new_epsg)
        self.x, self.y = spatial.change_proj(self.x, self.y, transformer)

        self.epsg = new_epsg
        self.transformer = Transformer.from_crs(self.epsg, 'epsg:4326')

    def add_additional_attributes(self, attribs: dict):
        """
        adds attributes defined by keys of the attribs dictionary with values of the corresponding values
        ignores keys: 'id', 'x', 'y'
        :param attribs:
        :return:
        """
        for k, v in attribs.items():
            if k not in self.__dict__:
                setattr(self, k, v)
                self.additional_attributes.append(k)

    def iter_through_additional_attributes(self):
        for attr, value in self.__dict__.items():
            if attr in self.additional_attributes:
                yield attr, value

    def is_exact(self, other):
        same_id = self.id == other.id
        same_lat = (round(self.lat, SPATIAL_TOLERANCE) == round(other.lat, SPATIAL_TOLERANCE))
        same_lon = (round(self.lon, SPATIAL_TOLERANCE) == round(other.lon, SPATIAL_TOLERANCE))
        return same_id and same_lat and same_lon

    def isin_exact(self, stops: list):
        for other in stops:
            if self.is_exact(other):
                return True
        return False

    def has_linkRefId(self):
        return 'linkRefId' in self.__dict__

    def has_id(self):
        return self.id


class Route:
    """
    A Route is an object which contains information about the trips, times and offsets, mode and name of the route which
    forms a part of a Service.

    Parameters
    ----------
    :param route_short_name: route's short name
    :param mode: mode
    :param stops: list of Stop class objects
    :param trips: dictionary {'trip_id' : 'HH:MM:SS' - departure time from first stop}
    :param arrival_offsets: list of 'HH:MM:SS' temporal offsets for each of the stops_mapping
    :param departure_offsets: list of 'HH:MM:SS' temporal offsets for each of the stops_mapping
    :param route: optional, network link_ids traversed by the vehicles in this Route instance
    :param route_long_name: optional, verbose name for the route if exists
    :param id: optional, unique identifier for the route if available, if not given, at the time of writing outputs to
        matsim network files, an id will be generated from the service id the route belongs to and the index of the
        route in the list of routes of that service.
    :param await_departure: optional, list of bools of length stops param, whether to await departure at each stop
    """

    def __init__(self, route_short_name: str, mode: str, stops: List[Stop], trips: Dict[str, str],
                 arrival_offsets: List[str], departure_offsets: List[str], route: list = None,
                 route_long_name: str = '', id: str = '', await_departure: list = None):
        self.route_short_name = route_short_name
        self.mode = mode.lower()
        self.stops = stops
        self.trips = trips
        self.arrival_offsets = arrival_offsets
        self.departure_offsets = departure_offsets
        self.route_long_name = route_long_name
        self.id = id
        if route is None:
            self.route = []
        else:
            self.route = route
        if await_departure is None:
            self.await_departure = []
        else:
            self.await_departure = await_departure

    def __eq__(self, other):
        same_route_name = self.route_short_name == other.route_short_name
        same_mode = self.mode.lower() == other.mode.lower()
        same_stops = self.stops == other.stops
        return same_route_name and same_mode and same_stops

    def __repr__(self):
        return "<{} instance at {}: with {} stops and {} trips>".format(
            self.__class__.__name__,
            id(self),
            len(self.stops),
            len(self.trips))

    def __str__(self):
        return self.info()

    def print(self):
        print(self.info())

    def info(self):
        return '{} ID: {}\nName: {}\nNumber of stops: {}\nNumber of trips: {}'.format(
            self.__class__.__name__, self.id, self.route_short_name, len(self.stops), len(self.trips))

    def plot(self, show=True, save=False, output_dir=''):
        route_graph = self.build_graph()
        if self.stops:
            return plot.plot_graph(
                nx.MultiGraph(route_graph),
                filename='route_{}_graph'.format(self.id),
                show=show,
                save=save,
                output_dir=output_dir,
                e_c='#EC7063'
            )

    def find_epsg(self):
        for stop in self.stops:
            return stop.epsg
        return None

    def is_exact(self, other):
        same_route_name = self.route_short_name == other.route_short_name
        same_mode = self.mode.lower() == other.mode.lower()
        same_stops = self.stops == other.stops
        same_trips = self.trips == other.trips
        same_arrival_offsets = self.arrival_offsets == other.arrival_offsets
        same_departure_offsets = self.departure_offsets == other.departure_offsets

        statement = same_route_name and same_mode and same_stops and same_trips and same_arrival_offsets \
            and same_departure_offsets
        return statement

    def isin_exact(self, routes: list):
        for other in routes:
            if self.is_exact(other):
                return True
        return False

    def build_graph(self):
        route_graph = nx.DiGraph(name='Route graph', crs={'init': self.find_epsg()})
        route_nodes = [(stop.id, {'x': stop.x, 'y': stop.y, 'lat': stop.lat, 'lon': stop.lon}) for stop in self.stops]
        route_graph.add_nodes_from(route_nodes)
        stop_edges = [(from_stop.id, to_stop.id) for from_stop, to_stop in zip(self.stops[:-1], self.stops[1:])]
        route_graph.add_edges_from(stop_edges)
        return route_graph

    def is_strongly_connected(self):
        g = self.build_graph()
        if nx.number_strongly_connected_components(g) == 1:
            return True
        return False

    def has_self_loops(self):
        """
        means that there are two consecutive stops that are the same
        :return:
        """
        g = self.build_graph()
        return list(nx.nodes_with_selfloops(g))

    def has_more_than_one_stop(self):
        if len(self.stops) > 1:
            return True
        return False

    def has_network_route(self):
        return self.route

    def has_id(self):
        return self.id

    def is_valid_route(self):
        return self.has_more_than_one_stop() and bool(self.has_network_route()) and bool(not self.has_self_loops())


class Service:
    """
    A Service is an object containing unique routes pertaining to the same public transit service

    Parameters
    ----------
    :param services: dictionary of Service class objects {'service_id' : Service}
    :param stops_mapping: dictionary of Stop class objects {'stop_id': Stop} which pertain to the Services
    :param epsg: 'epsg:12345'
    """

    def __init__(self, id: str, routes: List[Route]):
        self.id = id
        self.routes = routes
        # a service inherits a name from the first route in the list (all route names are still accessible via each
        # route object
        if routes:
            if routes[0].route_short_name:
                name = routes[0].route_short_name
            else:
                name = routes[0].route_long_name
            self.name = str(name)
        else:
            self.name = ''

    def __eq__(self, other):
        return self.id == other.id

    def __repr__(self):
        return "<{} instance at {}: with {} routes>".format(
            self.__class__.__name__,
            id(self),
            len(self))

    def __str__(self):
        return self.info()

    def __len__(self):
        return len(self.routes)

    def print(self):
        print(self.info())

    def info(self):
        return '{} ID: {}\nName: {}\nNumber of routes: {}\nNumber of unique stops: {}'.format(
            self.__class__.__name__, self.id, self.name, len(self), len(list(self.stops())))

    def plot(self, show=True, save=False, output_dir=''):
        service_graph = self.build_graph()
        if self.stops:
            return plot.plot_graph(
                nx.MultiGraph(service_graph),
                filename='service_{}_graph'.format(self.id),
                show=show,
                save=save,
                output_dir=output_dir,
                e_c='#EC7063'
            )

    def find_epsg(self):
        for stop in self.stops():
            return stop.epsg
        return None

    def is_exact(self, other):
        return (self.id == other.id) and (self.routes == other.routes)

    def isin_exact(self, services: list):
        for other in services:
            if self.is_exact(other):
                return True
        return False

    def stops(self):
        """
        Iterable returns unique stops for all routes within the service
        :return:
        """
        all_stops = set()
        for route in self.routes:
            all_stops = all_stops | set(route.stops)
        for stop in all_stops:
            yield stop

    def build_graph(self):
        service_graph = nx.DiGraph(name='Service graph', crs={'init': self.find_epsg()})
        for route in self.routes:
            service_graph = nx.compose(route.build_graph(), service_graph)
        return service_graph

    def is_strongly_connected(self):
        g = self.build_graph()
        if nx.number_strongly_connected_components(g) == 1:
            return True
        return False

    def has_self_loops(self):
        g = self.build_graph()
        return list(nx.nodes_with_selfloops(g))

    def validity_of_routes(self):
        return [route.is_valid_route() for route in self.routes]

    def has_valid_routes(self):
        return all(self.validity_of_routes())

    def invalid_routes(self):
        return [route for route in self.routes if not route.is_valid_route()]

    def has_uniquely_indexed_routes(self):
        indices = set([route.id for route in self.routes])
        if len(indices) != len(self.routes):
            return False
        return True

    def has_id(self):
        return self.id

    def is_valid_service(self):
        return self.has_valid_routes() and self.has_uniquely_indexed_routes()
