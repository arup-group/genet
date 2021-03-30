import ast
import pandas as pd
import logging
import genet.core as core
import genet.inputs_handler.gtfs_reader as gtfs_reader
import genet.schedule_elements as schedule_elements
import genet.utils.spatial as spatial
import genet.modify.change_log as change_log
from genet.exceptions import NetworkSchemaError


def read_matsim(path_to_network: str, path_to_schedule: str = None, path_to_vehicles: str = None):
    """

    :param path_to_network: path to MATSim's network.xml file
    :param path_to_schedule: path to MATSim's schedule.xml file, optional
    :param path_to_vehicles: path to MATSim's vehicles.xml file, optional, expected to be passed with a schedule
    :return: genet.Network object
    """
    pass


def read_json(path: str):
    """

    :param path: path to json or geojson
    :return: genet.Network object
    """
    pass


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
    :param epsg: projection for the output Schedule, e.g. 'epsg:27700'. In not provided, the Schedule remains in
        epsg:4326
    :return:
    """
    logging.info(f'Reading GTFS from {path}')
    schedule_graph = gtfs_reader.read_to_dict_schedule_and_stopd_db(path, day)
    s = schedule_elements.Schedule(epsg='epsg:4326', _graph=schedule_graph)
    if epsg is not None:
        s.reproject(new_epsg=epsg)
    return s
