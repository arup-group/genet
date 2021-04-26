import csv
import logging
import os
import shutil
import pandas as pd
import numpy as np
import networkx as nx
from datetime import datetime, timedelta
from genet.utils import spatial, persistence
import genet.modify.change_log as change_log
from genet import variables


def read_services_from_calendar(path, day):
    """
    return list of services to be included
    :param path: path to GTFS folder
    :param day: 'YYYYMMDD' for specific day
    :return:
    """
    logging.info("Reading the calendar for GTFS")

    weekdays = {
        0: 'monday',
        1: 'tuesday',
        2: 'wednesday',
        3: 'thursday',
        4: 'friday',
        5: 'saturday',
        6: 'sunday'
    }
    day_of_the_week = weekdays[datetime.strptime(day, '%Y%m%d').weekday()]

    services = []

    calendar_present = False
    for file_name in os.listdir(path):
        file = os.path.join(path, file_name)
        if ("calendar" in file) and (not ("dates" in file)):
            calendar_present = True
            with open(file, mode='r', encoding="utf-8-sig") as infile:
                reader = csv.DictReader(infile)
                for row in reader:
                    if (int(day) in range(int(row['start_date']), int(row['end_date']))) and \
                            (int(row[day_of_the_week]) == 1):
                        services.append(row['service_id'])
    if not services:
        if calendar_present:
            raise RuntimeError('The date you have selected yielded no services')
        else:
            raise RuntimeError('Calendar was not found with the GTFS')
    return services


def read_gtfs_to_db_like_tables(path):
    logging.info("Reading GTFS data into usable format")

    trips_db = None
    stops_db = None
    routes_db = None
    stop_times_db = None

    for file_name in os.listdir(path):
        file = os.path.join(path, file_name)

        if "stop_times" in file:
            logging.info("Reading stop times")
            stop_times_db = pd.read_csv(file, dtype={'trip_id': str, 'stop_id': str}, low_memory=False)

        elif "stops" in file:
            logging.info("Reading stops")
            stops_db = pd.read_csv(file, dtype={'stop_id': str})

        elif "trips" in file:
            logging.info("Reading trips")
            trips_db = pd.read_csv(file, dtype={'route_id': str, 'service_id': str, 'trip_id': str})

        elif "routes" in file:
            logging.info("Reading routes")
            routes_db = pd.read_csv(file, dtype={'route_id': str})

    return stop_times_db, stops_db, trips_db, routes_db


def get_mode(route_type):
    if not isinstance(route_type, int):
        route_type = int(route_type)

    if route_type in variables.EXTENDED_TYPE_MAP:
        return variables.EXTENDED_TYPE_MAP[route_type]
    else:
        return 'other'


def gtfs_db_to_schedule_graph(stop_times_db, stops_db, trips_db, routes_db, services):
    def get_time(time):
        # return time as datetime.datetime, account for 24 in %H
        time_list = time.split(':')
        if int(time_list[0]) >= 24:
            days = int(time_list[0]) // 24
            time_list[0] = int(time_list[0]) % 24
            if time_list[0] < 10:
                time_list[0] = '0{}'.format(time_list[0])
            else:
                time_list[0] = str(time_list[0])
            return datetime.strptime(':'.join(time_list), '%H:%M:%S') + timedelta(days=days)
        else:
            return datetime.strptime(time, '%H:%M:%S')

    def timedelta_to_hms(td):
        return str(td).split('days')[-1].strip(' ')

    def generate_stop_sequence(group):
        group = group.sort_values(by='stop_sequence')
        # remove stops that are loopy (consecutively duplicated)
        unique_stops_mask = group['stop_id'].shift() != group['stop_id']
        if not unique_stops_mask.all():
            logging.warning(
                'Your GTFS has (a) looooop edge(s)! A zero link between a node and itself, edge affected '
                '\nThis edge will not be considered for computation, the stop will be deleted and the '
                f'schedule will be changed. Affected stops: {group[~unique_stops_mask]["stop_id"].to_list()}')
        group = group.loc[unique_stops_mask]
        flattened = group.iloc[0, :][
            list(set(group.columns) - {'trip_id', 'stop_sequence', 'stop_id', 'arrival_time', 'departure_time'})]
        departure_time = group.iloc[0, :]['arrival_time']
        flattened['trip_departure_time'] = departure_time.strftime("%H:%M:%S")
        flattened['ordered_stops'] = group['stop_id'].to_list()
        flattened['stops_str'] = ','.join(group['stop_id'].to_list())
        flattened['arrival_offsets'] = [timedelta_to_hms(t - departure_time) for t in group['arrival_time']]
        flattened['departure_offsets'] = [timedelta_to_hms(t - departure_time) for t in group['departure_time']]
        return flattened

    def generate_trips(group):
        flattened = group.iloc[0, :][
            list(set(group.columns) - {'route_id', 'stops_str', 'trip_id', 'vehicle_id', 'trip_departure_time'})]
        trip_id = group['trip_id'].to_list()
        trip_departure_time = group['trip_departure_time'].to_list()
        vehicle_id = group['vehicle_id'].to_list()
        flattened['trips'] = {
            'trip_id': trip_id,
            'trip_departure_time': trip_departure_time,
            'vehicle_id': vehicle_id
        }
        return flattened

    def generate_routes(group):
        service_id = group.iloc[0, :]['service_id']
        group['route_id'] = [f'{service_id}_{i}' for i in range(len(group))]
        return group

    trips_db = trips_db[trips_db['service_id'].isin(services)]
    df = trips_db[['route_id', 'trip_id']].merge(
        routes_db[['route_id', 'route_type', 'route_short_name', 'route_long_name', 'route_color']], on='route_id',
        how='left')
    df['mode'] = df['route_type'].apply(lambda x: get_mode(x))
    df = df.merge(stop_times_db[['trip_id', 'stop_id', 'arrival_time', 'departure_time', 'stop_sequence']],
                  on='trip_id', how='left')
    df['arrival_time'] = df['arrival_time'].apply(lambda x: get_time(x))
    df['departure_time'] = df['departure_time'].apply(lambda x: get_time(x))

    df = df.groupby('trip_id').apply(generate_stop_sequence).reset_index()
    # drop stop sequences that are single stops
    df = df[df['ordered_stops'].str.len() > 1]
    df['vehicle_id'] = [f'veh_{i}' for i in range(len(df))]
    df = df.groupby(['route_id', 'stops_str']).apply(generate_trips).reset_index()
    df = df.drop('stops_str', axis=1)
    df['service_id'] = df['route_id'].astype(str)
    df = df.groupby(['service_id']).apply(generate_routes)

    g = nx.DiGraph(name='Schedule graph')
    g.graph['crs'] = {'init': 'epsg:4326'}
    g.graph['route_to_service_map'] = df.set_index('route_id')['service_id'].T.to_dict()
    g.graph['service_to_route_map'] = df.groupby('service_id')['route_id'].apply(list).to_dict()
    g.graph['change_log'] = change_log.ChangeLog()

    df['id'] = df['route_id']
    g.graph['routes'] = df.set_index('route_id').T.to_dict()
    df['id'] = df['service_id']
    df = df.rename(columns={'route_short_name': 'name'})
    g.graph['services'] = df[['service_id', 'id', 'name']].groupby('service_id').first().T.to_dict()

    # finally nodes
    stops = pd.DataFrame({
        col: np.repeat(df[col].values, df['ordered_stops'].str.len())
        for col in {'route_id', 'service_id'}}
    ).assign(stop_id=np.concatenate(df['ordered_stops'].values))
    stop_groups = stops.groupby('stop_id')
    stops = set(stop_groups.groups)
    g.add_nodes_from(stops)
    stops_db = stops_db.rename(columns={'stop_lat': 'lat', 'stop_lon': 'lon', 'stop_name': 'name'})
    stops_db['id'] = stops_db['stop_id']
    stops_db['x'] = stops_db['lon']
    stops_db['y'] = stops_db['lat']
    stops_db['epsg'] = 'epsg:4326'
    stops_db['s2_id'] = stops_db.apply(
        lambda x: spatial.generate_index_s2(lat=float(x['lat']), lng=float(x['lon'])), axis=1)
    nx.set_node_attributes(g, stops_db[stops_db['stop_id'].isin(stops)].set_index('stop_id').T.to_dict())
    nx.set_node_attributes(g, pd.DataFrame(stop_groups['route_id'].apply(set)).rename(
        columns={'route_id': 'routes'}).T.to_dict())
    nx.set_node_attributes(g, pd.DataFrame(stop_groups['service_id'].apply(set)).rename(
        columns={'service_id': 'services'}).T.to_dict())

    # and edges
    df['ordered_stops'] = df['ordered_stops'].apply(lambda x: list(zip(x[:-1], x[1:])))
    stop_cols = np.concatenate(df['ordered_stops'].values)
    edges = pd.DataFrame({
        col: np.repeat(df[col].values, df['ordered_stops'].str.len())
        for col in {'route_id', 'service_id'}}
    ).assign(from_stop=stop_cols[:, 0],
             to_stop=stop_cols[:, 1])
    edge_groups = edges.groupby(['from_stop', 'to_stop'])
    g.add_edges_from(edge_groups.groups)
    nx.set_edge_attributes(g, pd.DataFrame(edge_groups['route_id'].apply(set)).rename(
        columns={'route_id': 'routes'}).T.to_dict())
    nx.set_edge_attributes(g, pd.DataFrame(edge_groups['service_id'].apply(set)).rename(
        columns={'service_id': 'services'}).T.to_dict())
    return g


def read_gtfs_to_schedule_graph(path: str, day: str):
    if persistence.is_zip(path):
        gtfs_path = os.path.join(os.getcwd(), 'tmp')
        if not os.path.exists(gtfs_path):
            os.makedirs(gtfs_path)
        import zipfile
        with zipfile.ZipFile(path, 'r') as zip_ref:
            zip_ref.extractall(gtfs_path)
        gtfs_path = os.path.join(gtfs_path, os.path.splitext(os.path.basename(path))[0])
    else:
        gtfs_path = path

    services = read_services_from_calendar(gtfs_path, day=day)
    stop_times_db, stops_db, trips_db, routes_db = read_gtfs_to_db_like_tables(gtfs_path)
    schedule_graph = gtfs_db_to_schedule_graph(stop_times_db, stops_db, trips_db, routes_db, services)

    if persistence.is_zip(path):
        shutil.rmtree(os.path.dirname(gtfs_path))
    return schedule_graph
