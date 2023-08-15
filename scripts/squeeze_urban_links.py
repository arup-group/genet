import os
import argparse
import logging
import geopandas as gpd

import genet as gn
from genet.utils.persistence import ensure_dir
from genet.output.geojson import save_geodataframe, modal_subset

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(
        description='Tag minor network links as urban, given geometries: `urban_geometries`. '
                    'Minor links are defined as anything other than: osm way highway tags: motorway, motorway_link, '
                    'trunk, trunk_link, primary, primary_link. '
                    'Urban geometries are passed via geojson input with a specific format, see script arguments '
                    'for description. '
                    'Passing `study_area` subsets the urban geometries and links to be squeezed - only links in the '
                    'study area will be tagged and squeezed. This is useful if your geometries covers a larger area. '
                    'The script then reduces capacity and/or freespeed by a factor of current value on those links. '
                    'To squeeze links outside the study area, look at the `squeeze_external_area.py '
                    'script.'
    )

    arg_parser.add_argument('-n',
                            '--network',
                            help='Path to the network.xml file',
                            required=True)

    arg_parser.add_argument('-p',
                            '--projection',
                            help='The projection network is currently in, eg. "epsg:27700"',
                            required=True)

    arg_parser.add_argument('-ug',
                            '--urban_geometries',
                            help='Geojson or shp file that when read into geopandas produces a table with columns: '
                                 '"label" (with at least some of the values in this column being a string: "urban") '
                                 'and "geometry" (polygons defining urban areas)',
                            required=True)

    arg_parser.add_argument('-sa',
                            '--study_area',
                            help='Geojson or shp file that when read into geopandas produces a table with columns: '
                                 '"label" (with at least some of the values in this column being a string: "urban") '
                                 'and "geometry" (polygons defining urban areas)',
                            required=False,
                            default=None)

    arg_parser.add_argument('-f',
                            '--freespeed',
                            help='Factor, e.g. 0.5, to reduce the "freespeed" attribute for the urban non-major roads'
                                 'in the network. The current value will be multiplied by 0.5 (in that case).'
                                 'You can also pass 1.5, for example, to increase the value.',
                            required=False,
                            type=float,
                            default=1)

    arg_parser.add_argument('-c',
                            '--capacity',
                            help='Factor, e.g. 0.5, to reduce the "capacity" attribute for the urban non-major roads'
                                 'in the network. The current value will be multiplied by 0.5 (in that case).'
                                 'You can also pass 1.5, for example, to increase the value.',
                            required=False,
                            type=float,
                            default=1)

    arg_parser.add_argument('-od',
                            '--output_dir',
                            help='Output directory for the network',
                            required=False,
                            default=None)

    args = vars(arg_parser.parse_args())
    network = args['network']
    projection = args['projection']
    urban_geometries = args['urban_geometries']
    study_area = args['study_area']
    freespeed = args['freespeed']
    capacity = args['capacity']

    output_dir = args['output_dir']
    supporting_outputs = os.path.join(output_dir, 'supporting_outputs')
    ensure_dir(output_dir)
    ensure_dir(supporting_outputs)

    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

    logging.info(f'Reading in network at {network}')
    n = gn.read_matsim(path_to_network=network, epsg=projection)

    # URBAN TAGGING SECTION

    logging.info(f'Reading in urban geometries at {urban_geometries}')
    gdf_urban = gpd.read_file(urban_geometries)
    if gdf_urban.crs != projection:
        logging.info(
            f'Projecting urban geometries from {str(gdf_urban.crs)} to {projection}, to match the network projection')
        gdf_urban = gdf_urban.to_crs(projection)
    gdf_urban = gdf_urban[gdf_urban['label'] == 'urban']
    if gdf_urban.empty:
        raise RuntimeError('No areas labelled "urban" were found!!')
    if study_area:
        logging.info(f'Reading in Study Area geometries at {study_area}')
        gdf_study_area = gpd.read_file(study_area)
        if gdf_study_area.crs != projection:
            logging.info(
                f'Projecting Study Area geometries from {str(gdf_study_area.crs)} to {projection}, to match the network '
                'projection')
            gdf_study_area = gdf_study_area.to_crs(projection)
        logging.info(f'Subsetting urban geometries on study area')
        gdf_urban = gpd.sjoin(gdf_urban, gdf_study_area, how='inner', op='intersects').drop(columns=['index_right'])

    logging.info('Finding urban links')
    network_gdf = n.to_geodataframe()['links']
    network_urban = gpd.sjoin(network_gdf, gdf_urban, how='inner', op='intersects').drop(columns=['index_right'])
    if study_area:
        # subsetting gdf_urban on study area is not enough if it consists of polygons that extend beyond
        # but it does make it faster to work with gdf_urban if it was large to begin with
        network_urban = gpd.sjoin(network_gdf, gdf_study_area, how='inner', op='intersects')
    urban_links = set(network_urban["id"].astype('str'))

    logging.info('Finding major road links')
    major_links = set(n.extract_links_on_edge_attributes(
        conditions=[
            {'attributes': {'osm:way:highway': 'motorway'}},
            {'attributes': {'osm:way:highway': 'motorway_link'}},
            {'attributes': {'osm:way:highway': 'trunk'}},
            {'attributes': {'osm:way:highway': 'trunk_link'}},
            {'attributes': {'osm:way:highway': 'primary'}},
            {'attributes': {'osm:way:highway': 'primary_link'}}
        ],
        how=any
    ))
    logging.info('Finding car mode links')
    car_links = set(n.links_on_modal_condition('car'))

    logging.info('Finding minor road urban links')
    links_to_tag = (urban_links.intersection(car_links) - major_links)
    logging.info(f'{len(links_to_tag)} minor road links out of all {len(urban_links)} urban links and a total of '
                 f'{len(car_links)} car mode links will be tagged with the "urban" tag')

    logging.info('Generating geojson of urban road links')
    urban_tag_gdf = network_gdf[network_gdf['id'].isin(set(links_to_tag))]
    save_geodataframe(urban_tag_gdf[['id', 'geometry']].to_crs('epsg:4326'),
                      'urban_network_links',
                      supporting_outputs)

    logging.info('Applying "urban" tag to links')
    n.apply_attributes_to_links(
        {link_id: {'attributes': {'urban': 'True'}} for link_id in links_to_tag}
    )

    # THE SQUEEZE SECTION

    links_to_reduce = links_to_tag

    logging.info('Generating geojson outputs for visual validation')
    network_gdf = network_gdf.to_crs('epsg:4326')
    _gdf = network_gdf[network_gdf.apply(lambda x: modal_subset(x, {'car', 'bus'}), axis=1)]
    save_geodataframe(_gdf[['id', 'freespeed', 'geometry']], output_dir=supporting_outputs,
                      filename='freespeed_before')
    save_geodataframe(_gdf[['id', 'capacity', 'geometry']], output_dir=supporting_outputs,
                      filename='capacity_before')

    network_gdf = network_gdf[network_gdf['id'].isin(links_to_reduce)]
    if freespeed:
        logging.info(f'Changing freespeed by {freespeed * 100}%')
        network_gdf['freespeed'] = network_gdf['freespeed'] * freespeed
    if capacity:
        logging.info(f'Changing capacity by {capacity * 100}%')
        network_gdf['capacity'] = network_gdf['capacity'] * capacity

    n.apply_attributes_to_links(network_gdf[['id', 'freespeed', 'capacity']].set_index('id').T.to_dict())

    logging.info('Generating geojson outputs for visual validation')
    network_gdf = n.to_geodataframe()['links'].to_crs('epsg:4326')
    network_gdf = network_gdf[network_gdf.apply(lambda x: modal_subset(x, {'car', 'bus'}), axis=1)]
    save_geodataframe(network_gdf[['id', 'freespeed', 'geometry']], output_dir=supporting_outputs,
                      filename='freespeed_after')
    save_geodataframe(network_gdf[['id', 'capacity', 'geometry']], output_dir=supporting_outputs,
                      filename='capacity_after')

    logging.info(f'Saving network in {output_dir}')
    n.write_to_matsim(output_dir)
