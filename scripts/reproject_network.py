import argparse
import logging
import time

from genet import read_matsim

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description='Reproject a MATSim network')

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

    arg_parser.add_argument('-cp',
                            '--current_projection',
                            help='The projection network is currently in, eg. "epsg:27700"',
                            required=True)

    arg_parser.add_argument('-np',
                            '--new_projection',
                            help='The projection desired, eg. "epsg:27700"',
                            required=True)

    arg_parser.add_argument('-p',
                            '--processes',
                            help='The number of processes to split computation across',
                            required=False,
                            default=1,
                            type=int)

    arg_parser.add_argument('-od',
                            '--output_dir',
                            help='Output directory for the reprojected network',
                            required=True)

    args = vars(arg_parser.parse_args())
    network = args['network']
    schedule = args['schedule']
    vehicles = args['vehicles']
    current_projection = args['current_projection']
    new_projection = args['new_projection']
    processes = args['processes']
    output_dir = args['output_dir']

    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.WARNING)

    logging.info('Reading in network at {}'.format(network))
    if schedule:
        logging.info(f'Reading in schedule at {schedule}')
        if vehicles:
            logging.info(f'Reading in vehicles at {vehicles}')
        else:
            logging.info('No vehicles file given with the Schedule, vehicle types will be based on the default.')
    else:
        logging.info('You have not passed the schedule.xml file. If your network is road only, that is fine, otherwise'
                     'if you mix and match them, you will have a bad time.')
    n = read_matsim(
        path_to_network=network,
        epsg=current_projection,
        path_to_schedule=schedule,
        path_to_vehicles=vehicles
    )

    logging.info('Reprojecting the network.')

    start = time.time()
    n.reproject(new_projection, processes=processes)
    end = time.time()
    n.write_to_matsim(output_dir)

    logging.info(f'It took {round((end - start)/60, 3)} min to reproject the network.')
