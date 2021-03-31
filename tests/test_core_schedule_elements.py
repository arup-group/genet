import pytest
from networkx import Graph, DiGraph, set_node_attributes
from genet.schedule_elements import Schedule, Service, Route, Stop, verify_graph_schema
from genet.exceptions import ServiceIndexError, RouteIndexError, ScheduleElementGraphSchemaError
from tests.fixtures import assert_semantically_equal


def assert_all_elements_share_graph(elem):
    if isinstance(elem, Schedule):
        master_graph = id(elem.graph())
        for service in elem.services():
            assert master_graph == id(service._graph)
        for route in elem.routes():
            assert master_graph == id(route._graph)
    elif isinstance(elem, Service):
        master_graph = id(elem.graph())
        for route in elem.routes():
            assert master_graph == id(route._graph)


@pytest.fixture()
def schedule():
    return Schedule(epsg='epsg:27700', services=[
        Service(id='service1',
                routes=[
                    Route(id='1', route_short_name='route1', mode='bus',
                          stops=[
                              Stop(id='0', x=529455.7452394223, y=182401.37630677427, epsg='epsg:27700', linkRefId='0'),
                              Stop(id='1', x=529350.7866124967, y=182388.0201078112, epsg='epsg:27700', linkRefId='1')],
                          trips={'trip_id': ['route1_04:40:00'], 'trip_departure_time': ['04:40:00'],
                                 'vehicle_id': ['veh_0_bus']},
                          arrival_offsets=['00:00:00', '00:02:00'],
                          departure_offsets=['00:00:00', '00:02:00'],
                          route=['0', '1']),
                    Route(id='2', route_short_name='route2', mode='bus',
                          stops=[
                              Stop(id='1', x=529455.7452394223, y=182401.37630677427, epsg='epsg:27700', linkRefId='1'),
                              Stop(id='2', x=529350.7866124967, y=182388.0201078112, epsg='epsg:27700', linkRefId='2')],
                          trips={'trip_id': ['route2_05:40:00'], 'trip_departure_time': ['05:40:00'],
                                 'vehicle_id': ['veh_1_bus']},
                          arrival_offsets=['00:00:00', '00:03:00'],
                          departure_offsets=['00:00:00', '00:05:00'],
                          route=['1', '2'])
                ]),
        Service(id='service2',
                routes=[
                    Route(id='3', route_short_name='route3', mode='rail',
                          stops=[
                              Stop(id='3', x=529455.7452394223, y=182401.37630677427, epsg='epsg:27700', linkRefId='3'),
                              Stop(id='4', x=529350.7866124967, y=182388.0201078112, epsg='epsg:27700', linkRefId='4')],
                          trips={'trip_id': ['route3_04:40:00'], 'trip_departure_time': ['04:40:00'],
                                 'vehicle_id': ['veh_2_rail']},
                          arrival_offsets=['00:00:00', '00:02:00'],
                          departure_offsets=['00:00:00', '00:02:00'],
                          route=['3', '4']),
                    Route(id='4', route_short_name='route4', mode='rail',
                          stops=[
                              Stop(id='4', x=529455.7452394223, y=182401.37630677427, epsg='epsg:27700', linkRefId='4'),
                              Stop(id='5', x=529350.7866124967, y=182388.0201078112, epsg='epsg:27700', linkRefId='5')],
                          trips={'trip_id': ['route4_05:40:00'], 'trip_departure_time': ['05:40:00'],
                                 'vehicle_id': ['veh_3_rail']},
                          arrival_offsets=['00:00:00', '00:03:00'],
                          departure_offsets=['00:00:00', '00:05:00'],
                          route=['4', '5'])
                ])
    ])


@pytest.fixture()
def schedule_graph():
    graph = DiGraph(
        name='Schedule Graph',
        routes={'4': {'ordered_stops': ['4', '5'], 'route_short_name': 'route4', 'mode': 'rail',
                      'trips': {'trip_id': ['route4_05:40:00'], 'trip_departure_time': ['05:40:00'],
                                'vehicle_id': ['veh_0_bus']},
                      'arrival_offsets': ['00:00:00', '00:03:00'],
                      'departure_offsets': ['00:00:00', '00:05:00'], 'route_long_name': '', 'id': '4',
                      'route': ['4', '5'], 'await_departure': []},
                '3': {'ordered_stops': ['3', '4'], 'route_short_name': 'route3', 'mode': 'rail',
                      'trips': {'trip_id': ['route3_04:40:00'], 'trip_departure_time': ['04:40:00'],
                                'vehicle_id': ['veh_1_bus']},
                      'arrival_offsets': ['00:00:00', '00:02:00'],
                      'departure_offsets': ['00:00:00', '00:02:00'], 'route_long_name': '', 'id': '3',
                      'route': ['3', '4'], 'await_departure': []},
                '1': {'ordered_stops': ['0', '1'], 'route_short_name': 'route1', 'mode': 'bus',
                      'trips': {'trip_id': ['route1_04:40:00'], 'trip_departure_time': ['04:40:00'],
                                'vehicle_id': ['veh_2_bus']},
                      'arrival_offsets': ['00:00:00', '00:02:00'],
                      'departure_offsets': ['00:00:00', '00:02:00'], 'route_long_name': '', 'id': '1',
                      'route': ['0', '1'], 'await_departure': []},
                '2': {'ordered_stops': ['1', '2'], 'route_short_name': 'route2', 'mode': 'bus',
                      'trips': {'trip_id': ['route2_05:40:00'], 'trip_departure_time': ['05:40:00'],
                                'vehicle_id': ['veh_3_bus']},
                      'arrival_offsets': ['00:00:00', '00:03:00'],
                      'departure_offsets': ['00:00:00', '00:05:00'], 'route_long_name': '', 'id': '2',
                      'route': ['1', '2'], 'await_departure': []}},
        services={'service2': {'id': 'service2', 'name': 'route3'},
                  'service1': {'id': 'service1', 'name': 'route1'}},
        route_to_service_map={'1': 'service1', '2': 'service1', '3': 'service2', '4': 'service2'},
        service_to_route_map={'service1': ['1', '2'], 'service2': ['3', '4']},
        crs={'init': 'epsg:27700'}
    )
    nodes = {'4': {'services': ['service2'], 'routes': ['3', '4'], 'id': '4', 'x': 529350.7866124967,
                   'y': 182388.0201078112, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.52560003323918,
                   'lon': -0.13682698708848137, 's2_id': 5221390668558830581,
                   'additional_attributes': {'linkRefId'}, 'linkRefId': '4'},
             '5': {'services': ['service2'], 'routes': ['4'], 'id': '5', 'x': 529350.7866124967,
                   'y': 182388.0201078112, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.52560003323918,
                   'lon': -0.13682698708848137, 's2_id': 5221390668558830581,
                   'additional_attributes': {'linkRefId'}, 'linkRefId': '5'},
             '3': {'services': ['service2'], 'routes': ['3'], 'id': '3', 'x': 529455.7452394223,
                   'y': 182401.37630677427, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.525696033239186,
                   'lon': -0.13530998708775874, 's2_id': 5221390668020036699,
                   'additional_attributes': {'linkRefId'}, 'linkRefId': '3'},
             '1': {'services': ['service1'], 'routes': ['2', '1'], 'id': '1', 'x': 529350.7866124967,
                   'y': 182388.0201078112, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.52560003323918,
                   'lon': -0.13682698708848137, 's2_id': 5221390668558830581,
                   'additional_attributes': {'linkRefId'}, 'linkRefId': '1'},
             '2': {'services': ['service1'], 'routes': ['2'], 'id': '2', 'x': 529350.7866124967,
                   'y': 182388.0201078112, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.52560003323918,
                   'lon': -0.13682698708848137, 's2_id': 5221390668558830581,
                   'additional_attributes': {'linkRefId'}, 'linkRefId': '2'},
             '0': {'services': ['service1'], 'routes': ['1'], 'id': '0', 'x': 529455.7452394223,
                   'y': 182401.37630677427, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.525696033239186,
                   'lon': -0.13530998708775874, 's2_id': 5221390668020036699,
                   'additional_attributes': {'linkRefId'}, 'linkRefId': '0'}}
    edges = [('4', '5', {'services': ['service2'], 'routes': ['4'], 'modes': ['rail']}),
             ('3', '4', {'services': ['service2'], 'routes': ['3'], 'modes': ['rail']}),
             ('1', '2', {'services': ['service1'], 'routes': ['2'], 'modes': ['bus']}),
             ('0', '1', {'services': ['service1'], 'routes': ['1'], 'modes': ['bus']})]
    graph.add_nodes_from(nodes)
    graph.add_edges_from(edges)
    set_node_attributes(graph, nodes)
    return graph


def test_all_elements_in_schedule_share_the_same_graph(schedule):
    assert_all_elements_share_graph(schedule)


def test_generating_reference_nodes_for_route(schedule):
    reference_nodes_from_graph = schedule.route_reference_nodes(route_id='1')
    reference_nodes_from_object = schedule.route('1').reference_nodes()
    assert reference_nodes_from_graph == reference_nodes_from_object
    assert reference_nodes_from_graph == {'1', '0'}


def test_generating_reference_edges_for_route(schedule):
    reference_edges_from_graph = schedule.route_reference_edges(route_id='1')
    reference_edges_from_object = schedule.route('1').reference_edges()
    assert reference_edges_from_graph == reference_edges_from_object
    assert reference_edges_from_graph == {('0', '1')}


def test_generating_reference_nodes_for_service(schedule):
    reference_nodes_from_graph = schedule.service_reference_nodes(service_id='service1')
    reference_nodes_from_object = schedule['service1'].reference_nodes()
    assert reference_nodes_from_graph == reference_nodes_from_object
    assert reference_nodes_from_graph == {'2', '1', '0'}


def test_generating_reference_edges_for_service(schedule):
    reference_edges_from_graph = schedule.service_reference_edges(service_id='service1')
    reference_edges_from_object = schedule['service1'].reference_edges()
    assert reference_edges_from_graph == reference_edges_from_object
    assert reference_edges_from_graph == {('0', '1'), ('1', '2')}


@pytest.fixture()
def basic_service():
    return Service(id='service1',
                      routes=[
                          Route(id='1', route_short_name='route1', mode='bus',
                                stops=[
                                    Stop('0', x=1, y=1, epsg='epsg:4326'),
                                    Stop('1', x=2, y=2, epsg='epsg:4326'),
                                    Stop('2', x=3, y=3, epsg='epsg:4326')
                                ],
                                trips={
                                    'trip_id': ['route1_04:40:00'],
                                    'trip_departure_time': ['04:40:00'],
                                    'vehicle_id': ['veh_bus_1']
                                },
                                arrival_offsets=['00:00:00', '00:02:00'],
                                departure_offsets=['00:00:00', '00:02:00'],
                                route=[]),
                          Route(id='2', route_short_name='route2', mode='bus',
                                stops=[
                                    Stop('1', x=2, y=2, epsg='epsg:4326'),
                                    Stop('2', x=3, y=3, epsg='epsg:4326')
                                ],
                                trips={
                                    'trip_id': ['route2_05:40:00'],
                                    'trip_departure_time': ['05:40:00'],
                                    'vehicle_id': ['veh_bus_2']
                                },
                                arrival_offsets=['00:00:00', '00:03:00'],
                                departure_offsets=['00:00:00', '00:05:00'],
                                route=[]),
                          Route(id='3', route_short_name='route3', mode='bus',
                                stops=[
                                    Stop('0', x=1, y=1, epsg='epsg:4326'),
                                    Stop('1', x=2, y=2, epsg='epsg:4326'),
                                ],
                                trips={
                                    'trip_id': ['route1_04:40:00'],
                                    'trip_departure_time': ['04:40:00'],
                                    'vehicle_id': ['veh_bus_3']
                                },
                                arrival_offsets=['00:00:00', '00:02:00'],
                                departure_offsets=['00:00:00', '00:02:00'],
                                route=[]),
                          Route(id='4', route_short_name='route4', mode='bus',
                                stops=[
                                    Stop('2', x=3, y=3, epsg='epsg:4326'),
                                    Stop('1', x=2, y=2, epsg='epsg:4326'),
                                    Stop('0', x=1, y=1, epsg='epsg:4326')
                                ],
                                trips={
                                    'trip_id': ['route2_05:40:00'],
                                    'trip_departure_time': ['05:40:00'],
                                    'vehicle_id': ['veh_bus_4']
                                },
                                arrival_offsets=['00:00:00', '00:03:00'],
                                departure_offsets=['00:00:00', '00:05:00'],
                                route=[])
                      ])


def test_splitting_service_on_direction_finds_two_distinct_directions(basic_service):
    service_split = basic_service.split_by_direction()
    assert_semantically_equal(service_split,
                              {'North-East Bound': ['1', '2', '3'],
                               'South-West Bound': ['4']})


def test_splitting_service_graph_finds_two_distinct_directions(basic_service):
    routes, graph_groups = basic_service.split_graph()
    assert routes == [{'1', '2', '3'}, {'4'}]
    assert graph_groups == [{('0', '1'), ('1', '2')}, {('1', '0'), ('2', '1')}]


@pytest.fixture()
def service_with_separated_routes():
    return Service(id='service1',
                      routes=[
                          Route(id='1', route_short_name='route1', mode='bus',
                                stops=[
                                    Stop('0', x=0, y=0, epsg='epsg:4326'),
                                    Stop('1', x=0, y=1, epsg='epsg:4326'),
                                ],
                                trips={
                                    'trip_id': ['route1_04:40:00'],
                                    'trip_departure_time': ['04:40:00'],
                                    'vehicle_id': ['veh_bus_1']
                                },
                                arrival_offsets=['00:00:00', '00:02:00'],
                                departure_offsets=['00:00:00', '00:02:00'],
                                route=[]),
                          Route(id='2', route_short_name='route2', mode='bus',
                                stops=[
                                    Stop('2', x=0, y=2, epsg='epsg:4326'),
                                    Stop('3', x=0, y=3, epsg='epsg:4326'),
                                ],
                                trips={
                                    'trip_id': ['route2_05:40:00'],
                                    'trip_departure_time': ['05:40:00'],
                                    'vehicle_id': ['veh_bus_2']
                                },
                                arrival_offsets=['00:00:00', '00:03:00'],
                                departure_offsets=['00:00:00', '00:05:00'],
                                route=[]),
                          Route(id='3', route_short_name='route3', mode='bus',
                                stops=[
                                    Stop('0', x=0, y=0, epsg='epsg:4326'),
                                    Stop('1', x=0, y=1, epsg='epsg:4326'),
                                    Stop('2', x=0, y=2, epsg='epsg:4326'),
                                    Stop('3', x=0, y=3, epsg='epsg:4326')
                                ],
                                trips={
                                    'trip_id': ['route1_04:40:00'],
                                    'trip_departure_time': ['04:40:00'],
                                    'vehicle_id': ['veh_bus_3']
                                },
                                arrival_offsets=['00:00:00', '00:02:00'],
                                departure_offsets=['00:00:00', '00:02:00'],
                                route=['0', '1', '2', '3'])
                      ])


def test_splitting_service_on_direction_combines_separated_routes(service_with_separated_routes):
    service_split = service_with_separated_routes.split_by_direction()
    assert_semantically_equal(service_split, {'North Bound': ['1', '2', '3']})


def test_splitting_service_graph_combines_separated_routes(service_with_separated_routes):
    routes, graph_groups = service_with_separated_routes.split_graph()
    assert routes == [{'2', '1', '3'}]
    assert graph_groups == [{('1', '2'), ('2', '3'), ('0', '1')}]


@pytest.fixture()
def service_with_loopy_routes():
    return Service(id='service1',
                      routes=[
                          Route(id='1_dir_1', route_short_name='route1', mode='bus',
                                stops=[
                                    Stop('A', x=1, y=0, epsg='epsg:4326'),
                                    Stop('B', x=0, y=-1, epsg='epsg:4326'),
                                    Stop('C', x=-1, y=0, epsg='epsg:4326'),
                                    Stop('D', x=0, y=1, epsg='epsg:4326'),
                                    Stop('A', x=1, y=0, epsg='epsg:4326'),
                                    ],
                                trips={
                                    'trip_id': ['route1_04:40:00'],
                                    'trip_departure_time': ['04:40:00'],
                                    'vehicle_id': ['veh_bus_1']
                                },
                                arrival_offsets=['', '', ''],
                                departure_offsets=['', '', '']),
                          Route(id='2_dir_1', route_short_name='route2', mode='bus',
                                stops=[
                                    Stop('A', x=1, y=0, epsg='epsg:4326'),
                                    Stop('C', x=-1, y=0, epsg='epsg:4326'),
                                    Stop('D', x=0, y=1, epsg='epsg:4326'),
                                    Stop('A', x=1, y=0, epsg='epsg:4326'),
                                ],
                                trips={
                                    'trip_id': ['route2_05:40:00'],
                                    'trip_departure_time': ['05:40:00'],
                                    'vehicle_id': ['veh_bus_2']
                                },
                                arrival_offsets=['', '', ''],
                                departure_offsets=['', '', '']),
                          Route(id='3_dir_2', route_short_name='route3', mode='bus',
                                stops=[
                                    Stop('A', x=1, y=0, epsg='epsg:4326'),
                                    Stop('D', x=0, y=1, epsg='epsg:4326'),
                                    Stop('C', x=-1, y=0, epsg='epsg:4326'),
                                    Stop('B', x=0, y=-1, epsg='epsg:4326'),
                                    Stop('A', x=1, y=0, epsg='epsg:4326'),
                                ],
                                trips={
                                    'trip_id': ['route1_04:40:00'],
                                    'trip_departure_time': ['04:40:00'],
                                    'vehicle_id': ['veh_bus_3']
                                },
                                arrival_offsets=['', '', ''],
                                departure_offsets=['', '', '']),
                          Route(id='4_dir_2', route_short_name='route4', mode='bus',
                                stops=[
                                    Stop('A', x=1, y=0, epsg='epsg:4326'),
                                    Stop('D', x=0, y=1, epsg='epsg:4326'),
                                    Stop('C', x=-1, y=0, epsg='epsg:4326'),
                                    Stop('A', x=1, y=0, epsg='epsg:4326'),
                                ],
                                trips={
                                    'trip_id': ['route1_04:40:00'],
                                    'trip_departure_time': ['04:40:00'],
                                    'vehicle_id': ['veh_bus_4']
                                },
                                arrival_offsets=['', '', ''],
                                departure_offsets=['', '', '']),
                      ])

def test_splitting_service_on_direction_with_loopy_routes(service_with_loopy_routes):
    service_split = service_with_loopy_routes.split_by_direction()
    # loopy services are a bit disappointing right now, can't win them all I guess :(
    assert_semantically_equal(service_split,
                              {'South-West Bound': ['1_dir_1'],
                               'West Bound': ['2_dir_1'],
                               'North-West Bound': ['3_dir_2', '4_dir_2']})


def test_splitting_service_graph_with_loopy_routes(service_with_loopy_routes):
    routes, graph_groups = service_with_loopy_routes.split_graph()
    assert routes == [{'1_dir_1', '2_dir_1'}, {'3_dir_2', '4_dir_2'}]
    assert graph_groups == [{('C', 'D'), ('A', 'B'), ('D', 'A'), ('B', 'C'), ('A', 'C')},
                            {('A', 'D'), ('C', 'B'), ('D', 'C'), ('B', 'A'), ('C', 'A')}]


@pytest.fixture()
def service_with_routes_that_have_non_overlapping_graph_edges():
    return Service(id='service1',
                      routes=[
                          Route(id='1_dir_1', route_short_name='route1', mode='rail',
                                stops=[
                                    Stop('A', x=0, y=1, epsg='epsg:4326'),
                                    Stop('B', x=0, y=2, epsg='epsg:4326'),
                                    Stop('C', x=0, y=3, epsg='epsg:4326'),
                                    Stop('D', x=0, y=4, epsg='epsg:4326')
                                    ],
                                trips={
                                    'trip_id': ['route1_04:40:00'],
                                    'trip_departure_time': ['04:40:00'],
                                    'vehicle_id': ['veh_bus_1']
                                },
                                arrival_offsets=['', '', ''],
                                departure_offsets=['', '', '']),
                          Route(id='2_dir_1', route_short_name='route2', mode='rail',
                                stops=[
                                    Stop('A', x=0, y=1, epsg='epsg:4326'),
                                    Stop('C', x=0, y=3, epsg='epsg:4326')
                                ],
                                trips={
                                    'trip_id': ['route2_05:40:00'],
                                    'trip_departure_time': ['05:40:00'],
                                    'vehicle_id': ['veh_bus_2']
                                },
                                arrival_offsets=['', '', ''],
                                departure_offsets=['', '', '']),
                          Route(id='3_dir_2', route_short_name='route3', mode='rail',
                                stops=[
                                    Stop('C', x=0, y=3, epsg='epsg:4326'),
                                    Stop('B', x=0, y=2, epsg='epsg:4326'),
                                    Stop('A', x=0, y=1, epsg='epsg:4326')
                                ],
                                trips={
                                    'trip_id': ['route1_04:40:00'],
                                    'trip_departure_time': ['04:40:00'],
                                    'vehicle_id': ['veh_bus_3']
                                },
                                arrival_offsets=['', '', ''],
                                departure_offsets=['', '', '']),
                          Route(id='4_dir_2', route_short_name='route4', mode='rail',
                                stops=[
                                    Stop('C', x=0, y=3, epsg='epsg:4326'),
                                    Stop('A', x=0, y=1, epsg='epsg:4326')
                                ],
                                trips={
                                    'trip_id': ['route1_04:40:00'],
                                    'trip_departure_time': ['04:40:00'],
                                    'vehicle_id': ['veh_bus_4']
                                },
                                arrival_offsets=['', '', ''],
                                departure_offsets=['', '', '']),
                      ])

def test_splitting_service_on_direction_with_non_overlapping_graph_edges_produces_two_directions(service_with_routes_that_have_non_overlapping_graph_edges):
    service_split = service_with_routes_that_have_non_overlapping_graph_edges.split_by_direction()
    assert_semantically_equal(service_split,
                              {'North Bound': ['1_dir_1', '2_dir_1'],
                               'South Bound': ['3_dir_2', '4_dir_2']})


def test_splitting_service_graph_with_non_overlapping_graph_edges_produces_two_directions(service_with_routes_that_have_non_overlapping_graph_edges):
    routes, graph_groups = service_with_routes_that_have_non_overlapping_graph_edges.split_graph()
    assert routes == [{'1_dir_1', '2_dir_1'}, {'3_dir_2', '4_dir_2'}]
    assert graph_groups == [{('A', 'C'), ('C', 'D'), ('B', 'C'), ('A', 'B')},
                            {('B', 'A'), ('C', 'B'), ('C', 'A')}]


@pytest.fixture()
def service_edge_case_loopy_and_non_overlapping_graph():
    # inspired by district and circle LU lines
    return Service(id='service1',
                      routes=[
                          Route(id='1_dir_1', route_short_name='route1', mode='rail',
                                stops=[
                                    Stop('A', x=-1, y=0, epsg='epsg:4326'),
                                    Stop('C', x=-3, y=0, epsg='epsg:4326')
                                ],
                                trips={
                                    'trip_id': ['route1_04:40:00'],
                                    'trip_departure_time': ['04:40:00'],
                                    'vehicle_id': ['veh_bus_1']
                                },
                                arrival_offsets=['', '', ''],
                                departure_offsets=['', '', '']),
                          Route(id='2_dir_2', route_short_name='route2', mode='rail',
                                stops=[
                                    Stop('F', x=-6, y=0, epsg='epsg:4326'),
                                    Stop('A', x=-1, y=0, epsg='epsg:4326')
                                ],
                                trips={
                                    'trip_id': ['route2_05:40:00'],
                                    'trip_departure_time': ['05:40:00'],
                                    'vehicle_id': ['veh_bus_2']
                                },
                                arrival_offsets=['', '', ''],
                                departure_offsets=['', '', '']),
                          Route(id='3_dir_1', route_short_name='route3', mode='rail',
                                stops=[
                                    Stop('E', x=-5, y=0, epsg='epsg:4326'),
                                    Stop('F', x=-6, y=0, epsg='epsg:4326')
                                ],
                                trips={
                                    'trip_id': ['route1_04:40:00'],
                                    'trip_departure_time': ['04:40:00'],
                                    'vehicle_id': ['veh_bus_3']
                                },
                                arrival_offsets=['', '', ''],
                                departure_offsets=['', '', '']),
                          Route(id='4_dir_1', route_short_name='route4', mode='rail',
                                stops=[
                                    Stop('A', x=-1, y=0, epsg='epsg:4326'),
                                    Stop('B', x=-2, y=0, epsg='epsg:4326'),
                                    Stop('C', x=-3, y=0, epsg='epsg:4326'),
                                    Stop('D', x=-4, y=0, epsg='epsg:4326'),
                                    Stop('E', x=-5, y=0, epsg='epsg:4326')
                                ],
                                trips={
                                    'trip_id': ['route1_04:40:00'],
                                    'trip_departure_time': ['04:40:00'],
                                    'vehicle_id': ['veh_bus_4']
                                },
                                arrival_offsets=['', '', ''],
                                departure_offsets=['', '', '']),
                      ])

def test_splitting_service_edge_case_on_direction_results_in_two_directions(service_edge_case_loopy_and_non_overlapping_graph):
    service_split = service_edge_case_loopy_and_non_overlapping_graph.split_by_direction()
    assert_semantically_equal(service_split,
                              {'West Bound': ['1_dir_1', '3_dir_1', '4_dir_1'],
                               'East Bound': ['2_dir_2']})


# this one is a right mess, result varies based on order in with routes are specified.
@pytest.mark.xfail()
def test_splitting_service_edge_case_on_direction_results_in_two_directions(service_edge_case_loopy_and_non_overlapping_graph):
    routes, graph_groups = service_edge_case_loopy_and_non_overlapping_graph.split_graph()
    assert routes == [{'1_dir_1', '3_dir_1', '4_dir_1'}, {'2_dir_2'}]
    assert graph_groups == [{('A', 'C'), ('E', 'F'), ('C', 'D'), ('B', 'C'), ('D', 'E'), ('A', 'B')},
                            {('F', 'A')}]


def test_reindexing_route(schedule):
    r = schedule.route('1')
    assert set(schedule['service1'].route_ids()) == {'1', '2'}
    r.reindex('new_index_for_route_1')
    assert_all_elements_share_graph(schedule)
    assert r.id == 'new_index_for_route_1'
    for node in r.reference_nodes():
        assert 'new_index_for_route_1' in schedule._graph.nodes[node]['routes']
        assert not '1' in schedule._graph.nodes[node]['routes']
    assert schedule.route('new_index_for_route_1').id == 'new_index_for_route_1'
    assert set(schedule['service1'].route_ids()) == {'new_index_for_route_1', '2'}
    with pytest.raises(RouteIndexError) as e:
        schedule.route('1')
    assert 'not found' in str(e.value)


def test_reindexing_route_with_nonunique_index_throws_error(schedule):
    r = schedule.route('1')
    with pytest.raises(RouteIndexError) as e:
        r.reindex('2')
    assert 'already exists' in str(e.value)


def test_reindexing_service(schedule):
    s = schedule['service1']
    s.reindex('new_index_for_service1')
    assert_all_elements_share_graph(schedule)
    assert s.id == 'new_index_for_service1'
    for node in s.reference_nodes():
        assert 'new_index_for_service1' in schedule._graph.nodes[node]['services']
        assert not 'service1' in schedule._graph.nodes[node]['services']
    assert schedule['new_index_for_service1'].id == 'new_index_for_service1'
    with pytest.raises(ServiceIndexError) as e:
        schedule['service1']
    assert 'not found' in str(e.value)


def test_reindexing_service_with_nonunique_index_throws_error(schedule):
    s = schedule['service1']
    with pytest.raises(ServiceIndexError) as e:
        s.reindex('service2')
    assert 'already exists' in str(e.value)


def test_adding_schedules_retains_shared_graph(schedule):
    schedule_2 = Schedule(epsg='epsg:27700', services=[
        Service(id='service3',
                routes=[
                    Route(id='31', route_short_name='3route1', mode='bus',
                          stops=[
                              Stop(id='30', x=529455.7452394223, y=182401.37630677427, epsg='epsg:27700',
                                   linkRefId='0'),
                              Stop(id='31', x=529350.7866124967, y=182388.0201078112, epsg='epsg:27700',
                                   linkRefId='1')],
                          trips={'trip_id': ['route1_04:40:00'], 'trip_departure_time': ['04:40:00'],
                                 'vehicle_id': ['veh_0_bus']},
                          arrival_offsets=['00:00:00', '00:02:00'],
                          departure_offsets=['00:00:00', '00:02:00'],
                          route=['0', '1']),
                    Route(id='32', route_short_name='3route2', mode='bus',
                          stops=[
                              Stop(id='31', x=529455.7452394223, y=182401.37630677427, epsg='epsg:27700',
                                   linkRefId='1'),
                              Stop(id='32', x=529350.7866124967, y=182388.0201078112, epsg='epsg:27700',
                                   linkRefId='2')],
                          trips={'trip_id': ['route2_05:40:00'], 'trip_departure_time': ['05:40:00'],
                                 'vehicle_id': ['veh_1_bus']},
                          arrival_offsets=['00:00:00', '00:03:00'],
                          departure_offsets=['00:00:00', '00:05:00'],
                          route=['1', '2'])
                ])])

    schedule.add(schedule_2)
    assert_all_elements_share_graph(schedule)


def test_lesser_element_graphs_inherit_master_graphs_attributes(schedule):
    service = schedule['service1']
    service_graph = service.graph()

    assert schedule.graph().name == service_graph.name
    assert schedule.graph().graph['crs'] == service_graph.graph['crs']


def test_modes(schedule):
    assert set(schedule.modes()) == {'bus', 'rail'}


def test_mode_map_for_schedule(schedule):
    assert_semantically_equal(schedule.mode_graph_map(),
                              {'bus': {('1', '2'), ('0', '1')}, 'rail': {('3', '4'), ('4', '5')}})


def test_mode_map_for_service(schedule):
    assert_semantically_equal(schedule['service1'].mode_graph_map(),
                              {'bus': {('1', '2'), ('0', '1')}})


def test_mode_map_for_route(schedule):
    assert_semantically_equal(schedule.route('1').mode_graph_map(),
                              {'bus': {('0', '1')}})


def test_schedule_subgraph(schedule):
    sub_g = schedule.subgraph({('1', '2'), ('0', '1')})

    assert_semantically_equal(sub_g.edges(data=True)._adjdict,
                              {'2': {}, '0': {'1': {'services': {'service1'}, 'routes': {'1'}}},
                               '1': {'2': {'services': {'service1'}, 'routes': {'2'}}}})

    assert_semantically_equal(dict(sub_g.nodes(data=True)),
                              {'0': {'services': {'service1'}, 'routes': {'1'}, 'id': '0', 'x': 529455.7452394223,
                                     'y': 182401.37630677427, 'epsg': 'epsg:27700', 'name': '',
                                     'lat': 51.525696033239186, 'lon': -0.13530998708775874,
                                     's2_id': 5221390668020036699, 'additional_attributes': {'linkRefId'},
                                     'linkRefId': '0'},
                               '1': {'services': {'service1'}, 'routes': {'1', '2'}, 'id': '1', 'x': 529350.7866124967,
                                     'y': 182388.0201078112, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.52560003323918,
                                     'lon': -0.13682698708848137, 's2_id': 5221390668558830581,
                                     'additional_attributes': {'linkRefId'}, 'linkRefId': '1'},
                               '2': {'services': {'service1'}, 'routes': {'2'}, 'id': '2', 'x': 529350.7866124967,
                                     'y': 182388.0201078112, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.52560003323918,
                                     'lon': -0.13682698708848137, 's2_id': 5221390668558830581,
                                     'additional_attributes': {'linkRefId'}, 'linkRefId': '2'}})


def test_service_subgraph(schedule):
    sub_g = schedule['service1'].subgraph({('0', '1')})

    assert_semantically_equal(sub_g.edges(data=True)._adjdict,
                              {'0': {'1': {'services': {'service1'}, 'routes': {'1'}}}, '1': {}})

    assert_semantically_equal(dict(sub_g.nodes(data=True)),
                              {'0': {'services': {'service1'}, 'routes': {'1'}, 'id': '0', 'x': 529455.7452394223,
                                     'y': 182401.37630677427, 'epsg': 'epsg:27700', 'name': '',
                                     'lat': 51.525696033239186, 'lon': -0.13530998708775874,
                                     's2_id': 5221390668020036699, 'additional_attributes': {'linkRefId'},
                                     'linkRefId': '0'},
                               '1': {'services': {'service1'}, 'routes': {'1', '2'}, 'id': '1', 'x': 529350.7866124967,
                                     'y': 182388.0201078112, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.52560003323918,
                                     'lon': -0.13682698708848137, 's2_id': 5221390668558830581,
                                     'additional_attributes': {'linkRefId'}, 'linkRefId': '1'}})


def test_route_subgraph(schedule):
    sub_g = schedule.route('1').subgraph({('0', '1')})

    assert_semantically_equal(sub_g.edges(data=True)._adjdict,
                              {'0': {'1': {'services': {'service1'}, 'routes': {'1'}}}, '1': {}})

    assert_semantically_equal(dict(sub_g.nodes(data=True)),
                              {'1': {'services': {'service1'}, 'routes': {'2', '1'}, 'id': '1', 'x': 529350.7866124967,
                                     'y': 182388.0201078112, 'epsg': 'epsg:27700', 'lat': 51.52560003323918,
                                     'lon': -0.13682698708848137, 's2_id': 5221390668558830581,
                                     'additional_attributes': {'linkRefId'}, 'linkRefId': '1', 'name': ''},
                               '0': {'services': {'service1'}, 'routes': {'1'}, 'id': '0', 'x': 529455.7452394223,
                                     'y': 182401.37630677427, 'epsg': 'epsg:27700', 'lat': 51.525696033239186,
                                     'lon': -0.13530998708775874, 's2_id': 5221390668020036699,
                                     'additional_attributes': {'linkRefId'}, 'linkRefId': '0', 'name': ''}})


def test_building_route_from_graph(schedule_graph):
    r = Route(_graph=schedule_graph, **schedule_graph.graph['routes']['1'])
    assert r.reference_nodes() == {'1', '0'}
    assert r.reference_edges() == {('0', '1')}


def test_building_service_from_graph(schedule_graph):
    s = Service(_graph=schedule_graph, **schedule_graph.graph['services']['service1'])
    assert s.reference_nodes() == {'1', '2', '0'}
    assert s.reference_edges() == {('1', '2'), ('0', '1')}


def test_building_schedule_from_graph(schedule_graph):
    s = Schedule(_graph=schedule_graph)
    assert s.reference_nodes() == {'4', '5', '3', '1', '2', '0'}
    assert s.reference_edges() == {('4', '5'), ('3', '4'), ('1', '2'), ('0', '1')}


def test_instantiating_route_with_new_attributes(schedule):
    schedule.apply_attributes_to_routes({
        '1': {'new_attribute': 'value'}
    })
    r = schedule.route('1')
    assert r.new_attribute == 'value'


def test_instantiating_service_with_new_attributes(schedule):
    schedule.apply_attributes_to_services({
        'service1': {'new_attribute': 'value'}
    })
    s = schedule['service1']
    assert s.new_attribute == 'value'


def test_graph_schema_verification_throws_error_when_given_wrong_type_object():
    g = {}

    with pytest.raises(ScheduleElementGraphSchemaError) as e:
        verify_graph_schema(g)
    assert 'The graph for a schedule element needs to be a networkx.DiGraph' in str(e.value)


def test_graph_schema_verification_throws_error_when_attributes_missing_from_stops():
    g = DiGraph()
    g.add_node('1', x=1, y=2)

    with pytest.raises(ScheduleElementGraphSchemaError) as e:
        verify_graph_schema(g)
    assert 'missing the following attributes' in str(e.value)


def test_graph_schema_verification_throws_error_when_routes_missing():
    g = DiGraph()
    g.add_node('1', x=1, y=2, id='1', epsg='epsg:27700')

    with pytest.raises(ScheduleElementGraphSchemaError) as e:
        verify_graph_schema(g)
    assert 'Graph is missing `routes` attribute' in str(e.value)


def test_graph_schema_verification_throws_error_when_missing_route_attributes():
    g = DiGraph()
    g.add_node('1', x=1, y=2, id='1', epsg='epsg:27700')
    g.graph['routes'] = {'1': {}}

    with pytest.raises(ScheduleElementGraphSchemaError) as e:
        verify_graph_schema(g)
    assert 'missing the following attributes:' in str(e.value)


def test_graph_schema_verification_throws_error_when_services_missing():
    g = DiGraph()
    g.add_node('1', x=1, y=2, id='1', epsg='epsg:27700')
    g.graph['routes'] = {'1': {'arrival_offsets': [], 'ordered_stops': [], 'route_short_name': '', 'mode': '',
                               'departure_offsets': [], 'trips': {}}}

    with pytest.raises(ScheduleElementGraphSchemaError) as e:
        verify_graph_schema(g)
    assert 'Graph is missing `services` attribute' in str(e.value)


def test_graph_schema_verification_throws_error_when_missing_service_attributes():
    g = DiGraph()
    g.add_node('1', x=1, y=2, id='1', epsg='epsg:27700')
    g.graph['routes'] = {'1': {'arrival_offsets': [], 'ordered_stops': [], 'route_short_name': '', 'mode': '',
                               'departure_offsets': [], 'trips': {}}}
    g.graph['services'] = {'1': {}}

    with pytest.raises(ScheduleElementGraphSchemaError) as e:
        verify_graph_schema(g)
    assert 'missing the following attributes:' in str(e.value)
