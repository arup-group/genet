import pytest
from genet.schedule_elements import Service
from genet.utils import plot
from tests.fixtures import *
from tests.test_core_components_route import self_looping_route, route


@pytest.fixture()
def service():
    route_1 = Route(id='1', route_short_name='name',
                    mode='bus',
                    stops=[Stop(id='1', x=4, y=2, epsg='epsg:27700', linkRefId='1'),
                           Stop(id='2', x=1, y=2, epsg='epsg:27700', linkRefId='2'),
                           Stop(id='3', x=3, y=3, epsg='epsg:27700', linkRefId='3'),
                           Stop(id='4', x=7, y=5, epsg='epsg:27700', linkRefId='4')],
                    trips={'1': '1', '2': '2'},
                    arrival_offsets=['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                    departure_offsets=['00:00:00', '00:05:00', '00:09:00', '00:15:00'],
                    route=['1', '2', '3', '4'])
    route_2 = Route(id='2', route_short_name='name_2',
                    mode='bus',
                    stops=[Stop(id='5', x=4, y=2, epsg='epsg:27700', linkRefId='5'),
                           Stop(id='6', x=1, y=2, epsg='epsg:27700', linkRefId='6'),
                           Stop(id='7', x=3, y=3, epsg='epsg:27700', linkRefId='7'),
                           Stop(id='8', x=7, y=5, epsg='epsg:27700', linkRefId='8')],
                    trips={'1': '1', '2': '2'},
                    arrival_offsets=['00:00:00', '00:03:00', '00:07:00', '00:13:00'],
                    departure_offsets=['00:00:00', '00:05:00', '00:09:00', '00:15:00'],
                    route=['5', '6', '7', '8'])
    return Service(id='service', routes=[route_1, route_2])


@pytest.fixture()
def strongly_connected_service():
    route_1 = Route(route_short_name='name',
                    mode='bus',
                    stops=[Stop(id='1', x=4, y=2, epsg='epsg:27700'), Stop(id='2', x=1, y=2, epsg='epsg:27700'),
                           Stop(id='3', x=3, y=3, epsg='epsg:27700'), Stop(id='4', x=7, y=5, epsg='epsg:27700'),
                           Stop(id='1', x=4, y=2, epsg='epsg:27700')],
                    trips={'1': '1', '2': '2'}, arrival_offsets=['1', '2'], departure_offsets=['1', '2'])
    route_2 = Route(route_short_name='name_2',
                    mode='bus',
                    stops=[Stop(id='5', x=4, y=2, epsg='epsg:27700'), Stop(id='2', x=1, y=2, epsg='epsg:27700'),
                           Stop(id='7', x=3, y=3, epsg='epsg:27700'), Stop(id='8', x=7, y=5, epsg='epsg:27700'),
                           Stop(id='5', x=4, y=2, epsg='epsg:27700')],
                    trips={'1': '1', '2': '2'}, arrival_offsets=['1', '2', '3', '4', '5'],
                    departure_offsets=['1', '2', '3', '4', '5'])
    return Service(id='service', routes=[route_1, route_2])


def test__repr__shows_route_length(service):
    assert str(len(service)) in service.__repr__()


def test__str__shows_info(service):
    assert service.id in service.__str__()
    assert service.name in service.__str__()
    assert str(len(service)) in service.__str__()


def test_print_shows_info(mocker, service):
    mocker.patch.object(Service, 'info')
    service.print()
    Service.info.assert_called_once()


def test_info_shows_id_name_and_len(service):
    info = service.info()
    assert service.id in info
    assert service.name in info
    assert str(len(service)) in info


def test_plot_delegates_to_util_plot_plot_graph_routes(mocker, route):
    mocker.patch.object(plot, 'plot_graph')
    route.plot()
    plot.plot_graph.assert_called_once()


def test_services_equal(route, similar_non_exact_test_route):
    a = Service(id='service',
                routes=[route, similar_non_exact_test_route])

    b = Service(id='service',
                routes=[route, similar_non_exact_test_route])

    assert a == b


def test_services_exact(route, similar_non_exact_test_route):
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
    route_1 = Route(route_short_name='name', id='1',
                  mode='bus',
                  stops=[Stop(id='1', x=4, y=2, epsg='epsg:27700'), Stop(id='2', x=1, y=2, epsg='epsg:27700'),
                         Stop(id='3', x=3, y=3, epsg='epsg:27700'), Stop(id='4', x=7, y=5, epsg='epsg:27700')],
                  trips={'1': '1', '2': '2'}, arrival_offsets=['1', '2'], departure_offsets=['1', '2'])
    route_2 = Route(route_short_name='name_2', id='2',
                  mode='bus',
                  stops=[Stop(id='5', x=4, y=2, epsg='epsg:27700'), Stop(id='6', x=1, y=2, epsg='epsg:27700'),
                         Stop(id='7', x=3, y=3, epsg='epsg:27700'), Stop(id='8', x=7, y=5, epsg='epsg:27700')],
                  trips={'1': '1', '2': '2'}, arrival_offsets=['1', '2'], departure_offsets=['1', '2'])
    service = Service(id='service',
                      routes=[route_1, route_2])

    g = service.graph()

    assert_semantically_equal(dict(g.nodes(data=True)),
                              {'5': {'routes': ['2'], 'id': '5', 'x': 4.0, 'y': 2.0, 'epsg': 'epsg:27700',
                                     'lat': 49.76682779861249, 'lon': -7.557106577683727, 's2_id': 5205973754090531959,
                                     'additional_attributes': [], 'services': ['service']},
                               '6': {'routes': ['2'], 'id': '6', 'x': 1.0, 'y': 2.0, 'epsg': 'epsg:27700',
                                     'lat': 49.766825803756994, 'lon': -7.557148039524952, 's2_id': 5205973754090365183,
                                     'additional_attributes': [], 'services': ['service']},
                               '7': {'routes': ['2'], 'id': '7', 'x': 3.0, 'y': 3.0, 'epsg': 'epsg:27700',
                                     'lat': 49.76683608549253, 'lon': -7.557121424907424, 's2_id': 5205973754090203369,
                                     'additional_attributes': [], 'services': ['service']},
                               '8': {'routes': ['2'], 'id': '8', 'x': 7.0, 'y': 5.0, 'epsg': 'epsg:27700',
                                     'lat': 49.766856648946295, 'lon': -7.5570681956375, 's2_id': 5205973754097123809,
                                     'additional_attributes': [], 'services': ['service']},
                               '1': {'routes': ['1'], 'id': '1', 'x': 4.0, 'y': 2.0, 'epsg': 'epsg:27700',
                                     'lat': 49.76682779861249, 'lon': -7.557106577683727, 's2_id': 5205973754090531959,
                                     'additional_attributes': [], 'services': ['service']},
                               '2': {'routes': ['1'], 'id': '2', 'x': 1.0, 'y': 2.0, 'epsg': 'epsg:27700',
                                     'lat': 49.766825803756994, 'lon': -7.557148039524952, 's2_id': 5205973754090365183,
                                     'additional_attributes': [], 'services': ['service']},
                               '3': {'routes': ['1'], 'id': '3', 'x': 3.0, 'y': 3.0, 'epsg': 'epsg:27700',
                                     'lat': 49.76683608549253, 'lon': -7.557121424907424, 's2_id': 5205973754090203369,
                                     'additional_attributes': [], 'services': ['service']},
                               '4': {'routes': ['1'], 'id': '4', 'x': 7.0, 'y': 5.0, 'epsg': 'epsg:27700',
                                     'lat': 49.766856648946295, 'lon': -7.5570681956375, 's2_id': 5205973754097123809,
                                     'additional_attributes': [], 'services': ['service']}})
    assert_semantically_equal(list(g.edges), [('5', '6'), ('6', '7'), ('7', '8'), ('1', '2'), ('2', '3'), ('3', '4')])


def test_build_graph_builds_correct_graph_when_some_stops_overlap():
    route_1 = Route(route_short_name='name', id='1',
                  mode='bus',
                  stops=[Stop(id='1', x=4, y=2, epsg='epsg:27700'), Stop(id='2', x=1, y=2, epsg='epsg:27700'),
                         Stop(id='3', x=3, y=3, epsg='epsg:27700'), Stop(id='4', x=7, y=5, epsg='epsg:27700')],
                  trips={'1': '1', '2': '2'}, arrival_offsets=['1', '2'], departure_offsets=['1', '2'])
    route_2 = Route(route_short_name='name_2', id='2',
                  mode='bus',
                  stops=[Stop(id='1', x=4, y=2, epsg='epsg:27700'), Stop(id='6', x=1, y=2, epsg='epsg:27700'),
                         Stop(id='7', x=3, y=3, epsg='epsg:27700'), Stop(id='4', x=7, y=5, epsg='epsg:27700')],
                  trips={'1': '1', '2': '2'}, arrival_offsets=['1', '2'], departure_offsets=['1', '2'])
    service = Service(id='service',
                      routes=[route_1, route_2])

    g = service.graph()

    assert_semantically_equal(dict(g.nodes(data=True)),
                              {'1': {'routes': ['2', '1'], 'id': '1', 'x': 4.0, 'y': 2.0, 'epsg': 'epsg:27700',
                                     'lat': 49.76682779861249, 'lon': -7.557106577683727, 's2_id': 5205973754090531959,
                                     'additional_attributes': [], 'services': ['service']},
                               '6': {'routes': ['2'], 'id': '6', 'x': 1.0, 'y': 2.0, 'epsg': 'epsg:27700',
                                     'lat': 49.766825803756994, 'lon': -7.557148039524952, 's2_id': 5205973754090365183,
                                     'additional_attributes': [], 'services': ['service']},
                               '7': {'routes': ['2'], 'id': '7', 'x': 3.0, 'y': 3.0, 'epsg': 'epsg:27700',
                                     'lat': 49.76683608549253, 'lon': -7.557121424907424, 's2_id': 5205973754090203369,
                                     'additional_attributes': [], 'services': ['service']},
                               '4': {'routes': ['2', '1'], 'id': '4', 'x': 7.0, 'y': 5.0, 'epsg': 'epsg:27700',
                                     'lat': 49.766856648946295, 'lon': -7.5570681956375, 's2_id': 5205973754097123809,
                                     'additional_attributes': [], 'services': ['service']},
                               '2': {'routes': ['1'], 'id': '2', 'x': 1.0, 'y': 2.0, 'epsg': 'epsg:27700',
                                     'lat': 49.766825803756994, 'lon': -7.557148039524952, 's2_id': 5205973754090365183,
                                     'additional_attributes': [], 'services': ['service']},
                               '3': {'routes': ['1'], 'id': '3', 'x': 3.0, 'y': 3.0, 'epsg': 'epsg:27700',
                                     'lat': 49.76683608549253, 'lon': -7.557121424907424, 's2_id': 5205973754090203369,
                                     'additional_attributes': [], 'services': ['service']}})
    assert_semantically_equal(list(g.edges), [('1', '6'), ('6', '7'), ('7', '4'), ('1', '2'), ('2', '3'), ('3', '4')])
    assert 'Service' in g.name


def test_is_strongly_connected_with_strongly_connected_service(strongly_connected_service):
    assert strongly_connected_service.is_strongly_connected()


def test_is_strongly_connected_with_not_strongly_connected_service(service):
    assert not service.is_strongly_connected()


def test_has_self_loops_with_self_has_self_looping_service(self_looping_route):
    s = Service(id='1', routes=[self_looping_route])
    assert s.has_self_loops()


def test_has_self_loops_returns_self_looping_stops(self_looping_route):
    s = Service(id='1', routes=[self_looping_route])
    loop_nodes = s.has_self_loops()
    assert loop_nodes == ['1']


def test_has_self_loops_with_non_looping_route(service):
    assert not service.has_self_loops()


def test_validity_of_routes(self_looping_route, route):
    s = Service(id='1', routes=[self_looping_route, route])
    assert s.validity_of_routes() == [False, True]


def test_has_valid_routes(self_looping_route, route):
    s = Service(id='1', routes=[self_looping_route, route])
    assert not s.has_valid_routes()


def test_has_valid_routes_with_only_valid_routes(route):
    s = Service(id='1', routes=[route, route])
    assert s.has_valid_routes()


def test_invalid_routes_shows_invalid_routes(self_looping_route, route):
    s = Service(id='1', routes=[self_looping_route, route])
    assert s.invalid_routes() == [self_looping_route]


def test_unique_indexing_of_with_uniquely_indexed_service(service):
    assert service.has_uniquely_indexed_routes()


def test_has_id(service):
    assert service.has_id()


def test_is_valid_with_valid_service(service):
    assert service.is_valid_service()


def test_is_valid_with_looping_route(self_looping_route, route):
    s = Service(id='1', routes=[self_looping_route, route])
    assert not s.is_valid_service()


def test_is_valid_with_non_network_route(service):
    service.routes['1'].route = []
    service.routes['2'].route = []
    assert not service.is_valid_service()

