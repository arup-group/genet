from genet.inputs_handler import read
from tests.fixtures import *

gtfs_test_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_data", "gtfs"))

def test_read_gtfs_returns_expected_schedule(correct_stops_to_service_mapping_from_test_gtfs,
                                             correct_stops_to_route_mapping_from_test_gtfs):
    schedule = read.read_gtfs(gtfs_test_file, '20190604')

    assert schedule['1001'] == Service(
        '1001',
        [Route(
            route_short_name='BTR',
            mode='bus',
            stops=[Stop(id='BSE', x=-0.1413621, y=51.5226864, epsg='epsg:4326'),
                   Stop(id='BSN', x=-0.140053, y=51.5216199, epsg='epsg:4326')],
            trips={'trip_id': ['BT1'], 'trip_departure_time': ['03:21:00'], 'vehicle_id': ['veh_0_bus']},
            arrival_offsets=['0:00:00', '0:02:00'],
            departure_offsets=['0:00:00', '0:02:00']
        )])
    assert schedule['1002'] == Service(
        '1002',
        [Route(
            route_short_name='RTR',
            mode='rail',
            stops=[Stop(id='RSN', x=-0.1410946, y=51.5231335, epsg='epsg:4326'),
                   Stop(id='RSE', x=-0.1421595, y=51.5192615, epsg='epsg:4326')],
            trips={'trip_id': ['RT1'], 'trip_departure_time': ['03:21:00'], 'vehicle_id': ['veh_1_rail']},
            arrival_offsets=['0:00:00', '0:02:00'],
            departure_offsets=['0:00:00', '0:02:00']
        )])
    assert_semantically_equal(schedule.stop_to_service_ids_map(), correct_stops_to_service_mapping_from_test_gtfs)
    assert_semantically_equal(schedule.stop_to_route_ids_map(), correct_stops_to_route_mapping_from_test_gtfs)
