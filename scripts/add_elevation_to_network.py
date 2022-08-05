import argparse
import logging
import os
import json

import genet
from genet import read_matsim
from genet.utils.persistence import ensure_dir
import genet.output.sanitiser as sanitiser
import genet.utils.elevation as elevation

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description='Add elevation data to network nodes, validate it, and calculate link slopes.')

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

    arg_parser.add_argument('-we',
                            '--write_elevation_to_network',
                            help='Whether node elevation data should be written as attribute to the network; defaults to True',
                            default=True)

    arg_parser.add_argument('-ws',
                            '--write_slope_to_network',
                            help='Whether link slope data should be written as attribute to the network; defaults to True',
                            default=True)

    arg_parser.add_argument('-sj',
                            '--save_jsons',
                            help='Whether elevation and slope dictionaries and report are saved; defaults to True',
                            default=True)

    args = vars(arg_parser.parse_args())
    network = args['network']
    projection = args['projection']
    elevation = args['elevation']
    tif_null_value = args['null_value']
    output_dir = args['output_dir']
    write_elevation_to_network = args['write_elevation_to_network']
    write_slope_to_network = args['write_slope_to_network']
    save_dict_to_json = args['save_jsons']
    elevation_output_dir = os.path.join(output_dir, 'elevation')
    ensure_dir(elevation_output_dir)

    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.WARNING)

    logging.info('Reading in network at {}'.format(network))

    n = read_matsim(
        path_to_network=network,
        epsg=projection
    )

    logging.info('Creating elevation dictionary for network nodes')
    elevation_dictionary = n.get_node_elevation_dictionary(elevation_tif_file_path=elevation, null_value=tif_null_value)

    if save_dict_to_json is True:
        with open(os.path.join(elevation_output_dir, 'node_elevation_dictionary.json'), 'w',
                  encoding='utf-8') as f:
            json.dump(sanitiser.sanitise_dictionary(elevation_dictionary), f, ensure_ascii=False, indent=4)


    logging.info('Validating the node elevation data')
    report = genet.utils.elevation.validation_report_for_node_elevation(elevation_dictionary)
    logging.info(report['summary'])

    if save_dict_to_json is True:
        with open(os.path.join(elevation_output_dir, 'validation_report_for_elevation.json'), 'w',
                  encoding='utf-8') as f:
            json.dump(sanitiser.sanitise_dictionary(report), f, ensure_ascii=False, indent=4)


    if write_elevation_to_network is True:
        logging.info('Adding node elevation as attribute to the network')
        node_attrib_dict = {}
        for node_id in elevation_dictionary.keys():
            elevation_value = elevation_dictionary[node_id]['z']
            node_attrib_dict[node_id] = {'z': elevation_value}

        n.apply_attributes_to_nodes(node_attrib_dict)


    logging.info('Creating slope dictionary for network links')
    slope_dictionary = n.get_link_slope_dictionary(elevation_dict=elevation_dictionary)

    if save_dict_to_json is True:
        with open(os.path.join(elevation_output_dir, 'link_slope_dictionary.json'), 'w',
                  encoding='utf-8') as f:
            json.dump(sanitiser.sanitise_dictionary(slope_dictionary), f, ensure_ascii=False, indent=4)


    if write_slope_to_network is True:
        logging.info('Adding link slope as an additional attribute to the network')
        attrib_dict = {}
        for link_id in slope_dictionary.keys():
            slope_value = slope_dictionary[link_id]['slope']
            attrib_dict[link_id] = {
                'attributes': {'slope': {'name': 'slope', 'class': 'java.lang.String', 'text': slope_value}}}

        n.apply_attributes_to_links(attrib_dict)


    logging.info('Writing the updated network')
    n.write_to_matsim(elevation_output_dir)
