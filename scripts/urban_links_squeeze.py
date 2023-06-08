import os
import argparse
import logging

import genet as gn
from genet.utils.persistence import ensure_dir

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(
        description='Reduce capacity and/or freespeed by x% of current value on the links tagged as "urban".'
                    'Use script `tag_urban_links.py` to tag minor links as urban given spatial polygons.'
    )

    arg_parser.add_argument('-n',
                            '--network',
                            help='Path to the network.xml file',
                            required=True)

    arg_parser.add_argument('-p',
                            '--projection',
                            help='The projection network is currently in, eg. "epsg:27700"',
                            required=True)

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
    freespeed = args['freespeed'] / 100
    capacity = args['capacity'] / 100

    output_dir = args['output_dir']
    supporting_outputs = os.path.join(output_dir, 'supporting_outputs')
    ensure_dir(output_dir)
    ensure_dir(supporting_outputs)

    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)

    if not (freespeed or capacity):
        logging.info('No change detected')
        exit()

    logging.info(f'Reading in network at {network}')
    n = gn.read_matsim(path_to_network=network, epsg=projection)

    logging.info("Extracting tagged network links satisfying attributes-urban-True")
    links_to_reduce = n.extract_links_on_edge_attributes(
        conditions={'attributes': {'urban': 'True'}})
    logging.info(f"Found {len(links_to_reduce)} links")

    gdf = n.to_geodataframe()['links']
    gdf = gdf.to_crs('epsg:4326')
    _gdf = gdf[gdf.apply(lambda x: gn.output.geojson.modal_subset(x, {'car', 'bus'}), axis=1)]
    gn.output.geojson.save_geodataframe(_gdf[['id', 'freespeed', 'geometry']], output_dir=supporting_outputs,
                                        filename='freespeed_before')
    gn.output.geojson.save_geodataframe(_gdf[['id', 'capacity', 'geometry']], output_dir=supporting_outputs,
                                        filename='capacity_before')

    gdf = gdf[gdf['id'].isin(links_to_reduce)]
    if freespeed:
        logging.info(f'Changing freespeed by {freespeed*100}%')
        gdf['freespeed'] = gdf['freespeed'] * freespeed
    if capacity:
        logging.info(f'Changing capacity by {capacity*100}%')
        gdf['capacity'] = gdf['capacity'] * capacity

    n.apply_attributes_to_links(gdf[['id', 'freespeed', 'capacity']].set_index('id').T.to_dict())

    logging.info('Generating geojson outputs for visual validation')
    gdf = n.to_geodataframe()['links']
    gdf = gdf.to_crs('epsg:4326')
    gdf = gdf[gdf.apply(lambda x: gn.output.geojson.modal_subset(x, {'car', 'bus'}), axis=1)]
    gn.output.geojson.save_geodataframe(gdf[['id', 'freespeed', 'geometry']], output_dir=supporting_outputs,
                                        filename='freespeed_after')
    gn.output.geojson.save_geodataframe(gdf[['id', 'capacity', 'geometry']], output_dir=supporting_outputs,
                                        filename='capacity_after')

    logging.info(f'Saving network in {output_dir}')
    n.write_to_matsim(output_dir)
