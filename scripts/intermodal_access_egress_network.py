import argparse
import logging
import os
import json

from genet import read_matsim
from genet import spatial
from genet.utils.persistence import ensure_dir
import genet.output.sanitiser as sanitiser


def cast_catchment(network_spatial_tree, df_stops, distance):
    return network_spatial_tree.closest_links(
        gdf_points=df_stops,
        distance_radius=distance).dropna()


def find_closest_links_by_step(network_spatial_tree, df_stops, step_size=10, distance_threshold=None):
    def threshold_reached(d):
        if distance_threshold is not None:
            return d <= distance_threshold
        else:
            return True

    distance = step_size
    logging.info(f'Processing catchment: {distance}')
    nodes = cast_catchment(network_spatial_tree=network_spatial_tree,
                           df_stops=df_stops.loc[:, ['id', 'geometry']].copy(), distance=distance)
    nodes['catchment'] = distance
    stop_ids = set(df_stops['id'])

    while set(nodes.index) != stop_ids and threshold_reached(distance):
        # increase distance by step size until all stops have closest links or reached threshold
        distance += step_size
        logging.info(f'Processing catchment: {distance}, {len(stop_ids - set(nodes.index))} stops remaining')
        _df = cast_catchment(
            network_spatial_tree=network_spatial_tree,
            df_stops=df_stops.loc[df_stops['id'].isin(stop_ids - set(nodes.index)), ['id', 'geometry']].copy(),
            distance=distance)
        _df['catchment'] = distance
        nodes = nodes.append(_df)
    return nodes


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(
        description='Process to add access and egress links for PT stops of given modes. Intended to generate '
                    'PT schedules to work with SBB extensions in MATSim: '
                    'https://github.com/matsim-org/matsim-libs/tree/master/contribs/sbb-extensions#intermodal-access-and-egress')

    arg_parser.add_argument('-n',
                            '--network',
                            help='Location of the input network.xml file',
                            required=True)

    arg_parser.add_argument('-s',
                            '--schedule',
                            help='Location of the schedule.xml file',
                            required=True)

    arg_parser.add_argument('-v',
                            '--vehicles',
                            help='Location of the vehicles.xml file',
                            required=False,
                            default=None)

    arg_parser.add_argument('-p',
                            '--projection',
                            help='The projection network is in, eg. "epsg:27700"',
                            required=True)

    arg_parser.add_argument('-pm',
                            '--pt_modes',
                            help='Comma separated modes to subset stops of interest. A stop is linked to a mode '
                                 'via a transit route using that stop. Optional, otherwise considers all stops',
                            required=False,
                            default=None)

    arg_parser.add_argument('-nm',
                            '--network_snap_modes',
                            help='Comma separated modes to subset the network graph. '
                                 'The links from this modal subgraph will be considered for the stop to graph '
                                 'relationship. Two new attributes (per mode) will be added to PT stops:'
                                 'xmodeAccessible = true and accessLinkId_xmode = link_id',
                            required=False,
                            default='car')

    arg_parser.add_argument('-tm',
                            '--teleport_modes',
                            help='Comma separated (teleported) modes to enable for given PT stops '
                                 'No links will be found for these modes. One new attributes (per mode) will be added '
                                 'to PT stops: xmodeAccessible = true',
                            required=False,
                            default=None)

    arg_parser.add_argument('-ss',
                            '--step_size',
                            help='In metres. This process finds links in the nearest neighbourhood of a stop. The '
                                 'size of the neighbourhood increases by `step_size` value each time until it finds '
                                 'links to relate to stops.',
                            required=False,
                            default=25,
                            type=float)

    arg_parser.add_argument('-dt',
                            '--distance_threshold',
                            help='In metres. This is the limit of how wide the search area for a link can be for each '
                                 'stop.',
                            required=False,
                            default=None,
                            type=float)

    arg_parser.add_argument('-od',
                            '--output_dir',
                            help='Output directory for the updated schedule',
                            required=True)

    args = vars(arg_parser.parse_args())
    network = args['network']
    schedule = args['schedule']
    vehicles = args['vehicles']
    projection = args['projection']

    pt_modes = args['pt_modes']
    network_snap_modes = args['network_snap_modes']
    teleport_modes = args['teleport_modes']
    step_size = args['step_size']
    distance_threshold = args['distance_threshold']

    output_dir = args['output_dir']
    supporting_outputs = os.path.join(output_dir, 'supporting_outputs')
    ensure_dir(output_dir)
    ensure_dir(supporting_outputs)

    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.WARNING)

    logging.info('Reading in network at {}'.format(network))

    n = read_matsim(
        path_to_network=network,
        epsg=projection,
        path_to_schedule=schedule,
        path_to_vehicles=vehicles
    )

    logging.info(f'The following modes are present in the Schedule: {n.schedule.modes()}')
    df_stops = n.schedule.to_geodataframe()['nodes'].to_crs("epsg:4326")
    if pt_modes is not None:
        logging.info(f'Stops serving the following modes will be considered: {pt_modes}')
        stops_subset = n.schedule.stops_on_modal_condition(modes=pt_modes.split(','))
        df_stops = df_stops.loc[stops_subset]
        df_stops[['lat', 'lon', 'geometry']].to_file(os.path.join(supporting_outputs, 'stops.geojson'),
                                                     driver='GeoJSON')
        logging.info(f'Modal subsetting resulted in {len(df_stops)} stops to snap')

    if network_snap_modes is not None:
        logging.info('Building Spatial Tree')
        spatial_tree = spatial.SpatialTree(n)

        for snap_mode in network_snap_modes.split(','):
            logging.info(f'Snapping mode: {snap_mode}')
            sub_tree = spatial_tree.modal_subtree(modes={snap_mode})

            closest_links = find_closest_links_by_step(
                network_spatial_tree=sub_tree,
                df_stops=df_stops,
                step_size=step_size,
                distance_threshold=distance_threshold
            )

            # TODO There are multiple links to choose from, for the time being we are not precious about which link is
            #  selected.
            selected_links = closest_links.reset_index().groupby('index').first()
            if len(selected_links) != len(df_stops):
                logging.warning(f'Only {len(selected_links)} out of {len(df_stops)} stops found a link to snap to. '
                                'Consider removing the distance threshold if you want all stops to find a nearest link.')

            # Let's create some handy geojson outputs to verify our snapping
            selected_links[['catchment', 'geometry']].to_file(
                os.path.join(supporting_outputs, f'{snap_mode}_stop_catchments.geojson'), driver='GeoJSON')
            # join to get link geoms
            selected_links = selected_links.join(
                sub_tree.links[['link_id', 'geometry']], how='left', on='link_id', lsuffix='_left', rsuffix='')
            selected_links[['geometry']].to_file(
                os.path.join(supporting_outputs, f'{snap_mode}_access_egress_links.geojson'), driver='GeoJSON')
            # get number of stops in each catchment
            catchment_value_counts = selected_links['catchment'].value_counts().to_dict()
            with open(os.path.join(supporting_outputs, f'{snap_mode}_catchment_value_counts.json'), 'w') as outfile:
                json.dump(sanitiser.sanitise_dictionary(catchment_value_counts), outfile)
            logging.info(f'Number of stops in each catchment bin: {catchment_value_counts}')

            # generate the data dictionaries for updating stops data
            access_link_id_tag = f'accessLinkId_{snap_mode}'
            accessible_tag = f'{snap_mode}Accessible'
            distance_catchment_tag = f'{snap_mode}_distance_catchment_tag'

            selected_links[access_link_id_tag] = selected_links['link_id']
            selected_links[accessible_tag] = 'true'
            selected_links[distance_catchment_tag] = selected_links['catchment'].astype(str)
            new_stops_data = selected_links[[access_link_id_tag, accessible_tag, distance_catchment_tag]].T.to_dict()
            new_stops_data = {k: {'attributes': v} for k, v in new_stops_data.items()}

            n.schedule.apply_attributes_to_stops(new_stops_data)

    if teleport_modes is not None:
        for tele_mode in teleport_modes.split(','):
            logging.info(f'Adding access to mode: {tele_mode}')

            # generate the data dictionaries for updating stops data
            accessible_tag = f'{tele_mode}Accessible'
            df_stops[accessible_tag] = 'true'
            new_stops_data = df_stops[[accessible_tag]].T.to_dict()
            new_stops_data = {k: {'attributes': v} for k, v in new_stops_data.items()}

            n.schedule.apply_attributes_to_stops(new_stops_data)

    logging.info('Writing the schedule.')
    n.schedule.write_to_matsim(output_dir)
