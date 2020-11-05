import pytest
from genet import Stop, Route, Service, Schedule
import genet.use.schedule as use_schedule


@pytest.fixture()
def schedule():
    route_1 = Route(route_short_name='name',
                    mode='bus', id='1',
                    stops=[Stop(id='1', x=4, y=2, epsg='epsg:27700', name='Stop_1'),
                           Stop(id='2', x=1, y=2, epsg='epsg:27700', name='Stop_2'),
                           Stop(id='3', x=3, y=3, epsg='epsg:27700', name='Stop_3'),
                           Stop(id='4', x=7, y=5, epsg='epsg:27700')],
                    trips={'1': '17:00:00', '2': '18:30:00'},
                    arrival_offsets=['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                    departure_offsets=['00:00:00', '00:05:00', '00:09:00', '00:15:00'])
    route_2 = Route(route_short_name='name_2',
                    mode='bus', id='2',
                    stops=[Stop(id='4', x=7, y=5, epsg='epsg:27700'),
                           Stop(id='3', x=3, y=3, epsg='epsg:27700', name='Stop_3'),
                           Stop(id='2', x=1, y=2, epsg='epsg:27700', name='Stop_2'),
                           Stop(id='1', x=4, y=2, epsg='epsg:27700', name='Stop_1')],
                    trips={'1': '17:00:00', '2': '18:30:00'},
                    arrival_offsets=['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                    departure_offsets=['00:00:00', '00:05:00', '00:09:00', '00:15:00'])
    service = Service(id='service', routes=[route_1, route_2])
    return Schedule(epsg='epsg:27700', services=[service])


def test_generating_trips_geodataframe_for_schedule(schedule):
    use_schedule.generate_trips_dataframe(schedule)
    pass


def test_generating_edge_vph_geodataframe(schedule):
    use_schedule.generate_edge_vph_geodataframe(schedule)
    pass

def test_generating_trips_geodataframe_for_service(schedule):
    use_schedule.generate_trips_dataframe(schedule.service('service'))
    pass


def test_generating_edge_vph_geodataframe_for_service(schedule):
    use_schedule.generate_edge_vph_geodataframe(schedule)
    pass


def test_generating_trips_geodataframe_for_route(schedule):
    use_schedule.generate_trips_dataframe(schedule.route('1'))
    pass


def test_generating_edge_vph_geodataframe_for_route(schedule):
    use_schedule.generate_edge_vph_geodataframe(schedule)
    pass
