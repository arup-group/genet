import os
import argparse
import logging
import geopandas as gpd

from genet import read_matsim
from genet.utils.persistence import ensure_dir
from genet.output.geojson import save_geodataframe

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(
        description='Tag minor network links as urban given geometries. Minor links are defined as anything other'
                    'than: osm way highway tags: motorway, motorway_link, trunk, trunk_link, primary, primary_link. '
                    'Urban geometries are passed via geojson input with a specific format, see script arguments '
                    'for description.'
    )

    arg_parser.add_argument('-n',
                            '--network',
                            help='Location of the network.xml file',
                            required=True)

    arg_parser.add_argument('-p',
                            '--projection',
                            help='The projection network is in, eg. "epsg:27700"',
                            required=True)

    arg_parser.add_argument('-ug',
                            '--urban_geometries',
                            help='Geojson or shp file that when read into geopandas produces a table with columns: '
                                 '"label" (with at least some of the values in this column being a string: "urban") '
                                 'and "geometry" (polygons defining urban areas)',
                            required=True)

    arg_parser.add_argument('-od',
                            '--output_dir',
                            help='Output directory for the reprojected network',
                            required=True)

    args = vars(arg_parser.parse_args())
    network = args['network']
    projection = args['projection']
    urban_geometries = args['urban_geometries']

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

    logging.info(f'Reading in urban geometries at {urban_geometries}')
    gdf_urban = gpd.read_file(urban_geometries)
    if gdf_urban.crs != projection:
        logging.info(
            f'Projecting urban geometries from {str(gdf_urban.crs)} to {projection}, to match the network projection')
        gdf_urban = gdf_urban.to_crs(projection)
    gdf_urban = gdf_urban[gdf_urban['label'] == 'urban']
    if gdf_urban.empty:
        raise RuntimeError('No areas labelled "urban" were found!!')

    logging.info('Finding urban links')
    network_gdf = n.to_geodataframe()['links']
    network_urban = gpd.sjoin(network_gdf, gdf_urban, how='inner', op='intersects')
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

    logging.info('Generating geojson of urban links')
    urban_tag_gdf = network_gdf[network_gdf['id'].isin(set(links_to_tag))]
    save_geodataframe(urban_tag_gdf[['id', 'geometry']].to_crs('epsg:4326'),
                      'urban_network_links',
                      supporting_outputs)

    logging.info('Applying "urban" tag to links')
    n.apply_attributes_to_links(
        {link_id: {'attributes': {'urban': 'True'}} for link_id in links_to_tag}
    )

    logging.info(f"Saving network to {output_dir}")
    n.write_to_matsim(output_dir)
