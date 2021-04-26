import ast
import pandas as pd
import geopandas as gpd
import networkx as nx
import json
import logging
import genet.core as core
import genet.inputs_handler.gtfs_reader as gtfs_reader
import genet.inputs_handler.osm_reader as osm_reader
import genet.utils.parallel as parallel
import genet.inputs_handler.matsim_reader as matsim_reader
import genet.schedule_elements as schedule_elements
import genet.utils.spatial as spatial
import genet.modify.change_log as change_log
from genet.exceptions import NetworkSchemaError


def read_matsim(path_to_network: str, epsg: str, path_to_schedule: str = None, path_to_vehicles: str = None):
    """
    Reads MATSim's network.xml to genet.Network object and if give, also the schedule.xml and vehicles.xml into
    genet.Schedule object, part of the genet.Network object.
    :param path_to_network: path to MATSim's network.xml file
    :param path_to_schedule: path to MATSim's schedule.xml file, optional
    :param path_to_vehicles: path to MATSim's vehicles.xml file, optional, expected to be passed with a schedule
    :param epsg: projection for the network, e.g. 'epsg:27700'
    :return: genet.Network object
    """
    n = read_matsim_network(path_to_network=path_to_network, epsg=epsg)
    if path_to_schedule:
        n.schedule = read_matsim_schedule(
            path_to_schedule=path_to_schedule, path_to_vehicles=path_to_vehicles, epsg=epsg)
    return n


def read_matsim_network(path_to_network: str, epsg: str):
    """
    Reads MATSim's network.xml to genet.Network object
    :param path_to_network: path to MATSim's network.xml file
    :param epsg: projection for the network, e.g. 'epsg:27700'
    :return: genet.Network object
    """
    n = core.Network(epsg=epsg)
    n.graph, n.link_id_mapping, duplicated_nodes, duplicated_links = \
        matsim_reader.read_network(path_to_network, n.transformer)
    n.graph.graph['name'] = 'Network graph'
    n.graph.graph['crs'] = {'init': n.epsg}
    if 'simplified' not in n.graph.graph:
        n.graph.graph['simplified'] = False

    for node_id, duplicated_node_attribs in duplicated_nodes.items():
        for duplicated_node_attrib in duplicated_node_attribs:
            n.change_log.remove(
                object_type='node',
                object_id=node_id,
                object_attributes=duplicated_node_attrib
            )
    for link_id, reindexed_duplicated_links in duplicated_links.items():
        for duplicated_link in reindexed_duplicated_links:
            n.change_log.modify(
                object_type='link',
                old_id=link_id,
                old_attributes=n.link(duplicated_link),
                new_id=duplicated_link,
                new_attributes=n.link(duplicated_link)
            )
    return n


def read_matsim_schedule(path_to_schedule: str, epsg: str, path_to_vehicles: str = None):
    """
    Reads MATSim's schedule.xml (and possibly vehicles.xml) to genet.Schedule object
    :param path_to_schedule: path to MATSim's schedule.xml file,
    :param path_to_vehicles: path to MATSim's vehicles.xml file, optional but encouraged
    :param epsg: projection for the schedule, e.g. 'epsg:27700'
    :return: genet.Schedule object
    """
    services, minimal_transfer_times = matsim_reader.read_schedule(path_to_schedule, epsg)
    if path_to_vehicles:
        vehicles, vehicle_types = matsim_reader.read_vehicles(path_to_vehicles)
        matsim_schedule = schedule_elements.Schedule(
            services=services, epsg=epsg, vehicles=vehicles, vehicle_types=vehicle_types)
    else:
        matsim_schedule = schedule_elements.Schedule(services=services, epsg=epsg)
    matsim_schedule.minimal_transfer_times = minimal_transfer_times
    return matsim_schedule


def read_json(network_path: str, epsg: str, schedule_path: str = ''):
    """
    Reads Network and, if passed, Schedule JSON files in to a genet.Network
    :param network_path: path to json network file
    :param schedule_path: path to json schedule file
    :param epsg: projection for the network, e.g. 'epsg:27700'
    :return: genet.Network object
    """
    n = read_json_network(network_path, epsg)
    if schedule_path:
        n.schedule = read_json_schedule(schedule_path, epsg)
    return n


def read_geojson_network(nodes_path: str, links_path: str, epsg: str):
    """
    Reads Network graph from JSON file.
    :param nodes_path: path to geojson network nodes file
    :param links_path: path to geojson network links file
    :param epsg: projection for the network, e.g. 'epsg:27700'
    :return: genet.Network object
    """
    logging.info(f'Reading Network nodes from {nodes_path}')
    nodes = gpd.read_file(nodes_path)
    nodes = nodes.drop('geometry', axis=1)
    nodes['id'] = nodes['id'].astype(int).astype(str)
    nodes = nodes.set_index('id', drop=False)
    if 'index' in nodes.columns:
        nodes = nodes.drop('index', axis=1)

    logging.info(f'Reading Network links from {links_path}')
    links = gpd.read_file(links_path).to_crs(epsg)
    links['modes'] = links['modes'].apply(lambda x: set(x.split(',')))
    links['id'] = links['id'].astype(int).astype(str)
    links = links.set_index('id', drop=False)
    if 'index' in links.columns:
        links = links.drop('index', axis=1)

    n = core.Network(epsg=epsg)
    n.add_nodes(nodes.T.to_dict())
    n.add_links(links.T.to_dict())
    n.change_log = change_log.ChangeLog()
    return n


def read_json_network(network_path: str, epsg: str):
    """
    Reads Network graph from JSON file.
    :param network_path: path to json or geojson network file
    :param epsg: projection for the network, e.g. 'epsg:27700'
    :return: genet.Network object
    """
    logging.info(f'Reading Network from {network_path}')
    with open(network_path) as json_file:
        json_data = json.load(json_file)
    for node, data in json_data['nodes'].items():
        try:
            del data['geometry']
        except KeyError:
            pass

    for link, data in json_data['links'].items():
        try:
            data['geometry'] = spatial.decode_polyline_to_shapely_linestring(data['geometry'])
        except KeyError:
            pass
        try:
            data['modes'] = set(data['modes'].split(','))
        except KeyError:
            pass

    n = core.Network(epsg=epsg)
    n.add_nodes(json_data['nodes'])
    n.add_links(json_data['links'])
    n.change_log = change_log.ChangeLog()
    return n


def read_json_schedule(schedule_path: str, epsg: str):
    """
    Reads Schedule from a JSON file.
    :param schedule_path: path to json or geojson schedule file
    :param epsg: projection for the network, e.g. 'epsg:27700'
    :return: genet.Schedule object
    """
    logging.info(f'Reading Schedule from {schedule_path}')
    with open(schedule_path) as json_file:
        json_data = json.load(json_file)

    for service_id, service_data in json_data['schedule']['services'].items():
        routes = []
        for route_id, route_data in service_data['routes'].items():
            stops = route_data.pop('ordered_stops')
            route_data['stops'] = [schedule_elements.Stop(**json_data['schedule']['stops'][stop], epsg=epsg) for stop in
                                   stops]
            routes.append(schedule_elements.Route(**route_data))
        service_data['routes'] = routes

    services = [schedule_elements.Service(**service_data) for service_id, service_data in
                json_data['schedule']['services'].items()]

    s = schedule_elements.Schedule(
        epsg=epsg,
        services=services,
        vehicles=json_data['vehicles']['vehicles'],
        vehicle_types=json_data['vehicles']['vehicle_types'])
    if 'minimal_transfer_times' in json_data['schedule']:
        s.minimal_transfer_times = json_data['schedule']['minimal_transfer_times']
    return s


def _literal_eval_col(df_col):
    try:
        df_col = df_col.apply(lambda x: ast.literal_eval(x))
    except KeyError:
        pass
    return df_col


def read_csv(path_to_network_nodes: str, path_to_network_links: str, epsg: str):
    """
    Reads CSV data into a genet.Network object
    :param path_to_network_nodes: CSV file describing nodes. Should at least include columns:
    - id: unique ID for the node
    - x: spatial coordinate in given epsg
    - y: spatial coordinate in given epsg
    :param path_to_network_links: CSV file describing links.
    Should at least include columns:
    - from - source Node ID
    - to - target Node ID
    Optional columns, but strongly encouraged
    - id - unique ID for link
    - length - link length in metres
    - freespeed - meter/seconds speed
    - capacity - vehicles/hour
    - permlanes - number of lanes
    - modes - set of modes
    :param epsg: projection for the network, e.g. 'epsg:27700'
    :return: genet.Network object
    """
    logging.info(f'Reading nodes from {path_to_network_nodes}')
    df_nodes = pd.read_csv(path_to_network_nodes)
    if {'index', 'id'}.issubset(set(df_nodes.columns)):
        df_nodes = df_nodes.drop('index', axis=1)
    elif 'id' not in df_nodes.columns:
        raise NetworkSchemaError('Expected `id` column in the nodes.csv is missing. This need to be the IDs to which '
                                 'links.csv refers to in `from` and `to` columns.')
    df_nodes['id'] = df_nodes['id'].astype(int).astype(str)
    df_nodes = df_nodes.set_index('id', drop=False)
    try:
        df_nodes = df_nodes.drop('geometry', axis=1)
    except KeyError:
        pass

    logging.info(f'Reading links from {path_to_network_nodes}')
    df_links = pd.read_csv(path_to_network_links)
    if {'index', 'id'}.issubset(set(df_links.columns)):
        df_links = df_links.drop('index', axis=1)
    elif 'id' not in df_links.columns:
        if 'index' in df_links.columns:
            if not df_links['index'].duplicated().any():
                df_links['id'] = df_links['index']
            else:
                df_links = df_links.drop('index', axis=1)
        else:
            df_links['id'] = range(len(df_links))

    df_links['id'] = df_links['id'].astype(int).astype(str)
    df_links['from'] = df_links['from'].astype(int).astype(str)
    df_links['to'] = df_links['to'].astype(int).astype(str)
    df_links = df_links.set_index('id', drop=False)
    # recover encoded geometry
    try:
        df_links['geometry'] = df_links['geometry'].apply(lambda x: spatial.decode_polyline_to_shapely_linestring(x))
    except KeyError:
        pass
    df_links['attributes'] = _literal_eval_col(df_links['attributes'])
    df_links['modes'] = _literal_eval_col(df_links['modes'])

    n = core.Network(epsg=epsg)
    n.add_nodes(df_nodes.T.to_dict())
    n.add_links(df_links.T.to_dict())
    n.change_log = change_log.ChangeLog()
    return n


def read_gtfs(path, day, epsg=None):
    """
    Reads from GTFS. The resulting services will not have network routes. Assumed to be in lat lon epsg:4326.
    :param path: to GTFS folder or a zip file
    :param day: 'YYYYMMDD' to use from the gtfs
    :param epsg: projection for the output Schedule, e.g. 'epsg:27700'. If not provided, the Schedule remains in
        epsg:4326
    :return:
    """
    logging.info(f'Reading GTFS from {path}')
    schedule_graph = gtfs_reader.read_gtfs_to_schedule_graph(path, day)
    s = schedule_elements.Schedule(epsg='epsg:4326', _graph=schedule_graph)
    if epsg is not None:
        s.reproject(new_epsg=epsg)
    return s


def read_osm(osm_file_path, osm_read_config, num_processes: int = 1, epsg=None):
    """
    Reads OSM data into a graph of the Network object
    :param osm_file_path: path to .osm or .osm.pbf file
    :param osm_read_config: config file (see configs folder in genet for examples) which informs for example which
    highway types to read (in case of road network) and what modes to assign to them
    :param num_processes: number of processes to split parallelisable operations across
    :param epsg: projection for the output Network, e.g. 'epsg:27700'. If not provided, defaults to epsg:4326
    :return: genet.Network object
    """
    if epsg is None:
        epsg = 'epsg:4326'
    config = osm_reader.Config(osm_read_config)
    n = core.Network(epsg)
    nodes, edges = osm_reader.generate_osm_graph_edges_from_file(
        osm_file_path, config, num_processes)

    nodes_and_attributes = parallel.multiprocess_wrap(
        data=nodes,
        split=parallel.split_dict,
        apply=osm_reader.generate_graph_nodes,
        combine=parallel.combine_dict,
        epsg=epsg
    )
    reindexing_dict, nodes_and_attributes = n.add_nodes(nodes_and_attributes)

    edges_attributes = parallel.multiprocess_wrap(
        data=edges,
        split=parallel.split_list,
        apply=osm_reader.generate_graph_edges,
        combine=parallel.combine_list,
        reindexing_dict=reindexing_dict,
        nodes_and_attributes=nodes_and_attributes,
        config_path=osm_read_config
    )
    n.add_edges(edges_attributes)

    logging.info('Deleting isolated nodes which have no edges.')
    n.remove_nodes(list(nx.isolates(n.graph)))
    return n
