import argparse
import genet as gn
import logging
import json
import os


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description='Generate Google Directions API requests for a network for '
                                                     'inspection')

    arg_parser.add_argument('-n',
                            '--network',
                            help='Location of the network.xml file',
                            required=True)

    arg_parser.add_argument('-p',
                            '--projection',
                            help='The projection network is currently in, eg. "epsg:27700"',
                            required=True)

    arg_parser.add_argument('-od',
                            '--output_dir',
                            help='Output directory for the generated requests',
                            required=False,
                            default=None)

    args = vars(arg_parser.parse_args())
    network = args['network']
    projection = args['projection']
    output_dir = args['output_dir']

    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.WARNING)

    n = gn.Network(projection)
    logging.info(f'Reading in network at {network}')
    n.read_matsim_network(network)

    logging.info('Generating requests for the network')
    api_requests = gn.google_directions.generate_requests(n=n)
    logging.info(f'Generated {len(api_requests)} for the given network')

    if output_dir:
        logging.info(f'Saving results to {output_dir}')
        gn.utils.persistence.ensure_dir(output_dir)
        with open(os.path.join(output_dir, 'api_requests.json'), 'w') as fp:
            json.dump(api_requests, fp)
