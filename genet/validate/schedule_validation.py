import logging


def generate_validation_report(schedule):
    logging.info('Checking validity of the Schedule')
    is_valid_schedule, invalid_stages = schedule.is_valid_schedule(return_reason=True)
    report = {
        'schedule_level': {
            'is_valid_schedule': is_valid_schedule,
            'invalid_stages': invalid_stages,
            'has_valid_services': schedule.has_valid_services(),
            'invalid_services': [service.id for service in schedule.invalid_services()]},
        'service_level': {},
        'route_level': {}}

    if not is_valid_schedule:
        logging.warning('This schedule is not valid')

    for service_id, service in schedule.services.items():
        is_valid_service, invalid_stages = service.is_valid_service(return_reason=True)
        report['service_level'][service_id] = {
            'is_valid_service': is_valid_service,
            'invalid_stages': invalid_stages,
            'has_valid_routes': service.has_valid_routes()}

        if not is_valid_service:
            logging.warning('Service id={} is not valid'.format(service_id))

        report['route_level'][service_id] = {}
        if service.has_uniquely_indexed_routes():
            report['service_level'][service_id]['invalid_routes'] = [route.id for route in service.invalid_routes()]
            for route in service.routes.values():
                is_valid_route, invalid_stages = route.is_valid_route(return_reason=True)
                report['route_level'][service_id][route.id] = {
                    'is_valid_route': is_valid_route,
                    'invalid_stages': invalid_stages,
                }
                if not is_valid_route:
                    logging.warning('Route id={} under Service id={} is not valid'.format(route.id, service_id))
        else:
            report['service_level'][service_id]['invalid_routes'] = [i for i in service.routes.keys() if
                                                                     not service.routes[i].is_valid_route()]
            i = 0
            for route in service.routes.values():
                is_valid_route, invalid_stages = route.is_valid_route(return_reason=True)
                report['route_level'][service_id][i] = {
                    'is_valid_route': is_valid_route,
                    'invalid_stages': invalid_stages,
                }
                if not is_valid_route:
                    logging.warning('Route at index {} under Service id={} is not valid'.format(i, service_id))
                i += 1
    return report
