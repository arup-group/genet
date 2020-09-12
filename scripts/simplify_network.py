import argparse
import genet as gn
import logging
import time


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

    # arg_parser.add_argument('-p',
    #                         '--processes',
    #                         help='The number of processes to split computation across',
    #                         required=False,
    #                         default=1,
    #                         type=int)

    arg_parser.add_argument('-od',
                            '--output_dir',
                            help='Output directory for the reprojected network',
                            required=True)

    args = vars(arg_parser.parse_args())
    network = args['network']
    schedule = args['schedule']
    projection = args['projection']
    # processes = args['processes']
    output_dir = args['output_dir']

    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.WARNING)

    n = gn.Network(projection)
    logging.info('Reading in network at {}'.format(network))
    n.read_matsim_network(network)
    if schedule:
        logging.info('Reading in schedule at {}'.format(schedule))
        n.read_matsim_schedule(schedule)
    logging.info('Simplifying the Network.')

    start = time.time()
    n.simplify()
    end = time.time()
    report = n.generate_validation_report()
    logging.info(f'Graph validation: {report["graph"]}')
    if n.schedule:
        logging.info(f'Schedule level validation: {report["schedule"]["schedule_level"]["is_valid_schedule"]}')
        logging.info(f'Routing validation: {report["routing"]["services_have_routes_in_the_graph"]}')

    n.write_to_matsim(output_dir)

    logging.info(f'It took {round((end - start)/60, 3)} min to simplify the network.')
