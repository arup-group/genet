import argparse
import json
import logging
import os

from genet import read_matsim
from genet.utils.persistence import ensure_dir
from genet.output.sanitiser import sanitise_dictionary

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description='Generate own links for given modes in a MATSim network, '
                                                     'creating a separate modal subgraph.')

    arg_parser.add_argument('-n',
                            '--network',
                            help='Location of the network.xml file',
                            required=True)

    arg_parser.add_argument('-p',
                            '--projection',
                            help='The projection network is in, eg. "epsg:27700"',
                            required=True)

    arg_parser.add_argument('-m',
                            '--modes',
                            help='Comma separated modes to split from the network',
                            required=True)

    arg_parser.add_argument('-od',
                            '--output_dir',
                            help='Output directory for the simplified network',
                            required=True)

    args = vars(arg_parser.parse_args())
    network = args['network']
    projection = args['projection']
    modes = args['modes'].split(',')
    output_dir = args['output_dir']
    ensure_dir(output_dir)

    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.WARNING)

    logging.info(f'Reading in network at {network}')
    n = read_matsim(
        path_to_network=network,
        epsg=projection,
    )
    logging.info(f'Number of links before separating graph: {len(n.link_id_mapping)}')

    for mode in modes:
        logging.info(f'Splitting links for mode: {mode}')
        df = n.link_attribute_data_under_key('modes')
        modal_links = n.links_on_modal_condition({mode})
        # leave the links that have a single mode as they are
        modal_links = set(modal_links) & set(df[df != {mode}].index)
        update_mode_links = {k: {'modes': df.loc[k] - {mode}} for k in modal_links}
        new_links = {f'{mode}---{k}': {**n.link(k), **{'modes': {mode}, 'id': f'{mode}---{k}'}} for k in modal_links}
        n.apply_attributes_to_links(update_mode_links)
        n.add_links(new_links)

    logging.info(f'Number of links after separating graph: {len(n.link_id_mapping)}')

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
