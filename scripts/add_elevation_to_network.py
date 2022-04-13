import argparse
import logging

from genet import read_matsim
from genet.utils.persistence import ensure_dir

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description='Add elevation data to network nodes and validate it')

    arg_parser.add_argument('-n',
                            '--network',
                            help='Location of the input network.xml file',
                            required=True)

    arg_parser.add_argument('-p',
                            '--projection',
                            help='The projection network is in, eg. "epsg:27700"',
                            required=True)

    arg_parser.add_argument('-el',
                            '--elevation',
                            help='Path to the elevation tif file',
                            required=True)

    arg_parser.add_argument('-nv',
                            '--null_value',
                            help='Value that represents null in the elevation tif file',
                            required=True)

    arg_parser.add_argument('-od',
                            '--output_dir',
                            help='Output directory for the updated network',
                            required=True)

    args = vars(arg_parser.parse_args())
    network = args['network']
    projection = args['projection']
    elevation = args['elevation']
    tif_null_value = args['null_value']
    output_dir = args['output_dir']
    ensure_dir(output_dir)

    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.WARNING)

    logging.info('Reading in network at {}'.format(network))

    n = read_matsim(
        path_to_network=network,
        epsg=projection
    )

    logging.info('Adding elevation to network nodes')
    n.add_elevation_to_nodes(elevation_tif_file_path=elevation, null_value=tif_null_value)

    logging.info('Validating the elevation data added to network nodes')

    logging.info('Writing the network.')
    n.write_to_matsim(output_dir)
