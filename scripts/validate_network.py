import argparse
import genet as gn
import logging
import time
import os
import json
from genet.utils.persistence import ensure_dir


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description='Simplify a MATSim network by removing '
                                                     'intermediate links from paths')

    arg_parser.add_argument('-n',
                            '--network',
                            help='Location of the network.xml file',
                            required=True)

    arg_parser.add_argument('-s',
                            '--schedule',
                            help='Location of the schedule.xml file',
                            required=False,
                            default='')

    arg_parser.add_argument('-v',
                            '--vehicles',
                            help='Location of the vehicles.xml file',
                            required=False,
                            default='')

    arg_parser.add_argument('-p',
                            '--projection',
                            help='The projection network is in, eg. "epsg:27700"',
                            required=True)

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
    ensure_dir(output_dir)

    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.WARNING)

    n = gn.Network(projection)
    logging.info('Reading in network at {}'.format(network))
    n.read_matsim_network(network)
    if schedule:
        logging.info(f'Reading in schedule at {schedule}')
        if vehicles:
            logging.info(f'Reading in vehicles at {vehicles}')
        else:
            logging.info('No vehicles file given with the Schedule, vehicle types will be based on the default.')
        n.read_matsim_schedule(schedule, vehicles)

    logging.info('Generating validation report')
    report = n.generate_validation_report()
    logging.info(f'Graph validation: {report["graph"]["graph_connectivity"]}')
    if n.schedule:
        logging.info(f'Schedule level validation: {report["schedule"]["schedule_level"]["is_valid_schedule"]}')
        logging.info(f'Routing validation: {report["routing"]["services_have_routes_in_the_graph"]}')

    with open(os.path.join(output_dir, 'validation_report.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=4)
