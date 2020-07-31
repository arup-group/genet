import argparse
import genet as gn
import logging


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description='Create a road-only MATSim network')

    arg_parser.add_argument('-o',
                            '--osm',
                            help='Location of the osm file',
                            required=True)

    arg_parser.add_argument('-c',
                            '--config',
                            help='Location of the config file defining what and how to read from the osm file',
                            required=True)

    arg_parser.add_argument('-cc',
                            '--connected_components',
                            help='Number of connected components within graph for modes `walk`,`bike`,`car`',
                            default=1)

    arg_parser.add_argument('-p',
                            '--projection',
                            help='The projection for the network eg. "epsg:27700"',
                            required=True)

    arg_parser.add_argument('-pp',
                            '--processes',
                            help='Number of parallel processes to split process across',
                            default=1,
                            type=int)

    arg_parser.add_argument('-od',
                            '--output_dir',
                            help='Output directory for the network',
                            required=True)

    args = vars(arg_parser.parse_args())
    osm = args['osm']
    config = args['config']
    connected_components = args['connected_components']
    projection = args['projection']
    processes = args['processes']
    output_dir = args['output_dir']

    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.WARNING)

    n = gn.Network(projection)
    logging.info('Reading in network at {}'.format(osm))
    n.read_osm(osm, config, num_processes=processes)
    # TODO uncomment when this functionality makes it to master
    # for mode in ['walk', 'car', 'bike']:
    #     n.retain_n_connected_subgraphs(n=connected_components, mode=mode)
    n.write_to_matsim(output_dir)
