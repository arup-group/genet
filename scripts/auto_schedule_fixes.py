import math

import argparse
import json
import logging
import os
import time
import datetime
import pandas as pd
import geopandas as gpd

from genet import read_matsim
from genet.utils.persistence import ensure_dir
from genet.output.geojson import save_geodataframe


def write_scaled_vehicles(network, list_of_scales, output_dir):
    for i in list_of_scales:
        scale = float(i) / 100
        network.schedule.scale_vehicle_capacity(scale, scale, output_dir)


def generate_headway_geojson(n, gdf, output_dir, filename_suffix):
    _ = n.schedule.headway_stats()
    _ = _.merge(gdf[['route_id', 'geometry']], how='left', on='route_id')
    save_geodataframe(gpd.GeoDataFrame(_).to_crs('epsg:4326'), f'headway_stats_{filename_suffix}', output_dir)


def generate_speed_geojson(n, gdf, output_dir, filename_suffix):
    _ = n.schedule.speed_geodataframe()
    # fill infinity by large number to show up in visualisations
    _.loc[_['speed'] == math.inf, 'speed'] = 9999

    _ = _.groupby(['service_id', 'route_id', 'route_name', 'mode']).max()['speed'].reset_index()
    _ = _.merge(gdf[['route_id', 'geometry']], how='left', on='route_id')
    save_geodataframe(gpd.GeoDataFrame(_).to_crs('epsg:4326'), f'max_speeds_{filename_suffix}', output_dir)


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(
        description=''
    )

    arg_parser.add_argument('-n',
                            '--network',
                            help='Location of the network.xml file',
                            required=True)

    arg_parser.add_argument('-s',
                            '--schedule',
                            help='Location of the schedule.xml file',
                            required=False,
                            default=None)

    arg_parser.add_argument('-v',
                            '--vehicles',
                            help='Location of the vehicles.xml file',
                            required=False,
                            default=None)

    arg_parser.add_argument('-p',
                            '--projection',
                            help='The projection network is in, eg. "epsg:27700"',
                            required=True)

    arg_parser.add_argument('-vsc',
                            '--vehicle_scalings',
                            help='Comma seperated string of scales for vehicles, e.g. 1,10,25',
                            required=False,
                            default=None,
                            type=str)

    arg_parser.add_argument('-od',
                            '--output_dir',
                            help='Output directory for the simplified network',
                            required=True)

    args = vars(arg_parser.parse_args())
    network = args['network']
    schedule = args['schedule']
    vehicles = args['vehicles']
    projection = args['projection']
    output_dir = args['output_dir']
    scale_list = args['vehicle_scalings']
    ensure_dir(output_dir)

    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.WARNING)

    logging.info('Reading in network at {}'.format(network))
    n = read_matsim(
        path_to_network=network,
        epsg=projection,
        path_to_schedule=schedule,
        path_to_vehicles=vehicles
    )

    gdf = n.schedule_network_routes_geodataframe().to_crs('epsg:4326')

    logging.info("Checking for zero headways")
    if n.schedule.has_trips_with_zero_headways():
        generate_headway_geojson(n, gdf, output_dir, 'before')
        n.schedule.fix_trips_with_zero_headways()
        generate_headway_geojson(n, gdf, output_dir, 'after')
    else:
        logging.info("No trips with zero headways were found")

    logging.info("Checking for infinite speeds")
    if n.schedule.has_infinite_speeds():
        generate_speed_geojson(n, gdf, output_dir, 'before')
        n.schedule.fix_infinite_speeds()
        generate_speed_geojson(n, gdf, output_dir, 'after')
    else:
        logging.info("No routes with infinite speeds were found")

    logging.info(f'Saving network in {output_dir}')
    n.write_to_matsim(output_dir)
    if scale_list:
        logging.info('Generating scaled vehicles xml.')
        scale_list = scale_list.split(",")
        write_scaled_vehicles(n, scale_list, output_dir)
