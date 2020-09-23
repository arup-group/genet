import argparse
import genet as gn
import logging
import time
import os
import json
from genet.utils.persistence import ensure_dir


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
                            default='')

    arg_parser.add_argument('-p',
                            '--projection',
                            help='The projection network is in, eg. "epsg:27700"',
                            required=True)

    arg_parser.add_argument('-np',
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
    projection = args['projection']
    processes = args['processes']
    output_dir = args['output_dir']
    ensure_dir(output_dir)

    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.WARNING)

    n = gn.Network(projection)
    logging.info('Reading in network at {}'.format(network))
    n.read_matsim_network(network)
    if schedule:
        logging.info('Reading in schedule at {}'.format(schedule))
        n.read_matsim_schedule(schedule)
    logging.info('Simplifying the Network.')

    start = time.time()
    n.simplify(no_processes=processes)
    end = time.time()

    logging.info(
        f'Simplification resulted in {len(n.link_simplification_map)} links being simplified.')
    with open(os.path.join(output_dir, 'link_simp_map.json'), 'w', encoding='utf-8') as f:
        json.dump(n.link_simplification_map, f, ensure_ascii=False, indent=4)

    n.write_to_matsim(output_dir)

    logging.info('Generating validation report')
    report = n.generate_validation_report()
    logging.info(f'Graph validation: {report["graph"]["graph_connectivity"]}')
    if n.schedule:
        logging.info(f'Schedule level validation: {report["schedule"]["schedule_level"]["is_valid_schedule"]}')
        logging.info(f'Routing validation: {report["routing"]["services_have_routes_in_the_graph"]}')

    logging.info(f'It took {round((end - start)/60, 3)} min to simplify the network.')
