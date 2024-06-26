import io
import itertools
import json
import logging
import math
import os
from abc import ABC, abstractmethod
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timedelta
from typing import Callable, Iterator, Literal, Optional, Union

import dictdiffer
import geopandas as gpd
import importlib_resources
import networkx as nx
import numpy as np
import pandas as pd
import yaml
from keplergl import KeplerGl
from pandas import DataFrame, Series
from pyproj import Geod, Transformer
from s2sphere import CellId
from shapely.geometry.base import BaseGeometry

import genet.modify.change_log as change_log
import genet.modify.schedule as mod_schedule
import genet.output.matsim_xml_writer as matsim_xml_writer
import genet.output.sanitiser as sanitiser
import genet.output.spatial as spatial_output
import genet.use.schedule as use_schedule
import genet.utils.dict_support as dict_support
import genet.utils.graph_operations as graph_operations
import genet.utils.io
import genet.utils.parallel as parallel
import genet.utils.persistence as persistence
import genet.utils.plot as plot
import genet.utils.spatial as spatial
import genet.validate.schedule as schedule_validation
from genet.exceptions import (
    ConflictingStopData,
    InconsistentVehicleModeError,
    RouteIndexError,
    RouteInitialisationError,
    ScheduleElementGraphSchemaError,
    ServiceIndexError,
    ServiceInitialisationError,
    StopIndexError,
    UndefinedCoordinateSystemError,
)

# number of decimal places to consider when comparing lat lons
SPATIAL_TOLERANCE = 8


class ScheduleElement(ABC):
    """
    Base class for Route, Service and Schedule
    """

    def __init__(self):
        self._graph: nx.DiGraph
        # check if in graph first
        if "crs" in self._graph.graph:
            self.epsg = self._graph.graph["crs"]
        else:
            self.epsg = self.find_epsg()
            self._graph.graph["crs"] = self.epsg

    def _surrender_to_graph(self):
        d = deepcopy(self.__dict__)
        return d

    def _get_service_from_graph(self, service_id):
        if service_id in self._graph.graph["services"]:
            return Service(_graph=self._graph, **self._graph.graph["services"][service_id])
        else:
            raise ServiceIndexError(f"Service with index {service_id} not found")

    def _get_route_from_graph(self, route_id):
        if route_id in self._graph.graph["routes"]:
            return Route(_graph=self._graph, **self._graph.graph["routes"][route_id])
        else:
            raise RouteIndexError(f"Route with index {route_id} not found")

    def _stop_ids_in_graph(self, stop_ids: list[str]):
        return set(stop_ids).issubset(set(self._graph.nodes))

    def _route_ids_in_graph(self, route_ids: list[str]):
        return set(route_ids).issubset(set(self._graph.graph["routes"].keys()))

    def _service_ids_in_graph(self, service_ids: list[str]):
        return set(service_ids).issubset(set(self._graph.graph["services"].keys()))

    def change_log(self):
        return change_log.ChangeLog(df=self._graph.graph["change_log"])

    @abstractmethod
    def _add_additional_attribute_to_graph(self, k, v):
        pass

    def add_additional_attributes(self, attribs: dict):
        """Adds attributes defined by keys of the attribs dictionary with values of the corresponding values.

        Args:
            attribs (dict): The additional attributes `{attribute_name: attribute_value}`
        """
        for k, v in attribs.items():
            if k not in self.__dict__:
                setattr(self, k, v)
                if "_graph" in self.__dict__:
                    self._add_additional_attribute_to_graph(k, v)

    def has_attrib(self, attrib_name):
        return attrib_name in self.__dict__

    @abstractmethod
    def reference_nodes(self):
        pass

    def route_reference_nodes(self, route_id: Union[str, int]) -> set:
        """Method to extract nodes for a route straight from the graph.

        Equivalent to route_object.reference_nodes() but faster if used from a higher order object like Service or Schedule.

        Args:
            route_id (Union[str, int]): Route in graph.

        Returns:
            set: graph nodes for the route with ID: route_id - not ordered
        """
        return {
            node
            for node, node_routes in self._graph.nodes(data="routes")
            if route_id in node_routes
        }

    def service_reference_nodes(self, service_id: Union[str, int]) -> set:
        """Method to extract nodes for a service straight from the graph.

        Equivalent to service_object.reference_nodes() but faster if used from a higher order object: Schedule.

        Args:
            service_id (Union[str, int]): Service in graph.

        Returns:
            set: graph nodes for the service with ID: service_id - not ordered.
        """
        return {
            node
            for node, node_services in self._graph.nodes(data="services")
            if service_id in node_services
        }

    @abstractmethod
    def reference_edges(self):
        pass

    def route_reference_edges(self, route_id: Union[str, int]) -> set:
        """Method to extract edges for a route straight from the graph.

        Equivalent to route_object.reference_edges() but faster if used from a higher order object like Service or Schedule.

        Args:
            route_id (Union[str, int]): Route in graph.

        Returns:
            set: graph edges for the route with ID: route_id
        """
        return {
            (u, v)
            for u, v, edge_routes in self._graph.edges(data="routes")
            if route_id in edge_routes
        }

    def service_reference_edges(self, service_id: Union[str, int]) -> set:
        """Method to extract nodes for a service straight from the graph

        Equivalent to service_object.reference_edges() but faster if used from a higher order object: Schedule.

        Args:
            service_id (Union[str, int]): Service in graph.

        Returns:
            set: graph edges for the service with ID: service_id

        """
        return {
            (u, v)
            for u, v, edge_services in self._graph.edges(data="services")
            if service_id in edge_services
        }

    @abstractmethod
    def plot(self, output_dir: str = "", data: Union[bool, set] = False) -> KeplerGl:
        """Plots the schedule element on a kepler map.

        Ensure all prerequisites are installed https://docs.kepler.gl/docs/keplergl-jupyter#install.

        Args:
            output_dir (str, optional): Output directory for the image, if passed, will save plot to html. Defaults to "".
            data (Union[bool, set], optional):
                If False, only the geometry and ID will be visible.
                If True, will visualise all data on the map (not suitable for large networks)
                If a set of keys e.g. {'name'}, will visualise those keys.
                Defaults to False.

        Returns:
            KeplerGl: Kepler plot object
        """

    def _remove_routes_from_nodes(self, nodes: set[str], route_ids: set[str]):
        for node in nodes:
            self._graph.nodes[node]["routes"] = self._graph.nodes[node]["routes"] - route_ids

    def _remove_routes_from_edges(self, edges: set[tuple[str, str]], route_ids: set[str]):
        for u, v in edges:
            self._graph[u][v]["routes"] = self._graph[u][v]["routes"] - route_ids

    def _add_routes_to_nodes(self, nodes: set[str], route_ids: set[str]):
        for node in nodes:
            self._graph.nodes[node]["routes"] = self._graph.nodes[node]["routes"] | route_ids

    def _add_routes_to_edges(self, edges: set[tuple[str, str]], route_ids: set[str]):
        for u, v in edges:
            self._graph[u][v]["routes"] = self._graph[u][v]["routes"] | route_ids

    def _remove_services_from_nodes(self, nodes: set[str], service_ids: set[str]):
        for node in nodes:
            self._graph.nodes[node]["services"] = self._graph.nodes[node]["services"] - service_ids

    def _remove_services_from_edges(self, edges: set[tuple[str, str]], service_ids: set[str]):
        for u, v in edges:
            self._graph[u][v]["services"] = self._graph[u][v]["services"] - service_ids

    def _add_services_to_nodes(self, nodes: set[str], service_ids: set[str]):
        for node in nodes:
            self._graph.nodes[node]["services"] = self._graph.nodes[node]["services"] | service_ids

    def _add_services_to_edges(self, edges: set[tuple[str, str]], service_ids: set[str]):
        for u, v in edges:
            self._graph[u][v]["services"] = self._graph[u][v]["services"] | service_ids

    def _generate_services_on_nodes(self, nodes: set[str]):
        for node in nodes:
            self._graph.nodes[node]["services"] = {
                self._graph.graph["route_to_service_map"][r_id]
                for r_id in self._graph.nodes[node]["routes"]
            }

    def _generate_services_on_edges(self, edges: set[tuple[str, str]]):
        for u, v in edges:
            self._graph[u][v]["services"] = {
                self._graph.graph["route_to_service_map"][r_id]
                for r_id in self._graph[u][v]["routes"]
            }

    def stop(self, stop_id):
        stop_data = {
            k: v
            for k, v in dict(self._graph.nodes[stop_id]).items()
            if k not in {"routes", "services"}
        }
        return Stop(**stop_data)

    def stops(self) -> Iterator["Stop"]:
        """
        Yields:
            Iterable returns stops in the Schedule Element
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
            mode_map[route.mode] = mode_map[route.mode] | {
                (u, v) for u, v in route.reference_edges()
            }
        return mode_map

    def graph(self):
        return nx.DiGraph(nx.edge_subgraph(self._graph, self.reference_edges()))

    def subgraph(self, edges):
        return nx.DiGraph(nx.edge_subgraph(self.graph(), edges))

    def stop_to_service_ids_map(self):
        return dict(self.graph().nodes(data="services"))

    def stop_to_route_ids_map(self):
        return dict(self.graph().nodes(data="routes"))

    def reproject(self, new_epsg: str, processes: int = 1):
        """Changes projection of the element to `new_epsg`.

        Args:
            new_epsg (str):
                New projection, e.g., "epsg:1234".
            processes (int, optional):
                Number of parallel processes to use when reprojecting. Defaults to 1.
        """
        if not self.stops_have_this_projection(new_epsg):
            g = self.graph()
            reprojected_node_attribs = parallel.multiprocess_wrap(
                data=dict(g.nodes(data=True)),
                split=parallel.split_dict,
                apply=mod_schedule.reproj_stops,
                combine=parallel.combine_dict,
                processes=processes,
                new_epsg=new_epsg,
            )
            nx.set_node_attributes(self._graph, reprojected_node_attribs)
            self.epsg = new_epsg

    def unique_stop_projections(self):
        return {x[1] for x in self.graph().nodes(data="epsg")}

    def stops_have_this_projection(self, epsg):
        return self.unique_stop_projections() == {epsg}

    def has_uniformly_projected_stops(self):
        return bool(len(self.unique_stop_projections()) == 1)

    def find_epsg(self):
        if "crs" in self._graph.graph:
            return self._graph.graph["crs"]
        else:
            epsg = list(
                {d for k, d in dict(self._graph.nodes(data="epsg", default="")).items()} - {""}
            )
            if epsg:
                if len(epsg) == 1:
                    return epsg[0]
                else:
                    return epsg
        return None

    @abstractmethod
    def service_attribute_data(
        self, keys: Union[list, str], index_name: Optional[str] = None
    ) -> pd.DataFrame:
        """Generates a pandas.DataFrame object indexed by Service IDs, with attribute data stored for Services under `key`.

        Args:
            keys (Union[list, str]):
                List of either a string e.g. 'name', or if accessing nested information, a dictionary.
                E.g. `{'attributes': {'osm:way:name': 'text'}}`.
            index_name (Optional[str], optional): gives the index_name to dataframes index. Defaults to None.
        Returns:
            pd.DataFrame: Service attribute data
        """

    @abstractmethod
    def route_attribute_data(self, keys: Union[list, str], index_name: Optional[str] = None):
        """Generates a pandas.DataFrame object indexed by Route IDs, with attribute data stored for Routes under `key`.

        Args:
            keys (Union[list, str]):
                List of either a string e.g. 'name', or if accessing nested information, a dictionary.
                E.g. `{'attributes': {'osm:way:name': 'text'}}`.
            index_name (Optional[str], optional): gives the index_name to dataframes index. Defaults to None.
        Returns:
            pd.DataFrame: Route attribute data
        """

    @abstractmethod
    def stop_attribute_data(self, keys: Union[list, str], index_name: Optional[str] = None):
        """Generates a pandas.DataFrame object indexed by Stop IDs, with attribute data stored for Stops under `key`.

        Args:
            keys (Union[list, str]):
                List of either a string e.g. 'name', or if accessing nested information, a dictionary.
                E.g. `{'attributes': {'osm:way:name': 'text'}}`.
            index_name (Optional[str], optional): gives the index_name to dataframes index. Defaults to None.
        Returns:
            pd.DataFrame: Stop attribute data
        """

    @abstractmethod
    def trips_with_stops_to_dataframe(self, gtfs_day: str = "19700101") -> pd.DataFrame:
        """Generates a DataFrame holding all the trips,
        their movements from stop to stop (in datetime with given GTFS day, if specified in `gtfs_day`) and vehicle IDs,
        next to the route ID and service ID.

        Args:
            gtfs_day (str, optional): day used for GTFS when creating the network in YYYYMMDD format. Defaults to "19700101".

        Returns:
            pd.DataFrame: Trips.
        """

    def route_trips_with_stops_to_dataframe(self, gtfs_day: str = "19700101") -> pd.DataFrame:
        logging.warning(
            "`route_trips_with_stops_to_dataframe` method is deprecated and will be replaced by "
            "`trips_to_dataframe` in later versions."
        )
        return self.trips_with_stops_to_dataframe(gtfs_day)

    def route_trips_to_dataframe(self, gtfs_day="19700101"):
        logging.warning(
            "`route_trips_to_dataframe` method is deprecated and will be replaced by `trips_to_dataframe`"
            "in later versions."
        )
        return self.trips_to_dataframe(gtfs_day)

    def speed_geodataframe(
        self, network_factor: float = 1.3, gdf_network_links: Optional[gpd.GeoDataFrame] = None
    ) -> gpd.GeoDataFrame:
        """DataFrame of speed for PT routes, in metres/second for each stop pair.

        !!! note
            - The unit of metres is not guaranteed - this assumes the object is in local metre-based projection.
            - If you pass a GeoDataFrame of genet.Network links you will get routed speeds as well as teleported with a factor
            - Assumes genet.Network links geometry if passed. If not, gives the stop-to-stop line geometry

        Args:
            network_factor (float, optional): Network factor to be applied to the Euclidean distance between stops. Defaults to 1.3.
            gdf_network_links (Optional[gpd.GeoDataFrame], optional):
                GeoDataFrame of genet.Network links, can be obtained using: `genet.Network.to_geodataframe()['links']`.
                Defaults to None.

        Returns:
            gpd.GeoDataFrame: Speeds for public transport routes.
        """
        df = self.trips_with_stops_to_dataframe()
        df["time"] = (df["arrival_time"] - df["departure_time"]).dt.total_seconds()
        df = df[
            [
                "service_id",
                "service_name",
                "route_id",
                "route_name",
                "mode",
                "from_stop",
                "to_stop",
                "from_stop_name",
                "to_stop_name",
                "time",
            ]
        ].drop_duplicates()
        df["distance"] = (
            df.apply(
                lambda row: spatial.distance_between_s2cellids(
                    self._graph.nodes[row["from_stop"]]["s2_id"],
                    self._graph.nodes[row["to_stop"]]["s2_id"],
                ),
                axis=1,
            )
            * network_factor
        )
        df["speed"] = df["distance"] / df["time"]
        if gdf_network_links is not None:
            network_distance_df = use_schedule.network_routed_distance_gdf(self, gdf_network_links)
            df = gpd.GeoDataFrame(
                df.merge(
                    network_distance_df,
                    left_on=["route_id", "from_stop", "to_stop"],
                    right_on=["id", "from_stop", "to_stop"],
                )
            )
            df["routed_speed"] = df["network_distance"] / df["time"]
        else:
            df["network_distance"] = float("nan")
            df["routed_speed"] = float("nan")
            schedule_links = self.to_geodataframe()["links"]
            df = gpd.GeoDataFrame(
                pd.merge(
                    df,
                    schedule_links[["u", "v", "geometry"]],
                    left_on=["from_stop", "to_stop"],
                    right_on=["u", "v"],
                ),
                crs=schedule_links.crs,
            )
            df.drop(["u", "v"], axis=1, inplace=True)
        return df.drop(["time", "distance", "network_distance"], axis=1)

    def average_route_speeds(self, network_factor: float = 1.3) -> dict:
        """Average speed for each route in object.

        Args:
            network_factor (float, optional): Does not consider network routes, network factor is applied to Euclidean distance. Defaults to 1.3.

        Returns:
            dict: Dictionary `{route_ID: average_speed_in_m_per_s}`
        """
        df = self.speed_geodataframe(network_factor=network_factor)
        # computing with all trips is redundant as the speeds for each trip for the same route are the same we can
        # select the first or random trip from each route, but depending on how it's done, it might not improve
        # performance very much
        return df.groupby("route_id")["speed"].mean().to_dict()

    @abstractmethod
    def trips_to_dataframe(self, gtfs_day: str = "19700101") -> pd.DataFrame:
        """Generates a DataFrame holding all the trips IDs,
        their departure times (in datetime with given GTFS day, if specified in `gtfs_day`) and vehicle IDs, next to the route ID and service ID.

        Check out also `trips_with_stops_to_dataframe` for a more complex version.
        All trips are expanded over all of their stops, giving scheduled timestamps of each trips expected to arrive and leave the stop.

        Args:
            gtfs_day (str, optional): day used for GTFS when creating the network in YYYYMMDD format. Defaults to "19700101".

        Returns:
            pd.DataFrame: Trips.
        """

    @abstractmethod
    def route(self, route_id: Union[str, int]) -> "Route":
        """Attempting to extract route from route given an id should yield itself unless index doesn't match.

        Args:
            route_id (Union[str, int]): ID to extract.

        Raises:
            IndexError: ID must match self ID.

        Returns:
            Route: This route.
        """

    def trips_headways(
        self,
        from_time: Optional[str] = None,
        to_time: Optional[str] = None,
        gtfs_day: str = "19700101",
    ) -> pd.DataFrame:
        """Generates a DataFrame holding all the trips IDs, their departure times and vehicle IDs, next to the route ID and service ID.

        Departure times given in datetime format with given GTFS day, if specified in `gtfs_day`.

        Adds two columns: `headway` and `headway_mins` by calculating the time difference in ordered trip departures for each unique route.

        This can also be done for a specific time frame by specifying from_time and to_time (or just one of them).

        Args:
            from_time (Optional[str], optional): "HH:MM:SS" format, used as lower time bound for subsetting. Defaults to None.
            to_time (Optional[str], optional): "HH:MM:SS" format, used as upper time bound for subsetting. Defaults to None.
            gtfs_day (str, optional): day used for GTFS when creating the network in YYYYMMDD format. Defaults to "19700101".

        Returns:
            pd.DataFrame: Departure and headway times.
        """
        df = (
            self.trips_to_dataframe(gtfs_day=gtfs_day)
            .sort_values(["route_id", "trip_departure_time"])
            .reset_index(drop=True)
        )

        year = int(gtfs_day[:4])
        month = int(gtfs_day[4:6])
        day = int(gtfs_day[6:8])

        df = df.groupby("route_id", group_keys=False).apply(get_headway)
        df["headway_mins"] = pd.to_timedelta(df["headway"]).dt.total_seconds() / 60

        if from_time is not None:
            hour, minute, second = list(map(int, from_time.split(":")))
            df = df[df["trip_departure_time"] >= datetime(year, month, day, hour, minute, second)]
        if to_time is not None:
            hour, minute, second = list(map(int, to_time.split(":")))
            df = df[df["trip_departure_time"] <= datetime(year, month, day, hour, minute, second)]

        return df

    def headway_stats(
        self,
        from_time: Optional[str] = None,
        to_time: Optional[str] = None,
        gtfs_day: str = "19700101",
    ) -> pd.DataFrame:
        """
        Generates a DataFrame calculating mean headway in minutes for all routes, with their service ID.
        This can also be done for a specific time frame by specifying from_time and to_time (or just one of them).

        Args:
            from_time (Optional[str], optional): "HH:MM:SS" format, used as lower time bound for subsetting. Defaults to None.
            to_time (Optional[str], optional): "HH:MM:SS" format, used as upper time bound for subsetting. Defaults to None.
            gtfs_day (str, optional): day used for GTFS when creating the network in YYYYMMDD format. Defaults to "19700101".

        Returns:
            pd.DataFrame: Headway stats.
        """
        df = self.trips_headways(from_time=from_time, to_time=to_time, gtfs_day=gtfs_day)

        groupby_cols = []
        if "service_id" in df.columns:
            groupby_cols.append("service_id")
        groupby_cols += ["route_id", "mode"]

        # first trips don't have a headway, they are kept as NaT and NaN
        if not df.empty:
            route_groups = df.groupby(by=groupby_cols)
            df = route_groups.describe()
            df = df["headway_mins"][["mean", "std", "max", "min"]]
            df["trip_count"] = route_groups.apply(len)
            df.reset_index(inplace=True)
            df = df.rename(
                columns={
                    "mean": "mean_headway_mins",
                    "std": "std_headway_mins",
                    "max": "max_headway_mins",
                    "min": "min_headway_mins",
                }
            )
        return df

    def to_geodataframe(self) -> dict[str, gpd.GeoDataFrame]:
        """Generates GeoDataFrames of the Schedule graph in Schedule's crs.

        Returns:
            dict[str, gpd.GeoDataFrame]: dict with keys 'nodes' and 'links', values are the GeoDataFrames corresponding to nodes and edges
        """
        return spatial_output.generate_geodataframes(self.graph())

    def kepler_map(self, output_dir="", file_name="kepler_map", data=False):
        gdf = self.to_geodataframe()
        if data is not True:
            gdf["links"] = sanitiser._subset_plot_gdf(
                data, gdf["links"], base_keys={"u", "v", "geometry"}
            )
            gdf["nodes"] = sanitiser._subset_plot_gdf(
                data, gdf["nodes"], base_keys={"id", "lat", "lon"}
            )

        m = plot.plot_geodataframes_on_kepler_map(
            {
                "schedule_links": sanitiser.sanitise_geodataframe(gdf["links"]),
                "schedule_stops": sanitiser.sanitise_geodataframe(gdf["nodes"]),
            },
            kepler_config="schedule",
        )
        if output_dir:
            persistence.ensure_dir(output_dir)
            m.save_to_html(file_name=os.path.join(output_dir, f"{file_name}.html"))
        return m


class Stop:
    def __init__(
        self,
        id: Union[str, int],
        x: Union[str, int, float],
        y: Union[str, int, float],
        epsg: str,
        transformer: Optional[Transformer] = None,
        name: str = "",
        **kwargs,
    ):
        """A transit stop that features in a Route object.

        Args:
            id (Union[str, int]): Unique identifier.
            x (Union[str, int, float]): x coordinate or lat if using 'epsg:4326'.
            y (Union[str, int, float]): y coordinate or lon if using 'epsg:4326'.
            epsg (str): Projection, e.g. "epsg:4326".
            transformer (Optional[Transformer], optional):
                E.g., result of pyproj.Transformer.from_crs(epsg, 'epsg:4326', always_xy=True).
                Optional but makes things MUCH faster if you're reading through a lot of stops in the same projection,
                 all stops are mapped back to 'epsg:4326' and indexed with s2sphere.
                 Defaults to None.
            name (str, optional): human readable name for the stop. Defaults to "".

        Keyword Args: Additional attributes which will be attached to the class.
        """
        self.id = id
        self.x = float(x)
        self.y = float(y)
        self.epsg = epsg
        self.name = name

        if ("lat" in kwargs) and ("lon" in kwargs):
            self.lat, self.lon = kwargs["lat"], kwargs["lon"]
        else:
            if self.epsg == "epsg:4326":
                self.lon, self.lat = float(x), float(y)
            else:
                if transformer is None:
                    transformer = Transformer.from_crs(self.epsg, "epsg:4326", always_xy=True)
                self.lon, self.lat = spatial.change_proj(x, y, transformer)
        if "s2_id" in kwargs:
            self.s2_id = kwargs["s2_id"]
        else:
            self.s2_id = spatial.generate_index_s2(lat=self.lat, lng=self.lon)

        if kwargs:
            self.add_additional_attributes(kwargs)

    def __eq__(self, other):
        return (self._round_lat() == other._round_lat()) and (
            self._round_lon() == other._round_lon()
        )

    def __hash__(self):
        return hash((self.id, self._round_lat(), self._round_lon()))

    def __repr__(self):
        return "<{} instance at {}: in {}>".format(self.__class__.__name__, id(self), self.epsg)

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
            return "{} ID: {}\nProjection: {}\nLat, Lon: {}, {}\nlinkRefId: {}".format(
                self.__class__.__name__,
                self.id,
                self.epsg,
                self._round_lat(),
                self._round_lon(),
                self.linkRefId,
            )
        else:
            return "{} ID: {}\nProjection: {}\nLat, Lon: {}, {}".format(
                self.__class__.__name__, self.id, self.epsg, self._round_lat(), self._round_lon()
            )

    def reproject(self, new_epsg: str, transformer: Optional[Transformer] = None):
        """Changes projection of a stop.

        If doing many stops, it's much quicker to pass the transformer as well as epsg.

        Args:
            new_epsg (str):
                New projection, e.g., "epsg:1234".
            transformer (Optional[Transformer], optional):
                E.g., result of pyproj.Transformer.from_crs(epsg, 'epsg:4326', always_xy=True).
                Optional but makes things MUCH faster if you're reading through a lot of stops in the same projection,
                 all stops are mapped back to 'epsg:4326' and indexed with s2sphere.
                 Defaults to None.
        """
        if transformer is None:
            transformer = Transformer.from_crs(self.epsg, new_epsg, always_xy=True)
        self.x, self.y = spatial.change_proj(self.x, self.y, transformer)
        self.epsg = new_epsg

    def add_additional_attributes(self, attribs: dict):
        """Adds attributes defined by keys of the attribs dictionary with values of the corresponding values.

        Ignores keys: 'id', 'x', 'y'.

        Args:
            attribs (dict): The additional attributes {attrribute_name: attribute_value}
        """
        for k, v in attribs.items():
            if k not in self.__dict__ or (not self.__dict__[k]):
                setattr(self, k, v)

    def additional_attribute(self, attrib_name):
        return self.__dict__[attrib_name]

    def is_exact(self, other):
        same_id = self.id == other.id
        same_lat = round(self.lat, SPATIAL_TOLERANCE) == round(other.lat, SPATIAL_TOLERANCE)
        same_lon = round(self.lon, SPATIAL_TOLERANCE) == round(other.lon, SPATIAL_TOLERANCE)
        return same_id and same_lat and same_lon

    def isin_exact(self, stops: list):
        for other in stops:
            if self.is_exact(other):
                return True
        return False

    def has_linkRefId(self):
        return "linkRefId" in self.__dict__

    def has_attrib(self, attrib_name):
        return attrib_name in self.__dict__

    def has_id(self):
        return self.id


class Route(ScheduleElement):
    def __init__(
        self,
        route_short_name: str,
        mode: str,
        arrival_offsets: list[str],
        departure_offsets: list[str],
        trips: Optional[dict[str, list[str]]] = None,
        headway_spec: Optional[dict] = None,
        network_links: Optional[list] = None,
        route_long_name: str = "",
        id: str = "",
        await_departure: Optional[list] = None,
        stops: Optional[list[Union[Stop, str]]] = None,
        **kwargs,
    ):
        """A Route is an object which contains information about the trips, times and offsets, mode and name of the route which forms a part of a Service.

        !!! note
            Not providing some of the optional parameters may result in the object failing validation.

        Args:
            route_short_name (str): route's short name.
            mode (str):  mode.
            arrival_offsets (list[str]): list of 'HH:MM:SS' temporal offsets for each of the stops_mapping.
            departure_offsets (list[str]): list of 'HH:MM:SS' temporal offsets for each of the stops_mapping.
            trips (Optional[dict[str, list[str]]], optional):
                Provide either detailed trip information of headway specification dictionary with keys: 'trip_id', 'trip_departure_time', 'vehicle_id'.
                Each value is a list e.g. :
                ```python
                {
                    'trip_id': ['trip_1', 'trip_2'],  # IDs of trips, unique within the Route
                    'trip_departure_time': ['HH:MM:SS', 'HH:MM:SS'],  # departure time from first stop for each trip_id
                    'vehicle_id': [veh_1, veh_2]} # vehicle IDs for each trip_id, don't need to be unique (i.e. vehicles can be shared between trips, but it's up to you to make this physically possible).
                }
                ```
                Defaults to None.
            headway_spec (Optional[dict], optional):
                Dictionary with tuple keys: (from time, to time) and headway values in minutes:
                `{('HH:MM:SS', 'HH:MM:SS'): headway_minutes}`.
                Defaults to None.
            network_links (Optional[list], optional):
                Network link_ids traversed by the vehicles in this Route instance. Defaults to None.
            route_long_name (str, optional):
                Verbose name for the route if exists. Defaults to "".
            id (str, optional):
                Unique identifier for the route if available, if not given, will be generated. Defaults to "".
            await_departure (Optional[list], optional):
                List of bools of length stops param, whether to await departure at each stop. Defaults to None.
            stops (Optional[list[Union[Stop, str]]], optional):
                Ordered list of Stop class objects or Stop IDs already present in a Schedule, if generating a Route to add.
                Defaults to None.

        Keyword Args: Additional attributes which will be attached to the class.

        """
        self.route_short_name = route_short_name
        self.mode = mode
        self.arrival_offsets = arrival_offsets
        self.departure_offsets = departure_offsets
        self.route_long_name = route_long_name
        self.id = id
        ordered_stops = None
        _graph = None
        if trips is not None:
            self.trips = trips
        elif headway_spec is not None:
            self.generate_trips_from_headway(headway_spec)
        else:
            raise RouteInitialisationError(
                "Please provide trip or headway information to initialise Route object"
            )

        if network_links is None:
            self.network_links = []
        else:
            self.network_links = network_links
        if await_departure is None:
            self.await_departure = []
        else:
            self.await_departure = await_departure
        if kwargs:
            if "ordered_stops" in kwargs:
                ordered_stops = kwargs.pop("ordered_stops")
            if "_graph" in kwargs:
                _graph = kwargs.pop("_graph")
            self.add_additional_attributes(kwargs)

        if ordered_stops is not None:
            if _graph is not None:
                # check graph type and schema
                verify_graph_schema(_graph)
                self._graph = _graph
            else:
                raise RouteInitialisationError(
                    "When passing `ordered_stops` you are expected to pass `_graph` too. "
                    "You may prefer to pass a list of Stop objects to `stops` instead"
                )
            # check all stops in _graph
            if not self._stop_ids_in_graph(ordered_stops):
                raise RouteInitialisationError(
                    "Some stop IDs passed in `ordered_stops` are missing from the _graph "
                    "object passed"
                )
            self.ordered_stops = ordered_stops
        elif stops is not None:
            try:
                self.ordered_stops = [stop.id for stop in stops]
            except AttributeError:
                self.ordered_stops = stops
            self._graph = self._build_graph(stops=stops)
        else:
            raise RouteInitialisationError(
                "You need to either pass `ordered_stops` with a valid `_graph` or "
                "a list of Stop objects to `stops`"
            )
        super().__init__()

    def __eq__(self, other):
        same_route_name = self.route_short_name == other.route_short_name
        same_mode = self.mode.lower() == other.mode.lower()
        same_stops = list(self.stops()) == list(other.stops())
        same_trips = self.trips == other.trips
        same_arrival_offsets = self.arrival_offsets == other.arrival_offsets
        same_departure_offsets = self.departure_offsets == other.departure_offsets
        return all(
            [
                same_route_name,
                same_mode,
                same_stops,
                same_trips,
                same_arrival_offsets,
                same_departure_offsets,
            ]
        )

    def __repr__(self):
        return "<{} instance at {}: with {} stops and {} trips>".format(
            self.__class__.__name__, id(self), len(self.ordered_stops), len(self.trips["trip_id"])
        )

    def __str__(self):
        return self.info()

    def _build_graph(self, stops: list[Stop]):
        route_graph = nx.DiGraph(name="Route graph")
        try:
            route_nodes = [(stop.id, stop.__dict__) for stop in stops]
            stop_edges = [
                (from_stop.id, to_stop.id) for from_stop, to_stop in zip(stops[:-1], stops[1:])
            ]
        except AttributeError:
            route_nodes = [(stop, {}) for stop in stops]
            stop_edges = [(from_stop, to_stop) for from_stop, to_stop in zip(stops[:-1], stops[1:])]
        route_graph.add_nodes_from(route_nodes, routes={self.id})
        route_graph.add_edges_from(stop_edges, routes={self.id})
        route_graph.graph["routes"] = {self.id: self._surrender_to_graph()}
        route_graph.graph["services"] = {}
        route_graph.graph["change_log"] = change_log.ChangeLog()
        return route_graph

    def _add_additional_attribute_to_graph(self, k, v):
        self._graph.graph["routes"][self.id][k] = v

    def reference_nodes(self):
        return self.route_reference_nodes(self.id)

    def reference_edges(self):
        return self.route_reference_edges(self.id)

    def modes(self):
        return {self.mode}

    def vehicles(self):
        return set(self.trips["vehicle_id"])

    def _index_unique(self, idx):
        return idx not in self._graph.graph["routes"]

    def reindex(self, new_id: Union[str, int]):
        """Changes the current index of the object to `new_id`.

        Args:
            new_id (Union[str, int]): desired value of the new index

        Raises:
            RouteIndexError: New ID cannot already exist.
        """
        if not self._index_unique(new_id):
            raise RouteIndexError(f"Route of index {new_id} already exists")
        if self.id != new_id:
            # change data on graph
            nodes = self.reference_nodes()
            self._remove_routes_from_nodes(nodes=nodes, route_ids={self.id})
            self._add_routes_to_nodes(nodes=nodes, route_ids={new_id})
            edges = self.reference_edges()
            self._remove_routes_from_edges(edges=edges, route_ids={self.id})
            self._add_routes_to_edges(edges=edges, route_ids={new_id})
            self._graph.graph["routes"][new_id] = self._graph.graph["routes"][self.id]
            self._graph.graph["routes"][new_id]["id"] = new_id
            del self._graph.graph["routes"][self.id]

            if "route_to_service_map" in self._graph.graph:
                # if route is tied to a service, update the indexing
                corresponding_service_id = self._graph.graph["route_to_service_map"][self.id]
                self._graph.graph["service_to_route_map"][corresponding_service_id] = list(
                    set(self._graph.graph["service_to_route_map"][corresponding_service_id])
                    - {self.id}
                    | {new_id}
                )
                self._graph.graph["route_to_service_map"][new_id] = corresponding_service_id
                del self._graph.graph["route_to_service_map"][self.id]

            self._graph.graph["change_log"].modify(
                object_type="route",
                old_id=self.id,
                new_id=new_id,
                old_attributes={"id": self.id},
                new_attributes={"id": new_id},
            )
            logging.info(f"Reindexed Route from {self.id} to {new_id}")
            self.id = new_id

    def print(self):
        print(self.info())

    def info(self):
        return "{} ID: {}\nName: {}\nNumber of stops: {}\nNumber of trips: {}".format(
            self.__class__.__name__,
            self.id,
            self.route_short_name,
            len(self.ordered_stops),
            len(self.trips["trip_id"]),
        )

    def plot(self, output_dir: str = "", data: Union[bool, set] = False) -> KeplerGl:
        return self.kepler_map(output_dir, f"route_{self.id}_map", data=data)

    def stops(self) -> Iterator["Stop"]:
        """
        Yields:
            Iterable returns Stop objects in the Route in order of travel
        """
        for s in self.ordered_stops:
            yield self.stop(s)

    def route(self, route_id: Union[str, int]) -> "Route":
        if route_id == self.id:
            return self
        else:
            raise IndexError(f"{route_id} does not match Route's id: {self.id}")

    def routes(self):
        """
        This iterator is on the same level as the object and yields itself
        """
        yield self

    def service_attribute_data(
        self, keys: Union[list, str], index_name: Optional[str] = None
    ) -> pd.DataFrame:
        raise ServiceIndexError("A Route cannot generate a DataFrame with Services data")

    def route_attribute_data(
        self, keys: Union[list, str], index_name: Optional[str] = None
    ) -> pd.DataFrame:
        return graph_operations.build_attribute_dataframe(
            iterator=[(self.id, self.__dict__)], keys=keys, index_name=index_name
        )

    def stop_attribute_data(
        self, keys: Union[list, str], index_name: Optional[str] = None
    ) -> pd.DataFrame:
        return graph_operations.build_attribute_dataframe(
            iterator=[(s.id, s.__dict__) for s in self.stops()], keys=keys, index_name=index_name
        )

    def trips_with_stops_to_dataframe(self, gtfs_day: str = "19700101") -> pd.DataFrame:
        df = None
        _df = DataFrame(
            {
                "departure_time": [
                    use_schedule.get_offset(self.departure_offsets[i])
                    for i in range(len(self.ordered_stops) - 1)
                ],
                "arrival_time": [
                    use_schedule.get_offset(self.arrival_offsets[i])
                    for i in range(1, len(self.ordered_stops))
                ],
                "from_stop": self.ordered_stops[:-1],
                "to_stop": self.ordered_stops[1:],
            }
        )
        for trip_id, trip_dep_time, veh_id in zip(
            self.trips["trip_id"], self.trips["trip_departure_time"], self.trips["vehicle_id"]
        ):
            trip_df = _df.copy()
            trip_df["trip_id"] = trip_id
            trip_df["vehicle_id"] = veh_id
            trip_dep_time = use_schedule.sanitise_time(trip_dep_time, gtfs_day=gtfs_day)
            trip_df["departure_time"] = trip_dep_time + trip_df["departure_time"]
            trip_df["arrival_time"] = trip_dep_time + trip_df["arrival_time"]
            if df is None:
                df = trip_df
            else:
                df = pd.concat([df, trip_df])
        df["route_id"] = self.id
        df["route_name"] = self.route_short_name.replace("\\", "_").replace("/", "_")
        df["mode"] = self.mode
        df["from_stop_name"] = df["from_stop"].apply(
            lambda x: self.stop(x).name.replace("\\", "_").replace("/", "_")
        )
        df["to_stop_name"] = df["to_stop"].apply(
            lambda x: self.stop(x).name.replace("\\", "_").replace("/", "_")
        )
        df = df.reset_index(drop=True)
        return df

    def trips_to_dataframe(self, gtfs_day="19700101"):
        df = pd.DataFrame(self.trips)

        df["route_id"] = self.id
        df["trip_departure_time"] = df["trip_departure_time"].apply(
            lambda x: use_schedule.sanitise_time(x, gtfs_day)
        )
        df["mode"] = self.mode
        return df

    def generate_trips_from_headway(self, headway_spec: dict):
        """Generates new trips for the route.

        All newly generated trips get unique vehicles with this method.

        Args:
            headway_spec (dict):
                dictionary with tuple keys: (from time, to time) and headway values in minutes:
                `{('HH:MM:SS', 'HH:MM:SS'): headway_minutes}`.
        """
        new_trip_departures = list(generate_trip_departures_from_headway(headway_spec))
        new_trip_departures.sort()
        new_trip_departures = [t.strftime("%H:%M:%S") for t in new_trip_departures]

        trips = {
            "trip_id": [f"{self.id}_{t}" for t in new_trip_departures],
            "trip_departure_time": new_trip_departures,
            "vehicle_id": [f"veh_{self.mode}_{self.id}_{t}" for t in new_trip_departures],
        }
        if "trips" in self.__dict__:
            self._graph.graph["routes"][self.id]["trips"] = trips
            self._graph.graph["change_log"] = self.change_log().modify(
                object_type="route",
                old_id=self.id,
                old_attributes=self.trips,
                new_id=self.id,
                new_attributes=trips,
            )
        self.trips = trips

    def is_exact(self, other):
        same_route_name = self.route_short_name == other.route_short_name
        same_mode = self.mode.lower() == other.mode.lower()
        same_stops = list(self.stops()) == list(other.stops())
        same_trips = self.trips == other.trips
        same_arrival_offsets = self.arrival_offsets == other.arrival_offsets
        same_departure_offsets = self.departure_offsets == other.departure_offsets

        statement = (
            same_route_name
            and same_mode
            and same_stops
            and same_trips
            and same_arrival_offsets
            and same_departure_offsets
        )
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
            distance += spatial.distance_between_s2cellids(
                self.stop(prev_stop).s2_id, self.stop(next_stop).s2_id
            )
        return distance

    def is_strongly_connected(self):
        if nx.number_strongly_connected_components(self.graph()) == 1:
            return True
        return False

    def has_self_loops(self) -> list:
        """Means that there are two consecutive stops that are the same

        Returns:
            list: All self-loops.
        """
        return list(nx.nodes_with_selfloops(self.graph()))

    def has_more_than_one_stop(self):
        if len(self.ordered_stops) > 1:
            return True
        return False

    def has_network_links(self) -> bool:
        return bool(self.network_links)

    def divide_network_links_between_stops(self):
        if self.has_network_links():
            stops_linkrefids = [self._graph.nodes[i]["linkRefId"] for i in self.ordered_stops]
            if not stops_linkrefids:
                raise RuntimeError(
                    "This Stops in this Route are not snapped to the network via `linkRefId` attribute"
                )
            return use_schedule.divide_network_route(self.network_links, stops_linkrefids)
        else:
            raise RuntimeError("This Route does not have a network route to divide")

    def has_correctly_ordered_route(self):
        if self.has_network_links():
            stops_linkrefids = [
                self._graph.nodes[i]["linkRefId"]
                for i in self.ordered_stops
                if "linkRefId" in self._graph.nodes[i]
            ]
            if len(stops_linkrefids) != len(self.ordered_stops):
                logging.warning("Not all stops reference network link ids.")
                return False
            divided_route = self.divide_network_links_between_stops()
            if not divided_route:
                return False
            reassembled_route = sum(divided_route, [])
            reassembled_route = [reassembled_route[0]] + [
                reassembled_route[i]
                for i in range(1, len(reassembled_route))
                if reassembled_route[i - 1] != reassembled_route[i]
            ]
            if (len(stops_linkrefids) - 1) == len(divided_route) and (
                reassembled_route == self.network_links
            ):
                return True
        return False

    def has_valid_offsets(self):
        if not self.arrival_offsets or not self.departure_offsets:
            return False
        elif len(self.arrival_offsets) != len(self.ordered_stops) or len(
            self.departure_offsets
        ) != len(self.ordered_stops):
            return False
        for arr_offset, dep_offset in zip(self.arrival_offsets, self.departure_offsets):
            dt_arr_offset = datetime.strptime(arr_offset, "%H:%M:%S")
            dt_dep_offset = datetime.strptime(dep_offset, "%H:%M:%S")
            if dt_arr_offset > dt_dep_offset:
                return False
        for next_arr_offset, prev_dep_offset in zip(
            self.arrival_offsets[1:], self.departure_offsets[:-1]
        ):
            dt_next_arr_offset = datetime.strptime(next_arr_offset, "%H:%M:%S")
            dt_prev_dep_offset = datetime.strptime(prev_dep_offset, "%H:%M:%S")
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
            invalid_stages.append("not_has_more_than_one_stop")

        if not bool(self.has_correctly_ordered_route()):
            valid = False
            invalid_stages.append("not_has_correctly_ordered_route")

        if not bool(self.has_valid_offsets()):
            valid = False
            invalid_stages.append("not_has_valid_offsets")

        if bool(self.has_self_loops()):
            valid = False
            invalid_stages.append("has_self_loops")

        if return_reason:
            return valid, invalid_stages
        return valid


class Service(ScheduleElement):
    def __init__(self, id: str, routes: Optional[list[Route]] = None, name: str = "", **kwargs):
        """A Service is an object containing unique routes pertaining to the same public transit service.

        !!! note
            Not providing some of the optional parameters may result in the object failing validation.

        Args:
            id (str): Unique identifier for the service
            routes (Optional[list[Route]], optional): List of Route objects, if the Routes are not uniquely indexed, they will be re-indexed. Defaults to None.
            name (str, optional): Name for the service, if not provided, will inherit the first non-trivial name from routes. Defaults to "".

        Keyword Args: Additional attributes which will be attached to the class.

        Raises:
            ServiceInitialisationError: `routes` must be a valid graph or a list of Route objects.
        """
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
            if "_graph" in kwargs:
                _graph = kwargs.pop("_graph")
            self.add_additional_attributes(kwargs)

        if _graph is not None:
            # check graph type and schema
            verify_graph_schema(_graph)
            self._graph = _graph
        elif routes is not None:
            # re-index if not unique ids
            self._graph = self._build_graph(self._ensure_unique_routes(routes))
        else:
            raise ServiceInitialisationError(
                "You need to pass either a valid `_graph` or a list of Route objects to `routes`"
            )
        super().__init__()

    def __eq__(self, other):
        return self.id == other.id

    def __repr__(self):
        return "<{} instance at {}: with {} routes>".format(
            self.__class__.__name__, id(self), len(self)
        )

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
        service_graph = nx.DiGraph(name="Service graph")
        service_graph.graph["change_log"] = change_log.ChangeLog()
        for route in routes:
            g = route.graph()
            nodes = dict_support.merge_complex_dictionaries(dict(g.nodes(data=True)), nodes)
            edges = dict_support.combine_edge_data_lists(list(g.edges(data=True)), edges)
            graph_routes = dict_support.merge_complex_dictionaries(g.graph["routes"], graph_routes)
            service_graph.graph["change_log"] = service_graph.graph["change_log"].merge_logs(
                g.graph["change_log"]
            )

        service_graph.add_nodes_from(nodes, services={_id})
        service_graph.add_edges_from(edges, services={_id})
        nx.set_node_attributes(service_graph, nodes)
        service_graph.graph["routes"] = deepcopy(graph_routes)
        service_graph.graph["services"] = {_id: self._surrender_to_graph()}
        service_graph.graph["route_to_service_map"] = {route.id: _id for route in routes}
        service_graph.graph["service_to_route_map"] = {_id: [route.id for route in routes]}
        return service_graph

    def _add_additional_attribute_to_graph(self, k, v):
        self._graph.graph["services"][self.id][k] = v

    def _ensure_unique_routes(self, routes: list[Route]):
        unique_routes = []
        route_ids = []
        for route in routes:
            idx = route.id
            if (not idx) or (idx in route_ids):
                new_id = self.id + f"_{len(unique_routes)}"
                route.reindex(new_id)
                logging.warning(
                    f"Route has been re-indexed from {idx} tp {new_id} due to an ID clash"
                )
                idx = new_id
            route_ids.append(idx)
            unique_routes.append(route)
        return unique_routes

    def reference_nodes(self):
        return self.service_reference_nodes(self.id)

    def reference_edges(self):
        return self.service_reference_edges(self.id)

    def split_by_direction(self) -> dict:
        """Divide the routes of the Service by direction e.g. North- and South-bound.

        Depending on the mode, typically a Service will have either 1 or 2 directions.
        Some Services will have more, especially ones that are loops.

        Returns:
            dict:
                Dictionary with directions as keys and lists of routes which head in that direction as values. E.g.:
                ```python
                {
                    "North-East Bound": ['route_1', 'route_2'],
                    "South-West Bound": ['route_3', 'route_4']
                }
                ```
        """
        geodesic = Geod(ellps="WGS84")
        route_direction_map = {}
        for route_id in self.route_ids():
            ordered_stops = self._graph.graph["routes"][route_id]["ordered_stops"]
            start_stop = self.stop(ordered_stops[0])
            end_stop = self.stop(ordered_stops[-1])
            if start_stop == end_stop:
                # just check which way it's heading
                end_stop = self.stop(ordered_stops[1])
            azimuth = geodesic.inv(
                lats1=start_stop.lat, lons1=start_stop.lon, lats2=end_stop.lat, lons2=end_stop.lon
            )[0]
            route_direction_map[route_id] = spatial.map_azimuth_to_name(azimuth)
        res = defaultdict(list)
        for key, val in sorted(route_direction_map.items()):
            res[val].append(key)
        return dict(res)

    def split_graph(self) -> tuple[list, list]:
        """Divide the routes and the graph of the Service by share of Service's graph.

        Most services with have one or two outputs, but some will have more.
        The results of this method may vary from `split_by_direction`.
        The output graph edges in the list will be independent of each other (the edges will be independent, but they may share nodes), sometimes producing more than two sets.

        The method is not symmetric, if the Routes in a Service are listed in a different order this may lead to some graph groups merging (in a desired way).

        Returns:
            tuple[list, list]:
                (routes, graph_groups) where:
                - routes is a list of sets with grouped route IDs
                - graph_groups is a list of the same length as routes.
                Each item is a set of graph edges and corresponds to the item in routes list in that same index.
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
                for routes_group, graph_edge_group in zip(
                    list(itertools.compress(routes, overlap_mask)),
                    list(itertools.compress(graph_edges, overlap_mask)),
                ):
                    routes_group.add(route_id)
                    graph_edge_group |= route_edges
            else:
                logging.warning(
                    f"Graph of route: `{route_id}` overlaps with multiple current graph groups. This will "
                    f"result in merging of those groups. This is usually desirable but check results to "
                    f"ensure expected behaviour."
                )
                merge_multiple_overlaps()
        return routes, graph_edges

    def modes(self):
        return {r.mode for r in self.routes()}

    def vehicles(self):
        return set().union(
            *[r_dat["trips"]["vehicle_id"] for r_id, r_dat in self.graph().graph["routes"].items()]
        )

    def _index_unique(self, idx):
        return idx not in self._graph.graph["services"]

    def reindex(self, new_id: Union[str, int]):
        """Changes the current index of the object to `new_id`.

        Args:
            new_id (Union[str, int]): Desired value of the new index

        Raises:
            ServiceIndexError: Cannot reindex to an existing ID.
        """
        if not self._index_unique(new_id):
            raise ServiceIndexError(f"Service of index {new_id} already exists")
        if self.id != new_id:
            # change data on graph
            nodes = self.reference_nodes()
            self._remove_services_from_nodes(nodes=nodes, service_ids={self.id})
            self._add_services_to_nodes(nodes=nodes, service_ids={new_id})
            edges = self.reference_edges()
            self._remove_services_from_edges(edges=edges, service_ids={self.id})
            self._add_services_to_edges(edges=edges, service_ids={new_id})
            self._graph.graph["services"][new_id] = self._graph.graph["services"][self.id]
            self._graph.graph["services"][new_id]["id"] = new_id
            del self._graph.graph["services"][self.id]

            # if service has routes tied to it, update the indexing
            for r_id in self.route_ids():
                self._graph.graph["route_to_service_map"][r_id] = new_id
            self._graph.graph["service_to_route_map"][new_id] = self._graph.graph[
                "service_to_route_map"
            ][self.id]
            del self._graph.graph["service_to_route_map"][self.id]

            self._graph.graph["change_log"].modify(
                object_type="service",
                old_id=self.id,
                new_id=new_id,
                old_attributes={"id": self.id},
                new_attributes={"id": new_id},
            )
            logging.info(f"Reindexed Service from {self.id} to {new_id}")
            self.id = new_id

    def print(self):
        print(self.info())

    def info(self):
        return "{} ID: {}\nName: {}\nNumber of routes: {}\nNumber of stops: {}".format(
            self.__class__.__name__, self.id, self.name, len(self), len(self.reference_nodes())
        )

    def plot(self, output_dir: str = "", data: Union[bool, set] = False) -> KeplerGl:
        return self.kepler_map(output_dir, f"service_{self.id}_map", data=data)

    def service_attribute_data(
        self, keys: Union[list, str], index_name: Optional[str] = None
    ) -> pd.DataFrame:
        return graph_operations.build_attribute_dataframe(
            iterator=[(self.id, self.__dict__)], keys=keys, index_name=index_name
        )

    def route_attribute_data(self, keys: Union[list, str], index_name: Optional[str] = None):
        return graph_operations.build_attribute_dataframe(
            iterator=[(rid, self._graph.graph["routes"][rid]) for rid in self.route_ids()],
            keys=keys,
            index_name=index_name,
        )

    def stop_attribute_data(self, keys: Union[list, str], index_name: Optional[str] = None):
        return graph_operations.build_attribute_dataframe(
            iterator=[(s.id, s.__dict__) for s in self.stops()], keys=keys, index_name=index_name
        )

    def trips_with_stops_to_dataframe(self, gtfs_day: str = "19700101") -> pd.DataFrame:
        df = None
        for route in self.routes():
            _df = route.trips_with_stops_to_dataframe(gtfs_day=gtfs_day)
            if df is None:
                df = _df
            else:
                df = pd.concat([df, _df])
        df["service_id"] = self.id
        df["service_name"] = self.name.replace("\\", "_").replace("/", "_")
        df = df.reset_index(drop=True)
        return df

    def trips_to_dataframe(self, gtfs_day: str = "19700101") -> pd.DataFrame:
        df = None
        for route in self.routes():
            _df = route.trips_to_dataframe(gtfs_day=gtfs_day)
            if df is None:
                df = _df
            else:
                df = pd.concat([df, _df])
        df["service_id"] = self.id
        df = df.reset_index(drop=True)
        return df

    def route(self, route_id: Union[str, int]) -> "Route":
        return self._get_route_from_graph(route_id)

    def route_ids(self):
        """
        Iterator for the Route IDs in the Service
        """
        for route_id in self._graph.graph["service_to_route_map"][self.id]:
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
            invalid_stages.append("not_has_valid_routes")

        if return_reason:
            return valid, invalid_stages
        return valid


class Schedule(ScheduleElement):
    def __init__(
        self,
        epsg: str = "",
        services: Optional[list[Service]] = None,
        _graph: Optional[nx.DiGraph] = None,
        minimal_transfer_times: Optional[dict[str, dict[str, float]]] = None,
        vehicles: Optional[dict] = None,
        vehicle_types: Union[str, dict] = (
            importlib_resources.files("genet") / "configs" / "vehicles" / "vehicle_definitions.yml"
        ).as_posix(),
        **kwargs,
    ):
        """Class to provide methods and structure for transit schedules.

        Args:
            epsg (str, optional): Projection for the schedule (each stop has its own epsg), e.g. 'epsg:4326'. Defaults to "".
            services (Optional[list[Service]], optional): list of Service class objects. Defaults to None.
            _graph (Optional[nx.DiGraph], optional): Schedule graph, used for re-instantiating the object, passed without `services`. Defaults to None.
            minimal_transfer_times (Optional[dict[str, dict[str, float]]], optional):
                Seconds to transfer between `stop_id_1` and `stop_id_2`, e.g.: `{'stop_id_1': {'stop_id_2': 0.0}}`.
                Defaults to None.
            vehicles (Optional[dict], optional):
                Dictionary of vehicle IDs from Route objects, mapping them to vehicle types in vehicle_types.
                Looks like this: `{veh_id : {'type': 'bus'}}`.
                Defaults to None and generates itself from the vehicles IDs in Routes, maps to the mode of the Route.
                Checks if those modes are defined in the vehicle_types.
            vehicle_types (Union[str, dict], optional):
                YAML file based on `genet/configs/vehicles/vehicle_definitions.yml` or dictionary of vehicle types and their specification.
                Indexed by the vehicle type that vehicles in the `vehicles` attribute are referring to.
                ```python
                {'bus' : {
                    'capacity': {'seats': {'persons': '70'}, 'standingRoom': {'persons': '0'}},
                    'length': {'meter': '18.0'},
                    'width': {'meter': '2.5'},
                    'accessTime': {'secondsPerPerson': '0.5'},
                    'egressTime': {'secondsPerPerson': '0.5'},
                    'doorOperation': {'mode': 'serial'},
                    'passengerCarEquivalents': {'pce': '2.8'}}}
                ```
                Defaults to reading `genet/configs/vehicles/vehicle_definitions.yml`.

        Raises:
            UndefinedCoordinateSystemError: A coordinate reference system must be defined by `epsg` or within `_graph`.
        """
        if isinstance(vehicle_types, dict):
            self.vehicle_types = vehicle_types
        else:
            self.vehicle_types = read_vehicle_types(vehicle_types)

        if _graph is not None:
            # check graph type and schema
            verify_graph_schema(_graph)
            self._graph = _graph
            if epsg == "":
                try:
                    epsg = self._graph.graph["crs"]
                except KeyError:
                    raise UndefinedCoordinateSystemError(
                        "You need to specify the coordinate system for the schedule"
                    )
        else:
            if epsg == "":
                raise UndefinedCoordinateSystemError(
                    "You need to specify the coordinate system for the schedule"
                )
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
                            new_idx = f"{idx}_{i}"
                            i += 1
                        service.reindex(new_idx)
                        logging.warning(
                            f"Service has been re-indexed from {idx} to {new_idx} due to an ID clash"
                        )
                        idx = new_idx
                    clashing_route_ids = route_ids & used_route_indices
                    for r_id in clashing_route_ids:
                        # Services index their routes uniquely within themselves
                        service.route(r_id).reindex(f"{idx}_{r_id}")
                    used_route_indices |= set(service.route_ids())
                    used_service_indices.append(idx)
            else:
                services = []
            self._graph = self._build_graph(services)
        self.init_epsg = epsg
        self.attributes = {"crs": epsg}
        self.transformer = Transformer.from_crs(epsg, "epsg:4326", always_xy=True)
        if minimal_transfer_times is not None:
            self.minimal_transfer_times = minimal_transfer_times
        else:
            self.minimal_transfer_times = {}
        if vehicles is None:
            self.vehicles = {}
            self.generate_vehicles()
        else:
            self.vehicles = vehicles
        self.validate_vehicle_definitions()

        if kwargs:
            self.add_additional_attributes(kwargs)

        super().__init__()

    def __nonzero__(self):
        return self.services()

    def __getitem__(self, service_id):
        return self._get_service_from_graph(service_id)

    def __contains__(self, service_id):
        return service_id in self._graph.graph["services"]

    def __repr__(self):
        return "<{} instance at {}: with {} services>".format(
            self.__class__.__name__, id(self), len(self)
        )

    def __str__(self):
        return self.info()

    def __len__(self):
        return len(self.service_ids())

    def __copy__(self):
        g_copy = self._graph.copy()
        g_copy.graph = deepcopy(self._graph.graph)
        g_copy.graph["change_log"] = change_log.ChangeLog(df=self._graph.graph["change_log"].copy())
        return Schedule(_graph=g_copy, minimal_transfer_times=deepcopy(self.minimal_transfer_times))

    def _build_graph(self, services):
        nodes = {}
        edges = {}
        graph_routes = {}
        graph_services = {}
        schedule_graph = nx.DiGraph(name="Schedule graph")
        schedule_graph.graph["route_to_service_map"] = {}
        schedule_graph.graph["service_to_route_map"] = {}
        schedule_graph.graph["change_log"] = change_log.ChangeLog()

        for service in services:
            g = service.graph()
            nodes = dict_support.merge_complex_dictionaries(dict(g.nodes(data=True)), nodes)
            edges = dict_support.combine_edge_data_lists(list(g.edges(data=True)), edges)
            graph_routes = dict_support.merge_complex_dictionaries(g.graph["routes"], graph_routes)
            graph_services = dict_support.merge_complex_dictionaries(
                g.graph["services"], graph_services
            )
            schedule_graph.graph["route_to_service_map"] = {
                **schedule_graph.graph["route_to_service_map"],
                **g.graph["route_to_service_map"],
            }
            schedule_graph.graph["service_to_route_map"] = {
                **schedule_graph.graph["service_to_route_map"],
                **g.graph["service_to_route_map"],
            }
            schedule_graph.graph["change_log"] = schedule_graph.graph["change_log"].merge_logs(
                g.graph["change_log"]
            )
            # TODO check for clashing stop ids overwriting data

        schedule_graph.add_nodes_from(nodes)
        schedule_graph.add_edges_from(edges)
        nx.set_node_attributes(schedule_graph, nodes)
        schedule_graph.graph["routes"] = graph_routes
        schedule_graph.graph["services"] = graph_services
        return schedule_graph

    def generate_vehicles(self, overwrite: bool = False):
        """Generate vehicles for the Schedule.

        Returns dictionary of vehicle IDs from Route objects, mapping them to vehicle types in vehicle_types.
        Looks like this: `{veh_id : {'type': 'bus'}}`.
        Generates itself from the vehicles IDs which exist in Routes, maps to the mode of the Route.

        Args:
            overwrite (bool, optional):
                If False, does not overwrite the types of vehicles currently in the schedule.
                If True, generates completely new vehicle types for all vehicles in the schedule based on Route modes.
                Defaults to False.

        Raises:
            InconsistentVehicleModeError: There should be no modal inconsistencies between vehicles and schedules.
        """
        if self:
            # generate vehicles using Services and Routes upon init
            df = self.trips_to_dataframe()[["route_id", "vehicle_id"]]
            df["type"] = df.apply(
                lambda x: self._graph.graph["routes"][x["route_id"]]["mode"], axis=1
            )
            df = df.drop(columns="route_id")
            # check mode consistency
            vehicles_to_modes = df.groupby("vehicle_id").apply(lambda x: list(x["type"].unique()))
            if (vehicles_to_modes.str.len() > 1).any():
                # there are vehicles which are shared across routes with different modes
                raise InconsistentVehicleModeError(
                    "Modal inconsistencies found while generating vehicles for Schedule."
                    " Vehicles and modes in question: "
                    f"{vehicles_to_modes[(vehicles_to_modes.str.len() > 1)].to_dict()}"
                )
            df = df.set_index("vehicle_id")
            if overwrite:
                self.vehicles = df.T.to_dict()
                self.validate_vehicle_definitions()
            else:
                self.vehicles = {**df.T.to_dict(), **self.vehicles}

    def scale_vehicle_capacity(self, capacity_scale: float, pce_scale: float, output_dir: str):
        """This method scales the vehicle capacities and pce to user defined scales and writes a new vehicle.xml.

        Args:
            capacity_scale (float): vehicle capacity scale
            pce_scale (float):  passenger car equivalents scale
            output_dir (str): Directory to save `vehicle.xml`

        Example:
            For 5%: `!#python scale_vehicle_capacity(0.05, 0.05,"")`
        """
        # save copy of existing vehicle data
        vehicle_types_dict = deepcopy(self.vehicle_types)

        # scale capacity and pce to defined scale
        for mode, mode_dict in self.vehicle_types.items():
            mode_dict["capacity"]["seats"]["persons"] = str(
                round(float(mode_dict["capacity"]["seats"]["persons"]) * capacity_scale)
            )
            mode_dict["capacity"]["standingRoom"]["persons"] = str(
                round(float(mode_dict["capacity"]["standingRoom"]["persons"]) * capacity_scale)
            )
            mode_dict["passengerCarEquivalents"]["pce"] = str(
                round(float(mode_dict["passengerCarEquivalents"]["pce"]) * pce_scale, 3)
            )

        # export scaled vehicles xml
        persistence.ensure_dir(output_dir)
        matsim_xml_writer.write_vehicles(
            output_dir,
            self.vehicles,
            self.vehicle_types,
            f"{int(capacity_scale * 100)}_perc_vehicles.xml",
        )

        self.vehicle_types = vehicle_types_dict

        logging.info(
            f"Created scaled vehicle file for {int(capacity_scale * 100)}% capacity & "
            f"{int(pce_scale * 100)}% pce."
        )

    def trips_to_dataframe(self, gtfs_day: str = "19700101") -> pd.DataFrame:
        df = self.route_attribute_data(
            keys=[{"trips": "trip_id"}, {"trips": "trip_departure_time"}, {"trips": "vehicle_id"}],
            index_name="route_id",
        )
        df = df.reset_index()
        df["service_id"] = df["route_id"].apply(
            lambda x: self._graph.graph["route_to_service_map"][x]
        )
        df["mode"] = df["route_id"].apply(lambda x: self.graph().graph["routes"][x]["mode"])
        df = df.rename(
            columns={
                "trips::trip_id": "trip_id",
                "trips::trip_departure_time": "trip_departure_time",
                "trips::vehicle_id": "vehicle_id",
            }
        )
        df = DataFrame(
            {
                col: np.repeat(df[col].values, df["trip_id"].str.len())
                for col in set(df.columns) - {"trip_id", "trip_departure_time", "vehicle_id"}
            }
        ).assign(
            trip_id=np.concatenate(df["trip_id"].values),
            trip_departure_time=np.concatenate(df["trip_departure_time"].values),
            vehicle_id=np.concatenate(df["vehicle_id"].values),
        )
        df["trip_departure_time"] = df["trip_departure_time"].apply(
            lambda x: use_schedule.sanitise_time(x, gtfs_day)
        )
        return df

    def generate_trips_dataframe_from_headway(
        self, route_id: Union[str, int], headway_spec: dict
    ) -> pd.DataFrame:
        """Generates new trips and vehicles for the specified route.

        Inherits one of the existing vehicle types.
        If the vehicle types vary for a route, you will need to generate your own trips dataframe and add those vehicles yourself.

        All newly generated trips get unique vehicles with this method.

        Args:
            route_id (Union[str, int]): existing route
            headway_spec (dict):
                dictionary with tuple keys: (from time, to time) and headway values in minutes:
                `{('HH:MM:SS', 'HH:MM:SS'): headway_minutes}`.

        Returns:
            pd.DataFrame: Trips.
        """
        veh_type = self.vehicles[self.route(route_id).trips["vehicle_id"][0]]
        new_trip_departures = list(generate_trip_departures_from_headway(headway_spec))
        new_trip_departures.sort()

        new_trips = pd.DataFrame(
            {
                "trip_id": [f'{route_id}_{t.strftime("%H:%M:%S")}' for t in new_trip_departures],
                "trip_departure_time": new_trip_departures,
                "vehicle_id": [
                    f'veh_{veh_type["type"]}_{route_id}_{t.strftime("%H:%M:%S")}'
                    for t in new_trip_departures
                ],
            }
        )
        new_trips["route_id"] = route_id
        new_trips["service_id"] = self._graph.graph["route_to_service_map"][route_id]
        return new_trips

    def generate_trips_from_headway(self, route_id: Union[str, int], headway_spec: dict):
        """Generates new trips and vehicles for the specified route.

        Inherits one of the existing vehicle type.
        If the vehicle types vary for a route, you will need to generate your own trips dataframe and add those vehicles yourself.

        All newly generated trips get unique vehicles with this method.

        Args:
            route_id (Union[str, int]): existing route
            headway_spec (dict):
                dictionary with tuple keys: (from time, to time) and headway values in minutes:
                `{('HH:MM:SS', 'HH:MM:SS'): headway_minutes}`.
        """
        veh_type = self.vehicles[self.route(route_id).trips["vehicle_id"][0]]
        old_vehicles = set(self.route(route_id).trips["vehicle_id"])
        new_trips = self.generate_trips_dataframe_from_headway(route_id, headway_spec)
        self.set_trips_dataframe(new_trips)
        self.vehicles = {
            **{veh_id: veh_type for veh_id in new_trips["vehicle_id"]},
            **self.vehicles,
        }
        list(map(self.vehicles.pop, old_vehicles - set(new_trips["vehicle_id"])))

    def unused_vehicles(self):
        """
        A scenario change to the network may result in changes to vehicle assignments, with some vehicles not
        being used anymore. This method checks if any of the vehicles are missing (i.e. exist in Schedule.vehicles,
        but are not used by services) and returns a list of these vehicles' IDs, if there are any.
        It also logs a warning which says whether any unused vehicles have been found.

        self.vehicles = dictionary of vehicle IDs from Route objects, in form {veh_id : {'type': 'bus'}}
        e.g.  {'fun_bus_1': {'type': 'bus'}, 'fun_bus_2': {'type': 'bus'}, 'some_bus_2': {'type': 'bus'}}
        """

        existing_vehicles = set(self.vehicles.keys())
        used_vehicles = self.trips_to_dataframe()
        used_vehicles = set(used_vehicles["vehicle_id"].to_list())

        unused_vehicles = existing_vehicles - used_vehicles

        if len(unused_vehicles) == 0:
            logging.info("All vehicles are being used.")
        else:
            logging.warning(str(len(unused_vehicles)) + " unused vehicles have been found.")

        return unused_vehicles

    def check_vehicle_uniqueness(self):
        """
        In MATSim, trips can share vehicles, but his may or may not be intended, e.g. it could result from a
        scenario change and be undesirable, leading to simulation not working correctly.
        This method checks if a vehicle ID is being used by two or more different trips, and then returns
        a dictionary of vehicle IDs together with trips for which they are being used.
        It also logs a warning which says whether any vehicles are being used for multiple trips.
        """
        trips_df = self.trips_to_dataframe()
        trips_df = trips_df[["trip_id", "vehicle_id"]]

        trips_dict = trips_df.set_index("trip_id")["vehicle_id"].to_dict()

        # finding duplicate values from dictionary by flipping keys and values
        flipped = {}
        not_unique_list = []

        for trip_id, vehicle_id in trips_dict.items():
            if vehicle_id not in flipped:
                flipped[vehicle_id] = [trip_id]
            else:
                not_unique_list.append(vehicle_id)
                flipped[vehicle_id].append(trip_id)

        duplicates_dict = {}
        for vehicle_id in not_unique_list:
            trip_ids = flipped[vehicle_id]
            duplicates_dict[vehicle_id] = []
            for id in trip_ids:
                duplicates_dict[vehicle_id].append(id)

        if len(duplicates_dict) == 0:
            logging.info("No vehicles being used for multiple trips have been found.")
        else:
            logging.warning(
                "Vehicles being used for multiple trips: {}".format(list(duplicates_dict.keys()))
            )

        return duplicates_dict

    def set_route_trips_dataframe(self, df):
        """
        This method exists for backwards compatibility only
        Please use set_trips_dataframe
        """
        logging.warning(
            "`set_route_trips_dataframe` method is deprecated and will be replaced by `set_trips_dataframe`"
            "in later versions."
        )
        return self.set_trips_dataframe(df)

    def set_trips_dataframe(self, df: pd.DataFrame):
        """Option to replace trips data currently stored under routes by an updated `trips_to_dataframe`.

        Need not be exhaustive in terms of routes. I.e. trips for some of the routes can be omitted if no changes are
        required. Needs to be exhaustive in terms of trips. I.e. if there are changes to a route, all of the trips
        required to be in that trip need to be present, it overwrites route.trips attribute.

        Args:
            df (pd.DataFrame): generated by `trips_to_dataframe` (or of the same format)
        """
        # convert route trips dataframe to apply dictionary shape and give to apply to routes method
        df["trip_departure_time"] = df["trip_departure_time"].dt.strftime("%H:%M:%S")
        df = df.groupby("route_id").apply(
            lambda x: Series(
                {
                    "trips": {
                        k: x[k].to_list() for k in ["trip_id", "trip_departure_time", "vehicle_id"]
                    }
                }
            )
        )
        self.apply_attributes_to_routes(df.T.to_dict())

    def overlapping_vehicle_ids(self, vehicles: dict) -> set:
        return set(self.vehicles.keys()) & set(vehicles.keys())

    def overlapping_vehicle_types(self, vehicle_types: dict) -> set:
        return set(self.vehicle_types.keys()) & set(vehicle_types.keys())

    def update_vehicles(
        self, vehicles: dict, vehicle_types: dict, overwrite: bool = True
    ) -> tuple[set, set]:
        """Updates vehicles and vehicle types.

        Args:
            vehicles (dict): vehicles to add.
            vehicle_types (dict): vehicle types to add.
            overwrite (bool, optional):
                If True: overwrites overlapping vehicle types data currently in the Schedule, adds vehicles as they are,
                    overwriting in case of clash
                If False: adds vehicles and vehicle types that do not clash with those already stored in the Schedule.
                Defaults to True.

        Returns:
            tuple[set, set]: Any clashing 1. vehicles and 2. vehicle types.
        """
        # check for vehicle ID overlap
        clashing_vehicles = self.overlapping_vehicle_ids(vehicles=vehicles)
        if clashing_vehicles:
            logging.warning(f"The following vehicles clash: {clashing_vehicles}")
            if overwrite:
                logging.warning("Overwrite is on. Vehicles listed above will be overwritten.")
            else:
                logging.warning(
                    "Overwrite is off. Clashing vehicles will remain as they are. "
                    "All others will be added."
                )
        # check for vehicle type overlap
        clashing_vehicle_types = self.overlapping_vehicle_types(vehicle_types=vehicle_types)
        if clashing_vehicle_types:
            logging.warning(f"The following vehicle types clash: {clashing_vehicle_types}")
            if overwrite:
                logging.warning("Overwrite is on. Vehicle types listed above will be overwritten.")
            else:
                logging.warning(
                    "Overwrite is off. Clashing vehicle types will remain as they are. "
                    "All others will be added."
                )

        if overwrite:
            self.vehicles = {**self.vehicles, **vehicles}
            self.vehicle_types = {**self.vehicle_types, **vehicle_types}
        else:
            self.vehicles = {**vehicles, **self.vehicles}
            self.vehicle_types = {**vehicle_types, **self.vehicle_types}

        self.validate_vehicle_definitions()
        return clashing_vehicles, clashing_vehicle_types

    def validate_vehicle_definitions(self) -> bool:
        """Checks if modes mapped to vehicle IDs in vehicles attribute of Schedule are defined in the vehicle_types.

        Returns:
            bool:
                Returns True if the vehicle types in the `vehicles` attribute exist in the `vehicle_types` attribute.
                But useful even just for the logging messages.
        """

        missing_vehicle_information = self.get_missing_vehicle_information()
        missing_vehicles = len(missing_vehicle_information["missing_vehicle_types"])

        if missing_vehicles == 0:
            return True
        else:
            logging.warning(
                "The following vehicle types are missing from the `vehicle_types` " + " attribute: "
                f'{missing_vehicle_information["missing_vehicle_types"]}'
            )
            logging.warning(
                "Vehicles affected by missing vehicle"
                " types: "
                f"{missing_vehicle_information['vehicles_affected']}"
            )
            return False

    def get_missing_vehicle_information(self):
        df_vehicles = graph_operations.build_attribute_dataframe(
            iterator=self.vehicles.items(), keys=["type"]
        )
        missing_vehicle_types = set(df_vehicles["type"]) - set(self.vehicle_types.keys())
        vehicles_affected = df_vehicles[df_vehicles["type"].isin(missing_vehicle_types)].T.to_dict()

        missing = {}
        missing["missing_vehicle_types"] = missing_vehicle_types
        missing["vehicles_affected"] = vehicles_affected

        return missing

    def reference_nodes(self):
        return set(self._graph.nodes())

    def reference_edges(self):
        return set(self._graph.edges())

    def modes(self):
        return set(self.route_attribute_data(keys="mode")["mode"].unique())

    def mode_to_routes_map(self):
        df = self.route_attribute_data(keys=["mode"], index_name="route_id").reset_index()
        return df.groupby("mode")["route_id"].apply(list).to_dict()

    def mode_graph_map(self):
        mode_map = {}
        mode_to_routes_map = self.mode_to_routes_map()
        for mode, route_ids in mode_to_routes_map.items():
            mode_map[mode] = set(
                graph_operations.extract_on_attributes(
                    iterator=[((u, v), data) for u, v, data in self._graph.edges(data=True)],
                    conditions={"routes": route_ids},
                )
            )
        return mode_map

    def reindex(self, new_id):
        if isinstance(self, Schedule):
            raise NotImplementedError("Schedule is not currently an indexed object")

    def add(self, other: "Schedule", overwrite: bool = True):
        """Adds another Schedule in-place.

        They have to be separable! I.e. the keys in services cannot overlap with the ones already present.

        TODO: add merging complicated schedules, parallels to the merging gtfs work.

        Args:
            other (Schedule): the other Schedule object to add
            overwrite (bool, optional):
                If True: overwrites overlapping vehicle types data currently in the Schedule, adds vehicles as they are,
                    overwriting in case of clash
                If False: adds vehicles and vehicle types from other that do not clash with those already stored in the Schedule.
                Defaults to True.

        Raises:
            NotImplementedError: Schedules must not have overlapping services.
        """
        if not self.is_separable_from(other):
            # have left and right indicies
            raise NotImplementedError("This method only supports adding non overlapping services.")
        elif self.epsg != other.epsg:
            other.reproject(self.epsg)

        self._graph.graph["services"] = dict_support.merge_complex_dictionaries(
            other._graph.graph["services"], self._graph.graph["services"]
        )
        self._graph.graph["routes"] = dict_support.merge_complex_dictionaries(
            other._graph.graph["routes"], self._graph.graph["routes"]
        )
        self._graph.graph["route_to_service_map"] = {
            **self._graph.graph["route_to_service_map"],
            **other._graph.graph["route_to_service_map"],
        }
        self._graph.graph["service_to_route_map"] = {
            **self._graph.graph["service_to_route_map"],
            **other._graph.graph["service_to_route_map"],
        }
        self.minimal_transfer_times = dict_support.merge_complex_dictionaries(
            other.minimal_transfer_times, self.minimal_transfer_times
        )
        # todo assuming separate schedules, with non conflicting ids, nodes and edges
        _ = deepcopy(self._graph.graph)
        self._graph.update(other._graph)
        self._graph.graph = _

        # merge change_log DataFrames
        self._graph.graph["change_log"] = self.change_log().merge_logs(other.change_log())

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
        return (
            "Schedule:\nNumber of services: {}\nNumber of routes: {}\nNumber of stops: {}".format(
                self.__len__(), self.number_of_routes(), len(self.reference_nodes())
            )
        )

    def graph(self):
        return self._graph

    def reproject(self, new_epsg: str, processes: int = 1):
        """Changes projection of the element to `new_epsg`.

        Args:
            new_epsg (str):
                New projection, e.g., "epsg:1234".
            processes (int, optional):
                Number of parallel processes to use when reprojecting. Defaults to 1.
        """
        ScheduleElement.reproject(self, new_epsg, processes=processes)
        self._graph.graph["crs"] = new_epsg

    def find_epsg(self):
        return self.init_epsg

    def plot(self, output_dir: str = "", data: Union[bool, set] = False) -> KeplerGl:
        return self.kepler_map(output_dir, "schedule_map", data=data)

    def trips_with_stops_to_dataframe(self, gtfs_day: str = "19700101") -> pd.DataFrame:
        df = self.route_attribute_data(
            keys=[
                "route_short_name",
                "mode",
                "trips",
                "arrival_offsets",
                "departure_offsets",
                "ordered_stops",
                "id",
            ]
        )
        df = df.rename(columns={"id": "route_id", "route_short_name": "route_name"})
        df["route_name"] = df["route_name"].apply(lambda x: x.replace("\\", "_").replace("/", "_"))
        df["service_id"] = df["route_id"].apply(
            lambda x: self._graph.graph["route_to_service_map"][x]
        )
        df["service_name"] = df["service_id"].apply(
            lambda x: self._graph.graph["services"][x]["name"].replace("\\", "_").replace("/", "_")
        )
        df["ordered_stops"] = df["ordered_stops"].apply(lambda x: list(zip(x[:-1], x[1:])))
        df["departure_offsets"] = df["departure_offsets"].apply(
            lambda x: list(map(use_schedule.get_offset, x[:-1]))
        )
        df["arrival_offsets"] = df["arrival_offsets"].apply(
            lambda x: list(map(use_schedule.get_offset, x[1:]))
        )

        # expand the frame stop to stop and extract offsets for arrival and departure from these stops
        stop_cols = np.concatenate(df["ordered_stops"].values)
        dep_offset_cols = np.concatenate(df["departure_offsets"].values)
        arr_offset_cols = np.concatenate(df["arrival_offsets"].values)
        df = DataFrame(
            {
                col: np.repeat(df[col].values, df["ordered_stops"].str.len())
                for col in set(df.columns)
                - {"ordered_stops", "arrival_offsets", "departure_offsets"}
            }
        ).assign(
            from_stop=stop_cols[:, 0],
            to_stop=stop_cols[:, 1],
            departure_time=dep_offset_cols,
            arrival_time=arr_offset_cols,
        )

        df["from_stop_name"] = df["from_stop"].apply(
            lambda x: self._graph.nodes[x]["name"].replace("\\", "_").replace("/", "_")
        )
        df["to_stop_name"] = df["to_stop"].apply(
            lambda x: self._graph.nodes[x]["name"].replace("\\", "_").replace("/", "_")
        )

        # expand the frame on all the trips each route makes
        trips = np.concatenate(
            df["trips"]
            .apply(
                lambda x: [
                    (trip_id, use_schedule.sanitise_time(trip_dep_time, gtfs_day), veh_id)
                    for trip_id, trip_dep_time, veh_id in zip(
                        x["trip_id"], x["trip_departure_time"], x["vehicle_id"]
                    )
                ]
            )
            .values
        )
        df = (
            DataFrame(
                {
                    col: np.repeat(df[col].values, df["trips"].str["trip_id"].str.len())
                    for col in set(df.columns) - {"trips"}
                }
            )
            .assign(trip_id=trips[:, 0], trip_dep_time=trips[:, 1], vehicle_id=trips[:, 2])
            .sort_values(by=["route_id", "trip_id", "departure_time"])
            .reset_index(drop=True)
        )

        df["departure_time"] = df["trip_dep_time"] + df["departure_time"]
        df["arrival_time"] = df["trip_dep_time"] + df["arrival_time"]
        df = df.drop("trip_dep_time", axis=1)
        return df

    def service_to_route_map(self):
        return self._graph.graph["service_to_route_map"]

    def route_to_service_map(self):
        return self._graph.graph["route_to_service_map"]

    def service_ids(self):
        """
        Returns list of service ids in the Schedule
        """
        return list(self._graph.graph["services"].keys())

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

    def route(self, route_id: Union[str, int]) -> "Route":
        return self._get_route_from_graph(route_id)

    def route_ids(self):
        """
        Returns list of route ids in the Schedule
        """
        return list(self._graph.graph["routes"].keys())

    def has_route(self, route_id):
        """
        Returns True if a route with ID `route_id` exists in the Schedule, False otherwise
        """
        return route_id in self._graph.graph["routes"].keys()

    def routes(self):
        """
        Iterator for Route objects in the Services of the Schedule
        """
        for route_id in self.route_ids():
            yield self._get_route_from_graph(route_id)

    def number_of_routes(self):
        return len(self._graph.graph["routes"])

    def has_stop(self, stop_id):
        """
        Returns True if a stop with ID `stop_id` exists in the Schedule, False otherwise
        """
        return self._graph.has_node(stop_id)

    def service_attribute_summary(self, data: bool = False):
        """Parses through data stored for Services in the Schedule and prints a summary tree.

        Args:
            data (bool, optional): If True, shows also up to 5 unique values stored under such keys. Defaults to False.
        """
        root = graph_operations.get_attribute_schema(
            self._graph.graph["services"].items(), data=data
        )
        graph_operations.render_tree(root, data)

    def route_attribute_summary(self, data: bool = False):
        """Parses through data stored for Routes in the Schedule and gives a summary tree.

        Args:
            data (bool, optional): If True, shows also up to 5 unique values stored under such keys. Defaults to False.
        """
        root = graph_operations.get_attribute_schema(self._graph.graph["routes"].items(), data=data)
        graph_operations.render_tree(root, data)

    def stop_attribute_summary(self, data: bool = False):
        """Parses through data stored for Stops in the Schedule and gives a summary tree.

        Args:
            data (bool, optional): If True, shows also up to 5 unique values stored under such keys. Defaults to False.
        """
        root = graph_operations.get_attribute_schema(self._graph.nodes(data=True), data=data)
        graph_operations.render_tree(root, data)

    def service_attribute_data(
        self, keys: Union[list, str], index_name: Optional[str] = None
    ) -> pd.DataFrame:
        return graph_operations.build_attribute_dataframe(
            iterator=self._graph.graph["services"].items(), keys=keys, index_name=index_name
        )

    def route_attribute_data(self, keys: Union[list, str], index_name: Optional[str] = None):
        return graph_operations.build_attribute_dataframe(
            iterator=self._graph.graph["routes"].items(), keys=keys, index_name=index_name
        )

    def stop_attribute_data(self, keys: Union[list, str], index_name: Optional[str] = None):
        return graph_operations.build_attribute_dataframe(
            iterator=self._graph.nodes(data=True), keys=keys, index_name=index_name
        )

    def extract_service_ids_on_attributes(
        self, conditions: Union[list, dict], how: Callable = any, mixed_dtypes: bool = True
    ) -> list[str]:
        """Extracts IDs of Services stored in the Schedule based on values of their attributes.

        Fails silently, assumes not all Services have those attributes.

        In the case were the attributes stored are a list or set,
        like in the case of a simplified network (there will be a mix of objects that are sets and not),
        an intersection of values satisfying condition(s) is considered in case of iterable value,
        if not empty, it is deemed successful by default.
        To disable this behaviour set mixed_dtypes to False.

        Args:
            conditions (Union[list, dict]):
                {'attribute_key': 'target_value'} or nested {'attribute_key': {'another_key': {'yet_another_key': 'target_value'}}},
                where 'target_value' could be:

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
                ```python
                def below_exclusive_upper_bound(value):
                    return value < 100
                ```
                (if mixed_dtypes==True and in case of set/list edge_data[key], at least one item in
                edge_data[key] returns True after applying function)

            how (Callable, optional):
                The level of rigour used to match conditions. Defaults to any.
                - all: means all conditions need to be met
                - any: means at least one condition needs to be met

            mixed_dtypes (bool, optional):
                If True, will consider the intersection of single values or lists of values in queried dictionary keys, e.g. as in simplified networks.
                Defaults to True.

        Returns:
            list[str]: list of ids in the schedule satisfying conditions.

        """
        return graph_operations.extract_on_attributes(
            self._graph.graph["services"].items(),
            conditions=conditions,
            how=how,
            mixed_dtypes=mixed_dtypes,
        )

    def extract_route_ids_on_attributes(
        self, conditions: Union[list, dict], how: Callable = any, mixed_dtypes: bool = True
    ) -> list[str]:
        """Extracts IDs of Routes stored in the Schedule based on values of their attributes.

        Fails silently, assumes not all Routes have those attributes.

        In the case were the attributes stored are a list or set,
        like in the case of a simplified network (there will be a mix of objects that are sets and not),
        an intersection of values satisfying condition(s) is considered in case of iterable value,
        if not empty, it is deemed successful by default.
        To disable this behaviour set mixed_dtypes to False.

        Args:
            conditions (Union[list, dict]):
                {'attribute_key': 'target_value'} or nested {'attribute_key': {'another_key': {'yet_another_key': 'target_value'}}},
                where 'target_value' could be:

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
                ```python
                def below_exclusive_upper_bound(value):
                    return value < 100
                ```
                (if mixed_dtypes==True and in case of set/list edge_data[key], at least one item in
                edge_data[key] returns True after applying function)

            how (Callable, optional):
                The level of rigour used to match conditions. Defaults to any.
                - all: means all conditions need to be met
                - any: means at least one condition needs to be met

            mixed_dtypes (bool, optional):
                If True, will consider the intersection of single values or lists of values in queried dictionary keys, e.g. as in simplified networks.
                Defaults to True.

        Returns:
            list[str]: list of ids in the schedule satisfying conditions.
        """
        return graph_operations.extract_on_attributes(
            self._graph.graph["routes"].items(),
            conditions=conditions,
            how=how,
            mixed_dtypes=mixed_dtypes,
        )

    def extract_stop_ids_on_attributes(
        self, conditions: Union[list, dict], how: Callable = any, mixed_dtypes: bool = True
    ) -> list[str]:
        """Extracts IDs of Stops stored in the Schedule based on values of their attributes.

        Fails silently, assumes not all Routes have those attributes.

        In the case were the attributes stored are a list or set,
        like in the case of a simplified network (there will be a mix of objects that are sets and not),
        an intersection of values satisfying condition(s) is considered in case of iterable value,
        if not empty, it is deemed successful by default.
        To disable this behaviour set mixed_dtypes to False.

        Args:
            conditions (Union[list, dict]):
                {'attribute_key': 'target_value'} or nested {'attribute_key': {'another_key': {'yet_another_key': 'target_value'}}},
                where 'target_value' could be:

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
                ```python
                def below_exclusive_upper_bound(value):
                    return value < 100
                ```
                (if mixed_dtypes==True and in case of set/list edge_data[key], at least one item in
                edge_data[key] returns True after applying function)

            how (Callable, optional):
                The level of rigour used to match conditions. Defaults to any.
                - all: means all conditions need to be met
                - any: means at least one condition needs to be met

            mixed_dtypes (bool, optional):
                If True, will consider the intersection of single values or lists of values in queried dictionary keys, e.g. as in simplified networks.
                Defaults to True.

        Returns:
            list[str]: list of ids in the schedule satisfying conditions.
        """
        return graph_operations.extract_on_attributes(
            self._graph.nodes(data=True), conditions=conditions, how=how, mixed_dtypes=mixed_dtypes
        )

    def services_on_modal_condition(self, modes: Union[str, list]) -> list:
        """
        Finds Service IDs which hold Routes with modes or singular mode given in `modes`.
        Note that a Service can have Routes with different modes.

        Args:
            modes (Union[str, list]):  string mode e.g. 'bus' or a list of such modes e.g. ['bus', 'rail'].

        Returns:
            list: list of Service IDs
        """
        route_ids = self.routes_on_modal_condition(modes=modes)
        return list({self._graph.graph["route_to_service_map"][r_id] for r_id in route_ids})

    def routes_on_modal_condition(self, modes: Union[str, list]) -> list:
        """
        Finds Route IDs with modes or singular mode given in `modes`

        Args:
            modes (Union[str, list]):  string mode e.g. 'bus' or a list of such modes e.g. ['bus', 'rail'].

        Returns:
            list: list of Route IDs
        """
        conditions = {"mode": modes}
        return self.extract_route_ids_on_attributes(conditions=conditions)

    def stops_on_modal_condition(self, modes: Union[str, list]) -> list:
        """
        Finds Stop IDs used by Routes with modes or singular mode given in `modes`

        Args:
            modes (Union[str, list]):  string mode e.g. 'bus' or a list of such modes e.g. ['bus', 'rail'].

        Returns:
            list: list of Stop IDs
        """
        route_ids = self.routes_on_modal_condition(modes=modes)
        return self.extract_stop_ids_on_attributes(conditions={"routes": route_ids})

    def subschedule(self, service_ids: list) -> "Schedule":
        """Subset a Schedule object using a spatial bound.
        Args:
            service_ids (list): Collection of service IDs in the Schedule for subsetting.

        Returns:
            Schedule: A new Schedule object that is a subset of the original.
        """
        subschedule = self.__copy__()
        for s in subschedule.service_ids():
            if s not in service_ids:
                subschedule.remove_service(s)
        subschedule.remove_unused_stops()
        return subschedule

    def subschedule_on_spatial_condition(
        self,
        region_input: Union[str, BaseGeometry],
        how: Literal["interact", "within"] = "intersect",
    ) -> "Schedule":
        """Subset a Schedule object using a spatial

        Schedule: A new Schedule object that is a subset of the original
        """
        services_to_keep = self.services_on_spatial_condition(region_input=region_input, how=how)
        return self.subschedule(service_ids=services_to_keep)

    def services_on_spatial_condition(
        self,
        region_input: Union[str, BaseGeometry],
        how: Literal["interact", "within"] = "intersect",
    ) -> list:
        """Returns Service IDs which intersect region_input, by default, or are contained within region_input if how='within'.

        Args:
            region_input (Union[str, BaseGeometry]):
                - path to a geojson file, can have multiple features.
                - string with comma separated hex tokens of Google's S2 geometry.
                A region can be covered with cells and the tokens string copied using http://s2.sidewalklabs.com/regioncoverer/.
                E.g., '89c25985,89c25987,89c2598c,89c25994,89c25999ffc,89c2599b,89c259ec,89c259f4,89c25a1c,89c25a24'.
                - shapely.geometry object, e.g. Polygon or a shapely.geometry.GeometryCollection of such objects.
            how (Literal[intersect, within], optional):
                Defaults to "intersect".
                - 'intersect' will return IDs of the Services whose at least one Stop intersects the `region_input`.
                - 'within' will return IDs of the Services whose all of the Stops are contained within the `region_input`.

        Returns:
            list: Service IDs
        """
        if how == "intersect":
            stops_intersecting = self.stops_on_spatial_condition(region_input)
            return list(
                {
                    item
                    for sublist in [self._graph.nodes[x]["services"] for x in stops_intersecting]
                    for item in sublist
                }
            )
        elif how == "within":
            routes_contained = set(self.routes_on_spatial_condition(region_input, how="within"))
            return [
                service_id
                for service_id, route_ids in self._graph.graph["service_to_route_map"].items()
                if set(route_ids).issubset(routes_contained)
            ]
        else:
            raise NotImplementedError("Only `intersect` and `within` options for `how` param.")

    def routes_on_spatial_condition(
        self,
        region_input: Union[str, BaseGeometry],
        how: Literal["interact", "within"] = "intersect",
    ) -> list:
        """
        Returns Route IDs which intersect region_input, by default, or are contained within region_input if how='within'.

        Args:
            region_input (Union[str, BaseGeometry]):
                - path to a geojson file, can have multiple features.
                - string with comma separated hex tokens of Google's S2 geometry.
                A region can be covered with cells and the tokens string copied using http://s2.sidewalklabs.com/regioncoverer/.
                E.g., '89c25985,89c25987,89c2598c,89c25994,89c25999ffc,89c2599b,89c259ec,89c259f4,89c25a1c,89c25a24'.
                - shapely.geometry object, e.g. Polygon or a shapely.geometry.GeometryCollection of such objects.
            how (Literal[intersect, within], optional):
                Defaults to "intersect".
                - 'intersect' will return IDs of the Services whose at least one Stop intersects the `region_input`.
                - 'within' will return IDs of the Services whose all of the Stops are contained within the `region_input`.

        Returns:
            list: Route IDs
        """
        stops_intersecting = set(self.stops_on_spatial_condition(region_input))
        if how == "intersect":
            return list(
                {
                    item
                    for sublist in [self._graph.nodes[x]["routes"] for x in stops_intersecting]
                    for item in sublist
                }
            )
        elif how == "within":
            return self.extract_route_ids_on_attributes(
                conditions={"ordered_stops": lambda x: set(x).issubset(stops_intersecting)},
                mixed_dtypes=False,
            )
        else:
            raise NotImplementedError("Only `intersect` and `within` options for `how` param.")

    def stops_on_spatial_condition(self, region_input: Union[str, BaseGeometry]) -> list:
        """Returns Stop IDs which intersect region_input.

        Args:
            region_input (Union[str, BaseGeometry]):
                - path to a geojson file, can have multiple features.
                - string with comma separated hex tokens of Google's S2 geometry.
                A region can be covered with cells and the tokens string copied using http://s2.sidewalklabs.com/regioncoverer/.
                E.g., '89c25985,89c25987,89c2598c,89c25994,89c25999ffc,89c2599b,89c259ec,89c259f4,89c25a1c,89c25a24'.
                - shapely.geometry object, e.g. Polygon or a shapely.geometry.GeometryCollection of such objects.

        Returns:
            list: Stop IDs
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

    def _add_additional_attribute_to_graph(self, k, v):
        raise NotImplementedError

    def _find_stops_on_geojson(self, geojson_input):
        shapely_input = spatial.read_geojson_to_shapely(geojson_input)
        return self._find_stops_on_shapely_geometry(shapely_input)

    def _find_stops_on_shapely_geometry(self, shapely_input):
        stops_gdf = self.to_geodataframe()["nodes"].to_crs("epsg:4326")
        return list(stops_gdf[stops_gdf.intersects(shapely_input)].index)

    def _find_stops_on_s2_geometry(self, s2_input):
        cell_union = spatial.s2_hex_to_cell_union(s2_input)
        return [
            _id
            for _id, s2_id in self._graph.nodes(data="s2_id")
            if cell_union.intersects(CellId(s2_id))
        ]

    def _verify_no_id_change(self, new_attributes):
        id_changes = [
            id
            for id, change_dict in new_attributes.items()
            if ("id" in change_dict) and (change_dict["id"] != id)
        ]
        if len(id_changes) != 0:
            raise NotImplementedError("Changing id can only be done via the `reindex` method")

    def apply_attributes_to_services(self, new_attributes: dict):
        """Adds, or changes if already present, the attributes in new_attributes.

        Doesn't replace the dictionary stored for the Services presently, so no data is lost, unless it is being overwritten.
        Changing IDs this way with result in an error.
        Use Service's `reindex` method instead.

        Args:
            new_attributes (dict): keys are Service IDs and values are dictionaries of data to add/replace if present.
        """
        self._verify_no_id_change(new_attributes)
        services = list(new_attributes.keys())
        old_attribs = [deepcopy(self._graph.graph["services"][service]) for service in services]
        new_attribs = [
            dict_support.set_nested_value(
                self._graph.graph["services"][service], new_attributes[service]
            )
            for service in services
        ]

        self._graph.graph["change_log"] = self.change_log().modify_bunch(
            "service", services, old_attribs, services, new_attribs
        )

        for service, new_service_attribs in zip(services, new_attribs):
            self._graph.graph["services"][service] = new_service_attribs
        logging.info(f"Changed Service attributes for {len(services)} services")

    def apply_attributes_to_routes(self, new_attributes: dict):
        """Adds, or changes if already present, the attributes in new_attributes.

        Doesn't replace the dictionary stored for the Routes presently, so no data is lost, unless it is being overwritten.
        Changing IDs this way with result in an error.
        Use Route's `reindex` method instead.

        Args:
            new_attributes (dict): keys are Service IDs and values are dictionaries of data to add/replace if present.
        """
        self._verify_no_id_change(new_attributes)
        # check for stop changes
        stop_changes = {
            id
            for id, change_dict in new_attributes.items()
            if ("ordered_stops" in change_dict)
            and (change_dict["ordered_stops"] != self._graph.graph["routes"][id]["ordered_stops"])
        }
        if stop_changes:
            logging.warning(f"Stop ID changes detected for Routes: {stop_changes}")
            nodes = {n for id in stop_changes for n in self.route_reference_nodes(id)}
            edges = {e for id in stop_changes for e in self.route_reference_edges(id)}
            self._remove_routes_from_nodes(nodes=nodes, route_ids=stop_changes)
            self._remove_routes_from_edges(edges=edges, route_ids=stop_changes)
            all_new_nodes = set()
            all_new_edges = set()
            for id in stop_changes:
                new_nodes = set(new_attributes[id]["ordered_stops"])
                all_new_nodes |= new_nodes
                new_edges = {
                    (u, v)
                    for u, v in zip(
                        new_attributes[id]["ordered_stops"][:-1],
                        new_attributes[id]["ordered_stops"][1:],
                    )
                }
                all_new_edges |= new_edges
                self._add_routes_to_nodes(nodes=new_nodes, route_ids={id})
                self._add_routes_to_edges(edges=new_edges, route_ids={id})
            self._generate_services_on_nodes(all_new_nodes | nodes)
            self._generate_services_on_edges(all_new_edges | edges)

        routes = list(new_attributes.keys())
        old_attribs = [deepcopy(self._graph.graph["routes"][route]) for route in routes]
        new_attribs = [
            dict_support.set_nested_value(self._graph.graph["routes"][route], new_attributes[route])
            for route in routes
        ]

        self._graph.graph["change_log"] = self.change_log().modify_bunch(
            "route", routes, old_attribs, routes, new_attribs
        )

        for route, new_route_attribs in zip(routes, new_attribs):
            self._graph.graph["routes"][route] = new_route_attribs
        logging.info(f"Changed Route attributes for {len(routes)} routes")

    def apply_attributes_to_stops(self, new_attributes: dict):
        """Adds, or changes if already present, the attributes in new_attributes.

        Doesn't replace the dictionary stored for the Stops presently, so no data is lost, unless it is being overwritten.
        Changing IDs this way with result in an error.
        Use Stop's `reindex` method instead.

        Args:
            new_attributes (dict): keys are Service IDs and values are dictionaries of data to add/replace if present.
        """
        self._verify_no_id_change(new_attributes)
        stops = list(new_attributes.keys())
        old_attribs = [deepcopy(self._graph.nodes[stop]) for stop in stops]
        new_attribs = [
            dict_support.set_nested_value(self._graph.nodes[stop], new_attributes[stop])
            for stop in stops
        ]

        self._graph.graph["change_log"] = self.change_log().modify_bunch(
            "stop", stops, old_attribs, stops, new_attribs
        )

        nx.set_node_attributes(self._graph, dict(zip(stops, new_attribs)))
        logging.info(f"Changed Stop attributes for {len(stops)} stops")

    def apply_function_to_services(self, function: Callable, location: str):
        """Applies a function or mapping to Services within the Schedule.

        Fails silently, if the keys referred to by the function are not present, they will not be considered.
        The function will only be applied where it is possible.

        Args:
            function (Callable):
                Function of Service attributes dictionary returning a value that should be stored under `location` or a dictionary mapping.
                In the case of a dictionary all values stored under `location` will be mapped to new values given by the mapping, if they are present.

            location (str): where to save the results: string defining the key in the Service attributes dictionary
        """
        new_attributes = graph_operations.apply_to_attributes(
            self._graph.graph["services"].items(), function, location
        )
        self.apply_attributes_to_services(new_attributes)

    def apply_function_to_routes(self, function: Union[dict, Callable], location: str):
        """Applies a function or mapping to Routes within the Schedule.

        Fails silently, if the keys referred to by the function are not present, they will not be considered.
        The function will only be applied where it is possible.

        Args:
            function (Union[dict, Callable]):
                Function of Service attributes dictionary returning a value that should be stored under `location` or a dictionary mapping.
                In the case of a dictionary all values stored under `location` will be mapped to new values given by the mapping, if they are present.

            location (str): where to save the results: string defining the key in the Service attributes dictionary
        """
        new_attributes = graph_operations.apply_to_attributes(
            self._graph.graph["routes"].items(), function, location
        )
        self.apply_attributes_to_routes(new_attributes)

    def apply_function_to_stops(self, function: Union[dict, Callable], location: str):
        """Applies a function or mapping to Stops within the Schedule.

        Fails silently, if the keys referred to by the function are not present, they will not be considered.
        The function will only be applied where it is possible.

        Args:
            function (Union[dict, Callable]):
                Function of Service attributes dictionary returning a value that should be stored under `location` or a dictionary mapping.
                In the case of a dictionary all values stored under `location` will be mapped to new values given by the mapping, if they are present.

            location (str): where to save the results: string defining the key in the Service attributes dictionary
        """
        new_attributes = graph_operations.apply_to_attributes(
            self._graph.nodes(data=True), function, location
        )
        self.apply_attributes_to_stops(new_attributes)

    def _compare_stops_data(self, g):
        stop_data_in_g = {
            k: {_k: _v for _k, _v in v.items() if _k not in {"routes", "services"}}
            for k, v in dict(g.nodes(data=True)).items()
        }
        stops_without_data = []
        stops_with_conflicting_data = []

        for stop, data in stop_data_in_g.items():
            if stop in self._graph.nodes():
                schedule_stop_data = {
                    _k: _v
                    for _k, _v in dict(self._graph.nodes[stop]).items()
                    if _k not in {"routes", "services"}
                }
                if (not data) and (not schedule_stop_data):
                    stops_without_data.append(stop)
                if data:
                    diff = list(dictdiffer.diff(data, schedule_stop_data))
                    # look for 'change' diffs as that has potential to overwrite/loose data
                    if [event for event in diff if event[0] == "change"]:
                        stops_with_conflicting_data.append(stop)
            elif not data:
                stops_without_data.append(stop)
        return stops_without_data, stops_with_conflicting_data

    def add_service(self, service: Service, force: bool = False):
        """Adds a service to Schedule.

        Args:
            service (Service): genet.Service object, must have index unique w.r.t. Services already in the Schedule.
            force (bool, optional):
                force the add, even if the stops in the Service have data conflicting with the stops of the same IDs that are already in the Schedule.
                This will force the Service to be added, the stops data of currently in the Schedule will persist.
                If you want to change the data for stops use `apply_attributes_to_stops` or `apply_function_to_stops`.
                Defaults to False.
        """
        self.add_services(services=[service], force=force)

    def add_services(self, services: list[Service], force: bool = False) -> list[Service]:
        """Adds multiple services to Schedule.

        Args:
            services (list[Service]): genet.Service objects, must have index unique w.r.t. Services already in the Schedule.
            force (bool, optional):
                force the add, even if the stops in the Service have data conflicting with the stops of the same IDs that are already in the Schedule.
                This will force the Service to be added, the stops data of currently in the Schedule will persist.
                If you want to change the data for stops use `apply_attributes_to_stops` or `apply_function_to_stops`.
                Defaults to False.
        Returns:
            list[Service]: `service` with graph updates.
        """
        clashing_ids = []
        for service in services:
            if self.has_service(service.id):
                clashing_ids.append(service.id)
        if clashing_ids:
            raise ServiceIndexError(
                f"Services with IDs {clashing_ids} already exist in the Schedule."
            )
        for service in services:
            for route in service.routes():
                if self.has_route(route.id):
                    logging.warning(
                        f"Route with ID `{route.id}` within this Service `{service.id}` already exists in the "
                        f"Schedule. This Route will be reindexed to `{service.id}_{route.id}`"
                    )
                    route.reindex(f"{service.id}_{route.id}")

        for service in services:
            g = service.graph()
            stops_without_data, stops_with_conflicting_data = self._compare_stops_data(g)
            if stops_without_data:
                logging.warning(f"The following stops are missing data: {stops_without_data}")
            if stops_with_conflicting_data:
                if force:
                    logging.warning(
                        f"The following stops will inherit the data currently stored under those Stop IDs in "
                        f"the Schedule: {stops_with_conflicting_data}."
                    )
                else:
                    raise ConflictingStopData(
                        "The following stops would inherit data currently stored under those "
                        f"Stop IDs in the Schedule: {stops_with_conflicting_data}. Use `force=True` "
                        "to continue with this operation in this manner. If you want to change the "
                        "data for stops use `apply_attributes_to_stops` or "
                        "`apply_function_to_stops`."
                    )
            nodes = dict_support.merge_complex_dictionaries(
                dict(g.nodes(data=True)), dict(self._graph.nodes(data=True))
            )
            edges = dict_support.combine_edge_data_lists(
                list(g.edges(data=True)), list(self._graph.edges(data=True))
            )

            route_ids_to_add = list(service.route_ids())
            self._graph.add_nodes_from(nodes)
            self._graph.add_edges_from(edges)
            nx.set_node_attributes(self._graph, nodes)
            for route_id in route_ids_to_add:
                self._graph.graph["routes"][route_id] = g.graph["routes"][route_id]
                self._graph.graph["route_to_service_map"][route_id] = g.graph[
                    "route_to_service_map"
                ][route_id]
            self._graph.graph["services"][service.id] = g.graph["services"][service.id]
            self._graph.graph["service_to_route_map"][service.id] = g.graph["service_to_route_map"][
                service.id
            ]

        service_ids = [service.id for service in services]
        service_data = [self._graph.graph["services"][sid] for sid in service_ids]
        route_ids = [list(service.route_ids()) for service in services]
        self._graph.graph["change_log"] = self._graph.graph["change_log"].add_bunch(
            object_type="service", id_bunch=service_ids, attributes_bunch=service_data
        )
        logging.info(f"Added Services with IDs `{service_ids}` and Routes: {route_ids}")
        for service in services:
            service._graph = self._graph
        self.generate_vehicles(overwrite=False)
        return services

    def remove_service(self, service_id: str):
        """Removes Service under given index `service_id`.

        Args:
            service_id (str): Service ID to remove.
        """
        self.remove_services(service_ids=[service_id])

    def remove_services(self, service_ids: list[str]):
        """Removes Services with given indices.

        Args:
            service_ids (list[str]): List of service IDs to remove.
        """
        service_ids = persistence.listify(service_ids)
        missing_ids = []
        for service_id in service_ids:
            if not self.has_service(service_id):
                missing_ids.append(service_id)
        if missing_ids:
            raise ServiceIndexError(
                f"Services with IDs {missing_ids} do not exist in the Schedule. "
                "Cannot remove Services that aren't present."
            )
        service_data = []
        route_ids = set()
        ref_nodes = set()
        ref_edges = set()
        for service_id in service_ids:
            service_data.append(self._graph.graph["services"][service_id])
            route_ids |= set(self._graph.graph["service_to_route_map"][service_id])
            ref_nodes |= self.service_reference_nodes(service_id)
            ref_edges |= self.service_reference_edges(service_id)

        self._remove_routes_from_nodes(nodes=ref_nodes, route_ids=route_ids)
        self._remove_services_from_nodes(nodes=ref_nodes, service_ids=set(service_ids))
        self._remove_routes_from_edges(edges=ref_edges, route_ids=route_ids)
        self._remove_services_from_edges(edges=ref_edges, service_ids=set(service_ids))

        for service_id in service_ids:
            del self._graph.graph["services"][service_id]
            del self._graph.graph["service_to_route_map"][service_id]
        for r_id in route_ids:
            del self._graph.graph["route_to_service_map"][r_id]
            del self._graph.graph["routes"][r_id]

        self._graph.graph["change_log"] = self._graph.graph["change_log"].remove_bunch(
            object_type="service", id_bunch=service_ids, attributes_bunch=service_data
        )

        # update vehicles
        old_vehicles = deepcopy(self.vehicles)
        self.vehicles = {}
        self.generate_vehicles()
        self.vehicles = {
            **self.vehicles,
            **{k: v for k, v in old_vehicles.items() if k in self.vehicles},
        }
        logging.info(f"Removed Services with IDs `{service_id}`, and Routes: {route_ids}")

    def add_route(self, service_id: Union[str, int], route: Route, force: bool = False):
        """Adds route to a service already in the Schedule.

        Args:
            service_id (Union[str, int]): service id in the Schedule to add the route to.
            route (Route): Route object to add.
            force (bool, optional):
                force the add, even if the stops in the Service have data conflicting with the stops of the same IDs that are already in the Schedule.
                This will force the Service to be added, the stops data of currently in the Schedule will persist.
                If you want to change the data for stops use `apply_attributes_to_stops` or `apply_function_to_stops`.
                Defaults to False.
        """
        self.add_routes(routes_dict={service_id: [route]}, force=force)

    def add_routes(self, routes_dict: dict[str, list[Route]], force: bool = False):
        """Adds routes to services already present in the Schedule.

        Args:
            routes_dict (dict[str, list[Route]]): dictionary specifying service IDs and list of routes (Route objects) to add to them.
            force (bool, optional):
                force the add, even if the stops in the Service have data conflicting with the stops of the same IDs that are already in the Schedule.
                This will force the Service to be added, the stops data of currently in the Schedule will persist.
                If you want to change the data for stops use `apply_attributes_to_stops` or `apply_function_to_stops`.
                Defaults to False.
        """
        missing_services = []
        route_ids = []
        for service_id, routes in routes_dict.items():
            if not self.has_service(service_id):
                missing_services.append(service_id)
            else:
                for route in routes:
                    if self.has_route(route.id):
                        service = self[service_id]
                        logging.warning(
                            f"Route with ID `{route.id}` for Service {service_id} within already exists "
                            "in the Schedule. This Route will be reindexed to "
                            f"`{service_id}_{len(service) + 1}`"
                        )
                        route.reindex(f"{service_id}_{len(service) + 1}")
                    route_ids.append(route.id)
        if missing_services:
            raise ServiceIndexError(
                f"Services with IDs `{missing_services}` do not exist in the Schedule. "
                "You must add Routes to an existing Service, or add a new Service"
            )

        for service_id, routes in routes_dict.items():
            for route in routes:
                g = route.graph()
                stops_without_data, stops_with_conflicting_data = self._compare_stops_data(g)
                if stops_without_data:
                    logging.warning(f"The following stops are missing data: {stops_without_data}")
                if stops_with_conflicting_data:
                    if force:
                        logging.warning(
                            f"The following stops will inherit the data currently stored under those Stop IDs in "
                            f"the Schedule: {stops_with_conflicting_data}."
                        )
                    else:
                        raise ConflictingStopData(
                            "The following stops would inherit data currently stored under those "
                            f"Stop IDs in the Schedule: {stops_with_conflicting_data}. Use `force=True` "
                            "to continue with this operation in this manner. If you want to change the "
                            "data for stops use `apply_attributes_to_stops` or "
                            "`apply_function_to_stops`."
                        )
                nx.set_edge_attributes(
                    g, {edge: {"services": {service_id}} for edge in set(g.edges())}
                )
                nx.set_node_attributes(
                    g, {node: {"services": {service_id}} for node in set(g.nodes())}
                )
                nodes = dict_support.merge_complex_dictionaries(
                    dict(g.nodes(data=True)), dict(self._graph.nodes(data=True))
                )
                edges = dict_support.combine_edge_data_lists(
                    list(g.edges(data=True)), list(self._graph.edges(data=True))
                )
                graph_routes = dict_support.merge_complex_dictionaries(
                    g.graph["routes"], self._graph.graph["routes"]
                )
                self._graph.graph["route_to_service_map"][route.id] = service_id
                self._graph.graph["service_to_route_map"][service_id].append(route.id)

                self._graph.add_nodes_from(nodes)
                self._graph.add_edges_from(edges)
                nx.set_node_attributes(self._graph, nodes)
                self._graph.graph["routes"] = graph_routes

        route_data = [self._graph.graph["routes"][rid] for rid in route_ids]
        self._graph.graph["change_log"] = self._graph.graph["change_log"].add_bunch(
            object_type="route", id_bunch=route_ids, attributes_bunch=route_data
        )
        logging.info(
            f"Added Routes with IDs {route_ids}, to Services `{list(routes_dict.keys())}` within the "
            f"Schedule"
        )
        for service_id, routes in routes_dict.items():
            for route in routes:
                route._graph = self._graph
        self.generate_vehicles(overwrite=False)
        return routes_dict

    def remove_route(self, route_id: str):
        """Removes Route under index `route_id`.

        Args:
            route_id (str): route ID to remove

        """
        self.remove_routes(route_ids=[route_id])

    def remove_routes(self, route_ids: list[str]):
        """Removes Route under index `route_id`.

        Args:
            route_ids (list[str]): route IDs to remove.
        """
        route_ids = persistence.listify(route_ids)
        missing_ids = []
        for route_id in route_ids:
            if not self.has_route(route_id):
                missing_ids.append(route_id)
        if missing_ids:
            raise RouteIndexError(
                f"Routes with IDs {missing_ids} do not exist in the Schedule. "
                "Cannot remove Routes that aren't present."
            )

        route_data = []
        service_ids = set()
        route_ref_nodes = set()
        route_ref_edges = set()
        for route_id in route_ids:
            route_data.append(self._graph.graph["routes"][route_id])
            service_id = self._graph.graph["route_to_service_map"][route_id]
            service_ids.add(service_id)
            route_ref_nodes |= self.route_reference_nodes(route_id)
            route_ref_edges |= self.route_reference_edges(route_id)

        self._remove_routes_from_nodes(nodes=route_ref_nodes, route_ids=set(route_ids))
        self._remove_routes_from_edges(edges=route_ref_edges, route_ids=set(route_ids))

        service_ref_nodes = set()
        service_ref_edges = set()
        for service_id in service_ids:
            for node in route_ref_nodes:
                if not (
                    self._graph.nodes[node]["routes"]
                    & set(self._graph.graph["service_to_route_map"][service_id])
                ):
                    service_ref_nodes.add(node)
            for u, v in route_ref_edges:
                if not (
                    self._graph[u][v]["routes"]
                    & set(self._graph.graph["service_to_route_map"][service_id])
                ):
                    service_ref_edges.add((u, v))
        self._remove_services_from_nodes(nodes=service_ref_nodes, service_ids=service_ids)
        self._remove_services_from_edges(edges=service_ref_edges, service_ids=service_ids)

        for route_id in route_ids:
            service_id = self._graph.graph["route_to_service_map"][route_id]
            self._graph.graph["service_to_route_map"][service_id].remove(route_id)
            del self._graph.graph["route_to_service_map"][route_id]
            del self._graph.graph["routes"][route_id]
            if not self._graph.graph["service_to_route_map"][service_id]:
                logging.warning(
                    f"Removal of Routes led to a whole service {service_id} being removed"
                )
                del self._graph.graph["service_to_route_map"][service_id]
                del self._graph.graph["services"][service_id]

        self._graph.graph["change_log"] = self._graph.graph["change_log"].remove_bunch(
            object_type="route", id_bunch=route_ids, attributes_bunch=route_data
        )

        # update vehicles
        old_vehicles = deepcopy(self.vehicles)
        self.vehicles = {}
        self.generate_vehicles()
        self.vehicles = {
            **self.vehicles,
            **{k: v for k, v in old_vehicles.items() if k in self.vehicles},
        }
        logging.info(f"Removed Routes with IDs {route_ids}, to Services `{service_id}`.")

    def remove_stop(self, stop_id: str):
        """Removes Stop under index `stop_id`.

        Args:
            stop_id (str): Stop ID to remove.
        """
        self.remove_stops([stop_id])

    def remove_stops(self, stop_ids: Union[list, set]):
        stop_ids = persistence.listify(set(stop_ids))
        for stop_id in stop_ids:
            if not self.has_stop(stop_id):
                stop_ids.pop(stop_id)
                raise StopIndexError(
                    f"Stop with ID `{stop_id}` does not exist in the Schedule. "
                    "Cannot remove a Stop that isn't present."
                )

        stop_data = [data for _id, data in self._graph.nodes(data=True) if _id in stop_ids]
        routes_affected = set().union(*[data.pop("routes") for data in stop_data])
        services_affected = set().union(*[data.pop("services") for data in stop_data])
        self._graph.remove_nodes_from(stop_ids)
        self.remove_stops_from_minimal_transfer_times(stop_ids)

        self._graph.graph["change_log"] = self._graph.graph["change_log"].remove_bunch(
            object_type="stop", id_bunch=stop_ids, attributes_bunch=stop_data
        )
        logging.info(
            f"Removed Stops with indices `{stop_ids}`."
            f"Routes affected: {routes_affected}. Services affected: {services_affected}."
        )

    def remove_stops_from_minimal_transfer_times(self, stop_ids):
        # first level keys of the min transfer times
        # 'stop_to_remove' : {'stop_1': 10}
        [self.minimal_transfer_times.pop(s) for s in stop_ids if s in self.minimal_transfer_times]
        # second level, stops the keys are mapping to
        # 'stop_1' : {'stop_to_remove': 10}
        [
            [val.pop(s) for s in stop_ids if s in val]
            for k, val in self.minimal_transfer_times.items()
        ]
        # clean up empties in the second level
        # 'stop_1' : {}
        empties = [s for s, val in self.minimal_transfer_times.items() if not val]
        [self.minimal_transfer_times.pop(s) for s in empties if s in self.minimal_transfer_times]

    def remove_unsused_stops(self):
        logging.warning(
            "This method has been replaced due to incorrect spelling and is now deprecated. "
            "It will be removed in future versions. Please use `remove_unused_stops` instead."
        )
        self.remove_unused_stops()

    def remove_unused_stops(self):
        stops_to_remove = set()
        for stop, data in self._graph.nodes(data="routes"):
            if not data:
                stops_to_remove.add(stop)
        # but leave those stops that have transfers
        stops_to_remove = stops_to_remove - set().union(
            *[{from_s} | set(val.keys()) for from_s, val in self.minimal_transfer_times.items()]
        )
        if stops_to_remove:
            self.remove_stops(stops_to_remove)

    def has_trips_with_zero_headways(self) -> bool:
        """Deletes trips that have zero headways and thus deemed duplicates.

        Returns:
            bool: True if any trips have zero headway.
        """
        trip_headways_df = self.trips_headways()
        zero_headways = trip_headways_df[(trip_headways_df["headway_mins"] == 0)]
        return not bool(zero_headways.empty)

    def fix_trips_with_zero_headways(self):
        """
        Deletes trips that have zero headways and thus deemed duplicates
        """
        trip_headways_df = self.trips_headways()
        zero_headways = trip_headways_df[(trip_headways_df["headway_mins"] == 0)]

        if not zero_headways.empty:
            logging.info(
                f"Found {len(zero_headways)} trips with zero headways. "
                f"{len(set(zero_headways['route_id']))} out of {len(set(trip_headways_df['route_id']))} "
                f"routes and {len(set(zero_headways['service_id']))} out of "
                f"{len(set(trip_headways_df['service_id']))} services are affected. "
                "These will now be dropped as though they are duplicates of other trips, "
                "thus resulting in zero headway between them"
            )
            new_trips = trip_headways_df[trip_headways_df["headway_mins"] != 0].drop(
                ["headway_mins", "headway"], axis=1
            )
            new_trips_for_affected_routes = new_trips.loc[
                new_trips["route_id"].isin(set(zero_headways["route_id"])), :
            ]
            self.set_trips_dataframe(new_trips_for_affected_routes.copy())
            self.generate_vehicles(overwrite=True)
            # check
            _trip_headways_df = self.trips_headways()
            _zero_headways = _trip_headways_df[(_trip_headways_df["headway_mins"] == 0)]
            logging.info(
                f"Checks after alterations result in {len(_zero_headways)} trips with zero headway"
            )
        else:
            logging.info("No trips with zero headway found. Nothing to do.")

    def has_infinite_speeds(self):
        pt_speeds = self.speed_geodataframe()
        pt_speeds_inf = pt_speeds[(pt_speeds["speed"] == math.inf)]
        return not bool(pt_speeds_inf.empty)

    def fix_infinite_speeds(self):
        df_speeds = self.speed_geodataframe()
        df_speeds_inf = df_speeds[(df_speeds["speed"] == math.inf)]
        if not df_speeds_inf.empty:
            affected_routes = set(df_speeds_inf["route_id"])
            logging.info(
                f"Found {len(affected_routes)} routes with infinite speeds. "
                f"{len(set(df_speeds_inf['service_id']))} out of {len(set(df_speeds['service_id']))} "
                "services are affected. "
                "These will now be dropped as though they are duplicates of other trips, "
                "thus resulting in zero headway between them"
            )
            new_route_attributes_dict = {}
            for route_id in affected_routes:
                df_route_speeds = df_speeds[df_speeds["route_id"] == route_id]
                df_route_speeds["length"] = [1.3 * x.length for x in df_route_speeds["geometry"]]

                old_arrival_offsets = self.route(route_id).__dict__["arrival_offsets"]
                old_departure_offsets = self.route(route_id).__dict__["departure_offsets"]
                updated_arrival_offsets = ["00:00:00"]
                updated_departure_offsets = ["00:00:00"]

                avg_speed = df_route_speeds[df_route_speeds["speed"] != math.inf]["speed"].mean()
                distances = df_route_speeds["length"].to_list()

                for i in range(1, len(old_arrival_offsets)):
                    # if the offset is the same as previous (i.e. GTFS error),
                    # OR if the previous offset got infilled with a value bigger than the current offset
                    if datetime.strptime(
                        updated_departure_offsets[i - 1], "%H:%M:%S"
                    ) >= datetime.strptime(old_arrival_offsets[i], "%H:%M:%S"):
                        time = round(distances[i - 1] / avg_speed, 0)
                        previous_offset = datetime.strptime(
                            updated_departure_offsets[i - 1], "%H:%M:%S"
                        )
                        current_offset = previous_offset + timedelta(seconds=time)
                        str_current_offset = datetime.strftime(current_offset, "%H:%M:%S")
                        updated_arrival_offsets.append(str_current_offset)
                        updated_departure_offsets.append(str_current_offset)
                    else:
                        updated_arrival_offsets.append(old_arrival_offsets[i])
                        updated_departure_offsets.append(old_departure_offsets[i])
                new_route_attributes_dict[route_id] = {
                    "arrival_offsets": updated_arrival_offsets,
                    "departure_offsets": updated_departure_offsets,
                }
            self.apply_attributes_to_routes(new_attributes=new_route_attributes_dict)
        else:
            logging.info("No routes with infinite speeds were found. Nothing to do.")

    def is_strongly_connected(self):
        if nx.number_strongly_connected_components(self.graph()) == 1:
            return True
        return False

    def has_self_loops(self):
        return list(nx.nodes_with_selfloops(self.graph()))

    def intermodal_access_egress_attribute_keys(self):
        return [
            node.name
            for node in graph_operations.get_attribute_schema(
                self._graph.nodes(data=True), data=False
            ).leaves
            if "accessLinkId" in node.name
        ]

    def has_intermodal_access_egress_connections(self):
        return bool(self.intermodal_access_egress_attribute_keys())

    def intermodal_access_egress_connections(self):
        attribute_keys = self.intermodal_access_egress_attribute_keys()
        df = self.stop_attribute_data(keys=[{"attributes": key} for key in attribute_keys])
        return df

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
            invalid_stages.append("not_has_valid_services")

        if return_reason:
            return valid, invalid_stages
        return valid

    def generate_validation_report(self):
        return schedule_validation.generate_validation_report(schedule=self)

    def generate_standard_outputs(self, output_dir, gtfs_day="19700101", filetype: str = "parquet"):
        """Generates geojsons that can be used for generating standard kepler visualisations.

        These can also be used for validating network for example inspecting link capacity, freespeed, number of lanes, the shape of modal subgraphs.

        Args:
            output_dir (str): path to folder where to save resulting geojsons.
            gtfs_day (str, optional):
                Day in format YYYYMMDD for the network's schedule for consistency in visualisations,
                Defaults to "19700101" (1970-01-01).
            filetype (str, optional):
                The file type to save the GeoDataFrame to: geojson, geoparquet or shp are supported.
                Defaults to parquet format.
        """
        spatial_output.generate_standard_outputs_for_schedule(
            self, output_dir=output_dir, gtfs_day=gtfs_day, filetype=filetype
        )
        logging.info("Finished generating standard outputs. Zipping folder.")
        persistence.zip_folder(output_dir)

    def write_to_matsim(self, output_dir: str, reproj_processes: int = 1):
        """Save to MATSim XML format.

        Args:
            output_dir (str): path to output directory.
            reproj_processes (int, optional):
                You can set this in case you have a lot of stops and your stops need to be reprojected.
                It splits the process across given number of processes.
                Defaults to 1.
        """
        persistence.ensure_dir(output_dir)
        matsim_xml_writer.write_matsim_schedule(output_dir, self, reproj_processes=reproj_processes)
        matsim_xml_writer.write_vehicles(output_dir, self.vehicles, self.vehicle_types)
        self.write_extras(output_dir)

    def write_extras(self, output_dir):
        self.change_log().export(os.path.join(output_dir, "schedule_change_log.csv"))

    def to_json(self):
        stop_keys = {
            d.name
            for d in graph_operations.get_attribute_schema(self._graph.nodes(data=True)).children
        }
        stop_keys = stop_keys - {"routes", "services", "additional_attributes", "epsg"}
        stops = self.stop_attribute_data(keys=stop_keys)
        services = self._graph.graph["services"]
        for service_id, data in services.items():
            data["routes"] = {
                route_id: self._graph.graph["routes"][route_id]
                for route_id in self._graph.graph["service_to_route_map"][service_id]
            }
        d = {"stops": dict_support.dataframe_to_dict(stops.T), "services": services}
        if self.minimal_transfer_times:
            d["minimal_transfer_times"] = self.minimal_transfer_times
        return {
            "schedule": d,
            "vehicles": {"vehicle_types": self.vehicle_types, "vehicles": self.vehicles},
        }

    def write_to_json(self, output_dir: str):
        """Writes Schedule to a single JSON file with stops, services, vehicles and minimum transfer times (if applicable)

        Args:
            output_dir (str): output directory.
        """
        persistence.ensure_dir(output_dir)
        logging.info(f"Saving Schedule to JSON in {output_dir}")
        with open(os.path.join(output_dir, "schedule.json"), "w") as outfile:
            json.dump(self.to_json(), outfile)
        self.write_extras(output_dir)

    def write_spatial(self, output_dir, epsg: Optional[str] = None, filetype: str = "parquet"):
        """Transforms Schedule (if applicable) to geopandas.GeoDataFrame of nodes and links and saves to
        the requested file format.

        Args:
            output_dir (str):
                Path to folder where to save the file.
            epsg (Optional[str], optional):
                Projection if the geometry is to be reprojected. Defaults to None (no reprojection).
            filetype (str, optional):
                The file type to save the GeoDataFrame to: geojson, geoparquet or shp are supported.
                Defaults to parquet format.
        """
        if filetype.lower() not in genet.utils.io.SUPPORTED_FILE_FORMATS:
            raise RuntimeError(
                "You've requested to save Schedule as a GeoDataFrame but did not select any of the "
                f"file formats available: {', '.join(genet.utils.io.SUPPORTED_FILE_FORMATS)}"
            )

        persistence.ensure_dir(output_dir)
        _gdfs = self.to_geodataframe()
        if epsg is not None:
            _gdfs["nodes"] = _gdfs["nodes"].to_crs(epsg)
            _gdfs["links"] = _gdfs["links"].to_crs(epsg)
        logging.info(f"Saving Schedule in {output_dir}")
        for gdf, filename in (
            (_gdfs["nodes"], "schedule_nodes"),
            (_gdfs["links"], "schedule_links"),
            (_gdfs["nodes"]["geometry"], "schedule_nodes_geometry_only"),
            (_gdfs["links"]["geometry"], "schedule_links_geometry_only"),
        ):
            genet.utils.io.save_geodataframe(gdf, filename, output_dir, filetype=filetype)
        self.write_extras(output_dir)

    def to_gtfs(self, gtfs_day: str, mode_to_route_type: Optional[dict] = None) -> dict:
        """Transforms Schedule in to GTFS-like format.

        It's not full GTFS as it only represents one day, misses a lot of optional data and does not include `agency.txt` required file.
        Produces 'stops', 'routes', 'trips', 'stop_times', 'calendar' tables.

        Args:
            gtfs_day (str): day used for GTFS when creating the network in YYYYMMDD format
            mode_to_route_type (Optional[dict], optional):
                PT modes in Route objects to route type code by default uses https://developers.google.com/transit/gtfs/reference#routestxt
                Example:
                ```python
                {
                    "tram": 0, "subway": 1, "rail": 2, "bus": 3, "ferry": 4, "cablecar": 5, "gondola": 6, "funicular": 7
                }
                ```
                Reference for extended mode types:
                https://developers.google.com/transit/gtfs/reference/extended-route-types.

        Returns:
            dict: keys are the names of the tables e.g. `stops` for the `stops.txt` file, values are pandas.DataFrame tables.
        """
        stops = self.stop_attribute_data(
            keys=[
                "id",
                "name",
                "lat",
                "lon",
                "stop_code",
                "stop_desc",
                "zone_id",
                "stop_url",
                "location_type",
                "parent_station",
                "stop_timezone",
                "wheelchair_boarding",
                "level_id",
                "platform_code",
            ]
        )
        stops = stops.rename(
            columns={"id": "stop_id", "name": "stop_name", "lat": "stop_lat", "lon": "stop_lon"}
        )

        routes = self.route_attribute_data(
            keys=[
                "id",
                "route_short_name",
                "route_long_name",
                "mode",
                "agency_id",
                "route_desc",
                "route_url",
                "route_type",
                "route_color",
                "route_text_color",
                "route_sort_order",
                "continuous_pickup",
                "continuous_drop_off",
            ]
        )
        if mode_to_route_type is None:
            mode_to_route_type = {
                "tram": 0,
                "subway": 1,
                "rail": 2,
                "bus": 3,
                "ferry": 4,
                "cablecar": 5,
                "gondola": 6,
                "funicular": 7,
            }
        routes.loc[routes["route_type"].isna(), "route_type"] = routes.loc[
            routes["route_type"].isna(), "mode"
        ].map(mode_to_route_type)
        routes["route_id"] = routes["id"].map(self._graph.graph["route_to_service_map"])
        routes = routes.drop(["mode", "id"], axis=1)
        routes = routes.groupby("route_id").first().reset_index()

        trips = self.route_attribute_data(
            keys=["id", "ordered_stops", "arrival_offsets", "departure_offsets"]
        )
        trips = trips.merge(self.trips_to_dataframe(), left_on="id", right_on="route_id")
        trips["route_id"] = trips["service_id"]

        # expand the frame for stops and offsets to get stop times
        trips["stop_sequence"] = trips["ordered_stops"].apply(lambda x: list(range(len(x))))
        trips["departure_offsets"] = trips["departure_offsets"].apply(
            lambda x: list(map(use_schedule.get_offset, x))
        )
        trips["arrival_offsets"] = trips["arrival_offsets"].apply(
            lambda x: list(map(use_schedule.get_offset, x))
        )
        stop_times = DataFrame(
            {
                col: np.repeat(trips[col].values, trips["ordered_stops"].str.len())
                for col in {"trip_id", "trip_departure_time"}
            }
        ).assign(
            stop_id=np.concatenate(trips["ordered_stops"].values),
            stop_sequence=np.concatenate(trips["stop_sequence"].values),
            departure_time=np.concatenate(trips["departure_offsets"].values),
            arrival_time=np.concatenate(trips["arrival_offsets"].values),
        )
        stop_times["arrival_time"] = (
            stop_times["trip_departure_time"] + stop_times["arrival_time"]
        ).dt.strftime("%H:%M:%S")
        stop_times["departure_time"] = (
            stop_times["trip_departure_time"] + stop_times["departure_time"]
        ).dt.strftime("%H:%M:%S")
        stop_times = stop_times.drop(["trip_departure_time"], axis=1)
        for col in [
            "stop_headsign",
            "pickup_type",
            "drop_off_type",
            "continuous_pickup",
            "continuous_drop_off",
            "shape_dist_traveled",
            "timepoint",
        ]:
            stop_times[col] = float("nan")

        # finish off trips frame
        trips = trips[["route_id", "service_id", "trip_id"]]
        for col in [
            "trip_headsign",
            "trip_short_name",
            "direction_id",
            "block_id",
            "shape_id",
            "wheelchair_accessible",
            "bikes_allowed",
        ]:
            trips[col] = float("nan")

        calendar = DataFrame(routes["route_id"])
        for col in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
            calendar[col] = 1
        calendar["start_date"] = gtfs_day
        calendar["end_date"] = gtfs_day
        return {
            "stops": stops,
            "routes": routes,
            "trips": trips,
            "stop_times": stop_times,
            "calendar": calendar,
        }

    def write_to_csv(
        self,
        output_dir: str,
        gtfs_day: str = "19700101",
        file_extention: Literal["csv", "txt"] = "csv",
    ):
        """Writes 'stops', 'routes', 'trips', 'stop_times', 'calendar' tables to CSV files.

        Args:
            output_dir (str): folder to output csv or txt files.
            gtfs_day (str, optional): day used for GTFS when creating the network in YYYYMMDD format. Defaults to "19700101".
            file_extention (Literal[csv, txt], optional): File extension to save to. Defaults to "csv".
        """
        persistence.ensure_dir(output_dir)
        logging.info(f"Saving Schedule to GTFS {file_extention} in {output_dir}")
        for table, df in self.to_gtfs(gtfs_day).items():
            file_path = os.path.join(output_dir, f"{table}.{file_extention}")
            logging.info(f"Saving {file_path}")
            df.to_csv(file_path)
        self.write_extras(output_dir)

    def write_to_gtfs(self, output_dir: str, gtfs_day: str = "19700101"):
        """Writes 'stops', 'routes', 'trips', 'stop_times', 'calendar' tables to CSV files.

        Args:
            output_dir (str): folder to output csv or txt files.
            gtfs_day (str, optional): day used for GTFS when creating the network in YYYYMMDD format. Defaults to "19700101".
        """
        self.write_to_csv(output_dir, gtfs_day=gtfs_day, file_extention="txt")

    def summary(self):
        report = {}
        schedule_stats = {
            "number_of_services": self.__len__(),
            "number_of_routes": self.number_of_routes(),
            "number_of_stops": len(self.reference_nodes()),
        }
        report["schedule_info"] = schedule_stats

        report["modes"] = {}
        schedule_modes = self.modes()
        report["modes"]["modes_in_schedule"] = schedule_modes

        services_by_modes = {}
        for mode in schedule_modes:
            services_by_modes[mode] = len(self.services_on_modal_condition(mode))
        report["modes"]["services_by_mode"] = services_by_modes

        stops_by_modes = {}
        for mode in schedule_modes:
            stops_by_modes[mode] = len(self.stops_on_modal_condition(mode))
        report["modes"]["pt_stops_by_mode"] = stops_by_modes

        df = pd.DataFrame(list(self.stop_attribute_data("attributes")["attributes"]))
        report["stop_attributes"] = set(df.columns)
        report["accessibility_tags"] = {}
        for col in df.columns:
            if "Accessible" in col:
                mode = col.replace("Accessible", "")
                network_access_tag = f"accessLinkId_{mode}"
                report["accessibility_tags"][mode] = {
                    "access_tag": col,
                    "number_of_stops_with_access_tag": len(df[col].dropna()),
                    "unique_values_under_access_tag": set(df[col].dropna().unique()),
                    "link_access_tag": (
                        network_access_tag
                        if network_access_tag in df.columns
                        else "not_connected_to_network"
                    ),
                    "number_of_stops_with_link_access_tag": (
                        len(df[network_access_tag].dropna())
                        if network_access_tag in df.columns
                        else 0
                    ),
                }
        return report


def verify_graph_schema(graph):
    if not isinstance(graph, nx.DiGraph):
        raise ScheduleElementGraphSchemaError(
            f"Object of type {type(graph)} passed. The graph for a schedule element needs "
            f"to be a networkx.DiGraph"
        )

    required_stop_attributes = {"x", "y", "id", "epsg"}
    for node, node_attribs in graph.nodes(data=True):
        if not required_stop_attributes.issubset(set(node_attribs.keys())):
            missing_attribs = required_stop_attributes - set(node_attribs.keys())
            raise ScheduleElementGraphSchemaError(
                f"Node/Stop {node} is missing the following attributes: " f"{missing_attribs}"
            )

    required_route_attributes = {
        "arrival_offsets",
        "ordered_stops",
        "route_short_name",
        "mode",
        "departure_offsets",
        "trips",
    }
    if "routes" not in graph.graph:
        raise ScheduleElementGraphSchemaError("Graph is missing `routes` attribute")
    else:
        for route_id, route_dict in graph.graph["routes"].items():
            if not required_route_attributes.issubset(set(route_dict.keys())):
                missing_attribs = required_route_attributes - set(route_dict.keys())
                raise ScheduleElementGraphSchemaError(
                    f"Route {route_id} is missing the following attributes: " f"{missing_attribs}"
                )

    required_service_attributes = {"id"}
    if "services" not in graph.graph:
        raise ScheduleElementGraphSchemaError("Graph is missing `services` attribute")
    else:
        for service_id, service_dict in graph.graph["services"].items():
            if not required_service_attributes.issubset(set(service_dict.keys())):
                missing_attribs = required_service_attributes - set(service_dict.keys())
                raise ScheduleElementGraphSchemaError(
                    f"Service {service_id} is missing the following attributes: "
                    f"{missing_attribs}"
                )


def read_vehicle_types(yml: str) -> dict:
    """
    Args:
        yml (str): path to .yml file based on example vehicles config in `genet/configs/vehicles/vehicle_definitions.yml`.

    Returns:
        dict: Vehicle type dictionary.
    """
    if persistence.is_yml(yml):
        yml = io.open(yml, mode="r")
    return yaml.load(yml, Loader=yaml.FullLoader)["VEHICLE_TYPES"]


def get_headway(group):
    group["headway"] = group["trip_departure_time"].diff()
    return group


def generate_trip_departures_from_headway(headway_spec: dict):
    """Generates new trip departure times.

    Args:
        headway_spec (dict):
            Dictionary with tuple keys: (from time, to time) and headway values in minutes:
            `{('HH:MM:SS', 'HH:MM:SS'): headway_minutes}`.
    """
    trip_departures = set()
    for (from_time, to_time), headway_mins in headway_spec.items():
        trip_departures |= set(
            pd.date_range(
                f"1970-01-01 {from_time}", f"1970-01-01 {to_time}", freq=f"{headway_mins}min"
            )
        )
    return trip_departures
