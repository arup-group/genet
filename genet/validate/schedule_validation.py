import logging


def generate_validation_report(schedule):
    logging.info('Checking validity of the Schedule')
    report = {
        'schedule_level': {},
        'service_level': {},
        'route_level': {},
        'vehicle_level': {}
    }

    logging.info('Computing headway stats')
    df_headway = schedule.headway_stats().set_index('route_id')

    route_validity = {}
    for route in schedule.routes():
        is_valid_route, invalid_stages = route.is_valid_route(return_reason=True)
        route_validity[route.id] = {
            'is_valid_route': is_valid_route,
            'invalid_stages': invalid_stages,
            'headway_stats': df_headway.loc[
                route.id, ['mean_headway_mins', 'std_headway_mins', 'max_headway_mins', 'min_headway_mins']].to_dict()
        }

    for service_id in schedule.service_ids():
        invalid_stages = []
        invalid_routes = []
        report['route_level'][service_id] = {}
        for route_id in schedule.service_to_route_map()[service_id]:
            if not route_validity[route_id]['is_valid_route']:
                invalid_routes.append(route_id)
                logging.warning(f'Route ID: {route_id} under Service ID: {service_id} is not valid')
            report['route_level'][service_id][route_id] = route_validity[route_id]

        if invalid_routes:
            is_valid_service = False
            has_valid_routes = False
            invalid_stages.append('not_has_valid_routes')
        else:
            is_valid_service = True
            has_valid_routes = True

        report['service_level'][service_id] = {
            'is_valid_service': is_valid_service,
            'invalid_stages': invalid_stages,
            'has_valid_routes': has_valid_routes,
            'invalid_routes': invalid_routes
        }
        if not is_valid_service:
            logging.warning(f'Service with ID: {service_id} is not valid')

    invalid_stages = []
    invalid_services = [service_id for service_id in schedule.service_ids() if
                        not report['service_level'][service_id]['is_valid_service']]

    logging.info('Checking validity of PT vehicles')
    has_valid_vehicle_def = schedule.validate_vehicle_definitions()
    missing_vehicle_types = schedule.get_missing_vehicle_information()

    report['vehicle_level'] = {
        'vehicle_definitions_valid': has_valid_vehicle_def,
        'vehicle_definitions_validity_components': {
            'missing_vehicles': {
                'missing_vehicles_types': missing_vehicle_types['missing_vehicle_types'],
                'vehicles_affected': missing_vehicle_types['vehicles_affected']},
            'unused_vehicles': schedule.unused_vehicles(),
            'multiple_use_vehicles': schedule.check_vehicle_uniqueness()}
    }

    if invalid_services or (not has_valid_vehicle_def):
        is_valid_schedule = False
        has_valid_services = False
        if invalid_services:
            invalid_stages.append('not_has_valid_services')
        if not has_valid_vehicle_def:
            invalid_stages.append('not_has_valid_vehicle_definitions')
    else:
        is_valid_schedule = True
        has_valid_services = True

    report['schedule_level'] = {
        'is_valid_schedule': is_valid_schedule,
        'invalid_stages': invalid_stages,
        'has_valid_services': has_valid_services,
        'invalid_services': invalid_services}

    zero_headways = df_headway[df_headway['min_headway_mins'] == 0]
    report['schedule_level']['headways'] = {}
    if not zero_headways.empty:
        report['schedule_level']['headways']['has_zero_min_headways'] = True
        report['schedule_level']['headways']['routes'] = {
            'number_of_affected': len(zero_headways),
            'ids': list(zero_headways.index)
        }
        report['schedule_level']['headways']['services'] = {
            'number_of_affected': len(zero_headways['service_id'].unique()),
            'ids': list(zero_headways['service_id'].unique())
        }

        logging.warning(f"Found {len(zero_headways)} PT Routes 0 minimum headway between trips. "
                        f"The following Services are affected: {report['schedule_level']['services']}")
    else:
        report['schedule_level']['headways']['has_zero_min_headways'] = False

    if not is_valid_schedule:
        logging.warning('This schedule is not valid')

    return report
