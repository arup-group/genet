from abc import abstractmethod
from typing import Union, Dict, List
from pyproj import Transformer, Geod
import networkx as nx
import numpy as np
import logging
import os
import io
import yaml
import pkgutil
import json
from datetime import datetime
from pandas import DataFrame, Series
from copy import deepcopy
from collections import defaultdict
import itertools
import dictdiffer
from s2sphere import CellId
import genet.utils.plot as plot
import genet.utils.spatial as spatial
import genet.utils.dict_support as dict_support
import genet.outputs_handler.matsim_xml_writer as matsim_xml_writer
import genet.utils.persistence as persistence
import genet.utils.graph_operations as graph_operations
import genet.utils.parallel as parallel
import genet.modify.schedule as mod_schedule
import genet.modify.change_log as change_log
import genet.use.schedule as use_schedule
import genet.validate.schedule_validation as schedule_validation
import genet.outputs_handler.geojson as gngeojson
from genet.exceptions import ScheduleElementGraphSchemaError, RouteInitialisationError, ServiceInitialisationError, \
    UndefinedCoordinateSystemError, ServiceIndexError, RouteIndexError, StopIndexError, ConflictingStopData, \
    InconsistentVehicleModeError

# number of decimal places to consider when comparing lat lons
SPATIAL_TOLERANCE = 8


class ScheduleElement:
    """
    Base class for Route, Service and Schedule
    """

    def __init__(self):
        # check if in graph first
        if 'crs' in self._graph.graph:
            self.epsg = self._graph.graph['crs']['init']
        else:
            self.epsg = self.find_epsg()
            self._graph.graph['crs'] = {'init': self.epsg}

    def _surrender_to_graph(self):
        d = deepcopy(self.__dict__)
        return d

    def _get_service_from_graph(self, service_id):
        if service_id in self._graph.graph['services']:
            return Service(_graph=self._graph, **self._graph.graph['services'][service_id])
        else:
            raise ServiceIndexError(f'Service with index {service_id} not found')

    def _get_route_from_graph(self, route_id):
        if route_id in self._graph.graph['routes']:
            return Route(_graph=self._graph, **self._graph.graph['routes'][route_id])
        else:
            raise RouteIndexError(f'Route with index {route_id} not found')

    def _stop_ids_in_graph(self, stop_ids: List[str]):
        return set(stop_ids).issubset(set(self._graph.nodes))

    def _route_ids_in_graph(self, route_ids: List[str]):
        return set(route_ids).issubset(set(self._graph.graph['routes'].keys()))

    def _service_ids_in_graph(self, service_ids: List[str]):
        return set(service_ids).issubset(set(self._graph.graph['services'].keys()))

    def change_log(self):
        return self._graph.graph['change_log']

    @abstractmethod
    def reference_nodes(self):
        pass

    def route_reference_nodes(self, route_id):
        """
        Method to extract nodes for a route straight from the graph, equivalent to route_object.reference_nodes() but
        faster if used from a higher order object like Service or Schedule
        :return: graph nodes for the route with ID: route_id - not ordered
        """
        return {node for node, node_routes in self._graph.nodes(data='routes') if route_id in node_routes}

    def service_reference_nodes(self, service_id):
        """
        Method to extract nodes for a service straight from the graph, equivalent to service_object.reference_nodes()
        but faster if used from a higher order object: Schedule
        :return: graph nodes for the service with ID: service_id - not ordered
        """
        return {node for node, node_services in self._graph.nodes(data='services') if service_id in node_services}

    @abstractmethod
    def reference_edges(self):
        pass

    def route_reference_edges(self, route_id):
        """
        Method to extract edges for a route straight from the graph, equivalent to route_object.reference_edges() but
        faster if used from a higher order object like Service or Schedule
        :return: graph edges for the route with ID: route_id
        """
        return {(u, v) for u, v, edge_routes in self._graph.edges(data='routes') if route_id in edge_routes}

    def service_reference_edges(self, service_id):
        """
        Method to extract nodes for a service straight from the graph, equivalent to service_object.reference_edges()
        but faster if used from a higher order object: Schedule
        :return: graph edges for the service with ID: service_id
        """
        return {(u, v) for u, v, edge_services in self._graph.edges(data='services') if service_id in edge_services}

    def stop(self, stop_id):
        stop_data = {k: v for k, v in dict(self._graph.nodes[stop_id]).items() if k not in {'routes', 'services'}}
        return Stop(**stop_data)

    def stops(self):
        """
        Iterable returns stops in the Schedule Element
        :return:
        """
        for s in self.reference_nodes():
            yield self.stop(s)

    @abstractmethod
    def routes(self):
        pass

    @abstractmethod
    def modes(self):
        pass

    def mode_graph_map(self):
        mode_map = {mode: set() for mode in self.modes()}
        for route in self.routes():
            mode_map[route.mode] = mode_map[route.mode] | {(u, v) for u, v in route.reference_edges()}
        return mode_map

    def graph(self):
        return nx.DiGraph(nx.edge_subgraph(self._graph, self.reference_edges()))

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
        if 'crs' in self._graph.graph:
            return self._graph.graph['crs']['init']
        else:
            epsg = list({d for k, d in dict(self._graph.nodes(data='epsg', default='')).items()} - {''})
            if epsg:
                if len(epsg) == 1:
                    return epsg[0]
                else:
                    return epsg
        return None


class Stop:
    """
    A transit stop that features in a Route object

    Required Parameters
    ----------
    :param id: unique identifier
    :param x: x coordinate or lat if using 'epsg:4326'
    :param y: y coordinate or lon if using 'epsg:4326'
    :param epsg: 'epsg:12345'

    Optional Parameters
    ----------
    :param transformer: pyproj.Transformer.from_crs(epsg, 'epsg:4326', always_xy=True) optional but makes things MUCH
    faster if you're reading through a lot of stops in the same projection, all stops are mapped back to 'epsg:4326'
    and indexed with s2sphere
    :param name: human readable name for the stop
    :param kwargs: additional attributes
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
                self.lon, self.lat = float(x), float(y)
            else:
                if transformer is None:
                    transformer = Transformer.from_crs(self.epsg, 'epsg:4326', always_xy=True)
                self.lon, self.lat = spatial.change_proj(x, y, transformer)
        if 's2_id' in kwargs:
            self.s2_id = kwargs['s2_id']
        else:
            self.s2_id = spatial.generate_index_s2(lat=self.lat, lng=self.lon)

        self.additional_attributes = set()
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
            transformer = Transformer.from_crs(self.epsg, new_epsg, always_xy=True)
        self.x, self.y = spatial.change_proj(self.x, self.y, transformer)
        self.epsg = new_epsg

    def add_additional_attributes(self, attribs: dict):
        """
        adds attributes defined by keys of the attribs dictionary with values of the corresponding values
        ignores keys: 'id', 'x', 'y'
        :param attribs: the additional attributes {attrribute_name: attribute_value}
        :return:
        """
        for k, v in attribs.items():
            if k not in self.__dict__ or (not self.__dict__[k] and k != "additional_attributes"):
                setattr(self, k, v)
                self.additional_attributes.add(k)

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

    Required Parameters
    ----------
    :param route_short_name: route's short name
    :param mode: mode
    :param trips: dictionary with keys: 'trip_id', 'trip_departure_time', 'vehicle_id'. Each value is a list
        e.g. : {'trip_id': ['trip_1', 'trip_2'],  - IDs of trips, unique within the Route
                'trip_departure_time': ['HH:MM:SS', 'HH:MM:SS'],  - departure time from first stop for each trip_id
                'vehicle_id': [veh_1, veh_2]} - vehicle IDs for each trip_id, don't need to be unique
                    (i.e. vehicles can be shared between trips, but it's up to you to make this physically possible)
    :param arrival_offsets: list of 'HH:MM:SS' temporal offsets for each of the stops_mapping
    :param departure_offsets: list of 'HH:MM:SS' temporal offsets for each of the stops_mapping

    Optional Parameters (note, not providing some of the parameters may result in the object failing validation)
    ----------
    :param stops: ordered list of Stop class objects or Stop IDs already present in a Schedule, if generating a Route
        to add
    :param route_long_name: optional, verbose name for the route if exists
    :param route: optional, network link_ids traversed by the vehicles in this Route instance
    :param id: optional, unique identifier for the route if available, if not given, will be generated
    :param await_departure: optional, list of bools of length stops param, whether to await departure at each stop
    :param kwargs: additional attributes
    """

    def __init__(self, route_short_name: str, mode: str, trips: Dict[str, List[str]], arrival_offsets: List[str],
                 departure_offsets: List[str], route: list = None, route_long_name: str = '', id: str = '',
                 await_departure: list = None, stops: List[Union[Stop, str]] = None, **kwargs):
        self.route_short_name = route_short_name
        self.mode = mode
        self.trips = trips
        self.arrival_offsets = arrival_offsets
        self.departure_offsets = departure_offsets
        self.route_long_name = route_long_name
        self.id = id
        ordered_stops = None
        _graph = None
        if route is None:
            self.route = []
        else:
            self.route = route
        if await_departure is None:
            self.await_departure = []
        else:
            self.await_departure = await_departure
        if kwargs:
            if 'ordered_stops' in kwargs:
                ordered_stops = kwargs.pop('ordered_stops')
            if '_graph' in kwargs:
                _graph = kwargs.pop('_graph')
            self.add_additional_attributes(kwargs)

        if ordered_stops is not None:
            if _graph is not None:
                # check graph type and schema
                verify_graph_schema(_graph)
                self._graph = _graph
            else:
                raise RouteInitialisationError('When passing `ordered_stops` you are expected to pass `_graph` too. '
                                               'You may prefer to pass a list of Stop objects to `stops` instead')
            # check all stops in _graph
            if not self._stop_ids_in_graph(ordered_stops):
                raise RouteInitialisationError('Some stop IDs passed in `ordered_stops` are missing from the _graph '
                                               'object passed')
            self.ordered_stops = ordered_stops
        elif stops is not None:
            try:
                self.ordered_stops = [stop.id for stop in stops]
            except AttributeError:
                self.ordered_stops = stops
            self._graph = self._build_graph(stops=stops)
        else:
            raise RouteInitialisationError('You need to either pass `ordered_stops` with a valid `_graph` or '
                                           'a list of Stop objects to `stops`')
        super().__init__()

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
            len(self.trips['trip_id']))

    def __str__(self):
        return self.info()

    def _build_graph(self, stops: List[Stop]):
        route_graph = nx.DiGraph(name='Route graph')
        try:
            route_nodes = [(stop.id, stop.__dict__) for stop in stops]
            stop_edges = [(from_stop.id, to_stop.id) for from_stop, to_stop in zip(stops[:-1], stops[1:])]
        except AttributeError:
            route_nodes = [(stop, {}) for stop in stops]
            stop_edges = [(from_stop, to_stop) for from_stop, to_stop in zip(stops[:-1], stops[1:])]
        route_graph.add_nodes_from(route_nodes, routes={self.id})
        route_graph.add_edges_from(stop_edges, routes={self.id})
        route_graph.graph['routes'] = {self.id: self._surrender_to_graph()}
        route_graph.graph['services'] = {}
        route_graph.graph['change_log'] = change_log.ChangeLog()
        return route_graph

    def add_additional_attributes(self, attribs: dict):
        """
        adds attributes defined by keys of the attribs dictionary with values of the corresponding values
        :param attribs: the additional attributes {attribute_name: attribute_value}
        :return:
        """
        for k, v in attribs.items():
            if k not in self.__dict__:
                setattr(self, k, v)

    def reference_nodes(self):
        return self.route_reference_nodes(self.id)

    def reference_edges(self):
        return self.route_reference_edges(self.id)

    def modes(self):
        return {self.mode}

    def _index_unique(self, idx):
        return idx not in self._graph.graph['routes']

    def reindex(self, new_id):
        """
        Changes the current index of the object to `new_id`
        :param new_id: desired value of the new index
        :return:
        """
        if not self._index_unique(new_id):
            raise RouteIndexError(f'Route of index {new_id} already exists')
        if self.id != new_id:
            # change data on graph
            g = self.graph()
            for stop in self.reference_nodes():
                g.nodes[stop]['routes'] = (g.nodes[stop]['routes'] - {self.id}) | {new_id}
            for u, v in self.reference_edges():
                g[u][v]['routes'] = (g[u][v]['routes'] - {self.id}) | {new_id}
            self._graph.update(g)
            self._graph.graph['routes'][new_id] = self._graph.graph['routes'][self.id]
            self._graph.graph['routes'][new_id]['id'] = new_id
            del self._graph.graph['routes'][self.id]

            if 'route_to_service_map' in self._graph.graph:
                # if route is tied to a service, update the indexing
                corresponding_service_id = self._graph.graph['route_to_service_map'][self.id]
                self._graph.graph['service_to_route_map'][corresponding_service_id] = list(
                    set(self._graph.graph['service_to_route_map'][corresponding_service_id]) - {self.id} | {new_id})
                self._graph.graph['route_to_service_map'][new_id] = corresponding_service_id
                del self._graph.graph['route_to_service_map'][self.id]

            self._graph.graph['change_log'].modify(
                object_type='route', old_id=self.id, new_id=new_id,
                old_attributes={'id': self.id}, new_attributes={'id': new_id}
            )
            logging.info(f'Reindexed Route from {self.id} to {new_id}')
            self.id = new_id

    def print(self):
        print(self.info())

    def info(self):
        return '{} ID: {}\nName: {}\nNumber of stops: {}\nNumber of trips: {}'.format(
            self.__class__.__name__, self.id, self.route_short_name, len(self.ordered_stops),
            len(self.trips['trip_id']))

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
        Iterable returns Stop objects in the Route in order of travel
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
        yield self

    def route_trips_with_stops_to_dataframe(self, gtfs_day='19700101'):
        """
        Generates a DataFrame holding all the trips, their movements from stop to stop (in datetime with given GTFS day,
        if specified in `gtfs_day`) and vehicle IDs, next to the route ID and service ID.
        :param gtfs_day: day used for GTFS when creating the network in YYYYMMDD format defaults to 19700101
        :return:
        """
        df = None
        _df = DataFrame({
            'departure_time':
                [use_schedule.get_offset(self.departure_offsets[i]) for i in range(len(self.ordered_stops) - 1)],
            'arrival_time':
                [use_schedule.get_offset(self.arrival_offsets[i]) for i in range(1, len(self.ordered_stops))],
            'from_stop': self.ordered_stops[:-1],
            'to_stop': self.ordered_stops[1:]
        })
        for trip_id, trip_dep_time, veh_id in zip(self.trips['trip_id'], self.trips['trip_departure_time'],
                                                  self.trips['vehicle_id']):
            trip_df = _df.copy()
            trip_df['trip'] = trip_id
            trip_df['vehicle_id'] = veh_id
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
                    and same_departure_offsets  # noqa: E127
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

    Required Parameters
    ----------
    :param id: unique identifier for the service

    Optional Parameters (note, not providing some of the parameters may result in the object failing validation)
    ----------
    :param routes: list of Route objects, if the Routes are not uniquely indexed, they will be re-indexed
    :param name: string, name for the service, if not provided, will inherit the first non-trivial name from routes
    :param kwargs: additional attributes
    """

    def __init__(self, id: str, routes: List[Route] = None, name: str = '', **kwargs):
        self.id = id
        # a service inherits a name from the first route in the list (all route names are still accessible via each
        # route object
        self.name = str(name)
        _graph = None
        if not self.name and routes:
            for route in routes:
                if route.route_short_name:
                    self.name = str(route.route_short_name)
                    break
        if kwargs:
            if '_graph' in kwargs:
                _graph = kwargs.pop('_graph')
            self.add_additional_attributes(kwargs)

        if _graph is not None:
            # check graph type and schema
            verify_graph_schema(_graph)
            self._graph = _graph
        elif routes is not None:
            # re-index if not unique ids
            self._graph = self._build_graph(self._ensure_unique_routes(routes))
        else:
            raise ServiceInitialisationError('You need to pass either a valid `_graph` or a list of Route objects to '
                                             '`routes`')
        super().__init__()

    def __eq__(self, other):
        return self.id == other.id

    def __repr__(self):
        return "<{} instance at {}: with {} routes>".format(
            self.__class__.__name__,
            id(self),
            len(self))

    def __getitem__(self, route_id):
        return self._get_route_from_graph(route_id)

    def __str__(self):
        return self.info()

    def __len__(self):
        return len(list(self.route_ids()))

    def _build_graph(self, routes):
        _id = self.id
        nodes = {}
        edges = {}
        graph_routes = {}
        service_graph = nx.DiGraph(name='Service graph')
        service_graph.graph['change_log'] = change_log.ChangeLog()
        for route in routes:
            g = route.graph()
            nodes = dict_support.merge_complex_dictionaries(dict(g.nodes(data=True)), nodes)
            edges = dict_support.combine_edge_data_lists(list(g.edges(data=True)), edges)
            graph_routes = dict_support.merge_complex_dictionaries(g.graph['routes'], graph_routes)
            service_graph.graph['change_log'] = service_graph.graph['change_log'].merge_logs(
                g.graph['change_log']
            )

        service_graph.add_nodes_from(nodes, services={_id})
        service_graph.add_edges_from(edges, services={_id})
        nx.set_node_attributes(service_graph, nodes)
        service_graph.graph['routes'] = deepcopy(graph_routes)
        service_graph.graph['services'] = {_id: self._surrender_to_graph()}
        service_graph.graph['route_to_service_map'] = {route.id: _id for route in routes}
        service_graph.graph['service_to_route_map'] = {_id: [route.id for route in routes]}
        return service_graph

    def add_additional_attributes(self, attribs: dict):
        """
        adds attributes defined by keys of the attribs dictionary with values of the corresponding values
        :param attribs: the additional attributes {attribute_name: attribute_value}
        :return:
        """
        for k, v in attribs.items():
            if k not in self.__dict__:
                setattr(self, k, v)

    def _ensure_unique_routes(self, routes: List[Route]):
        unique_routes = []
        route_ids = []
        for route in routes:
            idx = route.id
            if (not idx) or (idx in route_ids):
                new_id = self.id + f'_{len(unique_routes)}'
                route.reindex(new_id)
                logging.warning(f'Route has been re-indexed from {idx} tp {new_id} due to an ID clash')
                idx = new_id
            route_ids.append(idx)
            unique_routes.append(route)
        return unique_routes

    def reference_nodes(self):
        return self.service_reference_nodes(self.id)

    def reference_edges(self):
        return self.service_reference_edges(self.id)

    def split_by_direction(self):
        """
        Divide the routes of the Service by direction e.g. North- and Southbound. Depending on the mode,
        typically a Service will have either 1 or 2 directions. Some Services will have more, especially ones that
        are loops.
        :return: Dictionary with directions as keys and lists of routes which head in that direction as values. E.g.:
        {
            North-East Bound: ['route_1', 'route_2'],
            South-West Bound: ['route_3', 'route_4']
        }
        """
        geodesic = Geod(ellps='WGS84')
        route_direction_map = {}
        for route_id in self.route_ids():
            ordered_stops = self._graph.graph['routes'][route_id]['ordered_stops']
            start_stop = self.stop(ordered_stops[0])
            end_stop = self.stop(ordered_stops[-1])
            if start_stop == end_stop:
                # just check which way it's heading
                end_stop = self.stop(ordered_stops[1])
            azimuth = geodesic.inv(
                lats1=start_stop.lat,
                lons1=start_stop.lon,
                lats2=end_stop.lat,
                lons2=end_stop.lon)[0]
            route_direction_map[route_id] = spatial.map_azimuth_to_name(azimuth)
        res = defaultdict(list)
        for key, val in sorted(route_direction_map.items()):
            res[val].append(key)
        return dict(res)

    def split_graph(self):
        """
        Divide the routes and the graph of the Service by share of Service's graph. Most services with have one or two
        outputs, but some will have more. The results of this method may vary from `split_by_direction`. The output
        graph edges in the list will be independent of each other (the edges will be independent, but they may share
        nodes), sometimes producing more than two sets.
        The method is not symmetric, if the Routes in a Service are listed in a different order this may lead to some
        graph groups merging (in a desired way).
        :return: tuple (routes, graph_groups) where routes is a list of sets with grouped route IDs and graph_groups
            is a list of the same length as routes, each item is a set of graph edges and corresponds to the item in
            routes list in that same index
        """

        def route_overlap_condition(graph_edge_group):
            edges_in_common = bool(graph_edge_group & route_edges)
            if edges_in_common:
                return edges_in_common
            else:
                from_nodes = {i[0] for i in route_edges}
                to_nodes = {i[1] for i in route_edges}
                shares_from_node = (from_nodes - to_nodes) & {i[0] for i in graph_edge_group}
                shares_to_node = (to_nodes - from_nodes) & {i[1] for i in graph_edge_group}
                return bool(shares_from_node) & bool(shares_to_node)

        def route_overlap_mask():
            return [route_overlap_condition(graph_edge_group) for graph_edge_group in graph_edges]

        def merge_multiple_overlaps():
            merged_route_group = {route_id}
            merged_graph_edges = route_edges
            overlap_routes = list(itertools.compress(routes, overlap_mask))
            overlap_graph_edges = list(itertools.compress(graph_edges, overlap_mask))
            for r, e in zip(overlap_routes, overlap_graph_edges):
                merged_route_group |= r
                merged_graph_edges |= e
                routes.remove(r)
                graph_edges.remove(e)
            routes.append(merged_route_group)
            graph_edges.append(merged_graph_edges)

        routes = []
        graph_edges = []
        for route_id in self.route_ids():
            route_edges = set(self.route_reference_edges(route_id))
            overlap_mask = route_overlap_mask()
            route_overlap = sum(overlap_mask)
            if route_overlap == 0:
                routes.append({route_id})
                graph_edges.append(route_edges)
            elif route_overlap == 1:
                for routes_group, graph_edge_group in zip(list(itertools.compress(routes, overlap_mask)),
                                                          list(itertools.compress(graph_edges, overlap_mask))):
                    routes_group.add(route_id)
                    graph_edge_group |= route_edges
            else:
                logging.warning(f'Graph of route: `{route_id}` overlaps with multiple current graph groups. This will '
                                f'result in merging of those groups. This is usually desirable but check results to '
                                f'ensure expected behaviour.')
                merge_multiple_overlaps()
        return routes, graph_edges

    def modes(self):
        return {r.mode for r in self.routes()}

    def _index_unique(self, idx):
        return idx not in self._graph.graph['services']

    def reindex(self, new_id):
        """
        Changes the current index of the object to `new_id`
        :param new_id: desired value of the new index
        :return:
        """
        if not self._index_unique(new_id):
            raise ServiceIndexError(f'Service of index {new_id} already exists')
        if self.id != new_id:
            # change data on graph
            g = self.graph()
            for stop in self.reference_nodes():
                g.nodes[stop]['services'] = (g.nodes[stop]['services'] - {self.id}) | {new_id}
            for u, v in self.reference_edges():
                g[u][v]['services'] = (g[u][v]['services'] - {self.id}) | {new_id}
            self._graph.update(g)
            self._graph.graph['services'][new_id] = self._graph.graph['services'][self.id]
            self._graph.graph['services'][new_id]['id'] = new_id
            del self._graph.graph['services'][self.id]

            # if service has routes tied to it, update the indexing
            for r_id in self.route_ids():
                self._graph.graph['route_to_service_map'][r_id] = new_id
            self._graph.graph['service_to_route_map'][new_id] = self._graph.graph['service_to_route_map'][self.id]
            del self._graph.graph['service_to_route_map'][self.id]

            self._graph.graph['change_log'].modify(
                object_type='service', old_id=self.id, new_id=new_id,
                old_attributes={'id': self.id}, new_attributes={'id': new_id}
            )
            logging.info(f'Reindexed Service from {self.id} to {new_id}')
            self.id = new_id

    def print(self):
        print(self.info())

    def info(self):
        return '{} ID: {}\nName: {}\nNumber of routes: {}\nNumber of stops: {}'.format(
            self.__class__.__name__, self.id, self.name, len(self), len(self.reference_nodes()))

    def plot(self, show=True, save=False, output_dir=''):
        if self.reference_nodes():
            return plot.plot_graph(
                nx.MultiGraph(self.graph()),
                filename='service_{}_graph'.format(self.id),
                show=show,
                save=save,
                output_dir=output_dir,
                e_c='#EC7063'
            )

    def route_trips_with_stops_to_dataframe(self, gtfs_day='19700101'):
        """
        Generates a DataFrame holding all the trips, their movements from stop to stop (in datetime with given GTFS day,
        if specified in `gtfs_day`) and vehicle IDs, next to the route ID and service ID.
        :param gtfs_day: day used for GTFS when creating the network in YYYYMMDD format defaults to 19700101
        :return:
        """
        df = None
        for route in self.routes():
            _df = route.route_trips_with_stops_to_dataframe(gtfs_day=gtfs_day)
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
        return self._get_route_from_graph(route_id)

    def route_ids(self):
        """
        Iterator for the Route IDs in the Service
        """
        for route_id in self._graph.graph['service_to_route_map'][self.id]:
            yield route_id

    def routes(self):
        """
        Iterator for the Route objects in the Service
        """
        for route_id in self.route_ids():
            yield self._get_route_from_graph(route_id)

    def is_exact(self, other):
        return (self.id == other.id) and (set(self.route_ids()) == set(other.route_ids()))

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
        return [route.is_valid_route() for route in self.routes()]

    def has_valid_routes(self):
        return all(self.validity_of_routes())

    def invalid_routes(self):
        return [route for route in self.routes() if not route.is_valid_route()]

    def has_id(self):
        return self.id

    def is_valid_service(self, return_reason=False):
        invalid_stages = []
        valid = True

        if not self.has_valid_routes():
            valid = False
            invalid_stages.append('not_has_valid_routes')

        if return_reason:
            return valid, invalid_stages
        return valid


class Schedule(ScheduleElement):
    """
    Class to provide methods and structure for transit schedules

    Optional Parameters
    ----------
    :param epsg: 'epsg:12345', projection for the schedule (each stop has its own epsg)
    :param services: list of Service class objects
    :param _graph: Schedule graph, used for re-instantiating the object, passed without `services`
    :param vehicles: dictionary of vehicle IDs from Route objects, mapping them to vehicle types in vehicle_types.
        Looks like this: {veh_id : {'type': 'bus'}}
        Defaults to None and generates itself from the vehicles IDs in Routes, maps to the mode of the Route.
        Checks if those modes are defined in the vehicle_types.
    :param vehicle_types: yml file based on `genet/configs/vehicles/vehicle_definitions.yml` or dictionary of vehicle
        types and their specification. Indexed by the vehicle type that vehicles in the `vehicles` attribute are
         referring to.
            {'bus' : {
                'capacity': {'seats': {'persons': '70'}, 'standingRoom': {'persons': '0'}},
                'length': {'meter': '18.0'},
                'width': {'meter': '2.5'},
                'accessTime': {'secondsPerPerson': '0.5'},
                'egressTime': {'secondsPerPerson': '0.5'},
                'doorOperation': {'mode': 'serial'},
                'passengerCarEquivalents': {'pce': '2.8'}}}
        Defaults to reading `genet/configs/vehicles/vehicle_definitions.yml`
    """

    def __init__(self, epsg: str = '', services: List[Service] = None, _graph: nx.DiGraph = None, vehicles=None,
                 vehicle_types: Union[str, dict] = pkgutil.get_data(__name__, os.path.join("configs", "vehicles",
                                                                                           "vehicle_definitions.yml"))):
        if isinstance(vehicle_types, dict):
            self.vehicle_types = vehicle_types
        else:
            self.vehicle_types = read_vehicle_types(vehicle_types)

        if _graph is not None:
            # check graph type and schema
            verify_graph_schema(_graph)
            self._graph = _graph
            if epsg == '':
                try:
                    epsg = self._graph.graph['crs']['init']
                except KeyError:
                    raise UndefinedCoordinateSystemError(
                        'You need to specify the coordinate system for the schedule')
        else:
            if epsg == '':
                raise UndefinedCoordinateSystemError('You need to specify the coordinate system for the schedule')
            used_service_indices = []
            used_route_indices = set()
            if services is not None:
                for service in services:
                    idx = service.id
                    route_ids = set(service.route_ids())
                    if idx in used_service_indices:
                        i = 0
                        new_idx = idx
                        while new_idx in used_service_indices:
                            new_idx = f'{idx}_{i}'
                            i += 1
                        service.reindex(new_idx)
                        logging.warning(f'Service has been re-indexed from {idx} to {new_idx} due to an ID clash')
                        idx = new_idx
                    clashing_route_ids = route_ids & used_route_indices
                    for r_id in clashing_route_ids:
                        # Services index their routes uniquely within themselves
                        service.route(r_id).reindex(f'{idx}_{r_id}')
                    used_route_indices |= set(service.route_ids())
                    used_service_indices.append(idx)
            else:
                services = []
            self._graph = self._build_graph(services)
        self.init_epsg = epsg
        self.transformer = Transformer.from_crs(epsg, 'epsg:4326', always_xy=True)
        self.minimal_transfer_times = {}
        if vehicles is None:
            self.vehicles = {}
            self.generate_vehicles()
        else:
            self.vehicles = vehicles
        self.validate_vehicle_definitions()
        super().__init__()

    def __nonzero__(self):
        return self.services()

    def __getitem__(self, service_id):
        return self._get_service_from_graph(service_id)

    def __contains__(self, service_id):
        return service_id in self._graph.graph['services']

    def __repr__(self):
        return "<{} instance at {}: with {} services>".format(
            self.__class__.__name__,
            id(self),
            len(self))

    def __str__(self):
        return self.info()

    def __len__(self):
        return len(self.service_ids())

    def _build_graph(self, services):
        nodes = {}
        edges = {}
        graph_routes = {}
        graph_services = {}
        schedule_graph = nx.DiGraph(name='Schedule graph')
        schedule_graph.graph['route_to_service_map'] = {}
        schedule_graph.graph['service_to_route_map'] = {}
        schedule_graph.graph['change_log'] = change_log.ChangeLog()

        for service in services:
            g = service.graph()
            nodes = dict_support.merge_complex_dictionaries(dict(g.nodes(data=True)), nodes)
            edges = dict_support.combine_edge_data_lists(list(g.edges(data=True)), edges)
            graph_routes = dict_support.merge_complex_dictionaries(g.graph['routes'], graph_routes)
            graph_services = dict_support.merge_complex_dictionaries(g.graph['services'], graph_services)
            schedule_graph.graph['route_to_service_map'] = {**schedule_graph.graph['route_to_service_map'],
                                                            **g.graph['route_to_service_map']}
            schedule_graph.graph['service_to_route_map'] = {**schedule_graph.graph['service_to_route_map'],
                                                            **g.graph['service_to_route_map']}
            schedule_graph.graph['change_log'] = schedule_graph.graph['change_log'].merge_logs(
                g.graph['change_log']
            )
            # TODO check for clashing stop ids overwriting data

        schedule_graph.add_nodes_from(nodes)
        schedule_graph.add_edges_from(edges)
        nx.set_node_attributes(schedule_graph, nodes)
        schedule_graph.graph['routes'] = graph_routes
        schedule_graph.graph['services'] = graph_services
        return schedule_graph

    def generate_vehicles(self, overwrite=False):
        """
        Generate vehicles for the Schedule. Returns dictionary of vehicle IDs from Route objects, mapping them to
        vehicle types in vehicle_types. Looks like this:
            {veh_id : {'type': 'bus'}}
        Generates itself from the vehicles IDs which exist in Routes, maps to the mode of the Route.
        :param overwrite: False by default. If False, does not overwrite the types of vehicles currently in the schedule
            If True, generates completely new vehicle types for all vehicles in the schedule based on Route modes
        :return:
        """
        if self:
            # generate vehicles using Services and Routes upon init
            df = self.route_trips_to_dataframe()[['route_id', 'vehicle_id']]
            df['type'] = df.apply(
                lambda x: self._graph.graph['routes'][x['route_id']]['mode'], axis=1)
            df = df.drop(columns='route_id')
            # check mode consistency
            vehicles_to_modes = df.groupby('vehicle_id').apply(lambda x: list(x['type'].unique()))
            if (vehicles_to_modes.str.len() > 1).any():
                # there are vehicles which are shared across routes with different modes
                raise InconsistentVehicleModeError('Modal inconsistencies found while generating vehicles for Schedule.'
                                                   ' Vehicles and modes in question: '
                                                   f'{vehicles_to_modes[(vehicles_to_modes.str.len() > 1)].to_dict()}')
            df = df.set_index('vehicle_id')
            if overwrite:
                self.vehicles = df.T.to_dict()
                self.validate_vehicle_definitions()
            else:
                self.vehicles = {**df.T.to_dict(), **self.vehicles}

    def route_trips_to_dataframe(self, gtfs_day='19700101'):
        """
        Generates a DataFrame holding all the trips IDs, their departure times (in datetime with given GTFS day,
        if specified in `gtfs_day`) and vehicle IDs, next to the route ID and service ID.
        Check out also `route_trips_with_stops_to_dataframe` for a more complex version - all trips are expanded
        over all of their stops, giving scheduled timestamps of each trips expected to arrive and leave the stop.
        :param gtfs_day: day used for GTFS when creating the network in YYYYMMDD format defaults to 19700101
        :return:
        """
        df = self.route_attribute_data(
            keys=[{'trips': 'trip_id'}, {'trips': 'trip_departure_time'}, {'trips': 'vehicle_id'}],
            index_name='route_id')
        df = df.reset_index()
        df['service_id'] = df['route_id'].apply(lambda x: self._graph.graph['route_to_service_map'][x])
        df = df.rename(columns={'trips::trip_id': 'trip_id', 'trips::trip_departure_time': 'trip_departure_time',
                                'trips::vehicle_id': 'vehicle_id'})
        df = DataFrame({
            col: np.repeat(df[col].values, df['trip_id'].str.len())
            for col in set(df.columns) - {'trip_id', 'trip_departure_time', 'vehicle_id'}}
        ).assign(trip_id=np.concatenate(df['trip_id'].values),
                 trip_departure_time=np.concatenate(df['trip_departure_time'].values),
                 vehicle_id=np.concatenate(df['vehicle_id'].values))
        df['trip_departure_time'] = df['trip_departure_time'].apply(lambda x: use_schedule.sanitise_time(x, gtfs_day))
        return df

    def set_route_trips_dataframe(self, df):
        """
        Option to replace trips data currently stored under routes by an updated `route_trips_to_dataframe`.
        Need not be exhaustive in terms of routes. I.e. trips for some of the routes can be omitted if no changes are
        required. Needs to be exhaustive in terms of trips. I.e. if there are changes to a route, all of the trips
        required to be in that trip need to be present, it overwrites route.trips attribute.
        :param df: DataFrame generated by `route_trips_to_dataframe` (or of the same format)
        :return:
        """
        # convert route trips dataframe to apply dictionary shape and give to apply to routes method
        df['trip_departure_time'] = df['trip_departure_time'].dt.strftime('%H:%M:%S')
        df = df.groupby('route_id').apply(
            lambda x: Series({'trips': {k: x[k].to_list() for k in ['trip_id', 'trip_departure_time', 'vehicle_id']}}))
        self.apply_attributes_to_routes(df.T.to_dict())

    def overlapping_vehicle_ids(self, vehicles):
        return set(self.vehicles.keys()) & set(vehicles.keys())

    def overlapping_vehicle_types(self, vehicle_types):
        return set(self.vehicle_types.keys()) & set(vehicle_types.keys())

    def update_vehicles(self, vehicles, vehicle_types, overwrite=True):
        """
        Updates vehicles and vehicle types
        :param vehicles: vehicles to add
        :param vehicle_types: vehicle types to add
        :param overwrite: defaults to True
            If True: overwrites overlapping vehicle types data currently in the Schedule, adds vehicles as they are,
                overwriting in case of clash
            If False: adds vehicles and vehicle types that do not clash with those already stored in the Schedule
        :return:
        """
        # check for vehicle ID overlap
        clashing_vehicles = self.overlapping_vehicle_ids(vehicles=vehicles)
        if clashing_vehicles:
            logging.warning(f'The following vehicles clash: {clashing_vehicles}')
            if overwrite:
                logging.warning('Overwrite is on. Vehicles listed above will be overwritten.')
            else:
                logging.warning('Overwrite is off. Clashing vehicles will remain as they are. '
                                'All others will be added.')
        # check for vehicle type overlap
        clashing_vehicle_types = self.overlapping_vehicle_types(vehicle_types=vehicle_types)
        if clashing_vehicle_types:
            logging.warning(f'The following vehicle types clash: {clashing_vehicle_types}')
            if overwrite:
                logging.warning('Overwrite is on. Vehicle types listed above will be overwritten.')
            else:
                logging.warning('Overwrite is off. Clashing vehicle types will remain as they are. '
                                'All others will be added.')

        if overwrite:
            self.vehicles = {**self.vehicles, **vehicles}
            self.vehicle_types = {**self.vehicle_types, **vehicle_types}
        else:
            self.vehicles = {**vehicles, **self.vehicles}
            self.vehicle_types = {**vehicle_types, **self.vehicle_types}

        self.validate_vehicle_definitions()
        return clashing_vehicles, clashing_vehicle_types

    def validate_vehicle_definitions(self):
        """
        Checks if modes mapped to vehicle IDs in vehicles attribute of Schedule are defined in the vehicle_types.
        :return: returns True if the vehicle types in the `vehicles` attribute exist in the `vehicle_types` attribute.
            But useful even just for the logging messages.
        """
        df_vehicles = graph_operations.build_attribute_dataframe(iterator=self.vehicles.items(), keys=['type'])
        if set(df_vehicles['type']).issubset(set(self.vehicle_types.keys())):
            return True
        else:
            missing_vehicle_types = set(df_vehicles['type']) - set(self.vehicle_types.keys())
            logging.warning('The following vehicle types are missing from the `vehicle_types` attribute: '
                            f'{missing_vehicle_types}')
            logging.warning('Vehicles affected by missing vehicle types: '
                            f"{df_vehicles[df_vehicles['type'].isin(missing_vehicle_types)].T.to_dict()}")
        return False

    def reference_nodes(self):
        return set(self._graph.nodes())

    def reference_edges(self):
        return set(self._graph.edges())

    def modes(self):
        return set(self.route_attribute_data(keys='mode')['mode'].unique())

    def mode_to_routes_map(self):
        df = self.route_attribute_data(keys=['mode'], index_name='route_id').reset_index()
        return df.groupby('mode')['route_id'].apply(list).to_dict()

    def mode_graph_map(self):
        mode_map = {}
        mode_to_routes_map = self.mode_to_routes_map()
        for mode, route_ids in mode_to_routes_map.items():
            mode_map[mode] = set(graph_operations.extract_on_attributes(
                iterator=[((u, v), data) for u, v, data in self._graph.edges(data=True)],
                conditions={'routes': route_ids}))
        return mode_map

    def reindex(self, new_id):
        if isinstance(self, Schedule):
            raise NotImplementedError('Schedule is not currently an indexed object')

    def add(self, other, overwrite=True):
        """
        Adds another Schedule. They have to be separable! I.e. the keys in services cannot overlap with the ones
        already present (TODO: add merging complicated schedules, parallels to the merging gtfs work)
        :param other: the other Schedule object to add
        :param overwrite: defaults to True
            If True: overwrites overlapping vehicle types data currently in the Schedule, adds vehicles as they are,
                overwriting in case of clash
            If False: adds vehicles and vehicle types from other that do not clash with those already stored in the
            Schedule
        :return:
        """
        if not self.is_separable_from(other):
            # have left and right indicies
            raise NotImplementedError('This method only supports adding non overlapping services.')
        elif self.epsg != other.epsg:
            other.reproject(self.epsg)

        self._graph.graph['services'] = dict_support.merge_complex_dictionaries(
            other._graph.graph['services'], self._graph.graph['services'])
        self._graph.graph['routes'] = dict_support.merge_complex_dictionaries(
            other._graph.graph['routes'], self._graph.graph['routes'])
        self._graph.graph['route_to_service_map'] = \
            {**self._graph.graph['route_to_service_map'], **other._graph.graph['route_to_service_map']}
        self._graph.graph['service_to_route_map'] = \
            {**self._graph.graph['service_to_route_map'], **other._graph.graph['service_to_route_map']}
        self.minimal_transfer_times = {**other.minimal_transfer_times, **self.minimal_transfer_times}
        # todo assuming separate schedules, with non conflicting ids, nodes and edges
        self._graph.update(other._graph)

        # merge change_log DataFrames
        self._graph.graph['change_log'] = self.change_log().merge_logs(other.change_log())

        # merge vehicles
        self.update_vehicles(other.vehicles, other.vehicle_types, overwrite=overwrite)

    def is_separable_from(self, other):
        unique_service_ids = set(other.service_ids()) & set(self.service_ids()) == set()
        unique_route_ids = set(other.route_ids()) & set(self.route_ids()) == set()
        unique_nodes = other.reference_nodes() & self.reference_nodes() == set()
        unique_edges = other.reference_edges() & self.reference_edges() == set()
        return unique_service_ids and unique_route_ids and unique_nodes and unique_edges

    def print(self):
        print(self.info())

    def info(self):
        return 'Schedule:\nNumber of services: {}\nNumber of routes: {}\nNumber of stops: {}'.format(
            self.__len__(), self.number_of_routes(), len(self.reference_nodes()))

    def graph(self):
        return self._graph

    def reproject(self, new_epsg, processes=1):
        """
        Changes projection of the element to new_epsg
        :param new_epsg: 'epsg:1234'
        :param processes: integer number of processes to split stops data to be processed in parallel
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

    def route_trips_with_stops_to_dataframe(self, gtfs_day='19700101'):
        """
        Generates a DataFrame holding all the trips, their movements from stop to stop (in datetime with given GTFS day,
        if specified in `gtfs_day`) and vehicle IDs, next to the route ID and service ID.
        Check out also `route_trips_to_dataframe` for a simplified version (trips, their departure times and vehicles
        only)
        :param gtfs_day: day used for GTFS when creating the network in YYYYMMDD format defaults to 19700101
        :return:
        """
        df = self.route_attribute_data(
            keys=['route_short_name', 'mode', 'trips', 'arrival_offsets', 'departure_offsets', 'ordered_stops', 'id'])
        df = df.rename(columns={'id': 'route', 'route_short_name': 'route_name'})
        df['route_name'] = df['route_name'].apply(lambda x: x.replace("\\", "_").replace("/", "_"))
        df['service'] = df['route'].apply(lambda x: self._graph.graph['route_to_service_map'][x])
        df['service_name'] = df['service'].apply(
            lambda x: self._graph.graph['services'][x]['name'].replace("\\", "_").replace("/", "_"))
        df['ordered_stops'] = df['ordered_stops'].apply(lambda x: list(zip(x[:-1], x[1:])))
        df['departure_offsets'] = df['departure_offsets'].apply(lambda x: list(map(use_schedule.get_offset, x[:-1])))
        df['arrival_offsets'] = df['arrival_offsets'].apply(lambda x: list(map(use_schedule.get_offset, x[1:])))

        # expand the frame stop to stop and extract offsets for arrival and departure from these stops
        stop_cols = np.concatenate(df['ordered_stops'].values)
        dep_offset_cols = np.concatenate(df['departure_offsets'].values)
        arr_offset_cols = np.concatenate(df['arrival_offsets'].values)
        df = DataFrame({
            col: np.repeat(df[col].values, df['ordered_stops'].str.len())
            for col in set(df.columns) - {'ordered_stops', 'arrival_offsets', 'departure_offsets'}}
        ).assign(from_stop=stop_cols[:, 0],
                 to_stop=stop_cols[:, 1],
                 departure_time=dep_offset_cols,
                 arrival_time=arr_offset_cols)

        df['from_stop_name'] = df['from_stop'].apply(
            lambda x: self._graph.nodes[x]['name'].replace("\\", "_").replace("/", "_"))
        df['to_stop_name'] = df['to_stop'].apply(
            lambda x: self._graph.nodes[x]['name'].replace("\\", "_").replace("/", "_"))

        # expand the frame on all the trips each route makes
        trips = np.concatenate(
            df['trips'].apply(
                lambda x: [(trip_id, use_schedule.sanitise_time(trip_dep_time, gtfs_day), veh_id) for
                           trip_id, trip_dep_time, veh_id in
                           zip(x['trip_id'], x['trip_departure_time'], x['vehicle_id'])]).values)
        df = DataFrame({
            col: np.repeat(df[col].values, df['trips'].str['trip_id'].str.len())
            for col in set(df.columns) - {'trips'}}
        ).assign(trip=trips[:, 0],
                 trip_dep_time=trips[:, 1],
                 vehicle_id=trips[:, 2]).sort_values(by=['route', 'trip', 'departure_time']).reset_index(drop=True)

        df['departure_time'] = df['trip_dep_time'] + df['departure_time']
        df['arrival_time'] = df['trip_dep_time'] + df['arrival_time']
        df = df.drop('trip_dep_time', axis=1)
        return df

    def service_to_route_map(self):
        return self._graph.graph['service_to_route_map']

    def route_to_service_map(self):
        return self._graph.graph['route_to_service_map']

    def service_ids(self):
        """
        Returns list of service ids in the Schedule
        """
        return list(self._graph.graph['services'].keys())

    def has_service(self, service_id):
        """
        Returns True if a service with ID `service_id` exists in the Schedule, False otherwise
        """
        return service_id in self.service_ids()

    def services(self):
        """
        Iterator for Service objects in the Services of the Schedule
        """
        for service_id in self.service_ids():
            yield self._get_service_from_graph(service_id)

    def route(self, route_id):
        """
        Gives the Route objects under route_id
        :param route_id: string
        :return:
        """
        return self._get_route_from_graph(route_id)

    def route_ids(self):
        """
        Returns list of route ids in the Schedule
        """
        return list(self._graph.graph['routes'].keys())

    def has_route(self, route_id):
        """
        Returns True if a route with ID `route_id` exists in the Schedule, False otherwise
        """
        return route_id in self._graph.graph['routes'].keys()

    def routes(self):
        """
        Iterator for Route objects in the Services of the Schedule
        """
        for route_id in self.route_ids():
            yield self._get_route_from_graph(route_id)

    def number_of_routes(self):
        return len(self._graph.graph['routes'])

    def has_stop(self, stop_id):
        """
        Returns True if a stop with ID `stop_id` exists in the Schedule, False otherwise
        """
        return self._graph.has_node(stop_id)

    def service_attribute_summary(self, data=False):
        """
        Parses through data stored for Services in the Schedule and gives a summary tree.
        If data is True, shows also up to 5 unique values stored under such keys.
        :param data: bool, False by default
        :return:
        """
        root = graph_operations.get_attribute_schema(self._graph.graph['services'].items(), data=data)
        graph_operations.render_tree(root, data)

    def route_attribute_summary(self, data=False):
        """
        Parses through data stored for Routes in the Schedule and gives a summary tree.
        If data is True, shows also up to 5 unique values stored under such keys.
        :param data: bool, False by default
        :return:
        """
        root = graph_operations.get_attribute_schema(self._graph.graph['routes'].items(), data=data)
        graph_operations.render_tree(root, data)

    def stop_attribute_summary(self, data=False):
        """
        Parses through data stored for Stops in the Schedule and gives a summary tree.
        If data is True, shows also up to 5 unique values stored under such keys.
        :param data: bool, False by default
        :return:
        """
        root = graph_operations.get_attribute_schema(self._graph.nodes(data=True), data=data)
        graph_operations.render_tree(root, data)

    def service_attribute_data(self, keys: Union[list, str], index_name: str = None):
        """
        Generates a pandas.DataFrame object indexed by Service IDs, with attribute data stored for Services under `key`
        :param keys: list of either a string e.g. 'name', or if accessing nested information, a dictionary
            e.g. {'attributes': {'osm:way:name': 'text'}}
        :param index_name: optional, gives the index_name to dataframes index
        :return: pandas.DataFrame
        """
        return graph_operations.build_attribute_dataframe(
            iterator=self._graph.graph['services'].items(), keys=keys, index_name=index_name)

    def route_attribute_data(self, keys: Union[list, str], index_name: str = None):
        """
        Generates a pandas.DataFrame object indexed by Route IDs, with attribute data stored for Routes under `key`
        :param keys: list of either a string e.g. 'mode', or if accessing nested information, a dictionary
            e.g. {'attributes': {'osm:way:name': 'text'}}
        :param index_name: optional, gives the index_name to dataframes index
        :return: pandas.DataFrame
        """
        return graph_operations.build_attribute_dataframe(
            iterator=self._graph.graph['routes'].items(), keys=keys, index_name=index_name)

    def stop_attribute_data(self, keys: Union[list, str], index_name: str = None):
        """
        Generates a pandas.DataFrame object indexed by Stop IDs, with attribute data stored for Stops under `key`
        :param keys: list of either a string e.g. 'x', or if accessing nested information, a dictionary
            e.g. {'attributes': {'osm:way:name': 'text'}}
        :param index_name: optional, gives the index_name to dataframes index
        :return: pandas.DataFrame
        """
        return graph_operations.build_attribute_dataframe(
            iterator=self._graph.nodes(data=True), keys=keys, index_name=index_name)

    def extract_service_ids_on_attributes(self, conditions: Union[list, dict], how=any, mixed_dtypes=True):
        """
        Extracts IDs of Services stored in the Schedule based on values of their attributes.
        Fails silently, assumes not all Services have those attributes. In the case were the attributes stored are
        a list or set, like in the case of a simplified network (there will be a mix of objects that are sets and not)
        an intersection of values satisfying condition(s) is considered in case of iterable value, if not empty, it is
        deemed successful by default. To disable this behaviour set mixed_dtypes to False.
        :param conditions: {'attribute_key': 'target_value'} or nested
        {'attribute_key': {'another_key': {'yet_another_key': 'target_value'}}}, where 'target_value' could be

            - single value, string, int, float, where the edge_data[key] == value
                (if mixed_dtypes==True and in case of set/list edge_data[key], value is in edge_data[key])

            - list or set of single values as above, where edge_data[key] in [value1, value2]
                (if mixed_dtypes==True and in case of set/list edge_data[key],
                set(edge_data[key]) & set([value1, value2]) is non-empty)

            - for int or float values, two-tuple bound (lower_bound, upper_bound) where
              lower_bound <= edge_data[key] <= upper_bound
                (if mixed_dtypes==True and in case of set/list edge_data[key], at least one item in
                edge_data[key] satisfies lower_bound <= item <= upper_bound)

            - function that returns a boolean given the value e.g.

            def below_exclusive_upper_bound(value):
                return value < 100

                (if mixed_dtypes==True and in case of set/list edge_data[key], at least one item in
                edge_data[key] returns True after applying function)

        :param how : {all, any}, default any

        The level of rigour used to match conditions

            * all: means all conditions need to be met
            * any: means at least one condition needs to be met

        :param mixed_dtypes: True by default, used if values under dictionary keys queried are single values or lists of
        values e.g. as in simplified networks.
        :return: list of ids in the schedule satisfying conditions
        """
        return graph_operations.extract_on_attributes(
            self._graph.graph['services'].items(), conditions=conditions, how=how, mixed_dtypes=mixed_dtypes)

    def extract_route_ids_on_attributes(self, conditions: Union[list, dict], how=any, mixed_dtypes=True):
        """
        Extracts IDs of Routes stored in the Schedule based on values of their attributes.
        Fails silently, assumes not all Routes have those attributes. In the case were the attributes stored are
        a list or set, like in the case of a simplified network (there will be a mix of objects that are sets and not)
        an intersection of values satisfying condition(s) is considered in case of iterable value, if not empty, it is
        deemed successful by default. To disable this behaviour set mixed_dtypes to False.
        :param conditions: {'attribute_key': 'target_value'} or nested
        {'attribute_key': {'another_key': {'yet_another_key': 'target_value'}}}, where 'target_value' could be

            - single value, string, int, float, where the edge_data[key] == value
                (if mixed_dtypes==True and in case of set/list edge_data[key], value is in edge_data[key])

            - list or set of single values as above, where edge_data[key] in [value1, value2]
                (if mixed_dtypes==True and in case of set/list edge_data[key],
                set(edge_data[key]) & set([value1, value2]) is non-empty)

            - for int or float values, two-tuple bound (lower_bound, upper_bound) where
              lower_bound <= edge_data[key] <= upper_bound
                (if mixed_dtypes==True and in case of set/list edge_data[key], at least one item in
                edge_data[key] satisfies lower_bound <= item <= upper_bound)

            - function that returns a boolean given the value e.g.

            def below_exclusive_upper_bound(value):
                return value < 100

                (if mixed_dtypes==True and in case of set/list edge_data[key], at least one item in
                edge_data[key] returns True after applying function)

        :param how : {all, any}, default any

        The level of rigour used to match conditions

            * all: means all conditions need to be met
            * any: means at least one condition needs to be met

        :param mixed_dtypes: True by default, used if values under dictionary keys queried are single values or lists of
        values e.g. as in simplified networks.
        :return: list of ids in the schedule satisfying conditions
        """
        return graph_operations.extract_on_attributes(
            self._graph.graph['routes'].items(), conditions=conditions, how=how, mixed_dtypes=mixed_dtypes)

    def extract_stop_ids_on_attributes(self, conditions: Union[list, dict], how=any, mixed_dtypes=True):
        """
        Extracts IDs of Stops stored in the Schedule based on values of their attributes.
        Fails silently, assumes not all Routes have those attributes. In the case were the attributes stored are
        a list or set, like in the case of a simplified network (there will be a mix of objects that are sets and not)
        an intersection of values satisfying condition(s) is considered in case of iterable value, if not empty, it is
        deemed successful by default. To disable this behaviour set mixed_dtypes to False.
        :param conditions: {'attribute_key': 'target_value'} or nested
        {'attribute_key': {'another_key': {'yet_another_key': 'target_value'}}}, where 'target_value' could be

            - single value, string, int, float, where the edge_data[key] == value
                (if mixed_dtypes==True and in case of set/list edge_data[key], value is in edge_data[key])

            - list or set of single values as above, where edge_data[key] in [value1, value2]
                (if mixed_dtypes==True and in case of set/list edge_data[key],
                set(edge_data[key]) & set([value1, value2]) is non-empty)

            - for int or float values, two-tuple bound (lower_bound, upper_bound) where
              lower_bound <= edge_data[key] <= upper_bound
                (if mixed_dtypes==True and in case of set/list edge_data[key], at least one item in
                edge_data[key] satisfies lower_bound <= item <= upper_bound)

            - function that returns a boolean given the value e.g.

            def below_exclusive_upper_bound(value):
                return value < 100

                (if mixed_dtypes==True and in case of set/list edge_data[key], at least one item in
                edge_data[key] returns True after applying function)

        :param how : {all, any}, default any

        The level of rigour used to match conditions

            * all: means all conditions need to be met
            * any: means at least one condition needs to be met

        :param mixed_dtypes: True by default, used if values under dictionary keys queried are single values or lists of
        values e.g. as in simplified networks.
        :return: list of ids in the schedule satisfying conditions
        """
        return graph_operations.extract_on_attributes(
            self._graph.nodes(data=True), conditions=conditions, how=how, mixed_dtypes=mixed_dtypes)

    def services_on_modal_condition(self, modes: Union[str, list]):
        """
        Finds Service IDs which hold Routes with modes or singular mode given in `modes`.
        Note that a Service can have Routes with different modes.
        :param modes: string mode e.g. 'bus' or a list of such modes e.g. ['bus', 'rail']
        :return: list of Service IDs
        """
        route_ids = self.routes_on_modal_condition(modes=modes)
        return list({self._graph.graph['route_to_service_map'][r_id] for r_id in route_ids})

    def routes_on_modal_condition(self, modes: Union[str, list]):
        """
        Finds Route IDs with modes or singular mode given in `modes`
        :param modes: string mode e.g. 'bus' or a list of such modes e.g. ['bus', 'rail']
        :return: list of Route IDs
        """
        conditions = {'mode': modes}
        return self.extract_route_ids_on_attributes(conditions=conditions)

    def stops_on_modal_condition(self, modes: Union[str, list]):
        """
        Finds Stop IDs used by Routes with modes or singular mode given in `modes`
        :param modes: string mode e.g. 'bus' or a list of such modes e.g. ['bus', 'rail']
        :return: list of Stop IDs
        """
        route_ids = self.routes_on_modal_condition(modes=modes)
        return self.extract_stop_ids_on_attributes(conditions={'routes': route_ids})

    def services_on_spatial_condition(self, region_input, how='intersect'):
        """
        Returns Service IDs which intersect region_input, by default, or are contained within region_input if
        how='contain'
        :param region_input:
        :param how:
            - 'intersect' default, will return IDs of the Services whose at least one Stop intersects the
            region_input
            - 'contain' will return IDs of the Services whose all of the Stops are contained within the region_input
        :return: Service IDs
        """
        if how == 'intersect':
            stops_intersecting = self.stops_on_spatial_condition(region_input)
            return list({item for sublist in [self._graph.nodes[x]['services'] for x in stops_intersecting] for item in
                         sublist})
        elif how == 'within':
            routes_contained = set(self.routes_on_spatial_condition(region_input, how='within'))
            return [service_id for service_id, route_ids in self._graph.graph['service_to_route_map'].items() if
                    set(route_ids).issubset(routes_contained)]
        else:
            raise NotImplementedError('Only `intersect` and `within` options for `how` param.')

    def routes_on_spatial_condition(self, region_input, how='intersect'):
        """
        Returns Route IDs which intersect region_input, by default, or are contained within region_input if
        how='contain'
        :param region_input:
            - path to a geojson file, can have multiple features
            - string with comma separated hex tokens of Google's S2 geometry, a region can be covered with cells and
             the tokens string copied using http://s2.sidewalklabs.com/regioncoverer/
             e.g. '89c25985,89c25987,89c2598c,89c25994,89c25999ffc,89c2599b,89c259ec,89c259f4,89c25a1c,89c25a24'
            - shapely.geometry object, e.g. Polygon or a shapely.geometry.GeometryCollection of such objects
        :param how:
            - 'intersect' default, will return IDs of the Routes whose at least one Stop intersects the
            region_input
            - 'contain' will return IDs of the Routes whose all of the Stops are contained within the region_input
        :return: Route IDs
        """
        stops_intersecting = set(self.stops_on_spatial_condition(region_input))
        if how == 'intersect':
            return list(
                {item for sublist in [self._graph.nodes[x]['routes'] for x in stops_intersecting] for item in sublist})
        elif how == 'within':
            return self.extract_route_ids_on_attributes(
                conditions={'ordered_stops': lambda x: set(x).issubset(stops_intersecting)}, mixed_dtypes=False)
        else:
            raise NotImplementedError('Only `intersect` and `within` options for `how` param.')

    def stops_on_spatial_condition(self, region_input):
        """
        Returns Stop IDs which intersect region_input
        :param region_input:
            - path to a geojson file, can have multiple features
            - string with comma separated hex tokens of Google's S2 geometry, a region can be covered with cells and
             the tokens string copied using http://s2.sidewalklabs.com/regioncoverer/
             e.g. '89c25985,89c25987,89c2598c,89c25994,89c25999ffc,89c2599b,89c259ec,89c259f4,89c25a1c,89c25a24'
            - shapely.geometry object, e.g. Polygon or a shapely.geometry.GeometryCollection of such objects
        :return: Stop IDs
        """
        if isinstance(region_input, str):
            if persistence.is_geojson(region_input):
                return self._find_stops_on_geojson(region_input)
            else:
                # is assumed to be hex
                return self._find_stops_on_s2_geometry(region_input)
        else:
            # assumed to be a shapely.geometry input
            return self._find_stops_on_shapely_geometry(region_input)

    def _find_stops_on_geojson(self, geojson_input):
        shapely_input = spatial.read_geojson_to_shapely(geojson_input)
        return self._find_stops_on_shapely_geometry(shapely_input)

    def _find_stops_on_shapely_geometry(self, shapely_input):
        stops_gdf = self.to_geodataframe()['nodes'].to_crs("epsg:4326")
        return list(stops_gdf[stops_gdf.intersects(shapely_input)].index)

    def _find_stops_on_s2_geometry(self, s2_input):
        cell_union = spatial.s2_hex_to_cell_union(s2_input)
        return [_id for _id, s2_id in self._graph.nodes(data='s2_id') if cell_union.intersects(CellId(s2_id))]

    def _verify_no_id_change(self, new_attributes):
        id_changes = [id for id, change_dict in new_attributes.items() if
                      ('id' in change_dict) and (change_dict['id'] != id)]
        if len(id_changes) != 0:
            raise NotImplementedError('Changing id can only be done via the `reindex` method')

    def apply_attributes_to_services(self, new_attributes: dict):
        """
        Adds, or changes if already present, the attributes in new_attributes. Doesn't replace the dictionary
        stored for the Services presently, so no data is lost, unless it is being overwritten. Changing IDs this way
        with result in an error. Use Service's `reindex` method instead.
        :param new_attributes: keys are Service IDs and values are dictionaries of data to add/replace if present
        :return:
        """
        self._verify_no_id_change(new_attributes)
        services = list(new_attributes.keys())
        old_attribs = [deepcopy(self._graph.graph['services'][service]) for service in services]
        new_attribs = [{**self._graph.graph['services'][service], **new_attributes[service]} for service in services]

        self._graph.graph['change_log'] = self.change_log().modify_bunch('service', services, old_attribs, services,
                                                                         new_attribs)

        for service, new_service_attribs in zip(services, new_attribs):
            self._graph.graph['services'][service] = new_service_attribs
        logging.info(f'Changed Service attributes for {len(services)} services')

    def apply_attributes_to_routes(self, new_attributes: dict):
        """
        Adds, or changes if already present, the attributes in new_attributes. Doesn't replace the dictionary
        stored for the Routes presently, so no data is lost, unless it is being overwritten. Changing IDs this way
        with result in an error. Use Route's `reindex` method instead.
        :param new_attributes: keys are Route IDs and values are dictionaries of data to add/replace if present
        :return:
        """
        self._verify_no_id_change(new_attributes)
        routes = list(new_attributes.keys())
        old_attribs = [deepcopy(self._graph.graph['routes'][route]) for route in routes]
        new_attribs = [{**self._graph.graph['routes'][route], **new_attributes[route]} for route in routes]

        self._graph.graph['change_log'] = self.change_log().modify_bunch('route', routes, old_attribs, routes,
                                                                         new_attribs)

        for route, new_route_attribs in zip(routes, new_attribs):
            self._graph.graph['routes'][route] = new_route_attribs
        logging.info(f'Changed Route attributes for {len(routes)} routes')

    def apply_attributes_to_stops(self, new_attributes: dict):
        """
        Adds, or changes if already present, the attributes in new_attributes. Doesn't replace the dictionary
        stored for the Stops presently, so no data is lost, unless it is being overwritten. Changing IDs this way
        with result in an error. Use Stop's `reindex` method instead.
        :param new_attributes: keys are Stop IDs and values are dictionaries of data to add/replace if present
        :return:
        """
        self._verify_no_id_change(new_attributes)
        stops = list(new_attributes.keys())
        old_attribs = [deepcopy(self._graph.nodes[stop]) for stop in stops]
        new_attribs = [{**self._graph.nodes[stop], **new_attributes[stop]} for stop in stops]

        self._graph.graph['change_log'] = self.change_log().modify_bunch('stop', stops, old_attribs, stops, new_attribs)

        nx.set_node_attributes(self._graph, dict(zip(stops, new_attribs)))
        logging.info(f'Changed Stop attributes for {len(stops)} stops')

    def apply_function_to_services(self, function, location: str):
        """
        Applies a function or mapping to Services within the Schedule. Fails silently, if the keys referred to by the
        function are not present, they will not be considered. The function will only be applied where it is possible.
        :param function: function, a callable, of Service attributes dictionary returning a value that should be stored
            under `location` or a dictionary mapping - in the case of a dictionary all values stored under `location`
            will be mapped to new values given by the mapping, if they are present.
        :param location: where to save the results: string defining the key in the Service attributes dictionary
        :return:
        """
        new_attributes = graph_operations.apply_to_attributes(self._graph.graph['services'].items(), function, location)
        self.apply_attributes_to_services(new_attributes)

    def apply_function_to_routes(self, function, location: str):
        """
        Applies a function or mapping to Routes within the Schedule. Fails silently, if the keys referred to by the
        function are not present, they will not be considered. The function will only be applied where it is possible.
        :param function: function, a callable, of Route attributes dictionary returning a value that should be stored
            under `location` or a dictionary mapping - in the case of a dictionary all values stored under `location`
            will be mapped to new values given by the mapping, if they are present.
        :param location: where to save the results: string defining the key in the Route attributes dictionary
        :return:
        """
        new_attributes = graph_operations.apply_to_attributes(self._graph.graph['routes'].items(), function, location)
        self.apply_attributes_to_routes(new_attributes)

    def apply_function_to_stops(self, function, location: str):
        """
        Applies a function or mapping to Stops within the Schedule. Fails silently, if the keys referred to by the
        function are not present, they will not be considered. The function will only be applied where it is possible.
        :param function: function, a callable, of Stop attributes dictionary returning a value that should be stored
            under `location` or a dictionary mapping - in the case of a dictionary all values stored under `location`
            will be mapped to new values given by the mapping, if they are present.
        :param location: where to save the results: string defining the key in the Stop attributes dictionary
        :return:
        """
        new_attributes = graph_operations.apply_to_attributes(self._graph.nodes(data=True), function, location)
        self.apply_attributes_to_stops(new_attributes)

    def _compare_stops_data(self, g):
        stop_data_in_g = {k: {_k: _v for _k, _v in v.items() if _k not in {'routes', 'services'}} for k, v in
                          dict(g.nodes(data=True)).items()}
        stops_without_data = []
        stops_with_conflicting_data = []

        for stop, data in stop_data_in_g.items():
            if stop in self._graph.nodes():
                schedule_stop_data = {_k: _v for _k, _v in dict(self._graph.nodes[stop]).items() if
                                      _k not in {'routes', 'services'}}
                if (not data) and (not schedule_stop_data):
                    stops_without_data.append(stop)
                if data:
                    diff = list(dictdiffer.diff(data, schedule_stop_data))
                    # look for 'change' diffs as that has potential to overwrite/loose data
                    if [event for event in diff if event[0] == 'change']:
                        stops_with_conflicting_data.append(stop)
            elif not data:
                stops_without_data.append(stop)
        return stops_without_data, stops_with_conflicting_data

    def add_service(self, service: Service, force=False):
        """
        Adds a service to Schedule.
        :param service: genet.Service object, must have index unique w.r.t. Services already in the Schedule
        :param force: force the add, even if the stops in the Service have data conflicting with the stops of the same
            IDs that are already in the Schedule. This will force the Service to be added, the stops data of currently
            in the Schedule will persist. If you want to change the data for stops use `apply_attributes_to_stops` or
            `apply_function_to_stops`.
        :return:
        """
        if self.has_service(service.id):
            raise ServiceIndexError(f'Service with ID `{service.id}` already exists in the Schedule.')
        for route in service.routes():
            if self.has_route(route.id):
                logging.warning(f'Route with ID `{route.id}` within this Service `{service.id}` already exists in the '
                                f'Schedule. This Route will be reindexed to `{service.id}_{route.id}`')
                route.reindex(f'{service.id}_{route.id}')

        g = service.graph()
        stops_without_data, stops_with_conflicting_data = self._compare_stops_data(g)
        if stops_without_data:
            logging.warning(f'The following stops are missing data: {stops_without_data}')
        if stops_with_conflicting_data:
            if force:
                logging.warning(f'The following stops will inherit the data currently stored under those Stop IDs in '
                                f'the Schedule: {stops_with_conflicting_data}.')
            else:
                raise ConflictingStopData("The following stops would inherit data currently stored under those "
                                          f"Stop IDs in the Schedule: {stops_with_conflicting_data}. Use `force=True` "
                                          "to continue with this operation in this manner. If you want to change the "
                                          "data for stops use `apply_attributes_to_stops` or "
                                          "`apply_function_to_stops`.")
        nodes = dict_support.merge_complex_dictionaries(
            dict(g.nodes(data=True)), dict(self._graph.nodes(data=True)))
        edges = dict_support.combine_edge_data_lists(
            list(g.edges(data=True)), list(self._graph.edges(data=True)))
        graph_routes = dict_support.merge_complex_dictionaries(
            g.graph['routes'], self._graph.graph['routes'])
        graph_services = dict_support.merge_complex_dictionaries(
            g.graph['services'], self._graph.graph['services'])
        self._graph.graph['route_to_service_map'] = {**self._graph.graph['route_to_service_map'],
                                                     **g.graph['route_to_service_map']}
        self._graph.graph['service_to_route_map'] = {**self._graph.graph['service_to_route_map'],
                                                     **g.graph['service_to_route_map']}

        self._graph.add_nodes_from(nodes)
        self._graph.add_edges_from(edges)
        nx.set_node_attributes(self._graph, nodes)
        self._graph.graph['routes'] = graph_routes
        self._graph.graph['services'] = graph_services

        service_data = self._graph.graph['services'][service.id]
        route_ids = list(service.route_ids())
        self._graph.graph['change_log'].add(object_type='service', object_id=service.id, object_attributes=service_data)
        logging.info(f'Added Service with index `{service.id}`, data={service_data} and Routes: {route_ids}')
        service._graph = self._graph
        return service

    def remove_service(self, service_id):
        """
        Removes Service under index `service_id`
        :param service_id:
        :return:
        """
        if not self.has_service(service_id):
            raise ServiceIndexError(f'Service with ID `{service_id}` does not exist in the Schedule. '
                                    "Cannot remove a Service that isn't present.")
        service = self[service_id]
        service_data = self._graph.graph['services'][service_id]
        route_ids = set(self._graph.graph['service_to_route_map'][service_id])
        for stop in service.reference_nodes():
            self._graph.nodes[stop]['routes'] = list(set(self._graph.nodes[stop]['routes']) - route_ids)
            self._graph.nodes[stop]['services'] = list(set(self._graph.nodes[stop]['services']) - {service_id})
        for u, v in service.reference_edges():
            self._graph[u][v]['routes'] = list(set(self._graph[u][v]['routes']) - route_ids)
            self._graph[u][v]['services'] = list(set(self._graph[u][v]['services']) - {service_id})

        del self._graph.graph['services'][service_id]
        del self._graph.graph['service_to_route_map'][service_id]
        for r_id in route_ids:
            del self._graph.graph['route_to_service_map'][r_id]
            del self._graph.graph['routes'][r_id]
        self._graph.graph['change_log'].remove(object_type='service', object_id=service_id,
                                               object_attributes=service_data)
        logging.info(f'Removed Service with index `{service_id}`, data={service_data} and Routes: {route_ids}')

    def add_route(self, service_id, route: Route, force=False):
        """
        Adds route to a service already in the Schedule.
        :param service_id: service id in the Schedule to add the route to
        :param route: Route object to add
        :param force: force the add, even if the stops in the Route have data conflicting with the stops of the same
            IDs that are already in the Schedule. This will force the Route to be added, the stops data of currently
            in the Schedule will persist. If you want to change the data for stops use `apply_attributes_to_stops` or
            `apply_function_to_stops`.
        :return:
        """
        if not self.has_service(service_id):
            raise ServiceIndexError(f'Service with ID `{service_id}` does not exist in the Schedule. '
                                    'You must add a Route to an existing Service, or add a new Service')
        if self.has_route(route.id):
            service = self[service_id]
            logging.warning(f'Route with ID `{route.id}` within already exists in the Schedule. '
                            f'This Route will be reindexed to `{service_id}_{len(service)+1}`')
            route.reindex(f'{service_id}_{len(service)+1}')

        g = route.graph()
        stops_without_data, stops_with_conflicting_data = self._compare_stops_data(g)
        if stops_without_data:
            logging.warning(f'The following stops are missing data: {stops_without_data}')
        if stops_with_conflicting_data:
            if force:
                logging.warning(f'The following stops will inherit the data currently stored under those Stop IDs in '
                                f'the Schedule: {stops_with_conflicting_data}.')
            else:
                raise ConflictingStopData("The following stops would inherit data currently stored under those "
                                          f"Stop IDs in the Schedule: {stops_with_conflicting_data}. Use `force=True` "
                                          "to continue with this operation in this manner. If you want to change the "
                                          "data for stops use `apply_attributes_to_stops` or "
                                          "`apply_function_to_stops`.")
        nx.set_edge_attributes(g, {edge: {'services': {service_id}} for edge in set(g.edges())})
        nx.set_node_attributes(g, {node: {'services': {service_id}} for node in set(g.nodes())})
        nodes = dict_support.merge_complex_dictionaries(
            dict(g.nodes(data=True)), dict(self._graph.nodes(data=True)))
        edges = dict_support.combine_edge_data_lists(
            list(g.edges(data=True)), list(self._graph.edges(data=True)))
        graph_routes = dict_support.merge_complex_dictionaries(
            g.graph['routes'], self._graph.graph['routes'])
        self._graph.graph['route_to_service_map'][route.id] = service_id
        self._graph.graph['service_to_route_map'][service_id].append(route.id)

        self._graph.add_nodes_from(nodes)
        self._graph.add_edges_from(edges)
        nx.set_node_attributes(self._graph, nodes)
        self._graph.graph['routes'] = graph_routes

        route_data = self._graph.graph['routes'][route.id]
        self._graph.graph['change_log'].add(object_type='route', object_id=route.id, object_attributes=route_data)
        logging.info(f'Added Route with index `{route.id}`, data={route_data} to Service `{service_id}` within the '
                     f'Schedule')
        route._graph = self._graph
        return route

    def remove_route(self, route_id):
        """
        Removes Route under index `route_id`
        :param route_id:
        :return:
        """
        if not self.has_route(route_id):
            raise RouteIndexError(f'Route with ID `{route_id}` does not exist in the Schedule. '
                                  "Cannot remove a Route that isn't present.")
        route = self.route(route_id)
        route_data = self._graph.graph['routes'][route_id]
        service_id = self._graph.graph['route_to_service_map'][route_id]

        for stop in route.reference_nodes():
            self._graph.nodes[stop]['routes'] = self._graph.nodes[stop]['routes'] - {route_id}
            if (not self._graph.nodes[stop]['routes']) or (
                    self._graph.nodes[stop]['routes'] & set(self._graph.graph['service_to_route_map'])):
                self._graph.nodes[stop]['services'] = self._graph.nodes[stop]['services'] - {service_id}
        for u, v in route.reference_edges():
            self._graph[u][v]['routes'] = self._graph[u][v]['routes'] - {route_id}
            if (not self._graph[u][v]['routes']) or (
                    set(self._graph[u][v]['routes']) & set(self._graph.graph['service_to_route_map'])):
                self._graph[u][v]['services'] = self._graph[u][v]['services'] - {service_id}

        self._graph.graph['service_to_route_map'][service_id].remove(route_id)
        del self._graph.graph['route_to_service_map'][route_id]
        del self._graph.graph['routes'][route_id]
        self._graph.graph['change_log'].remove(object_type='route', object_id=route_id, object_attributes=route_data)
        logging.info(f'Removed Route with index `{route_id}`, data={route_data}. '
                     f'It was linked to Service `{service_id}`.')

    def remove_stop(self, stop_id):
        """
        Removes Stop under index `stop_id`
        :param stop_id:
        :return:
        """
        if not self.has_stop(stop_id):
            raise StopIndexError(f'Stop with ID `{stop_id}` does not exist in the Schedule. '
                                 "Cannot remove a Stop that isn't present.")

        stop_data = self._graph.nodes[stop_id]
        routes_affected = stop_data.pop('routes')
        services_affected = stop_data.pop('services')
        self._graph.remove_node(stop_id)
        self._graph.graph['change_log'].remove(object_type='stop', object_id=stop_id, object_attributes=stop_data)
        logging.info(f'Removed Stop with index `{stop_id}`, data={stop_data}. '
                     f'Routes affected: {routes_affected}. Services affected: {services_affected}.')

    def remove_unsused_stops(self):
        stops_to_remove = []
        for stop, data in self._graph.nodes(data='routes'):
            if not data:
                stops_to_remove.append(stop)
        for stop in stops_to_remove:
            self.remove_stop(stop)
        logging.info(f'Removed Stops with indecies `{stops_to_remove}` which were not used by any Routes.')

    def is_strongly_connected(self):
        if nx.number_strongly_connected_components(self.graph()) == 1:
            return True
        return False

    def has_self_loops(self):
        return list(nx.nodes_with_selfloops(self.graph()))

    def validity_of_services(self):
        return [service.is_valid_service() for service in self.services()]

    def has_valid_services(self):
        return all(self.validity_of_services())

    def invalid_services(self):
        return [service for service in self.services() if not service.is_valid_service()]

    def is_valid_schedule(self, return_reason=False):
        invalid_stages = []
        valid = True

        if not self.has_valid_services():
            valid = False
            invalid_stages.append('not_has_valid_services')

        if return_reason:
            return valid, invalid_stages
        return valid

    def generate_validation_report(self):
        return schedule_validation.generate_validation_report(schedule=self)

    def generate_standard_outputs(self, output_dir, gtfs_day='19700101', include_shp_files=False):
        """
        Generates geojsons that can be used for generating standard kepler visualisations.
        These can also be used for validating network for example inspecting link capacity, freespeed, number of lanes,
        the shape of modal subgraphs.
        :param output_dir: path to folder where to save resulting geojsons
        :param gtfs_day: day in format YYYYMMDD for the network's schedule for consistency in visualisations,
        defaults to 1970/01/01 otherwise
        :return: None
        """
        gngeojson.generate_standard_outputs_for_schedule(self, output_dir, gtfs_day, include_shp_files)
        logging.info('Finished generating standard outputs. Zipping folder.')
        persistence.zip_folder(output_dir)

    def write_to_matsim(self, output_dir):
        persistence.ensure_dir(output_dir)
        matsim_xml_writer.write_matsim_schedule(output_dir, self)
        matsim_xml_writer.write_vehicles(output_dir, self.vehicles, self.vehicle_types)
        self.write_extras(output_dir)

    def write_extras(self, output_dir):
        self.change_log().export(os.path.join(output_dir, 'schedule_change_log.csv'))

    def to_geodataframe(self):
        """
        Generates GeoDataFrames of the Schedule graph in Schedule's crs
        :return: dict with keys 'nodes' and 'links', values are the GeoDataFrames corresponding to nodes and edges
        """
        return gngeojson.generate_geodataframes(self._graph)

    def to_json(self):
        stop_keys = {d.name for d in graph_operations.get_attribute_schema(self._graph.nodes(data=True)).children}
        stop_keys = stop_keys - {'routes', 'services', 'additional_attributes', 'epsg'}
        stops = self.stop_attribute_data(keys=stop_keys)
        services = self._graph.graph['services']
        for service_id, data in services.items():
            data['routes'] = {route_id: self._graph.graph['routes'][route_id] for route_id in
                              self._graph.graph['service_to_route_map'][service_id]}
        d = {'stops': stops.T.to_dict(), 'services': services}
        if self.minimal_transfer_times:
            d['minimal_transfer_times'] = self.minimal_transfer_times
        return {'schedule': d, 'vehicles': {'vehicle_types': self.vehicle_types, 'vehicles': self.vehicles}}

    def write_to_json(self, output_dir):
        """
        Writes Schedule to a single JSON file with stops, services, vehicles and minimum transfer times (if applicable)
        :param output_dir: output directory
        :return:
        """
        persistence.ensure_dir(output_dir)
        logging.info(f'Saving Schedule to JSON in {output_dir}')
        with open(os.path.join(output_dir, 'schedule.json'), 'w') as outfile:
            json.dump(self.to_json(), outfile)
        self.write_extras(output_dir)

    def write_to_geojson(self, output_dir, epsg):
        """
        Writes Schedule graph to nodes and edges geojson files.
        :param output_dir: output directory
        :param epsg: projection if the geometry is to be reprojected, defaults to own projection
        :return:
        """
        persistence.ensure_dir(output_dir)
        _gdfs = self.to_geodataframe()
        if epsg is not None:
            _gdfs['nodes'] = _gdfs['nodes'].to_crs(epsg)
            _gdfs['links'] = _gdfs['links'].to_crs(epsg)
        logging.info(f'Saving Schedule to GeoJSON in {output_dir}')
        gngeojson.save_geodataframe(_gdfs['nodes'], 'schedule_nodes', output_dir)
        gngeojson.save_geodataframe(_gdfs['links'], 'schedule_links', output_dir)
        gngeojson.save_geodataframe(_gdfs['nodes']['geometry'], 'schedule_nodes_geometry_only', output_dir)
        gngeojson.save_geodataframe(_gdfs['links']['geometry'], 'schedule_links_geometry_only', output_dir)
        self.write_extras(output_dir)

    def to_gtfs(self, gtfs_day, mode_to_route_type: dict = None):
        """
        Transforms Schedule in to GTFS-like format. It's not full GTFS as it only represents one day, misses a lot
         of optional data and does not include `agency.txt` required file. Produces 'stops', 'routes', 'trips',
         'stop_times', 'calendar' tables.
        :param gtfs_day: day used for GTFS when creating the network in YYYYMMDD format
        :param mode_to_route_type: PT modes in Route objects to route type code by default uses
        https://developers.google.com/transit/gtfs/reference#routestxt
        {
            "tram": 0, "subway": 1, "rail": 2, "bus": 3, "ferry": 4, "cablecar": 5, "gondola": 6, "funicular": 7
        }
        Reference for extended mode types:
        https://developers.google.com/transit/gtfs/reference/extended-route-types

        :return: Dictionary, keys are the names of the tables e.g. `stops` for the `stops.txt` file, values are
            pandas.DataFrame tables.
        """
        stops = self.stop_attribute_data(
            keys=['id', 'name', 'lat', 'lon', 'stop_code', 'stop_desc', 'zone_id', 'stop_url', 'location_type',
                  'parent_station', 'stop_timezone', 'wheelchair_boarding', 'level_id', 'platform_code'])
        stops = stops.rename(columns={'id': 'stop_id', 'name': 'stop_name', 'lat': 'stop_lat', 'lon': 'stop_lon'})

        routes = self.route_attribute_data(
            keys=['id', 'route_short_name', 'route_long_name', 'mode', 'agency_id', 'route_desc', 'route_url',
                  'route_type', 'route_color', 'route_text_color', 'route_sort_order', 'continuous_pickup',
                  'continuous_drop_off'])
        if mode_to_route_type is None:
            mode_to_route_type = {
                "tram": 0, "subway": 1, "rail": 2, "bus": 3, "ferry": 4, "cablecar": 5, "gondola": 6, "funicular": 7
            }
        routes.loc[routes['route_type'].isna(), 'route_type'] = routes.loc[routes['route_type'].isna(), 'mode'].map(
            mode_to_route_type)
        routes['route_id'] = routes['id'].map(self._graph.graph['route_to_service_map'])
        routes = routes.drop(['mode', 'id'], axis=1)
        routes = routes.groupby('route_id').first().reset_index()

        trips = self.route_attribute_data(keys=['id', 'ordered_stops', 'arrival_offsets', 'departure_offsets'])
        trips = trips.merge(self.route_trips_to_dataframe(), left_on='id', right_on='route_id')
        trips['route_id'] = trips['service_id']

        # expand the frame for stops and offsets to get stop times
        trips['stop_sequence'] = trips['ordered_stops'].apply(lambda x: list(range(len(x))))
        trips['departure_offsets'] = trips['departure_offsets'].apply(lambda x: list(map(use_schedule.get_offset, x)))
        trips['arrival_offsets'] = trips['arrival_offsets'].apply(lambda x: list(map(use_schedule.get_offset, x)))
        stop_times = DataFrame({
            col: np.repeat(trips[col].values, trips['ordered_stops'].str.len())
            for col in {'trip_id', 'trip_departure_time'}}
        ).assign(stop_id=np.concatenate(trips['ordered_stops'].values),
                 stop_sequence=np.concatenate(trips['stop_sequence'].values),
                 departure_time=np.concatenate(trips['departure_offsets'].values),
                 arrival_time=np.concatenate(trips['arrival_offsets'].values))
        stop_times['arrival_time'] = (stop_times['trip_departure_time'] + stop_times['arrival_time']).dt.strftime(
            '%H:%M:%S')
        stop_times['departure_time'] = (stop_times['trip_departure_time'] + stop_times['departure_time']).dt.strftime(
            '%H:%M:%S')
        stop_times = stop_times.drop(['trip_departure_time'], axis=1)
        for col in ['stop_headsign', 'pickup_type', 'drop_off_type', 'continuous_pickup', 'continuous_drop_off',
                    'shape_dist_traveled', 'timepoint']:
            stop_times[col] = float('nan')

        # finish off trips frame
        trips = trips[['route_id', 'service_id', 'trip_id']]
        for col in ['trip_headsign', 'trip_short_name', 'direction_id', 'block_id', 'shape_id', 'wheelchair_accessible',
                    'bikes_allowed']:
            trips[col] = float('nan')

        calendar = DataFrame(routes['route_id'])
        for col in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
            calendar[col] = 1
        calendar['start_date'] = gtfs_day
        calendar['end_date'] = gtfs_day
        return {'stops': stops, 'routes': routes, 'trips': trips, 'stop_times': stop_times, 'calendar': calendar}

    def write_to_csv(self, output_dir, gtfs_day='19700101', file_extention='csv'):
        """
        Writes 'stops', 'routes', 'trips', 'stop_times', 'calendar' tables to CSV files
        :param output_dir: folder to output csv or txt files
        :param gtfs_day: day used for GTFS when creating the network in YYYYMMDD format defaults to 19700101
        :param file_extention: csv by default, or txt
        :return: None
        """
        persistence.ensure_dir(output_dir)
        logging.info(f'Saving Schedule to GTFS {file_extention} in {output_dir}')
        for table, df in self.to_gtfs(gtfs_day).items():
            file_path = os.path.join(output_dir, f'{table}.{file_extention}')
            logging.info(f'Saving {file_path}')
            df.to_csv(file_path)
        self.write_extras(output_dir)

    def write_to_gtfs(self, output_dir, gtfs_day='19700101'):
        """
        Writes 'stops', 'routes', 'trips', 'stop_times', 'calendar' tables to CSV files
        :param output_dir: folder to output txt files
        :param gtfs_day: day used for GTFS when creating the network in YYYYMMDD format defaults to 19700101
        :return: None
        """
        self.write_to_csv(output_dir, gtfs_day=gtfs_day, file_extention='txt')


def verify_graph_schema(graph):
    if not isinstance(graph, nx.DiGraph):
        raise ScheduleElementGraphSchemaError(
            f'Object of type {type(graph)} passed. The graph for a schedule element needs '
            f'to be a networkx.DiGraph')

    required_stop_attributes = {'x', 'y', 'id', 'epsg'}
    for node, node_attribs in graph.nodes(data=True):
        if not required_stop_attributes.issubset(set(node_attribs.keys())):
            missing_attribs = required_stop_attributes - set(node_attribs.keys())
            raise ScheduleElementGraphSchemaError(f'Node/Stop {node} is missing the following attributes: '
                                                  f'{missing_attribs}')

    required_route_attributes = {'arrival_offsets', 'ordered_stops', 'route_short_name', 'mode', 'departure_offsets',
                                 'trips'}
    if 'routes' not in graph.graph:
        raise ScheduleElementGraphSchemaError('Graph is missing `routes` attribute')
    else:
        for route_id, route_dict in graph.graph['routes'].items():
            if not required_route_attributes.issubset(set(route_dict.keys())):
                missing_attribs = required_route_attributes - set(route_dict.keys())
                raise ScheduleElementGraphSchemaError(f'Route {route_id} is missing the following attributes: '
                                                      f'{missing_attribs}')

    required_service_attributes = {'id'}
    if 'services' not in graph.graph:
        raise ScheduleElementGraphSchemaError('Graph is missing `services` attribute')
    else:
        for service_id, service_dict in graph.graph['services'].items():
            if not required_service_attributes.issubset(set(service_dict.keys())):
                missing_attribs = required_service_attributes - set(service_dict.keys())
                raise ScheduleElementGraphSchemaError(f'Service {service_id} is missing the following attributes: '
                                                      f'{missing_attribs}')


def read_vehicle_types(yml):
    """
    :param yml: path to .yml file based on example vehicles config in `genet/configs/vehicles/vehicle_definitions.yml`
        or a bytes stream of that file
    :return:
    """
    if persistence.is_yml(yml):
        yml = io.open(yml, mode='r')
    return yaml.load(yml, Loader=yaml.FullLoader)['VEHICLE_TYPES']
