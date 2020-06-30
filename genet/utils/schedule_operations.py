import logging


def generate_validation_report(schedule):
    logging.info('Checking validity of the Schedule')
    report = {
        'schedule_level': {
            'is_valid': schedule.is_valid_schedule(),
            'has_valid_services': schedule.has_valid_services(),
            'invalid_services': [service.id for service in schedule.invalid_services()]},
        'service_level': {},
        'route_level': {}}

    if not report['schedule_level']['is_valid']:
        logging.warning('This schedule is not valid')

    for service_id, service in schedule.services.items():
        report['service_level'][service_id] = {
            'is_valid': service.is_valid_service(),
            'has_valid_routes': service.has_valid_routes()}

        if not report['service_level'][service_id]['is_valid']:
            logging.warning('Service id={} is not valid'.format(service_id))

        if service.has_uniquely_indexed_routes():
            report['service_level'][service_id]['invalid_routes'] = [route.id for route in service.invalid_routes()]
            report['route_level'][service_id] = {}
            for route in service.routes:
                report['route_level'][service_id][route.id] = {
                    'is_valid_route': route.is_valid_route()}

                if not report['route_level'][service_id][route.id]['is_valid_route']:
                    logging.warning('Route id={} under Service id={} is not valid'.format(route.id, service_id))
        else:
            report['service_level'][service_id]['invalid_routes'] = [i for i in range(len(service.routes)) if
                                                                     not service.routes[i].is_valid_route()]
            report['route_level'][service_id] = []
            i = 0
            for route in service.routes:
                report['route_level'][service_id].append({
                    'is_valid_route': route.is_valid_route()})

                if not route.is_valid_route():
                    logging.warning('Route at index {} under Service id={} is not valid'.format(i, service_id))
                i += 1
    return report
