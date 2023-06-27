import argparse
import json
import logging
import os

from genet import read_matsim
from genet.utils.persistence import ensure_dir
from genet.output.sanitiser import sanitise_dictionary
from genet.output.geojson import save_geodataframe


def sort_modes_and_convert_to_str(modes):
    modes = list(modes)
    modes.sort()
    return ','.join(modes)


def generate_modal_network_geojsons(n, modes, output_dir, filename_suffix):
    logging.info(f"Generating visual outputs {filename_suffix}")
    gdf = n.to_geodataframe()['links'].to_crs('epsg:4326')
    for mode in modes:
        _gdf = gdf[gdf['modes'].apply(lambda x: mode in x)]
        _gdf['modes'] = _gdf['modes'].apply(sort_modes_and_convert_to_str)
        save_geodataframe(_gdf, f'mode_{mode}_{filename_suffix}', output_dir)


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(
        description='Generate new links, each for the use of a singular mode in a MATSim network. This creates '
                    'separate modal subgraphs for the given modes. It can be used with MATSim to ensure the two modes '
                    'do not come in contact. Given a link:'
                    '>>> `n.link("LINK_ID")`'
                    '   `{"id": "LINK_ID", "modes": {"car", "bike"}, "freespeed": 5, ...}`'

                    'The resulting links in the network will be:'
                    '>>> `n.link("LINK_ID")`'
                    '   `{"id": "LINK_ID", "modes": {"car"}, "freespeed": 5, ...}`'
                    '>>> `n.link("bike---LINK_ID")`'
                    '   `{"id": "bike---LINK_ID", "modes": {"bike"}, "freespeed": 5, ...}`'
                    'the new bike link will assume all the same attributes apart from the "modes".'

                    'In the case when a link already has a single dedicated mode, no updates are made to the link ID, '
                    'you can assume that all links that were in the network previously are still there, but their '
                    'allowed modes may have changed, so any simulation outputs may not be valid with this new network.'
    )

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
    modes = set(args['modes'].split(','))

    output_dir = args['output_dir']
    supporting_outputs = os.path.join(output_dir, 'supporting_outputs')
    ensure_dir(output_dir)
    ensure_dir(supporting_outputs)

    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.WARNING)

    logging.info(f'Reading in network at {network}')
    n = read_matsim(
        path_to_network=network,
        epsg=projection,
    )
    logging.info(f'Number of links before separating graph: {len(n.link_id_mapping)}')

    generate_modal_network_geojsons(n, modes, supporting_outputs, 'before')

    for mode in modes:
        logging.info(f'Splitting links for mode: {mode}')
        df = n.link_attribute_data_under_key('modes')
        modal_links = n.links_on_modal_condition({mode})
        # leave the links that have a sile mode as they are
        modal_links = set(modal_links) & set(df[df != {mode}].index)
        update_mode_links = {k: {'modes': df.loc[k] - {mode}} for k in modal_links}
        new_links = {f'{mode}---{k}': {**n.link(k), **{'modes': {mode}, 'id': f'{mode}---{k}'}} for k in modal_links}
        n.apply_attributes_to_links(update_mode_links)
        n.add_links(new_links)

    logging.info(f'Number of links after separating graph: {len(n.link_id_mapping)}')

    n.write_to_matsim(output_dir)

    logging.info('Generating validation report')
    report = n.generate_validation_report()
    logging.info(f'Graph validation: {report["graph"]["graph_connectivity"]}')
    with open(os.path.join(output_dir, 'validation_report.json'), 'w', encoding='utf-8') as f:
        json.dump(sanitise_dictionary(report), f, ensure_ascii=False, indent=4)

    generate_modal_network_geojsons(n, modes, supporting_outputs, 'after')
