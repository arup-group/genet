from genet.schedule_elements import Route
from tests.fixtures import stop_epsg_27700, route


def test_routes_equal(stop_epsg_27700):
    a = Route(
        route_short_name='route', mode='bus',
        stops=[stop_epsg_27700, stop_epsg_27700],
        trips={'VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00': '04:40:00'},
        arrival_offsets=['00:00:00', '00:02:00'],
        departure_offsets=['00:00:00', '00:02:00'])

    b = Route(
        route_short_name='route', mode='bus',
        stops=[stop_epsg_27700, stop_epsg_27700],
        trips={},
        arrival_offsets=[],
        departure_offsets=[])

    assert a == b


def test_routes_exact():
    a = Route(
        route_short_name='route', mode='bus',
        stops=[stop_epsg_27700, stop_epsg_27700],
        trips={'VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00': '04:40:00'},
        arrival_offsets=['00:00:00', '00:02:00'],
        departure_offsets=['00:00:00', '00:02:00'])

    b = Route(
        route_short_name='route', mode='bus',
        stops=[stop_epsg_27700, stop_epsg_27700],
        trips={'VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00': '04:40:00'},
        arrival_offsets=['00:00:00', '00:02:00'],
        departure_offsets=['00:00:00', '00:02:00'])

    assert a.is_exact(b)


def test_route_isin_exact_list(route):
    a = route

    assert a.isin_exact([route, route, route])


def test_route_is_not_in_exact_list(route, stop_epsg_27700):
    a = Route(
        route_short_name='route', mode='bus',
        stops=[stop_epsg_27700, stop_epsg_27700],
        trips={},
        arrival_offsets=[],
        departure_offsets=[])

    assert not a.isin_exact([route, route, route])
