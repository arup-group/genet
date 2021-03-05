import logging


def generate_validation_report(schedule):
    logging.info('Checking validity of the Schedule')
    report = {
        'schedule_level': {},
        'service_level': {},
        'route_level': {}
    }
    route_validity = {}
    for route in schedule.routes():
        is_valid_route, invalid_stages = route.is_valid_route(return_reason=True)
        route_validity[route.id] = {
            'is_valid_route': is_valid_route,
            'invalid_stages': invalid_stages
        }

    for service_id in schedule.service_ids():
        invalid_stages = []
        invalid_routes = []
        report['route_level'][service_id] = {}
        for route_id in schedule.service_to_route_map()[service_id]:
            if not route_validity[route_id]['is_valid_route']:
                invalid_routes.append(route_id)
                logging.warning(f'Route id={route_id} under Service id={service_id} is not valid')
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
            logging.warning('Service id={} is not valid'.format(service_id))

    invalid_stages = []
    invalid_services = [service_id for service_id in schedule.service_ids() if
                        not report['service_level'][service_id]['is_valid_service']]

    if invalid_services:
        is_valid_schedule = False
        has_valid_services = False
        invalid_stages.append('not_has_valid_services')
    else:
        is_valid_schedule = True
        has_valid_services = True

    report['schedule_level'] = {
        'is_valid_schedule': is_valid_schedule,
        'invalid_stages': invalid_stages,
        'has_valid_services': has_valid_services,
        'invalid_services': invalid_services}

    if not is_valid_schedule:
        logging.warning('This schedule is not valid')
    return report
