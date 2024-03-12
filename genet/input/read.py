import ast
import json
import logging
from typing import Optional

import geopandas as gpd
import networkx as nx
import pandas as pd

import genet
import genet.core as core
import genet.input.gtfs_reader as gtfs_reader
import genet.input.matsim_reader as matsim_reader
import genet.input.osm_reader as osm_reader
import genet.modify.change_log as change_log
import genet.schedule_elements as schedule_elements
import genet.utils.dict_support as dict_support
import genet.utils.parallel as parallel
import genet.utils.spatial as spatial
from genet.exceptions import NetworkSchemaError


def read_matsim(
    path_to_network: str,
    epsg: str,
    path_to_schedule: Optional[str] = None,
    path_to_vehicles: Optional[str] = None,
    force_long_form_attributes: bool = False,
) -> core.Network:
    """Creates a GeNet Network from MATSim's network.xml and (optionally) schedule.xml and vehicles.xml files.

    If given, schedule and vehicles files will be used to create a `genet.Schedule` object, which will be added to the generated `genet.Network` object.
    the schedule file needs to be given if the vehicles file is given.

    Args:
        path_to_network (str): Path to MATSim's `network.xml` file.
        epsg (str): Projection for the network, e.g. 'epsg:27700'.
        path_to_schedule (Optional[str], optional): Path to MATSim's `schedule.xml` file. Defaults to None.
        path_to_vehicles (Optional[str], optional): Path to MATSim's `vehicles.xml` file,. Defaults to None.
        force_long_form_attributes (bool, optional):
            If True the additional attributes will be read into verbose format:
            ```dict
                {'additional_attrib': {'name': 'additional_attrib', 'class': 'java.lang.String', 'text': attrib_value}}
            ```
            where `attrib_value` is always a python string.

            If False, defaults to short-form:
            ```python
                {'additional_attrib': attrib_value}
            ```
            where the type of `attrib_value` is mapped to a python type using the declared java class.

            !!! note
                Network level attributes cannot be forced to be read into long form.

            Defaults to False.

    Returns:
        core.Network: GeNet Network object.
    """
    n = read_matsim_network(
        path_to_network=path_to_network,
        epsg=epsg,
        force_long_form_attributes=force_long_form_attributes,
    )
    if path_to_schedule:
        n.schedule = read_matsim_schedule(
            path_to_schedule=path_to_schedule,
            path_to_vehicles=path_to_vehicles,
            epsg=epsg,
            force_long_form_attributes=force_long_form_attributes,
        )
    return n


def read_matsim_network(
    path_to_network: str, epsg: str, force_long_form_attributes: bool = False
) -> core.Network:
    """Reads MATSim's network.xml to genet.Network object.

    Args:
        path_to_network (str): Path to MATSim's `network.xml` file.
        epsg (str): Projection for the network, e.g. 'epsg:27700'.
        force_long_form_attributes (bool, optional):
            If True the additional attributes will be read into verbose format:
            ```dict
                {'additional_attrib': {'name': 'additional_attrib', 'class': 'java.lang.String', 'text': attrib_value}}
            ```
            where `attrib_value` is always a python string.

            If False, defaults to short-form:
            ```python
                {'additional_attrib': attrib_value}
            ```
            where the type of `attrib_value` is mapped to a python type using the declared java class.

            !!! note
                Network level attributes cannot be forced to be read into long form.

            Defaults to False.

    Returns:
        core.Network: GeNet Network object.
    """
    n = core.Network(epsg=epsg)
    (
        n.graph,
        n.link_id_mapping,
        duplicated_nodes,
        duplicated_links,
        network_attributes,
    ) = matsim_reader.read_network(
        path_to_network, n.transformer, force_long_form_attributes=force_long_form_attributes
    )
    n.attributes = dict_support.merge_complex_dictionaries(n.attributes, network_attributes)
    n.graph.graph["crs"] = n.epsg

    for node_id, duplicated_node_attribs in duplicated_nodes.items():
        for duplicated_node_attrib in duplicated_node_attribs:
            n.change_log.remove(
                object_type="node", object_id=node_id, object_attributes=duplicated_node_attrib
            )
    for link_id, reindexed_duplicated_links in duplicated_links.items():
        for duplicated_link in reindexed_duplicated_links:
            n.change_log.modify(
                object_type="link",
                old_id=link_id,
                old_attributes=n.link(duplicated_link),
                new_id=duplicated_link,
                new_attributes=n.link(duplicated_link),
            )
    return n


def read_matsim_schedule(
    path_to_schedule: str,
    epsg: str,
    path_to_vehicles: Optional[str] = None,
    force_long_form_attributes: bool = False,
) -> schedule_elements.Schedule:
    """Reads MATSim's schedule.xml (and possibly vehicles.xml) to genet.Schedule object.

    Args:
        path_to_schedule (str): Path to MATSim's `schedule.xml` file.
        epsg (str): Projection for the network, e.g. 'epsg:27700'.
        path_to_vehicles (Optional[str], optional): Path to MATSim's `vehicles.xml` file,. Defaults to None.
        force_long_form_attributes (bool, optional):
            If True the additional attributes will be read into verbose format:
            ```dict
                {'additional_attrib': {'name': 'additional_attrib', 'class': 'java.lang.String', 'text': attrib_value}}
            ```
            where `attrib_value` is always a python string.

            If False, defaults to short-form:
            ```python
                {'additional_attrib': attrib_value}
            ```
            where the type of `attrib_value` is mapped to a python type using the declared java class.

            !!! note
                Network level attributes cannot be forced to be read into long form.

            Defaults to False.

    Returns:
        schedule_elements.Schedule: GeNet Schedule object.
    """
    (
        services,
        minimal_transfer_times,
        transit_stop_id_mapping,
        schedule_attributes,
    ) = matsim_reader.read_schedule(
        path_to_schedule, epsg, force_long_form_attributes=force_long_form_attributes
    )
    if path_to_vehicles:
        vehicles, vehicle_types = matsim_reader.read_vehicles(path_to_vehicles)
        matsim_schedule = schedule_elements.Schedule(
            services=services, epsg=epsg, vehicles=vehicles, vehicle_types=vehicle_types
        )
    else:
        matsim_schedule = schedule_elements.Schedule(services=services, epsg=epsg)
    matsim_schedule.minimal_transfer_times = minimal_transfer_times

    extra_stops = {
        stop: transit_stop_id_mapping[stop]
        for stop in set(transit_stop_id_mapping) - set(matsim_schedule.graph().nodes())
    }
    for k in extra_stops.keys():
        extra_stops[k] = schedule_elements.Stop(**extra_stops[k]).__dict__
        extra_stops[k]["routes"] = set()
        extra_stops[k]["services"] = set()
    matsim_schedule._graph.add_nodes_from(extra_stops)
    nx.set_node_attributes(matsim_schedule._graph, extra_stops)
    matsim_schedule.attributes = dict_support.merge_complex_dictionaries(
        matsim_schedule.attributes, schedule_attributes
    )
    return matsim_schedule


def read_json(network_path: str, epsg: str, schedule_path: Optional[str] = None) -> core.Network:
    """Reads Network and, if passed, Schedule JSON files in to a genet.Network.

    Args:
        network_path (str): path to JSON network file.
        epsg (str): Projection for the network, e.g. 'epsg:27700'.
        schedule_path (Optional[str], optional): Path to json schedule file. Defaults to None.

    Returns:
        core.Network: GeNet network object.
    """
    n = read_json_network(network_path, epsg)
    if schedule_path is not None:
        n.schedule = read_json_schedule(schedule_path, epsg)
    return n


def read_geojson_network(nodes_path: str, links_path: str, epsg: str) -> core.Network:
    """Reads Network graph from JSON file.

    Args:
        nodes_path (str): Path to geojson network nodes file.
        links_path (str): Path to geojson network links file.
        epsg (str): Projection for the network, e.g. 'epsg:27700'.

    Returns:
        core.Network: GeNet network object.
    """
    logging.info(f"Reading Network nodes from {nodes_path}")
    nodes = gpd.read_file(nodes_path)
    nodes = nodes.drop("geometry", axis=1)
    nodes["id"] = nodes["id"].astype(int).astype(str)
    nodes = nodes.set_index("id", drop=False)
    if "index" in nodes.columns:
        nodes = nodes.drop("index", axis=1)

    logging.info(f"Reading Network links from {links_path}")
    links = gpd.read_file(links_path).to_crs(epsg)
    links["modes"] = links["modes"].apply(lambda x: set(x.split(",")))
    links["id"] = links["id"].astype(int).astype(str)
    links = links.set_index("id", drop=False)
    if "index" in links.columns:
        links = links.drop("index", axis=1)

    n = core.Network(epsg=epsg)
    n.add_nodes(nodes.T.to_dict())
    n.add_links(links.T.to_dict())
    n.change_log = change_log.ChangeLog()
    return n


def read_json_network(network_path: str, epsg: str) -> core.Network:
    """Reads network JSON file in to a genet.Network.

    Args:
        network_path (str): path to JSON or GeoJSON network file.
        epsg (str): Projection for the network, e.g. 'epsg:27700'.

    Returns:
        core.Network: GeNet network object.
    """
    logging.info(f"Reading Network from {network_path}")
    with open(network_path) as json_file:
        json_data = json.load(json_file)
    for _, data in json_data["nodes"].items():
        try:
            del data["geometry"]
        except KeyError:
            pass

    for _, data in json_data["links"].items():
        try:
            data["geometry"] = spatial.decode_polyline_to_shapely_linestring(data["geometry"])
        except KeyError:
            pass
        try:
            data["modes"] = set(data["modes"].split(","))
        except KeyError:
            pass

    n = core.Network(epsg=epsg)
    n.add_nodes(json_data["nodes"])
    n.add_links(json_data["links"])
    n.change_log = change_log.ChangeLog()
    return n


def read_json_schedule(schedule_path: str, epsg: str) -> schedule_elements.Schedule:
    """Reads Schedule from a JSON file.

    Args:
        schedule_path (str): path to JSON or GeoJSON schedule file.
        epsg (str): Projection for the network, e.g. 'epsg:27700'.

    Returns:
        schedule_elements.Schedule: GeNet schedule object.
    """
    logging.info(f"Reading Schedule from {schedule_path}")
    with open(schedule_path) as json_file:
        json_data = json.load(json_file)

    for service_id, service_data in json_data["schedule"]["services"].items():
        routes = []
        for route_id, route_data in service_data["routes"].items():
            stops = route_data.pop("ordered_stops")
            route_data["stops"] = [
                schedule_elements.Stop(**json_data["schedule"]["stops"][stop], epsg=epsg)
                for stop in stops
            ]
            routes.append(schedule_elements.Route(**route_data))
        service_data["routes"] = routes

    services = [
        schedule_elements.Service(**service_data)
        for service_id, service_data in json_data["schedule"]["services"].items()
    ]

    s = schedule_elements.Schedule(
        epsg=epsg,
        services=services,
        vehicles=json_data["vehicles"]["vehicles"],
        vehicle_types=json_data["vehicles"]["vehicle_types"],
    )
    if "minimal_transfer_times" in json_data["schedule"]:
        s.minimal_transfer_times = json_data["schedule"]["minimal_transfer_times"]
    return s


def _literal_eval_col(df_col):
    try:
        df_col = df_col.apply(lambda x: ast.literal_eval(x))
    except KeyError:
        pass
    return df_col


def read_csv(path_to_network_nodes: str, path_to_network_links: str, epsg: str) -> core.Network:
    """Reads CSV data into a genet.Network object

    Args:
        path_to_network_nodes (str):
            CSV file describing nodes.
            Should at least include columns:
            - id: unique ID for the node
            - x: spatial coordinate in given epsg
            - y: spatial coordinate in given epsg

        path_to_network_links (str):
            CSV file describing links.
            Should at least include columns:
            - from - source Node ID
            - to - target Node ID

            Optional columns, but strongly encouraged:
            - id - unique ID for link
            - length - link length in metres
            - freespeed - meter/seconds speed
            - capacity - vehicles/hour
            - permlanes - number of lanes
            - modes - set of modes

        epsg (str): Projection for the network, e.g. 'epsg:27700'.

    Raises:
        NetworkSchemaError: Network nodes must have at least the columns specified above.

    Returns:
        core.Network: GeNet network object.
    """
    logging.info(f"Reading nodes from {path_to_network_nodes}")
    df_nodes = pd.read_csv(path_to_network_nodes)
    if {"index", "id"}.issubset(set(df_nodes.columns)):
        df_nodes = df_nodes.drop("index", axis=1)
    elif "id" not in df_nodes.columns:
        raise NetworkSchemaError(
            "Expected `id` column in the nodes.csv is missing. This need to be the IDs to which "
            "links.csv refers to in `from` and `to` columns."
        )
    df_nodes["id"] = df_nodes["id"].astype(int).astype(str)
    df_nodes = df_nodes.set_index("id", drop=False)
    try:
        df_nodes = df_nodes.drop("geometry", axis=1)
    except KeyError:
        pass

    logging.info(f"Reading links from {path_to_network_nodes}")
    df_links = pd.read_csv(path_to_network_links)
    if {"index", "id"}.issubset(set(df_links.columns)):
        df_links = df_links.drop("index", axis=1)
    elif "id" not in df_links.columns:
        if "index" in df_links.columns:
            if not df_links["index"].duplicated().any():
                df_links["id"] = df_links["index"]
            else:
                df_links = df_links.drop("index", axis=1)
        else:
            df_links["id"] = range(len(df_links))

    df_links["id"] = df_links["id"].astype(int).astype(str)
    df_links["from"] = df_links["from"].astype(int).astype(str)
    df_links["to"] = df_links["to"].astype(int).astype(str)
    df_links = df_links.set_index("id", drop=False)
    # recover encoded geometry
    try:
        df_links["geometry"] = df_links["geometry"].apply(
            lambda x: spatial.decode_polyline_to_shapely_linestring(x)
        )
    except KeyError:
        pass
    df_links["attributes"] = _literal_eval_col(df_links["attributes"])
    df_links["modes"] = _literal_eval_col(df_links["modes"])

    n = core.Network(epsg=epsg)
    n.add_nodes(df_nodes.T.to_dict())
    n.add_links(df_links.T.to_dict())
    n.change_log = change_log.ChangeLog()
    return n


def read_gtfs(path: str, day: str, epsg: Optional[str] = None) -> schedule_elements.Schedule:
    """Reads schedule from GTFS.

    The resulting services will not have network routes.
    Input GTFS is assumed to be using the 'epsg:4326' projection.

    Args:
        path (str): Path to GTFS folder or a zip file.
        day (str): 'YYYYMMDD' to use from the GTFS.
        epsg (Optional[str], optional):
            Projection for the output Schedule, e.g. 'epsg:27700'.
            If not provided, defaults to 'epsg:4326'.
            Defaults to None.

    Returns:
        schedule_elements.Schedule: GeNet schedule.
    """
    logging.info(f"Reading GTFS from {path}")
    schedule_graph = gtfs_reader.read_gtfs_to_schedule_graph(path, day)
    s = schedule_elements.Schedule(epsg="epsg:4326", _graph=schedule_graph)
    if epsg is not None:
        s.reproject(new_epsg=epsg)
    return s


def read_osm(
    osm_file_path: str, osm_read_config: str, num_processes: int = 1, epsg: Optional[str] = None
) -> core.Network:
    """Reads OSM data into a graph of the Network object.

    Args:
        osm_file_path (str): path to .osm or .osm.pbf file
        osm_read_config (str):
            Path to config file, which informs e.g., which highway types to read (in case of road network) and what modes to assign to them.
            See configs folder in genet for examples.
        num_processes (int, optional): Number of processes to split parallelisable operations across. Defaults to 1.
        epsg (Optional[str], optional):
            Projection for the output Network, e.g. 'epsg:27700'.
            If not provided, defaults to epsg:4326.
            Defaults to None.

    Returns:
        core.Network: GeNet network object.
    """
    if epsg is None:
        epsg = "epsg:4326"
    config = osm_reader.Config(osm_read_config)
    n = core.Network(epsg)
    nodes, edges = osm_reader.generate_osm_graph_edges_from_file(
        osm_file_path, config, num_processes
    )

    nodes_and_attributes = parallel.multiprocess_wrap(
        data=nodes,
        split=parallel.split_dict,
        apply=osm_reader.generate_graph_nodes,
        combine=parallel.combine_dict,
        epsg=epsg,
        processes=num_processes,
    )
    reindexing_dict, nodes_and_attributes = n.add_nodes(
        nodes_and_attributes, ignore_change_log=True
    )

    edges_attributes = parallel.multiprocess_wrap(
        data=edges,
        split=parallel.split_list,
        apply=osm_reader.generate_graph_edges,
        combine=parallel.combine_list,
        reindexing_dict=reindexing_dict,
        nodes_and_attributes=nodes_and_attributes,
        config_path=osm_read_config,
        processes=num_processes,
    )
    n.add_edges(edges_attributes, ignore_change_log=True)

    logging.info("Deleting isolated nodes which have no edges.")
    n.remove_nodes(list(nx.isolates(n.graph)))
    return n


def read_matsim_road_pricing(path_to_file: str) -> "genet.use.road_pricing.Toll":
    """TODO: implement

    Args:
        path_to_file (str): path to MATSim's road_pricing.xml file

    Returns:
        genet.Toll: or other if applicable though not yet implemented (eg distance or area tolling)
    """
    raise NotImplementedError()
