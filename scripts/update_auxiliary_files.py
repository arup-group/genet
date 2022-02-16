import argparse
import json
import logging
import os
import glob
import pandas as pd
import geopandas as gpd
import lxml.etree as ET

from genet import read_matsim
from genet.utils.dict_support import find_nested_paths_to_value
from genet.utils.persistence import ensure_dir


def process_rp_file(rp_path, old_net_gdf, new_net_gdf, rp_out_path, validation_folder):
    filename = os.path.basename(rp_path)
    logging.info(f'Reading {rp_path}')
    old_ids = []
    new_ids = []
    missing_ids = []

    rp = ET.parse(rp_path)
    for elem in rp.getroot():
        for subelem in elem:
            if 'id' in subelem.attrib:
                link_id = subelem.attrib["id"]
                if link_id in old_to_new_map:
                    subelem.attrib["id"] = old_to_new_map[link_id]
                    old_ids.append(link_id)
                    new_ids.append(old_to_new_map[link_id])
                elif not old_n.has_link(link_id):
                    logging.warning(f'{link_id} not found in the OLD network. Removing')
                    missing_ids.append(link_id)
                    subelem.getparent().remove(subelem)
                elif not new_n.has_link(link_id):
                    logging.warning(f'{link_id} not found in the NEW network. Removing')
                    missing_ids.append(link_id)
                    subelem.getparent().remove(subelem)
                else:
                    # it's a link that didnt change ID, proceed
                    old_ids.append(link_id)
                    new_ids.append(link_id)

    rp_val_out_path = os.path.join(validation_folder, filename.strip('.xml'))
    ensure_dir(rp_val_out_path)
    old_net_gdf[old_net_gdf['id'].isin(old_ids)][['id', 'geometry']].to_file(
        os.path.join(rp_val_out_path, 'old_link_geometry.geojson'), driver='GeoJSON')
    new_net_gdf[new_net_gdf['id'].isin(new_ids)][['id', 'geometry']].to_file(
        os.path.join(rp_val_out_path, 'new_link_geometry.geojson'), driver='GeoJSON')

    if missing_ids:
        logging.warning(f'Found {len(missing_ids)} missing IDs: {missing_ids}')
        with open(os.path.join(rp_val_out_path, 'missing_links.txt'), 'w') as f:
            for item in missing_ids:
                f.write("%s\n" % item)

    rp_out_path = os.path.join(rp_out_path, filename)
    logging.info(f'Writing {rp_out_path}')
    rp.write(rp_out_path)
    return missing_ids


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

    arg_parser.add_argument('-r',
                            '--rp_file_dir',
                            help='Path to directory containing xml road-pricing files that are connected to the old '
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
                            help='Output directory for the updated files',
                            required=True)

    args = vars(arg_parser.parse_args())
    old_network = args['old_network']
    old_simplification_map = args['old_simplification_map']
    new_network = args['new_network']
    new_simplification_map = args['new_simplification_map']
    aux_file_dir = args['aux_file_dir']
    rp_file_dir = args['rp_file_dir']
    projection = args['projection']
    output_dir = args['output_dir']
    aux_output_dir = os.path.join(output_dir, 'auxiliary_files')
    rp_output_dir = os.path.join(output_dir, 'road_pricing_files')
    ensure_dir(aux_output_dir)
    ensure_dir(rp_output_dir)

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
    old_to_new_map_df['new_net_id'] = old_to_new_map_df['unsimp_id'].map(new_simplification_map)

    overlap = old_to_new_map_df[['old_net_id', 'new_net_id']].drop_duplicates().dropna().groupby('old_net_id').size()
    undefined_ids = set(overlap[overlap > 1].index)
    logging.info(f'Found {len(undefined_ids)} link IDs in the new network with ill-defined (one-to-many) mappings')

    logging.info('Checking for links in auxiliary files that have ill-defined mapping')
    values_to_correct = {}
    aux_file_links = set()
    for name, aux_file in old_n.auxiliary_files['link'].items():
        aux_file_links |= set(aux_file.map)
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
        ill_defined_link_log = os.path.join(aux_output_dir, 'ill_defined_link_log.json')
        logging.info(f'Saving information on which files should be updated and where to {ill_defined_link_log}')
        with open(ill_defined_link_log, 'w') as outfile:
            json.dump(values_to_correct, outfile)

    logging.info('Updating auxiliary files')
    old_to_new_map = old_to_new_map_df[~old_to_new_map_df['unsimp_id'].isin(undefined_ids)][
        ['old_net_id', 'new_net_id']].drop_duplicates().dropna().set_index('old_net_id')['new_net_id'].to_dict()
    old_to_new_map_path = os.path.join(output_dir, 'old_to_new_map.json')
    logging.info(f'Saving old-to-new ID map to {old_to_new_map_path}')
    with open(old_to_new_map_path, 'w') as outfile:
        json.dump(old_to_new_map, outfile)

    old_n.update_link_auxiliary_files(old_to_new_map)
    for name, aux_file in old_n.auxiliary_files['link'].items():
        aux_file.update()

    logging.info('Validating geometries of auxiliary files')
    old_links = old_n.to_geodataframe()['links'].to_crs('epsg:4326')
    new_links = new_n.to_geodataframe()['links'].to_crs('epsg:4326')
    # save geojson before and after
    geometries_dir = os.path.join(aux_output_dir, 'validation_geojsons')
    ensure_dir(geometries_dir)
    logging.info(f'Saving verification geojson to {geometries_dir}.')
    old_links[old_links['id'].isin(aux_file_links)][['id', 'geometry']].to_file(
        os.path.join(geometries_dir, 'old_link_geometry.geojson'), driver='GeoJSON')
    mapped_links = [old_to_new_map[i] for i in aux_file_links if i in old_to_new_map]
    # links that didn't get simplified / mapped
    mapped_links += [i for i in aux_file_links if i not in old_to_new_map]
    new_links[new_links['id'].isin(mapped_links)][['id', 'geometry']].to_file(
        os.path.join(geometries_dir, 'new_link_geometry.geojson'), driver='GeoJSON')

    old_to_new_map_df = old_to_new_map_df[old_to_new_map_df['old_net_id'].isin(aux_file_links)]
    old_to_new_map_df = old_to_new_map_df[['old_net_id', 'new_net_id']].drop_duplicates()
    old_to_new_map_df = pd.merge(old_to_new_map_df, old_links[['id', 'geometry']], left_on='old_net_id',
                                 right_on='id')
    old_to_new_map_df.rename(columns={'geometry': 'old_geom'}, inplace=True)
    old_to_new_map_df = pd.merge(old_to_new_map_df, new_links[['id', 'geometry']], left_on='new_net_id',
                                 right_on='id')
    old_to_new_map_df.rename(columns={'geometry': 'new_geom'}, inplace=True)
    mismatched_geometries = old_to_new_map_df[old_to_new_map_df.apply(lambda x: x['old_geom'] != x['new_geom'], axis=1)]
    if len(mismatched_geometries) > 0:
        mismatched_geometries_path = os.path.join(geometries_dir, 'mismatched_geometries.geojson')
        logging.warning(f'Found {len(mismatched_geometries_path)} geometries that are not matching exactly, they '
                        f'should be verified. Saving geojson to {mismatched_geometries_path}.')
        gpd.GeoDataFrame(mismatched_geometries).to_file(mismatched_geometries_path)

    logging.info('Writing auxiliary files')
    old_n.write_auxiliary_files(aux_output_dir)

    logging.info('Processing road pricing files')
    validation_folder = os.path.join(rp_output_dir, 'validation')
    all_missing_ids = []
    rps = list(glob.glob(os.path.join(rp_file_dir, '*.xml')))
    for rp_path in rps:
        all_missing_ids.append(
            process_rp_file(
                rp_path,
                old_net_gdf=old_links,
                new_net_gdf=new_links,
                rp_out_path=rp_output_dir,
                validation_folder=validation_folder
            )
        )
    if all_missing_ids:
        with open(os.path.join(rp_output_dir, 'all_missing_links.txt'), 'w') as f:
            for item in all_missing_ids:
                f.write("%s\n" % item)

    logging.info('Finished updating link IDs')
