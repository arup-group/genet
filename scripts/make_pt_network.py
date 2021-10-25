import os
import json
import argparse
import genet as gn
import logging


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description='Create a PT MATSim network')

    arg_parser.add_argument('-o',
                            '--osm',
                            help='Location of the osm file',
                            required=False)

    arg_parser.add_argument('-oc',
                            '--osm_config',
                            help='Location of the config file defining what and how to read from the osm file',
                            required=False)

    arg_parser.add_argument('-n',
                            '--network',
                            help='Location of the network file, if you already have one',
                            required=False)

    arg_parser.add_argument('-g',
                            '--gtfs',
                            help='Location of the gtfs zip file of folder with gtfs text files',
                            required=True)

    arg_parser.add_argument('-gd',
                            '--gtfs_day',
                            help='Location of the gtfs zip file of folder with gtfs text files',
                            required=True)

    arg_parser.add_argument('-sd',
                            '--snapping_distance',
                            help='Distance for snapping network nodes to transit stops',
                            default=30,
                            type=float
                            )

    arg_parser.add_argument('-p',
                            '--projection',
                            help='The projection for the network eg. "epsg:27700"',
                            required=True)

    arg_parser.add_argument('-pp',
                            '--processes',
                            help='Number of parallel processes to split process across',
                            default=1,
                            type=int)

    arg_parser.add_argument('-s',
                            '--solver',
                            help='Solver to use for finding closest nodes to stops',
                            default='glpk',
                            type=str)

    arg_parser.add_argument('-od',
                            '--output_dir',
                            help='Output directory for the network',
                            required=True)

    args = vars(arg_parser.parse_args())
    osm = args['osm']
    osm_config = args['osm_config']
    network = args['network']
    gtfs = args['gtfs']
    gtfs_day = args['gtfs_day']
    snapping_distance = args['snapping_distance']
    projection = args['projection']
    processes = args['processes']
    output_dir = args['output_dir']
    gn.utils.persistence.ensure_dir(output_dir)

    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.WARNING)

    n = None
    if osm is not None:
        logging.info(f'Reading in network at {osm}')
        n = gn.read_osm(osm, osm_config, num_processes=processes)
        logging.info('Connecting components for the graph')
        links_added = n.connect_components()
        logging.info('Connecting components for walk, bike and car')
        with open(os.path.join(output_dir, 'connecting_links.json'), 'w', encoding='utf-8') as f:
            json.dump(links_added, f, ensure_ascii=False, indent=4)
    elif network is not None:
        logging.info(f'Reading in network at {network}')
        n = gn.read_matsim_network(network, projection)
    else:
        raise NotImplementedError('You need to pass an OSM file and config to create a Network or an existing MATSim '
                                  'network.xml. If your network exists in another format, write a script to use an '
                                  'appropriate reading method for that network.')

    logging.info(f'Reading GTFS at {gtfs} for day: {gtfs_day}')
    n.schedule = gn.read_gtfs(gtfs, day=gtfs_day, epsg=projection)

    logging.info(f'Snapping and routing the schedule onto the network with distance threshold {snapping_distance}')
    unsnapped_services = n.route_schedule(snapping_distance, additional_modes={'bus': 'car'})

    n.simplify(no_processes=processes)

    logging.info(
        f'Simplification resulted in {len(n.link_simplification_map)} links being simplified.')
    with open(os.path.join(output_dir, 'link_simp_map.json'), 'w', encoding='utf-8') as f:
        json.dump(n.link_simplification_map, f, ensure_ascii=False, indent=4)

    logging.info('Generating validation report')
    report = n.generate_validation_report()
    logging.info(f'Graph validation: {report["graph"]["graph_connectivity"]}')
    if n.schedule:
        logging.info(f'Schedule level validation: {report["schedule"]["schedule_level"]["is_valid_schedule"]}')
        logging.info(f'Routing validation: {report["routing"]["services_have_routes_in_the_graph"]}')

    n.generate_standard_outputs(os.path.join(output_dir, 'standard_outputs'))

    logging.info(f'Writing results to {output_dir}')
    n.write_to_matsim(output_dir)
