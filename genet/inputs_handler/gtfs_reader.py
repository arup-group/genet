import csv
import logging
import os
import shutil
from datetime import datetime, timedelta
from genet.utils import spatial, persistence
from genet import variables


def read_services_from_calendar(path, day):
    """
    return list of services to be included
    :param path: path to GTFS folder
    :param day: 'YYYYMMDD' for specific day
    :return:
    """
    logging.info("Reading the calendar for GTFS")

    weekdays = {
        0: 'monday',
        1: 'tuesday',
        2: 'wednesday',
        3: 'thursday',
        4: 'friday',
        5: 'saturday',
        6: 'sunday'
    }
    day_of_the_week = weekdays[datetime.strptime(day, '%Y%m%d').weekday()]

    services = []

    calendar_present = False
    for file_name in os.listdir(path):
        file = os.path.join(path, file_name)
        if ("calendar" in file) and (not ("dates" in file)):
            calendar_present = True
            with open(file, mode='r') as infile:
                reader = csv.DictReader(infile)
                for row in reader:
                    if (int(day) in range(int(row['start_date']), int(row['end_date']))) and \
                            (int(row[day_of_the_week]) == 1):
                        services.append(row['service_id'])
    if not services:
        if calendar_present:
            raise RuntimeError('The date you have selected yielded no services')
        else:
            raise RuntimeError('Calendar was not found with the GTFS')
    return services


def read_gtfs_to_db_like_tables(path):
    logging.info("Reading GTFS data into usable format")

    trips_db = {}
    stops_db = {}
    routes_db = {}
    stop_times_db = {}
    stop_times = []

    for file_name in os.listdir(path):
        file = os.path.join(path, file_name)

        if "stop_times" in file:
            logging.info("Reading stop times")
            with open(file, mode='r') as infile:
                reader = csv.DictReader(infile)
                for row in reader:
                    stop_times.append(dict(row))
                    if row['trip_id'] in stop_times_db:
                        stop_times_db[row['trip_id']].append(dict(row))
                    else:
                        stop_times_db[row['trip_id']] = [dict(row)]

        elif "stops" in file:
            logging.info("Reading stops")
            with open(file, mode='r') as infile:
                reader = csv.DictReader(infile)
                for row in reader:
                    stops_db[row['stop_id']] = dict(row)

        elif "trips" in file:
            logging.info("Reading trips")
            with open(file, mode='r') as infile:
                reader = csv.DictReader(infile)
                for row in reader:
                    trips_db[row['trip_id']] = dict(row)

        elif "routes" in file:
            logging.info("Reading routes")
            with open(file, mode='r') as infile:
                reader = csv.DictReader(infile)
                for row in reader:
                    routes_db[row['route_id']] = dict(row)

    return stop_times, stop_times_db, stops_db, trips_db, routes_db


def get_mode(route_type):
    if not isinstance(route_type, int):
        route_type = int(route_type)

    if route_type in variables.EXTENDED_TYPE_MAP:
        return variables.EXTENDED_TYPE_MAP[route_type]
    else:
        return 'other'


def parse_db_to_schedule_dict(stop_times_db, stops_db, trips_db, route_db, services):
    def get_time(time):
        # return time as datetime.datetime, account for 24 in %H
        time_list = time.split(':')
        if int(time_list[0]) >= 24:
            days = int(time_list[0]) // 24
            time_list[0] = int(time_list[0]) % 24
            if time_list[0] < 10:
                time_list[0] = '0{}'.format(time_list[0])
            else:
                time_list[0] = str(time_list[0])
            return datetime.strptime(':'.join(time_list), '%H:%M:%S') + timedelta(days=days)
        else:
            return datetime.strptime(time, '%H:%M:%S')

    def get_the_route(route_id, stops):
        for i in range(len(schedule[route_id])):
            route = schedule[route_id][i]
            stops_already_in_schedule = route['stops']
            if stops == stops_already_in_schedule:
                return i
        return None

    def update_route_info(route_id, departure_time, i):
        # assuming all trips sharing the same route have the same time offsets
        schedule[route_id][i]['stops'] = stops
        schedule[route_id][i]['s2_stops'] = s2_stops

        for stop_time in stop_times:
            stop_arrival = get_time(stop_time['arrival_time'])
            stop_departure = get_time(stop_time['departure_time'])
            schedule[route_id][i]['arrival_offsets'].append(str(stop_arrival - departure_time))
            schedule[route_id][i]['departure_offsets'].append(str(stop_departure - departure_time))

    schedule = {}

    for trip_id, trip_val in trips_db.items():
        route_id = trip_val['route_id']
        if trip_val['service_id'] in services:
            if route_id not in schedule:
                schedule[route_id] = []
            route_val = route_db[route_id]
            stop_times = stop_times_db[trip_id]
            stops = [stop_time['stop_id'] for stop_time in stop_times]
            s2_stops = [spatial.grab_index_s2(
                lat=float(stops_db[stop]['stop_lat']), lng=float(stops_db[stop]['stop_lon'])) for stop in stops]

            if len(stops) > 1:
                # get the route
                i = get_the_route(route_id, stops)
                if i is not None:
                    # add this trip and it's departure time to already existing route
                    schedule[route_id][i]['trips'][trip_id] = stop_times[0]['arrival_time']
                if i is None:
                    # fresh route
                    schedule[route_id].append({
                        # route info
                        'route_short_name': route_val['route_short_name'],
                        'route_long_name': route_val['route_long_name'],
                        'mode': get_mode(route_val['route_type']),
                        'route_color': '#{}'.format(route_val['route_color']),
                        # trip ids and their own departure times
                        'trips': {trip_id: stop_times[0]['arrival_time']},
                        # stops and time offsets for each stop along the route
                        'stops': [],
                        'arrival_offsets': [],
                        'departure_offsets': []
                    })
                    i = len(schedule[route_id]) - 1
                    departure_time = get_time(schedule[route_id][i]['trips'][trip_id])
                    update_route_info(route_id, departure_time, i)
            elif len(schedule[route_id]) == 0:
                del schedule[route_id]

    return schedule


def read_to_dict_schedule_and_stopd_db(path: str, day: str):
    if persistence.is_zip(path):
        gtfs_path = os.path.join(os.getcwd(), 'tmp')
        if not os.path.exists(gtfs_path):
            os.makedirs(gtfs_path)
        import zipfile
        with zipfile.ZipFile(path, 'r') as zip_ref:
            zip_ref.extractall(gtfs_path)
        gtfs_path = os.path.join(gtfs_path, os.path.splitext(os.path.basename(path))[0])
    else:
        gtfs_path = path

    services = read_services_from_calendar(gtfs_path, day=day)
    stop_times, stop_times_db, stops_db, trips_db, routes_db = read_gtfs_to_db_like_tables(gtfs_path)
    schedule = parse_db_to_schedule_dict(stop_times_db, stops_db, trips_db, routes_db, services)

    if persistence.is_zip(path):
        shutil.rmtree(os.path.dirname(gtfs_path))

    return schedule, stops_db
