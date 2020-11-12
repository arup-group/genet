import os
import pandas as pd
from datetime import datetime, timedelta
import geopandas as gpd
from matplotlib import pyplot as plt


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


def generate_edge_vph_geodataframe(df, gdf_nodes, gdf_links):
    """
    Generates vehicles per hour for a trips dataframe
    :param df: trips dataframe
    :param gdf_nodes: geodataframe containing nodes of the schedule (element) graph
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
    if 'name' in gdf_nodes:
        df = pd.merge(df, gdf_nodes[['id', 'name']], left_on='from_stop', right_on='id', how='left')
        df = df.rename(columns={'name': 'from_stop_name'})
        df = pd.merge(df, gdf_nodes[['id', 'name']], left_on='to_stop', right_on='id', how='left')
        df = df.rename(columns={'name': 'to_stop_name'})
        cols_to_delete.extend(['id_x', 'id_y'])

    df = df.drop(cols_to_delete, axis=1)
    return df


def plot_train_frequency_bar_chart(df, output_path):
    """
    Generates vehicles per hour for a trips dataframe
    :param df: trips dataframe
    :param output_dir: path for the plot with .jpeg, or .png extension
    :return:
    """
    df.loc[:, 'hour'] = df['departure_time'].dt.round("H")
    df.loc[:, 'hour'] = df['hour'].dt.hour
    df = df.groupby(['hour', 'trip']).count().reset_index()
    df.loc[:, 'vph'] = 1
    df = df.groupby('hour').sum().reset_index()
    ax = pd.DataFrame(df).plot(
        x='hour', y='vph', kind='bar', title=f"{os.path.basename(output_path).split('.')[0]}")
    plt.savefig(output_path)
    plt.close()
    return ax
