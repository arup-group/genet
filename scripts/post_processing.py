import argparse
import json
import logging
import os
import time
import copy

from genet import read_matsim
from genet.utils.persistence import ensure_dir

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description='Simplify a MATSim network by removing '
                                                     'intermediate links from paths')

    arg_parser.add_argument('-n',
                            '--network',
                            help='Location of the network.xml file',
                            required=True)

    arg_parser.add_argument('-s',
                            '--schedule',
                            help='Location of the schedule.xml file',
                            required=False,
                            default=None)

    arg_parser.add_argument('-v',
                            '--vehicles',
                            help='Location of the vehicles.xml file',
                            required=False,
                            default=None)

    arg_parser.add_argument('-p',
                            '--projection',
                            help='The projection network is in, eg. "epsg:27700"',
                            required=True)

    arg_parser.add_argument('-vd',
                            '--vehicles_dictionary',
                            help='Json dictionary file of the PT vehicles and capacities, e.g. {"bus":{"bus_small":55,"bus_large":70}',
                            required=True)
    
    arg_parser.add_argument('-vm',
                            '--vehicle_mappings',
                            help='Json dictionary of the vehilce IDs and the associated vehicle mapping, e.g. {"vehicle_1":"bus_small"}',
                            required=True)
    
    arg_parser.add_argument('-d',
                        '--gtfs_day',
                        help='Day of gtfs to extract the vehicles in the schedule, defaults to "20180301:',
                        required=False,
                        default="20180301",
                        type=str
                        )

    arg_parser.add_argument('-np',
                            '--processes',
                            help='The number of processes to split computation across',
                            required=False,
                            default=1,
                            type=int)

    arg_parser.add_argument('-od',
                            '--output_dir',
                            help='Output directory for the simplified network',
                            required=True)

    args = vars(arg_parser.parse_args())
    network = args['network']
    schedule = args['schedule']
    vehicles = args['vehicles']
    projection = args['projection']
    vehicle_dictionary_path = args['vehicles_dictionary']
    vehicle_mapping_path = args['vehicle_mappings']
    gtfs_day = args['gtfs_day']
    processes = args['processes']
    output_dir = args['output_dir']
    
    ensure_dir(output_dir)

    logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.WARNING)

    logging.info('Reading in network at {}'.format(network))
    n = read_matsim(
        path_to_network=network,
        epsg=projection,
        path_to_schedule=schedule,
        path_to_vehicles=vehicles
    )

    logging.info('Simplifying the Network.')

    start = time.time()
    n.simplify(no_processes=processes)
    end = time.time()

    logging.info('Connecting components.')
    try:
        for mode in ['car', 'walk', 'bike']:
            n.connect_components(modes={mode}, weight=1/5)
    except RuntimeError as e:
        logging.exception('Error connecting components!')
        logging.info('Continuing...')

    logging.info(
        f'Simplification resulted in {len(n.link_simplification_map)} links being simplified.')
    with open(os.path.join(output_dir, 'link_simp_map.json'), 'w', encoding='utf-8') as f:
        json.dump(n.link_simplification_map, f, ensure_ascii=False, indent=4)


    logging.info(
        f'Updating PT vehicle capacities...'
    )

    with open(vehicle_dictionary_path, "r") as file:
        update_vehicles = json.load(file)

    with open(vehicle_mapping_path, "r") as file:
        mapping_vehicles_dict = json.load(file)

    ## add the new vehicle types to the network
    default_vehicle_types = n.schedule.vehicle_types
    for mode_name, mode_dict in update_vehicles.items():
        for v_type, cap in mode_dict.items():
            update_vehicle = copy.deepcopy(default_vehicle_types[mode_name])
            update_vehicle["capacity"]["seats"]["persons"] = str(cap)
            default_vehicle_types[v_type] = update_vehicle

    # get routes in currnet network and check if mapping of vehicles exist
    network_route_trips = n.schedule.route_trips_to_dataframe(gtfs_day=gtfs_day)
    network_route_trips["vehicle_type"] = network_route_trips.service_id.map(
        mapping_vehicles_dict
    )
    network_route_trips["mode"] = network_route_trips.vehicle_id.str.extract(
        r"_([a-zA-Z]+)"
    )
    modes_not_covered = (
        network_route_trips[network_route_trips.vehicle_type.isna()]["mode"]
        .unique()
        .tolist()
    )  # check for vehicle types not covered by the update
    logging.info(
        f"The following PT modes do not have vehicle mappings: {modes_not_covered}. The default will be used."
    )

    # Get all vehicle ids and thier vehicle type mappings
    vehicle_id_type_dict = dict(network_route_trips[["vehicle_id", "vehicle_type"]].values)

    # update all existing vehicles to a new vehicle type, if there is no mapping then do not update
    for v_id, v_type in vehicle_id_type_dict.items():
        if str(v_type) != "nan":
            n.schedule.vehicles[v_id]["type"] = v_type

    # Use GeNet's validation to if all Vehicle IDs have been defined
    logging.info(
        f"All vehicles in the schedule have been defined: {n.schedule.validate_vehicle_definitions()}"
    )

    n.write_to_matsim(output_dir)

    logging.info('Generating validation report')
    report = n.generate_validation_report()
    logging.info(f'Graph validation: {report["graph"]["graph_connectivity"]}')
    if n.schedule:
        logging.info(f'Schedule level validation: {report["schedule"]["schedule_level"]["is_valid_schedule"]}')
        logging.info(f'Routing validation: {report["routing"]["services_have_routes_in_the_graph"]}')
    with open(os.path.join(output_dir, 'validation_report.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=4)

    n.generate_standard_outputs(os.path.join(output_dir, 'standard_outputs'))

    logging.info(f'It took {round((end - start)/60, 3)} min to simplify the network.')
