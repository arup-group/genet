import argparse
import json
import logging
import os
import time

from genet import read_matsim
from genet.utils.persistence import ensure_dir
from genet.outputs_handler.sanitiser import sanitise_dictionary

def write_scaled_vehicles(network, list_of_scales,output_dir):
    for i in list_of_scales:
        scale = float(i)/100
        network.schedule.scale_vehicle_capacity(scale, scale, output_dir)

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

    arg_parser.add_argument('-np',
                            '--processes',
                            help='The number of processes to split computation across',
                            required=False,
                            default=1,
                            type=int)
    
    arg_parser.add_argument('-sc',
                            '--scales',
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
    processes = args['processes']
    output_dir = args['output_dir']
    scale_list = args['scales']
    ensure_dir(output_dir)

    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.WARNING)

    logging.info('Reading in network at {}'.format(network))
    n = read_matsim(
        path_to_network=network,
        epsg=projection,
        path_to_schedule=schedule,
        path_to_vehicles=vehicles
    )

    logging.info('Simplifying the Network.')

    start = time.time()
    n.simplify(no_processes=processes)
    end = time.time()

    logging.info(
        f'Simplification resulted in {len(n.link_simplification_map)} links being simplified.')
    with open(os.path.join(output_dir, 'link_simp_map.json'), 'w', encoding='utf-8') as f:
        json.dump(n.link_simplification_map, f, ensure_ascii=False, indent=4)

    n.write_to_matsim(output_dir)

    if scale_list:
        logging.info('Generating scaled vehicles xml.')
        scale_list = scale_list.split(",")
        write_scaled_vehicles(n, scale_list, output_dir)

    logging.info('Generating validation report')
    report = n.generate_validation_report()
    logging.info(f'Graph validation: {report["graph"]["graph_connectivity"]}')
    if n.schedule:
        logging.info(f'Schedule level validation: {report["schedule"]["schedule_level"]["is_valid_schedule"]}')
        logging.info(
            f'Schedule vehicle level validation: {report["schedule"]["vehicle_level"]["vehicle_definitions_valid"]}'
            )
        logging.info(f'Routing validation: {report["routing"]["services_have_routes_in_the_graph"]}')
    with open(os.path.join(output_dir, 'validation_report.json'), 'w', encoding='utf-8') as f:
        json.dump(sanitise_dictionary(report), f, ensure_ascii=False, indent=4)

    n.generate_standard_outputs(os.path.join(output_dir, 'standard_outputs'))

    logging.info(f'It took {round((end - start)/60, 3)} min to simplify the network.')
