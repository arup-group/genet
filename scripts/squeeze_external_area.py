import os
import argparse
import logging
import geopandas as gpd

from genet import read_matsim
from genet.utils.persistence import ensure_dir
from genet.output.geojson import save_geodataframe, modal_subset

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(
        description='Changes `freespeed` and `capacity` values for links **outside** of the given `study_area` '
                    'by given factors. '
                    'To squeeze links within the study area, look at the `squeeze_urban_links.py '
                    'script.'
    )

    arg_parser.add_argument('-n',
                            '--network',
                            help='Location of the network.xml file',
                            required=True)

    arg_parser.add_argument('-p',
                            '--projection',
                            help='The projection network is in, eg. "epsg:27700"',
                            required=True)

    arg_parser.add_argument('-sa',
                            '--study_area',
                            help='Geojson or shp file that when read into geopandas produces a table with a geometry '
                                 'column that describes the area which should be left unaffected by speed and '
                                 'capacity factors.',
                            required=False,
                            default=None)

    arg_parser.add_argument('-f',
                            '--freespeed',
                            help='Factor, e.g. 0.5, to reduce the "freespeed" attribute for the roads external to '
                                 'given Study Area in the network. The current value will be multiplied by 0.5 '
                                 '(in that case). You can also pass 1.5, for example, to increase the value.',
                            required=False,
                            type=float,
                            default=1)

    arg_parser.add_argument('-c',
                            '--capacity',
                            help='Factor, e.g. 0.5, to reduce the "capacity" attribute for the roads external to '
                                 'given Study Area in the network. The current value will be multiplied by 0.5 '
                                 '(in that case). You can also pass 1.5, for example, to increase the value.',
                            required=False,
                            type=float,
                            default=1)

    arg_parser.add_argument('-od',
                            '--output_dir',
                            help='Output directory for the reprojected network',
                            required=True)

    args = vars(arg_parser.parse_args())
    network = args['network']
    projection = args['projection']
    study_area = args['study_area']
    freespeed = args['freespeed']
    capacity = args['capacity']

    output_dir = args['output_dir']
    supporting_outputs = os.path.join(output_dir, 'supporting_outputs')
    ensure_dir(output_dir)
    ensure_dir(supporting_outputs)

    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.WARNING)

    logging.info(f'Reading in network at {network}')
    n = read_matsim(
        path_to_network=network,
        epsg=projection
    )

    logging.info(f'Reading in Study Area geometry at {study_area}')
    gdf_study_area = gpd.read_file(study_area)
    if gdf_study_area.crs != projection:
        logging.info(
            f'Projecting Study Area geometry from {str(gdf_study_area.crs)} to {projection}, '
            'to match the network projection')
        gdf_study_area = gdf_study_area.to_crs(projection)
    if gdf_study_area.empty:
        raise RuntimeError('The Study Area was not found!!')

    logging.info('Finding links external to the study area')
    network_gdf = n.to_geodataframe()['links']
    network_internal = gpd.sjoin(network_gdf, gdf_study_area, how='inner', op='intersects')
    external_links = set(network_gdf["id"].astype('str')) - set(network_internal["id"].astype('str'))

    logging.info('Finding car mode links')
    car_links = set(n.links_on_modal_condition('car'))

    logging.info('Finding minor road external links')
    links_to_squeeze = external_links.intersection(car_links)
    logging.info(f'{len(links_to_squeeze)} road links out of all {len(external_links)} external links and a total of '
                 f'{len(car_links)} car mode links will be squeezed.')

    logging.info('Generating geojson of external road links')
    external_tag_gdf = network_gdf[network_gdf['id'].isin(set(links_to_squeeze))]
    save_geodataframe(external_tag_gdf[['id', 'geometry']].to_crs('epsg:4326'),
                      'external_network_links',
                      supporting_outputs)

    # THE SQUEEZE SECTION

    network_gdf = network_gdf.to_crs('epsg:4326')
    _gdf = network_gdf[network_gdf.apply(lambda x: modal_subset(x, {'car', 'bus'}), axis=1)]
    save_geodataframe(_gdf[['id', 'freespeed', 'geometry']], output_dir=supporting_outputs,
                      filename='freespeed_before')
    save_geodataframe(_gdf[['id', 'capacity', 'geometry']], output_dir=supporting_outputs,
                      filename='capacity_before')

    network_gdf = network_gdf[network_gdf['id'].isin(links_to_squeeze)]
    if freespeed:
        logging.info(f'Changing freespeed by {freespeed * 100}%')
        network_gdf['freespeed'] = network_gdf['freespeed'] * freespeed
    if capacity:
        logging.info(f'Changing capacity by {capacity * 100}%')
        network_gdf['capacity'] = network_gdf['capacity'] * capacity

    n.apply_attributes_to_links(network_gdf[['id', 'freespeed', 'capacity']].set_index('id').T.to_dict())

    logging.info('Generating geojson outputs for visual validation')
    network_gdf = n.to_geodataframe()['links']
    network_gdf = network_gdf.to_crs('epsg:4326')
    network_gdf = network_gdf[network_gdf.apply(lambda x: modal_subset(x, {'car', 'bus'}), axis=1)]
    save_geodataframe(network_gdf[['id', 'freespeed', 'geometry']], output_dir=supporting_outputs,
                      filename='freespeed_after')
    save_geodataframe(network_gdf[['id', 'capacity', 'geometry']], output_dir=supporting_outputs,
                      filename='capacity_after')

    logging.info(f"Saving network to {output_dir}")
    n.write_to_matsim(output_dir)
