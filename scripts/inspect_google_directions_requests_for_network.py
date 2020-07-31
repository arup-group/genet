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

    arg_parser.add_argument('-sc',
                            '--subset_conditions',
                            help="Value or list of values to subset the network by using attributes-osm:way:highway "
                                 "network attributes. List given comma-separated e.g. `primary,motorway`"
                                 "{'attributes': {'osm:way:highway': {'text': VALUE(S)'}}}",
                            required=False,
                            default=None)

    arg_parser.add_argument('-od',
                            '--output_dir',
                            help='Output directory for the generated requests',
                            required=False,
                            default=None)

    args = vars(arg_parser.parse_args())
    network = args['network']
    projection = args['projection']
    subset_conditions = args['subset_conditions']
    if subset_conditions:
        subset_conditions = subset_conditions.split(',')
    output_dir = args['output_dir']

    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.WARNING)

    n = gn.Network(projection)
    logging.info(f'Reading in network at {network}')
    n.read_matsim_network(network)

    logging.info('Generating requests for the network')
    api_requests = gn.google_directions.generate_requests(n=n)
    logging.info(f'Generated {len(api_requests)} requests for the given network')

    if output_dir:
        logging.info(f'Saving results to {output_dir}')
        gn.google_directions.dump_all_api_requests_to_json(api_requests, output_dir)

    if subset_conditions is not None:
        logging.info(f"Considering subset of the network satisfying attributes-osm:way:highway-{subset_conditions}")
        links_to_keep = gn.graph_operations.extract_links_on_edge_attributes(
            n,
            conditions={'attributes': {'osm:way:highway': {'text': subset_conditions}}})
        remove_links = set(n.link_id_mapping.keys()) - set(links_to_keep)
        n.remove_links(remove_links, silent=True)
        api_requests = gn.google_directions.generate_requests(n=n)
        logging.info(f'Generated {len(api_requests)} requests for the subsetted network')

        if output_dir:
            sub_output_dir = os.path.join(output_dir, 'subset')
            logging.info(f'Saving subset results to {sub_output_dir}')
            gn.google_directions.dump_all_api_requests_to_json(api_requests, sub_output_dir)
