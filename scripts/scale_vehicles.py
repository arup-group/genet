import argparse
import logging

from genet import read_matsim_schedule
from genet.utils.persistence import ensure_dir


def write_scaled_vehicles(schedule, list_of_scales, output_dir):
    for i in list_of_scales:
        scale = float(i) / 100
        schedule.scale_vehicle_capacity(scale, scale, output_dir)


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description='Scale PT Schedule vehicles')

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
                            help='Comma separated string of scales for vehicles, e.g. 1,10,25',
                            required=True,
                            default="1,10",
                            type=str)

    arg_parser.add_argument('-od',
                            '--output_dir',
                            help='Output directory for the output vehicle files',
                            required=True)

    args = vars(arg_parser.parse_args())
    schedule = args['schedule']
    vehicles = args['vehicles']
    projection = args['projection']
    output_dir = args['output_dir']
    scale_list = args['vehicle_scalings']
    ensure_dir(output_dir)

    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.WARNING)

    logging.info('Reading in schedule at {}'.format(schedule))
    s = read_matsim_schedule(
        path_to_schedule=schedule,
        path_to_vehicles=vehicles,
        epsg=projection
    )

    logging.info('Generating scaled vehicles xml.')
    scale_list = scale_list.split(",")
    write_scaled_vehicles(s, scale_list, output_dir)
