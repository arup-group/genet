from genet.schedule_elements import Route, Stop
from tests.fixtures import stop_epsg_27700, route, assert_semantically_equal


def test_build_graph_builds_correct_graph():
    route = Route(route_short_name='name',
                  mode='bus',
                  stops=[Stop(id='1', x=4, y=2, epsg='epsg:27700'), Stop(id='2', x=1, y=2, epsg='epsg:27700'),
                         Stop(id='3', x=3, y=3, epsg='epsg:27700'), Stop(id='4', x=7, y=5, epsg='epsg:27700')],
                  trips={'1': '1', '2': '2'}, arrival_offsets=['1', '2'], departure_offsets=['1', '2'])
    g = route.build_graph()
    assert_semantically_equal(dict(g.nodes(data=True)),
                              {'1': {'x': 4.0, 'y': 2.0, 'lat': 49.76682779861249, 'lon': -7.557106577683727},
                               '2': {'x': 1.0, 'y': 2.0, 'lat': 49.766825803756994, 'lon': -7.557148039524952},
                               '3': {'x': 3.0, 'y': 3.0, 'lat': 49.76683608549253, 'lon': -7.557121424907424},
                               '4': {'x': 7.0, 'y': 5.0, 'lat': 49.766856648946295, 'lon': -7.5570681956375}})
    assert_semantically_equal(list(g.edges), [('1', '2'), ('2', '3'), ('3', '4')])


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
