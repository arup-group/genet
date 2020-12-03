import os
import pandas as pd
from datetime import datetime, timedelta
import geopandas as gpd
import numpy as np


def sanitise_time(time, gtfs_day='19700101'):
    time_list = time.split(':')
    if int(time_list[0]) >= 24:
        days = int(time_list[0]) // 24
        time_list[0] = int(time_list[0]) % 24
        if time_list[0] < 10:
            time_list[0] = '0{}'.format(time_list[0])
        else:
            time_list[0] = str(time_list[0])
        return datetime.strptime(gtfs_day + ' ' + ':'.join(time_list), '%Y%m%d %H:%M:%S') + timedelta(days=days)
    else:
        return datetime.strptime(gtfs_day + ' ' + time, '%Y%m%d %H:%M:%S')


def get_offset(time):
    time_list = time.split(':')
    return timedelta(seconds=int(time_list[0]) * 60 * 60 + int(time_list[1]) * 60 + int(time_list[2]))


def generate_trips_dataframe(schedule_element, route_ids=None, gtfs_day='19700101'):
    """
    Generates trips dataframe for the schedule element
    :param schedule_element: Route, Service or Schedule
    :param route_ids: Optional, to build the dataframe only for specific route ids. You can pass just one route id but
    that's the same as giving that route element as schedule_element and more efficient.
    :return:
    """
    df = pd.DataFrame(columns=['departure_time', 'arrival_time', 'from_stop', 'to_stop', 'trip', 'route', 'service'])

    for _id, route in schedule_element.routes():
        if (not route_ids) or (route.id in route_ids):
            _df = route.generate_trips_dataframe(gtfs_day)
            _df['route'] = route.id
            _df['service'] = _id
            _df['mode'] = route.mode
            df = df.append(_df)
    df = df.reset_index(drop=True)
    return df


def generate_edge_vph_geodataframe(df, gdf_links):
    """
    Generates vehicles per hour for a trips dataframe
    :param df: trips dataframe
    :param gdf_links: geodataframe containing links of the schedule (element) graph
    :return:
    """
    df.loc[:, 'hour'] = df['departure_time'].dt.round("H")
    df = df.groupby(['hour', 'trip', 'from_stop', 'to_stop']).count().reset_index()
    df.loc[:, 'vph'] = 1
    df = df.groupby(['hour', 'from_stop', 'to_stop']).sum().reset_index()

    cols_to_delete = ['departure_time', 'arrival_time']
    for col in ['route', 'service', 'mode']:
        if col in df.columns:
            cols_to_delete.append(col)

    df = pd.merge(gpd.GeoDataFrame(df), gdf_links[['u', 'v', 'geometry']], left_on=['from_stop', 'to_stop'],
                  right_on=['u', 'v'])
    cols_to_delete.extend(['u', 'v'])

    df = df.drop(cols_to_delete, axis=1)
    return df


def vehicles_per_hour(df, aggregate_by: list, output_path=''):
    """
    Generates vehicles per hour for a trips dataframe
    :param df: trips dataframe
    :param aggregate_by:
    :param output_path: path for the frame with .csv extension
    :return:
    """
    df.loc[:, 'hour'] = df['departure_time'].dt.round("H")
    df.loc[:, 'hour'] = df['hour'].dt.hour
    df = df.groupby(['hour', 'trip'] + aggregate_by).count().reset_index()
    df.loc[:, 'vph'] = 1
    df = pd.pivot_table(df, values='vph', index=aggregate_by, columns=['hour'],
                        aggfunc=np.sum).reset_index()
    df = df.fillna(0)
    if output_path:
        df.to_csv(output_path)
    return df


def trips_per_day_per_service(df, output_dir=''):
    """
    Generates trips per day per service for a trips dataframe
    :param df: trips dataframe
    :param output_dir: directory to save `trips_per_day_per_service.csv`
    :return:
    """
    trips_per_day = df.groupby(['service', 'service_name', 'mode']).count()['trip'].reset_index()
    trips_per_day = trips_per_day.rename(columns={'trip': 'number_of_trips'})
    if output_dir:
        trips_per_day.to_csv(os.path.join(output_dir, 'trips_per_day_per_service.csv'))
    return trips_per_day


def trips_per_day_per_route(df, output_dir=''):
    """
    Generates trips per day per route for a trips dataframe
    :param df: trips dataframe
    :param output_dir: directory to save `trips_per_day_per_service.csv`
    :return:
    """
    trips_per_day = df.groupby(['route', 'route_name', 'mode']).count()['trip'].reset_index()
    trips_per_day = trips_per_day.rename(columns={'trip': 'number_of_trips'})
    if output_dir:
        trips_per_day.to_csv(os.path.join(output_dir, 'trips_per_day_per_route.csv'))
    return trips_per_day
