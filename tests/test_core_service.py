from genet.schedule_elements import Service
from tests.fixtures import *


def test_services_equal(route):
    a = Service(id='service',
                routes=[route, similar_non_exact_test_route])

    b = Service(id='service',
                routes=[route, similar_non_exact_test_route])

    assert a == b


def test_services_exact(route):
    a = Service(id='service',
                routes=[route, similar_non_exact_test_route])

    b = Service(id='service',
                routes=[route, similar_non_exact_test_route])

    assert a.is_exact(b)


def test_route_isin_exact_list(test_service):
    a = test_service

    assert a.isin_exact([test_service, test_service])


def test_route_is_not_in_exact_list(similar_non_exact_test_route, test_service):
    a = Service(id='service',
                routes=[similar_non_exact_test_route])

    assert not a.isin_exact([test_service, test_service])


def test_build_graph_builds_correct_graph():
    route_1 = Route(route_short_name='name',
                  mode='bus',
                  stops=[Stop(id='1', x=4, y=2, epsg='epsg:27700'), Stop(id='2', x=1, y=2, epsg='epsg:27700'),
                         Stop(id='3', x=3, y=3, epsg='epsg:27700'), Stop(id='4', x=7, y=5, epsg='epsg:27700')],
                  trips={'1': '1', '2': '2'}, arrival_offsets=['1', '2'], departure_offsets=['1', '2'])
    route_2 = Route(route_short_name='name_2',
                  mode='bus',
                  stops=[Stop(id='5', x=4, y=2, epsg='epsg:27700'), Stop(id='6', x=1, y=2, epsg='epsg:27700'),
                         Stop(id='7', x=3, y=3, epsg='epsg:27700'), Stop(id='8', x=7, y=5, epsg='epsg:27700')],
                  trips={'1': '1', '2': '2'}, arrival_offsets=['1', '2'], departure_offsets=['1', '2'])
    service = Service(id='service',
                      routes=[route_1, route_2])

    g = service.build_graph()

    assert_semantically_equal(dict(g.nodes(data=True)),
                              {'5': {'x': 4.0, 'y': 2.0, 'lat': 49.76682779861249, 'lon': -7.557106577683727},
                               '6': {'x': 1.0, 'y': 2.0, 'lat': 49.766825803756994, 'lon': -7.557148039524952},
                               '7': {'x': 3.0, 'y': 3.0, 'lat': 49.76683608549253, 'lon': -7.557121424907424},
                               '8': {'x': 7.0, 'y': 5.0, 'lat': 49.766856648946295, 'lon': -7.5570681956375},
                               '1': {'x': 4.0, 'y': 2.0, 'lat': 49.76682779861249, 'lon': -7.557106577683727},
                               '2': {'x': 1.0, 'y': 2.0, 'lat': 49.766825803756994, 'lon': -7.557148039524952},
                               '3': {'x': 3.0, 'y': 3.0, 'lat': 49.76683608549253, 'lon': -7.557121424907424},
                               '4': {'x': 7.0, 'y': 5.0, 'lat': 49.766856648946295, 'lon': -7.5570681956375}})
    assert_semantically_equal(list(g.edges), [('5', '6'), ('6', '7'), ('7', '8'), ('1', '2'), ('2', '3'), ('3', '4')])


def test_build_graph_builds_correct_graph_when_some_stops_overlap():
    route_1 = Route(route_short_name='name',
                  mode='bus',
                  stops=[Stop(id='1', x=4, y=2, epsg='epsg:27700'), Stop(id='2', x=1, y=2, epsg='epsg:27700'),
                         Stop(id='3', x=3, y=3, epsg='epsg:27700'), Stop(id='4', x=7, y=5, epsg='epsg:27700')],
                  trips={'1': '1', '2': '2'}, arrival_offsets=['1', '2'], departure_offsets=['1', '2'])
    route_2 = Route(route_short_name='name_2',
                  mode='bus',
                  stops=[Stop(id='1', x=4, y=2, epsg='epsg:27700'), Stop(id='6', x=1, y=2, epsg='epsg:27700'),
                         Stop(id='7', x=3, y=3, epsg='epsg:27700'), Stop(id='4', x=7, y=5, epsg='epsg:27700')],
                  trips={'1': '1', '2': '2'}, arrival_offsets=['1', '2'], departure_offsets=['1', '2'])
    service = Service(id='service',
                      routes=[route_1, route_2])

    g = service.build_graph()

    assert_semantically_equal(dict(g.nodes(data=True)),
                              {'1': {'x': 4.0, 'y': 2.0, 'lat': 49.76682779861249, 'lon': -7.557106577683727},
                               '6': {'x': 1.0, 'y': 2.0, 'lat': 49.766825803756994, 'lon': -7.557148039524952},
                               '7': {'x': 3.0, 'y': 3.0, 'lat': 49.76683608549253, 'lon': -7.557121424907424},
                               '4': {'x': 7.0, 'y': 5.0, 'lat': 49.766856648946295, 'lon': -7.5570681956375},
                               '2': {'x': 1.0, 'y': 2.0, 'lat': 49.766825803756994, 'lon': -7.557148039524952},
                               '3': {'x': 3.0, 'y': 3.0, 'lat': 49.76683608549253, 'lon': -7.557121424907424}})
    assert_semantically_equal(list(g.edges), [('1', '6'), ('6', '7'), ('7', '4'), ('1', '2'), ('2', '3'), ('3', '4')])
    assert 'Service' in g.name
