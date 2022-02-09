import argparse
import json
import logging
import os
import glob
import pandas as pd

from genet import read_matsim
from genet.utils.dict_support import find_nested_paths_to_value
from genet.utils.persistence import ensure_dir

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description='Map auxiliary files from one network to another using '
                                                     'simplification maps for each network. Validate the updated '
                                                     'benchmarks using geometries')

    arg_parser.add_argument('-on',
                            '--old_network',
                            help='Location of the old network.xml file. The one auxiliary files reference',
                            required=True)

    arg_parser.add_argument('-om',
                            '--old_simplification_map',
                            help='Location of the json file outputted during simplification for the old network',
                            required=True)

    arg_parser.add_argument('-nn',
                            '--new_network',
                            help='Location of the new network.xml file. The one auxiliary files should transfer to',
                            required=True)

    arg_parser.add_argument('-nm',
                            '--new_simplification_map',
                            help='Location of the json file outputted during simplification for the new network',
                            required=True)

    arg_parser.add_argument('-a',
                            '--aux_file_dir',
                            help='Path to directory containing json and csv files that are connected to the old '
                                 'network. These will be updated using simplification maps to now reference the new '
                                 'network',
                            required=False,
                            default=None)

    arg_parser.add_argument('-p',
                            '--projection',
                            help='The projection network is in, eg. "epsg:27700"',
                            required=True)

    arg_parser.add_argument('-od',
                            '--output_dir',
                            help='Output directory for the updated auxiliary files',
                            required=True)

    args = vars(arg_parser.parse_args())
    old_network = args['old_network']
    old_simplification_map = args['old_simplification_map']
    new_network = args['new_network']
    new_simplification_map = args['new_simplification_map']
    aux_file_dir = args['aux_file_dir']
    projection = args['projection']
    output_dir = args['output_dir']
    ensure_dir(output_dir)

    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.WARNING)

    logging.info(f'Reading in networks at {old_network} and {new_network}')
    old_n = read_matsim(path_to_network=old_network, epsg=projection)
    new_n = read_matsim(path_to_network=new_network, epsg=projection)

    logging.info(f'Reading in simplification maps at {old_simplification_map} and {new_simplification_map}')
    with open(old_simplification_map) as json_file:
        old_simplification_map = json.load(json_file)
    with open(new_simplification_map) as json_file:
        new_simplification_map = json.load(json_file)

    logging.info('Reading and attaching auxiliary files')
    auxs = list(glob.glob(os.path.join(aux_file_dir, '*.csv'))) + list(glob.glob(os.path.join(aux_file_dir, '*.json')))
    for aux_path in auxs:
        logging.info(f'Reading {aux_path}')
        old_n.read_auxiliary_link_file(aux_path)

    logging.info('Creating a map between old and new network link IDs')
    old_to_new_map_df = pd.DataFrame(old_simplification_map.items(), columns=['unsimp_id', 'old_net_id'])
    old_to_new_map_df['new_net_id'] = old_to_new_map_df['puma_id'].map(new_simplification_map)

    overlap = old_to_new_map_df[['old_net_id', 'new_net_id']].drop_duplicates().dropna().groupby('old_net_id').size()
    undefined_ids = set(overlap[overlap > 1].index)
    logging.info(f'Found {len(undefined_ids)} link IDs in the new network with ill-defined (one-to-many) mappings')

    logging.info('Checking for links in auxiliary files that have ill-defined mapping')
    values_to_correct = {}
    for name, aux_file in old_n.auxiliary_files['link'].items():
        bad_links = set(aux_file.map) & undefined_ids
        if bad_links:
            values_to_correct[aux_file.filename] = []
            for l in bad_links:
                loc = find_nested_paths_to_value(aux_file.data, l)
                values_to_correct[aux_file.filename].append(loc)
                logging.warning(f'File {aux_file.filename} references links that are ill-defined and will not be '
                                f'mapped. Found at location: {loc}')
        aux_file.apply_map(dict(zip(bad_links, [None] * len(bad_links))))
    if values_to_correct:
        ill_defined_link_log = os.path.join(output_dir, 'ill_defined_link_log.json')
        logging.info(f'Saving information on which files should be updated and where to {ill_defined_link_log}')
        with open(ill_defined_link_log, 'w') as outfile:
            json.dump(values_to_correct, outfile)

    logging.info('Updating auxiliary files')
    old_to_new_map = old_to_new_map_df[['old_net_id', 'new_net_id']].drop_duplicates().dropna().loc[
        set(old_to_new_map_df) - undefined_ids].set_index('old_net_id')['new_net_id'].to_dict()
    old_to_new_map_path = os.path.join(output_dir, 'old_to_new_map.json')
    logging.info(f'Saving old-to-new ID map to {old_to_new_map_path}')
    with open(old_to_new_map_path, 'w') as outfile:
        json.dump(old_to_new_map, outfile)

    old_n.update_link_auxiliary_files(old_to_new_map)
    for name, aux_file in old_n.auxiliary_files['link'].items():
        aux_file.update()

    logging.info('Validating geometries of auxiliary files')
    old_links = old_n.to_geodataframe()['links']
    new_links = new_n.to_geodataframe()['links']
    old_to_new_map_df = old_to_new_map_df[old_to_new_map_df['old_net_id'].isin(old_to_new_map.keys())]
    old_to_new_map_df = pd.merge(old_to_new_map_df, old_links[['id', 'geometry']], left_on='old_net_id',
                                 right_on='id')
    old_to_new_map_df.rename(columns={'geometry': 'old_geom'}, inplace=True)
    old_to_new_map_df = pd.merge(old_to_new_map_df, new_links[['id', 'geometry']], left_on='new_net_id',
                                 right_on='id')
    old_to_new_map_df.rename(columns={'geometry': 'new_geom'}, inplace=True)
    mismatched_geometries = old_to_new_map_df[old_to_new_map_df.apply(lambda x: x['old_geom'] != x['new_geom'], axis=1)]
    if len(mismatched_geometries) > 0:
        mismatched_geometries_path = os.path.join(output_dir, 'mismatched_geometries.geojson')
        logging.warning(f'Found {len(mismatched_geometries_path)} geometries that are not matching exactly, they '
                        f'should be verified. Saving geojson to {mismatched_geometries_path}.')
        mismatched_geometries.to_file(mismatched_geometries_path)

    logging.info('Writing auxiliary files')
    old_n.write_auxiliary_files(output_dir)
