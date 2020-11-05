import pandas as pd
from datetime import datetime, timedelta
import geopandas as gpd
import genet.outputs_handler.geojson as gngeojson


def sanitise_time(time, gtfsday='19700101'):
    time_list = time.split(':')
    if int(time_list[0]) >= 24:
        days = int(time_list[0]) // 24
        time_list[0] = int(time_list[0]) % 24
        if time_list[0] < 10:
            time_list[0] = '0{}'.format(time_list[0])
        else:
            time_list[0] = str(time_list[0])
        return datetime.strptime(gtfsday + ' ' + ':'.join(time_list), '%Y%m%d %H:%M:%S') + timedelta(days=days)
    else:
        return datetime.strptime(gtfsday + ' ' + time, '%Y%m%d %H:%M:%S')


def get_offset(time):
    time_list = time.split(':')
    return timedelta(seconds=int(time_list[0]) * 60 * 60 + int(time_list[1]) * 60 + int(time_list[2]))


def generate_trips_dataframe(schedule_element):
    df = None
    for _id, route in schedule_element.routes():
        _df = route.generate_trips_dataframe()
        _df['route'] = route.id
        _df['service'] = _id

        if df is None:
            df = _df
        else:
            df = df.append(_df)
    return df


def generate_edge_vph_geodataframe(schedule_element):
    df = generate_trips_dataframe(schedule_element)
    df['hour'] = df['departure_time'].dt.round("H")
    df = df.groupby(['hour', 'trip', 'from_stop', 'to_stop']).count().reset_index()
    df['vph'] = 1
    df = df.groupby(['hour', 'from_stop', 'to_stop']).sum().reset_index()
    df = df.drop(['departure_time', 'arrival_time', 'route', 'service'], axis=1)

    gdf_nodes, gdf_links = gngeojson.generate_geodataframes(schedule_element.graph())
    df = pd.merge(gpd.GeoDataFrame(df), gdf_links[['u', 'v', 'geometry']], left_on=['from_stop', 'to_stop'],
                  right_on=['u', 'v'])
    cols_to_delete = ['u', 'v']
    if 'name' in gdf_nodes:
        df = pd.merge(df, gdf_nodes[['id', 'name']], left_on='from_stop', right_on='id', how='left')
        df = df.rename(columns={'name': 'from_stop_name'})
        df = pd.merge(df, gdf_nodes[['id', 'name']], left_on='to_stop', right_on='id', how='left')
        df = df.rename(columns={'name': 'to_stop_name'})
        cols_to_delete.extend(['id_x', 'id_y'])
    df = df.drop(cols_to_delete, axis=1)
    return df
