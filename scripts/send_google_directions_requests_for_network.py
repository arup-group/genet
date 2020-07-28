import argparse
import genet as gn
import logging


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description='Generate and send Google Directions API requests')

    arg_parser.add_argument('-n',
                            '--network',
                            help='Location of the network.xml file',
                            required=True)

    arg_parser.add_argument('-p',
                            '--projection',
                            help='The projection network is currently in, eg. "epsg:27700"',
                            required=True)

    arg_parser.add_argument('-t',
                            '--requests_threshold',
                            help='Max number of API requests you are happy to send. If exceeded, will fail without '
                                 'sending any',
                            required=True)

    arg_parser.add_argument('-k',
                            '--api_key',
                            help='Google Directions API key if not using AWS secrets manager',
                            required=False,
                            default=None)

    arg_parser.add_argument('-sn',
                            '--secret_name',
                            help='Secret name in AWS Secrets manager, if not passing the API key directly',
                            required=False,
                            default=None)

    arg_parser.add_argument('-rn',
                            '--region_name',
                            help='Region name in AWS, if not passing the API key directly',
                            required=False,
                            default=None)

    arg_parser.add_argument('-od',
                            '--output_dir',
                            help='Output directory for the parsed API requests',
                            required=True)

    args = vars(arg_parser.parse_args())
    network = args['network']
    projection = args['projection']
    requests_threshold = args['requests_threshold']
    key = args['key']
    secret_name = args['secret_name']
    region_name = args['region_name']
    output_dir = args['output_dir']

    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.WARNING)

    n = gn.Network(projection)
    logging.info('Reading in network at {}'.format(network))
    n.read_matsim_network(network)

    api_requests = gn.google_directions.send_requests_for_network(
        n=n,
        request_number_threshold=requests_threshold,
        output_dir=output_dir,
        traffic=False,
        key=None,
        secret_name=None,
        region_name=None
    )
