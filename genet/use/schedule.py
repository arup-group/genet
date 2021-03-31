import os
import pandas as pd
from datetime import datetime, timedelta
import geopandas as gpd
import numpy as np
import itertools


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


def generate_edge_vph_geodataframe(df, gdf_links):
    """
    Generates vehicles per hour for a trips dataframe
    :param df: trips dataframe
    :param gdf_links: geodataframe containing links of the schedule (element) graph
    :return:
    """
    df.loc[:, 'hour'] = df['departure_time'].dt.round("H")
    groupby_cols = ['hour', 'trip', 'from_stop', 'from_stop_name', 'to_stop', 'to_stop_name']
    df = df.groupby(groupby_cols).count().reset_index()
    df.loc[:, 'vph'] = 1
    groupby_cols.remove('trip')
    df = df.groupby(groupby_cols).sum().reset_index()

    cols_to_delete = list(set(df.columns) - (set(groupby_cols) | {'vph'}))
    df = pd.merge(gpd.GeoDataFrame(df, crs=gdf_links.crs), gdf_links, left_on=['from_stop', 'to_stop'],
                  right_on=['u', 'v'])
    cols_to_delete.extend(['u', 'v', 'routes', 'services'])
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
    trips_per_day = df.groupby(['service', 'service_name', 'route', 'mode']).nunique()['trip'].reset_index()
    trips_per_day = trips_per_day.groupby(['service', 'service_name', 'mode']).sum()['trip'].reset_index()
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
    trips_per_day = df.groupby(['route', 'route_name', 'mode']).nunique()['trip'].reset_index()
    trips_per_day = trips_per_day.rename(columns={'trip': 'number_of_trips'})
    if output_dir:
        trips_per_day.to_csv(os.path.join(output_dir, 'trips_per_day_per_route.csv'))
    return trips_per_day


def aggregate_trips_per_day_per_route_by_end_stop_pairs(schedule, trips_per_day_per_route):
    def route_id_intersect(row):
        intersect = set(schedule.graph().nodes[row['station_A']]['routes']) & set(
            schedule.graph().nodes[row['station_B']]['routes'])
        if intersect:
            return intersect
        else:
            return float('nan')

    df = None
    for mode in schedule.modes():
        end_points = set()
        for route in schedule.routes():
            if route.mode == mode:
                end_points |= {route.ordered_stops[0], route.ordered_stops[-1]}
        df_stops = pd.DataFrame.from_records(
            list(itertools.combinations({schedule.stop(pt).id for pt in end_points}, 2)),
            columns=['station_A', 'station_B']
        )
        df_stops['station_A_name'] = df_stops['station_A'].apply(lambda x: schedule.stop(x).name)
        df_stops['station_B_name'] = df_stops['station_B'].apply(lambda x: schedule.stop(x).name)
        df_stops['mode'] = mode
        if df is None:
            df = df_stops
        else:
            df = df.append(df_stops)
    df['routes_in_common'] = df.apply(lambda x: route_id_intersect(x), axis=1)
    df = df.dropna()
    trips_per_day_per_route = trips_per_day_per_route.set_index('route')
    df['number_of_trips'] = df['routes_in_common'].apply(
        lambda x: sum([trips_per_day_per_route.loc[r_id, 'number_of_trips'] for r_id in x]))
    return df


def aggregate_by_stop_names(df_aggregate_trips_per_day_per_route_by_end_stop_pairs):
    df = df_aggregate_trips_per_day_per_route_by_end_stop_pairs
    df = df[(df['station_A_name'] != '') & (df['station_B_name'] != '')]
    if not df.empty:
        df[['station_A_name', 'station_B_name']] = np.sort(df[['station_A_name', 'station_B_name']], axis=1)
        df = df.groupby(['station_A_name', 'station_B_name', 'mode']).sum()['number_of_trips'].reset_index()
    return df
