from typing import Union, Dict, List
from pyproj import Transformer
import networkx as nx
import logging
from datetime import datetime
from pandas import DataFrame
import genet.utils.plot as plot
import genet.utils.spatial as spatial
import genet.utils.dict_support as dict_support
import genet.inputs_handler.matsim_reader as matsim_reader
import genet.inputs_handler.gtfs_reader as gtfs_reader
import genet.outputs_handler.matsim_xml_writer as matsim_xml_writer
import genet.utils.persistence as persistence
import genet.utils.parallel as parallel
import genet.modify.schedule as mod_schedule
import genet.use.schedule as use_schedule
import genet.validate.schedule_validation as schedule_validation
import genet.outputs_handler.geojson as gngeojson

# number of decimal places to consider when comparing lat lons
SPATIAL_TOLERANCE = 8


class ScheduleElement:
    """
    Base class for Route, Service and Schedule
    """

    def __init__(self, stops):
        self._graph = self._build_graph(stops)
        self.reference_nodes = list(self._graph.nodes())
        self.reference_edges = list(self._graph.edges())
        self.epsg = self.find_epsg()
        self._graph.graph['crs'] = {'init': self.epsg}

    def _update_graph(self, new_graph):
        self._graph = new_graph

    def stop(self, stop_id):
        return Stop(**self._graph.nodes[stop_id])

    def stops(self):
        """
        Iterable returns stops in the Schedule Element
        :return:
        """
        for s in self.reference_nodes:
            yield self.stop(s)

    def modes(self):
        edge_modes = self.graph().edges(data='modes')
        modes = set()
        for u, v, e_modes in edge_modes:
            modes |= set(e_modes)
        return list(modes)

    def mode_graph_map(self):
        mode_map = {mode: set() for mode in self.modes()}
        for _id, route in self.routes():
            mode_map[route.mode] |= set(route.reference_edges)
        return mode_map

    def _build_graph(self, stops):
        pass

    def graph(self):
        return nx.edge_subgraph(self._graph, self.reference_edges)

    def subgraph(self, edges):
        return nx.DiGraph(nx.edge_subgraph(self.graph(), edges))

    def stop_to_service_ids_map(self):
        return dict(self.graph().nodes(data='services'))

    def stop_to_route_ids_map(self):
        return dict(self.graph().nodes(data='routes'))

    def reproject(self, new_epsg, processes=1):
        """
        Changes projection of the element to new_epsg
        :param new_epsg: 'epsg:1234'
        :return:
        """
        if self.epsg != new_epsg:
            g = self.graph()

            reprojected_node_attribs = parallel.multiprocess_wrap(
                data=dict(g.nodes(data=True)),
                split=parallel.split_dict,
                apply=mod_schedule.reproj_stops,
                combine=parallel.combine_dict,
                processes=processes,
                new_epsg=new_epsg
            )
            nx.set_node_attributes(self._graph, reprojected_node_attribs)
            self.epsg = new_epsg

    def find_epsg(self):
        for n in self.reference_nodes:
            return self.stop(n).epsg
        return None


class Stop:
    """
    A transit stop that features in a Route object

    Parameters
    ----------
    :param id: unique identifier
    :param x: x coordinate or lat if using 'epsg:4326'
    :param y: y coordinate or lon if using 'epsg:4326'
    :param epsg: 'epsg:12345'
    :param transformer: pyproj.Transformer.from_crs(epsg, 'epsg:4326') optional but makes things MUCH faster if you're
    reading through a lot of stops in the same projection, all stops are mapped back to 'epsg:4326' and indexed with
    s2sphere
    """

    def __init__(self, id: Union[str, int], x: Union[str, int, float], y: Union[str, int, float], epsg: str,
                 transformer: Transformer = None, name: str = '', **kwargs):
        self.id = id
        self.x = float(x)
        self.y = float(y)
        self.epsg = epsg
        self.name = name

        if ('lat' in kwargs) and ('lon' in kwargs):
            self.lat, self.lon = kwargs['lat'], kwargs['lon']
        else:
            if self.epsg == 'epsg:4326':
                self.lat, self.lon = float(x), float(y)
            else:
                if transformer is None:
                    transformer = Transformer.from_crs(self.epsg, 'epsg:4326')
                self.lat, self.lon = spatial.change_proj(x, y, transformer)
        if 's2_id' in kwargs:
            self.s2_id = kwargs['s2_id']
        else:
            self.s2_id = spatial.grab_index_s2(lat=self.lat, lng=self.lon)

        self.additional_attributes = []
        if kwargs:
            self.add_additional_attributes(kwargs)

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
        if self.has_linkRefId():
            return '{} ID: {}\nProjection: {}\nLat, Lon: {}, {}\nlinkRefId: {}'.format(
                self.__class__.__name__, self.id, self.epsg, self._round_lat(), self._round_lon(), self.linkRefId)
        else:
            return '{} ID: {}\nProjection: {}\nLat, Lon: {}, {}'.format(
                self.__class__.__name__, self.id, self.epsg, self._round_lat(), self._round_lon())

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

    def add_additional_attributes(self, attribs: dict):
        """
        adds attributes defined by keys of the attribs dictionary with values of the corresponding values
        ignores keys: 'id', 'x', 'y'
        :param attribs:
        :return:
        """
        for k, v in attribs.items():
            if k not in self.__dict__ or not self.__dict__[k]:
                setattr(self, k, v)
                self.additional_attributes.append(k)

    def iter_through_additional_attributes(self):
        for attr_key in self.additional_attributes:
            yield attr_key, self.__dict__[attr_key]

    def additional_attribute(self, attrib_name):
        return self.__dict__[attrib_name]

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

    def has_attrib(self, attrib_name):
        return attrib_name in self.__dict__

    def has_id(self):
        return self.id


class Route(ScheduleElement):
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
        self.ordered_stops = [stop.id for stop in stops]
        self.route_short_name = route_short_name
        self.mode = mode.lower()
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
        super().__init__(stops)

    def __eq__(self, other):
        same_route_name = self.route_short_name == other.route_short_name
        same_mode = self.mode.lower() == other.mode.lower()
        same_stops = list(self.stops()) == list(other.stops())
        return same_route_name and same_mode and same_stops

    def __repr__(self):
        return "<{} instance at {}: with {} stops and {} trips>".format(
            self.__class__.__name__,
            id(self),
            len(self.ordered_stops),
            len(self.trips))

    def __str__(self):
        return self.info()

    def _build_graph(self, stops: List[Stop]):
        route_graph = nx.DiGraph(name='Route graph')
        route_nodes = [(stop.id, stop.__dict__) for stop in stops]
        route_graph.add_nodes_from(route_nodes, routes=[self.id])
        stop_edges = [(from_stop.id, to_stop.id) for from_stop, to_stop in zip(stops[:-1], stops[1:])]
        route_graph.add_edges_from(stop_edges, routes=[self.id], modes=[self.mode])
        return route_graph

    def modes(self):
        return [self.mode]

    def reindex(self, new_id):
        if self.id != new_id:
            # change data on graph
            g = self.graph()
            for stop in self.reference_nodes:
                g.nodes[stop]['routes'] = list((set(g.nodes[stop]['routes']) - {self.id}) | {new_id})
            self._graph.update(g)
            self.id = new_id

    def print(self):
        print(self.info())

    def info(self):
        return '{} ID: {}\nName: {}\nNumber of stops: {}\nNumber of trips: {}'.format(
            self.__class__.__name__, self.id, self.route_short_name, len(self.ordered_stops), len(self.trips))

    def plot(self, show=True, save=False, output_dir=''):
        if self.ordered_stops:
            return plot.plot_graph(
                nx.MultiGraph(self.graph()),
                filename='route_{}_graph'.format(self.id),
                show=show,
                save=save,
                output_dir=output_dir,
                e_c='#EC7063'
            )

    def stops(self):
        """
        Iterable returns stops in the Route in order of travel
        :return:
        """
        for s in self.ordered_stops:
            yield self.stop(s)

    def route(self, route_id):
        """
        Attempting to extract route from route given an id should yield itself unless index doesnt match
        :param route_id:
        :return:
        """
        if route_id == self.id:
            return self
        else:
            raise IndexError(f"{route_id} does not match Route's id: {self.id}")

    def routes(self):
        """
        This iterator is on the same level as the object and yields itself
        """
        yield None, self

    def generate_trips_dataframe(self, gtfs_day='19700101'):
        df = None
        _df = DataFrame({
            'departure_time':
                [use_schedule.get_offset(self.departure_offsets[i]) for i in range(len(self.ordered_stops) - 1)],
            'arrival_time':
                [use_schedule.get_offset(self.arrival_offsets[i]) for i in range(1, len(self.ordered_stops))],
            'from_stop': [self.ordered_stops[i] for i in range(len(self.ordered_stops) - 1)],
            'to_stop': [self.ordered_stops[i] for i in range(1, len(self.ordered_stops))]
        })
        for trip_id, trip_dep_time in self.trips.items():
            trip_df = _df.copy()
            trip_df['trip'] = trip_id
            trip_dep_time = use_schedule.sanitise_time(trip_dep_time, gtfs_day=gtfs_day)
            trip_df['departure_time'] = trip_dep_time + trip_df['departure_time']
            trip_df['arrival_time'] = trip_dep_time + trip_df['arrival_time']
            if df is None:
                df = trip_df
            else:
                df = df.append(trip_df)
        df['route'] = self.id
        df['route_name'] = self.route_short_name.replace("\\", "_").replace("/", "_")
        df['mode'] = self.mode
        df['from_stop_name'] = df['from_stop'].apply(lambda x: self.stop(x).name.replace("\\", "_").replace("/", "_"))
        df['to_stop_name'] = df['to_stop'].apply(lambda x: self.stop(x).name.replace("\\", "_").replace("/", "_"))
        df = df.reset_index(drop=True)
        return df

    def is_exact(self, other):
        same_route_name = self.route_short_name == other.route_short_name
        same_mode = self.mode.lower() == other.mode.lower()
        same_stops = list(self.stops()) == list(other.stops())
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

    def crowfly_distance(self):
        distance = 0
        for prev_stop, next_stop in zip(self.ordered_stops[:-1], self.ordered_stops[1:]):
            # todo replace by accessing graph nodes
            distance += spatial.distance_between_s2cellids(self.stop(prev_stop).s2_id, self.stop(next_stop).s2_id)
        return distance

    def is_strongly_connected(self):
        if nx.number_strongly_connected_components(self.graph()) == 1:
            return True
        return False

    def has_self_loops(self):
        """
        means that there are two consecutive stops that are the same
        :return:
        """
        return list(nx.nodes_with_selfloops(self.graph()))

    def has_more_than_one_stop(self):
        if len(self.ordered_stops) > 1:
            return True
        return False

    def has_network_route(self):
        return self.route

    def has_correctly_ordered_route(self):
        if self.has_network_route():
            # todo replace by accessing graph nodes
            stops_linkrefids = [stop.linkRefId for stop in self.stops() if stop.has_linkRefId()]
            if len(stops_linkrefids) != len(self.ordered_stops):
                logging.warning('Not all stops reference network link ids.')
                return False
            for link_id in self.route:
                if link_id == stops_linkrefids[0]:
                    stops_linkrefids = stops_linkrefids[1:]
            if not stops_linkrefids:
                return True
        return False

    def has_valid_offsets(self):
        if not self.arrival_offsets or not self.departure_offsets:
            return False
        elif len(self.arrival_offsets) != len(self.ordered_stops) or len(self.departure_offsets) != len(
                self.ordered_stops):
            return False
        for arr_offset, dep_offset in zip(self.arrival_offsets, self.departure_offsets):
            dt_arr_offset = datetime.strptime(arr_offset, '%H:%M:%S')
            dt_dep_offset = datetime.strptime(dep_offset, '%H:%M:%S')
            if dt_arr_offset > dt_dep_offset:
                return False
        for next_arr_offset, prev_dep_offset in zip(self.arrival_offsets[1:], self.departure_offsets[:-1]):
            dt_next_arr_offset = datetime.strptime(next_arr_offset, '%H:%M:%S')
            dt_prev_dep_offset = datetime.strptime(prev_dep_offset, '%H:%M:%S')
            if dt_next_arr_offset < dt_prev_dep_offset:
                return False
        return True

    def has_id(self):
        return self.id

    def is_valid_route(self, return_reason=False):
        invalid_stages = []
        valid = True

        if not self.has_more_than_one_stop():
            valid = False
            invalid_stages.append('not_has_more_than_one_stop')

        if not bool(self.has_correctly_ordered_route()):
            valid = False
            invalid_stages.append('not_has_correctly_ordered_route')

        if not bool(self.has_valid_offsets()):
            valid = False
            invalid_stages.append('not_has_valid_offsets')

        if bool(self.has_self_loops()):
            valid = False
            invalid_stages.append('has_self_loops')

        if return_reason:
            return valid, invalid_stages
        return valid


class Service(ScheduleElement):
    """
    A Service is an object containing unique routes pertaining to the same public transit service

    Parameters
    ----------
    :param services: dictionary of Service class objects {'service_id' : Service}
    :param stops_mapping: dictionary of Stop class objects {'stop_id': Stop} which pertain to the Services
    :param epsg: 'epsg:12345'
    """

    def __init__(self, id: str, routes: List[Route], name: str = ''):
        self.id = id
        # a service inherits a name from the first route in the list (all route names are still accessible via each
        # route object
        self.name = str(name)
        if not name and routes:
            for route in routes:
                if route.route_short_name:
                    self.name = str(route.route_short_name)
                    break
        # create a dictionary and index if not unique ids
        self._routes = {}
        for route in routes:
            _id = route.id
            if (not _id) or (_id in self._routes):
                _id = self.id + f'_{len(self._routes)}'
                route.reindex(_id)
            self._routes[_id] = route
        super().__init__(None)

    def __eq__(self, other):
        return self.id == other.id

    def __repr__(self):
        return "<{} instance at {}: with {} routes>".format(
            self.__class__.__name__,
            id(self),
            len(self))

    def __getitem__(self, route_id):
        return self._routes[route_id]

    def __str__(self):
        return self.info()

    def __len__(self):
        return len(self._routes)

    def _build_graph(self, stops=None):
        nodes = {}
        edges = {}
        for route in self._routes.values():
            g = route.graph()
            nodes = dict_support.merge_complex_dictionaries(dict(g.nodes(data=True)), nodes)
            edges = dict_support.combine_edge_data_lists(list(g.edges(data=True)), edges)

        service_graph = nx.DiGraph(name='Service graph')
        service_graph.add_nodes_from(nodes, services=[self.id])
        service_graph.add_edges_from(edges, services=[self.id])
        nx.set_node_attributes(service_graph, nodes)
        # update route graphs by the larger graph
        self._update_graph(service_graph)
        return service_graph

    def _update_graph(self, new_graph):
        self._graph = new_graph
        for route in self._routes.values():
            route._graph = new_graph

    def reindex(self, new_id):
        if self.id != new_id:
            # change data on graph
            g = self.graph()
            for stop in self.reference_nodes:
                g.nodes[stop]['services'] = list((set(g.nodes[stop]['services']) - {self.id}) | {new_id})
            self._graph.update(g)
            self.id = new_id

    def print(self):
        print(self.info())

    def info(self):
        return '{} ID: {}\nName: {}\nNumber of routes: {}\nNumber of unique stops: {}'.format(
            self.__class__.__name__, self.id, self.name, len(self), len(self.reference_nodes))

    def plot(self, show=True, save=False, output_dir=''):
        if self.reference_nodes:
            return plot.plot_graph(
                nx.MultiGraph(self.graph()),
                filename='service_{}_graph'.format(self.id),
                show=show,
                save=save,
                output_dir=output_dir,
                e_c='#EC7063'
            )

    def generate_trips_dataframe(self, gtfs_day='19700101'):
        df = None
        for route_id, route in self.routes():
            _df = route.generate_trips_dataframe(gtfs_day=gtfs_day)
            if df is None:
                df = _df
            else:
                df = df.append(_df)
        df['service'] = self.id
        df['service_name'] = self.name.replace("\\", "_").replace("/", "_")
        df = df.reset_index(drop=True)
        return df

    def route(self, route_id):
        """
        Extract particular route from a Service given index
        :param route_id:
        :return:
        """
        return self._routes[route_id]

    def routes(self):
        """
        Iterator for _routes in the service
        """
        for route in self._routes.values():
            yield self.id, route

    def is_exact(self, other):
        return (self.id == other.id) and (self._routes == other._routes)

    def isin_exact(self, services: list):
        for other in services:
            if self.is_exact(other):
                return True
        return False

    def is_strongly_connected(self):
        if nx.number_strongly_connected_components(self.graph()) == 1:
            return True
        return False

    def has_self_loops(self):
        return list(nx.nodes_with_selfloops(self.graph()))

    def validity_of_routes(self):
        return [route.is_valid_route() for route in self._routes.values()]

    def has_valid_routes(self):
        return all(self.validity_of_routes())

    def invalid_routes(self):
        return [route for route in self._routes.values() if not route.is_valid_route()]

    def has_uniquely_indexed_routes(self):
        indices = set([route.id for route in self._routes.values()])
        if len(indices) != len(self):
            return False
        return True

    def has_id(self):
        return self.id

    def is_valid_service(self, return_reason=False):
        invalid_stages = []
        valid = True

        if not self.has_valid_routes():
            valid = False
            invalid_stages.append('not_has_valid_routes')

        if not bool(self.has_uniquely_indexed_routes()):
            valid = False
            invalid_stages.append('not_has_uniquely_indexed_routes')

        if return_reason:
            return valid, invalid_stages
        return valid


class Schedule(ScheduleElement):
    """
    Class to provide methods and structure for transit schedules

    Parameters
    ----------
    :param epsg: 'epsg:12345', projection for the schedule (each stop has its own epsg)
    :param services: list of Service class objects
    """

    def __init__(self, epsg, services: List[Service] = None):
        self.init_epsg = epsg
        self.transformer = Transformer.from_crs(epsg, 'epsg:4326')
        if services is None:
            self.services = {}
        else:
            assert epsg != '', 'You need to specify the coordinate system for the schedule'
            self.services = {}
            for service in services:
                self.services[service.id] = service
        self.minimal_transfer_times = {}
        super().__init__(None)

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

    def _build_graph(self, stops=None):
        nodes = {}
        edges = {}
        for service_id, service in self.services.items():
            g = service.graph()
            nodes = dict_support.merge_complex_dictionaries(dict(g.nodes(data=True)), nodes)
            edges = dict_support.combine_edge_data_lists(list(g.edges(data=True)), edges)
            # TODO check for clashing stop ids overwriting data

        schedule_graph = nx.DiGraph(name='Schedule graph')
        schedule_graph.add_nodes_from(nodes)
        schedule_graph.add_edges_from(edges)
        nx.set_node_attributes(schedule_graph, nodes)
        # update service and route graphs by the larger graph
        self._update_graph(schedule_graph)
        return schedule_graph

    def _update_graph(self, new_graph):
        self._graph = new_graph
        for service in self.services.values():
            service._graph = new_graph
            for route in service._routes.values():
                route._graph = new_graph

    def reindex(self, new_id):
        if isinstance(self, Schedule):
            raise NotImplementedError('Schedule is not an indexed object')

    def add(self, other):
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

        self.services = {**other.services, **self.services}
        self.minimal_transfer_times = {**other.minimal_transfer_times, **self.minimal_transfer_times}
        # todo assuming separate schedules, with non conflicting ids, nodes and edges
        self._graph.update(other._graph)
        other._update_graph(self._graph)
        self.reference_nodes = list(set(self.reference_nodes) | set(other.reference_nodes))
        self.reference_edges = list(set(self.reference_edges) | set(other.reference_edges))

    def is_separable_from(self, other):
        unique_service_ids = set(other.services.keys()) & set(self.services.keys()) == set()
        unique_nodes = set(other.reference_nodes) & set(self.reference_nodes) == set()
        unique_edges = set(other.reference_edges) & set(self.reference_edges) == set()
        return unique_service_ids and unique_nodes and unique_edges

    def print(self):
        print(self.info())

    def info(self):
        return 'Schedule:\nNumber of services: {}\nNumber of unique routes: {}\nNumber of stops: {}'.format(
            self.__len__(), self.number_of_routes(), len(self.reference_nodes))

    def graph(self):
        return self._graph

    def reproject(self, new_epsg, processes=1):
        """
        Changes projection of the element to new_epsg
        :param new_epsg: 'epsg:1234'
        :return:
        """
        ScheduleElement.reproject(self, new_epsg, processes=processes)
        self._graph.graph['crs'] = {'init': new_epsg}

    def find_epsg(self):
        return self.init_epsg

    def plot(self, show=True, save=False, output_dir=''):
        return plot.plot_graph(
            nx.MultiGraph(self.graph()),
            filename='schedule_graph',
            show=show,
            save=save,
            output_dir=output_dir,
            e_c='#EC7063'
        )

    def generate_trips_dataframe(self, gtfs_day='19700101'):
        df = None
        for service_id, service in self.services.items():
            _df = service.generate_trips_dataframe(gtfs_day=gtfs_day)
            if df is None:
                df = _df
            else:
                df = df.append(_df)
        df = df.reset_index(drop=True)
        return df

    def service_ids(self):
        return list(self.services.keys())

    def route(self, route_id):
        """
        Gives the route under id: route_id or a list of routes with such route ids if not uniquely indexed
        :param route_id:
        :return:
        """
        routes = []
        for service_id, service in self.services.items():
            if route_id in service._routes:
                routes.append(service[route_id])
        if not routes:
            raise KeyError(f'{route_id} not found in any of the Services')
        if len(routes) == 1:
            return routes[0]
        else:
            return routes

    def routes(self):
        """
        Iterator for _routes in the schedule
        """
        for service_id, service in self.services.items():
            for route in service._routes.values():
                yield service_id, route

    def number_of_routes(self):
        return len([r for id, r in self.routes()])

    def is_strongly_connected(self):
        if nx.number_strongly_connected_components(self.graph()) == 1:
            return True
        return False

    def has_self_loops(self):
        return list(nx.nodes_with_selfloops(self.graph()))

    def validity_of_services(self):
        return [service.is_valid_service() for service_id, service in self.services.items()]

    def has_valid_services(self):
        return all(self.validity_of_services())

    def invalid_services(self):
        return [service for service_id, service in self.services.items() if not service.is_valid_service()]

    def has_uniquely_indexed_services(self):
        indices = set([service.id for service_id, service in self.services.items()])
        if len(indices) != len(self.services):
            return False
        return True

    def is_valid_schedule(self, return_reason=False):
        invalid_stages = []
        valid = True

        if not self.has_valid_services():
            valid = False
            invalid_stages.append('not_has_valid_services')

        if not bool(self.has_uniquely_indexed_services()):
            valid = False
            invalid_stages.append('not_has_uniquely_indexed_services')

        if return_reason:
            return valid, invalid_stages
        return valid

    def generate_validation_report(self):
        return schedule_validation.generate_validation_report(schedule=self)

    def generate_standard_outputs(self, output_dir, gtfs_day='19700101'):
        """
        Generates geojsons that can be used for generating standard kepler visualisations.
        These can also be used for validating network for example inspecting link capacity, freespeed, number of lanes,
        the shape of modal subgraphs.
        :param output_dir: path to folder where to save resulting geojsons
        :param gtfs_day: day in format YYYYMMDD for the network's schedule for consistency in visualisations,
        defaults to 1970/01/01 otherwise
        :return: None
        """
        gngeojson.generate_standard_outputs_for_schedule(self, output_dir, gtfs_day)
        logging.info('Finished generating standard outputs. Zipping folder.')
        persistence.zip_folder(output_dir)

    def read_matsim_schedule(self, path):
        services, minimal_transfer_times = matsim_reader.read_schedule(path, self.epsg)
        matsim_schedule = self.__class__(services=services, epsg=self.epsg)
        matsim_schedule.minimal_transfer_times = minimal_transfer_times
        self.add(matsim_schedule)

    def read_gtfs_schedule(self, path, day):
        """
        Reads from GTFS. The resulting services will not have route lists. Assumes to be in lat lon epsg:4326
        :param path: to GTFS folder or a zip file
        :param day: 'YYYYMMDD' to use form the gtfs
        :return:
        """
        schedule, stops_db = gtfs_reader.read_to_dict_schedule_and_stopd_db(path, day)
        services = []
        for key, routes in schedule.items():
            routes_list = []
            for route in routes:
                r = Route(
                    route_short_name=route['route_short_name'],
                    mode=route['mode'],
                    stops=[Stop(id=id, x=stops_db[id]['stop_lat'], y=stops_db[id]['stop_lon'], epsg='epsg:4326') for id
                           in
                           route['stops']],
                    trips=route['trips'],
                    arrival_offsets=route['arrival_offsets'],
                    departure_offsets=route['departure_offsets']
                )
                routes_list.append(r)
            services.append(Service(id=key, routes=routes_list))

        # add services rather than creating new object (in case there are already services present)
        to_add = self.__class__('epsg:4326', services)
        self.add(to_add)

    def write_to_matsim(self, output_dir):
        persistence.ensure_dir(output_dir)
        vehicles = matsim_xml_writer.write_matsim_schedule(output_dir, self)
        matsim_xml_writer.write_vehicles(output_dir, vehicles)
