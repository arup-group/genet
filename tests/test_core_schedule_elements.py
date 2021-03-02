import pytest
from networkx import Graph, DiGraph, set_node_attributes
from genet.schedule_elements import Schedule, Service, Route, Stop, verify_graph_schema
from genet.exceptions import ServiceIndexError, RouteIndexError, ScheduleElementGraphSchemaError
from genet.inputs_handler import gtfs_reader
from tests.fixtures import assert_semantically_equal, correct_schedule_dict_from_test_gtfs, \
    correct_stopdb_from_test_gtfs


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
                          trips={'route1_04:40:00': '04:40:00'},
                          arrival_offsets=['00:00:00', '00:02:00'],
                          departure_offsets=['00:00:00', '00:02:00'],
                          route=['0', '1']),
                    Route(id='2', route_short_name='route2', mode='bus',
                          stops=[
                              Stop(id='1', x=529455.7452394223, y=182401.37630677427, epsg='epsg:27700', linkRefId='1'),
                              Stop(id='2', x=529350.7866124967, y=182388.0201078112, epsg='epsg:27700', linkRefId='2')],
                          trips={'route2_05:40:00': '05:40:00'},
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
                          trips={'route3_04:40:00': '04:40:00'},
                          arrival_offsets=['00:00:00', '00:02:00'],
                          departure_offsets=['00:00:00', '00:02:00'],
                          route=['3', '4']),
                    Route(id='4', route_short_name='route4', mode='rail',
                          stops=[
                              Stop(id='4', x=529455.7452394223, y=182401.37630677427, epsg='epsg:27700', linkRefId='4'),
                              Stop(id='5', x=529350.7866124967, y=182388.0201078112, epsg='epsg:27700', linkRefId='5')],
                          trips={'route4_05:40:00': '05:40:00'},
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
                      'trips': {'route4_05:40:00': '05:40:00'},
                      'arrival_offsets': ['00:00:00', '00:03:00'],
                      'departure_offsets': ['00:00:00', '00:05:00'], 'route_long_name': '', 'id': '4',
                      'route': ['4', '5'], 'await_departure': []},
                '3': {'ordered_stops': ['3', '4'], 'route_short_name': 'route3', 'mode': 'rail',
                      'trips': {'route3_04:40:00': '04:40:00'},
                      'arrival_offsets': ['00:00:00', '00:02:00'],
                      'departure_offsets': ['00:00:00', '00:02:00'], 'route_long_name': '', 'id': '3',
                      'route': ['3', '4'], 'await_departure': []},
                '1': {'ordered_stops': ['0', '1'], 'route_short_name': 'route1', 'mode': 'bus',
                      'trips': {'route1_04:40:00': '04:40:00'},
                      'arrival_offsets': ['00:00:00', '00:02:00'],
                      'departure_offsets': ['00:00:00', '00:02:00'], 'route_long_name': '', 'id': '1',
                      'route': ['0', '1'], 'await_departure': []},
                '2': {'ordered_stops': ['1', '2'], 'route_short_name': 'route2', 'mode': 'bus',
                      'trips': {'route2_05:40:00': '05:40:00'},
                      'arrival_offsets': ['00:00:00', '00:03:00'],
                      'departure_offsets': ['00:00:00', '00:05:00'], 'route_long_name': '', 'id': '2',
                      'route': ['1', '2'], 'await_departure': []}},
        services={'service2': {'id': 'service2', 'name': 'route3'},
                  'service1': {'id': 'service1', 'name': 'route1'}},
        route_to_service_map={'1': 'service1', '2':'service1', '3':'service2', '4':'service2'},
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
                          trips={'route1_04:40:00': '04:40:00'},
                          arrival_offsets=['00:00:00', '00:02:00'],
                          departure_offsets=['00:00:00', '00:02:00'],
                          route=['0', '1']),
                    Route(id='32', route_short_name='3route2', mode='bus',
                          stops=[
                              Stop(id='31', x=529455.7452394223, y=182401.37630677427, epsg='epsg:27700',
                                   linkRefId='1'),
                              Stop(id='32', x=529350.7866124967, y=182388.0201078112, epsg='epsg:27700',
                                   linkRefId='2')],
                          trips={'route2_05:40:00': '05:40:00'},
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

    assert_semantically_equal(list(sub_g.edges(data=True)),
                              [('1', '2', {'services': ['service1'], 'routes': ['2']}),
                               ('0', '1', {'services': ['service1'], 'routes': ['1']})])

    assert_semantically_equal(dict(sub_g.nodes(data=True)),
                              {'0': {'services': ['service1'], 'routes': ['1'], 'id': '0', 'x': 529455.7452394223,
                                     'y': 182401.37630677427, 'epsg': 'epsg:27700', 'name': '',
                                     'lat': 51.525696033239186, 'lon': -0.13530998708775874,
                                     's2_id': 5221390668020036699, 'additional_attributes': {'linkRefId'},
                                     'linkRefId': '0'},
                               '1': {'services': ['service1'], 'routes': ['1', '2'], 'id': '1', 'x': 529350.7866124967,
                                     'y': 182388.0201078112, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.52560003323918,
                                     'lon': -0.13682698708848137, 's2_id': 5221390668558830581,
                                     'additional_attributes': {'linkRefId'}, 'linkRefId': '1'},
                               '2': {'services': ['service1'], 'routes': ['2'], 'id': '2', 'x': 529350.7866124967,
                                     'y': 182388.0201078112, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.52560003323918,
                                     'lon': -0.13682698708848137, 's2_id': 5221390668558830581,
                                     'additional_attributes': {'linkRefId'}, 'linkRefId': '2'}})


def test_service_subgraph(schedule):
    sub_g = schedule['service1'].subgraph({('0', '1')})

    assert_semantically_equal(list(sub_g.edges(data=True)),
                              [('0', '1', {'services': ['service1'], 'routes': ['1']})])

    assert_semantically_equal(dict(sub_g.nodes(data=True)),
                              {'0': {'services': ['service1'], 'routes': ['1'], 'id': '0', 'x': 529455.7452394223,
                                     'y': 182401.37630677427, 'epsg': 'epsg:27700', 'name': '',
                                     'lat': 51.525696033239186, 'lon': -0.13530998708775874,
                                     's2_id': 5221390668020036699, 'additional_attributes': {'linkRefId'},
                                     'linkRefId': '0'},
                               '1': {'services': ['service1'], 'routes': ['1', '2'], 'id': '1', 'x': 529350.7866124967,
                                     'y': 182388.0201078112, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.52560003323918,
                                     'lon': -0.13682698708848137, 's2_id': 5221390668558830581,
                                     'additional_attributes': {'linkRefId'}, 'linkRefId': '1'}})


def test_route_subgraph(schedule):
    sub_g = schedule.route('1').subgraph({('0', '1')})

    assert_semantically_equal(list(sub_g.edges(data=True)),
                              [('0', '1', {'services': ['service1'], 'routes': ['1']})])

    assert_semantically_equal(dict(sub_g.nodes(data=True)),
                              {'1': {'services': ['service1'], 'routes': ['2', '1'], 'id': '1', 'x': 529350.7866124967,
                                     'y': 182388.0201078112, 'epsg': 'epsg:27700', 'lat': 51.52560003323918,
                                     'lon': -0.13682698708848137, 's2_id': 5221390668558830581,
                                     'additional_attributes': {'linkRefId'}, 'linkRefId': '1', 'name': ''},
                               '0': {'services': ['service1'], 'routes': ['1'], 'id': '0', 'x': 529455.7452394223,
                                     'y': 182401.37630677427, 'epsg': 'epsg:27700', 'lat': 51.525696033239186,
                                     'lon': -0.13530998708775874, 's2_id': 5221390668020036699,
                                     'additional_attributes': {'linkRefId'}, 'linkRefId': '0', 'name': ''}})


def test_reading_gtfs_into_schedule(correct_schedule_dict_from_test_gtfs, correct_stopdb_from_test_gtfs, mocker):
    mocker.patch.object(gtfs_reader, 'read_to_dict_schedule_and_stopd_db',
                        return_value=(correct_schedule_dict_from_test_gtfs, correct_stopdb_from_test_gtfs))
    s = Schedule('epsg:27700')
    s.read_gtfs_schedule('some_path_to_gtfs', 'day_for_gtfs')

    assert_semantically_equal(dict(s.graph().nodes(data=True)),
                              {'RSN': {'services': ['1002'], 'routes': ['1002_0'], 'id': 'RSN', 'x': 529061.7214134948,
                                       'y': 182106.20208785852, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.5231335,
                                       'lon': -0.1410946, 's2_id': 5221390332291192399, 'additional_attributes': set()},
                               'RSE': {'services': ['1002'], 'routes': ['1002_0'], 'id': 'RSE', 'x': 528998.7798063147,
                                       'y': 181673.74458124593, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.5192615,
                                       'lon': -0.1421595, 's2_id': 5221390324026756531, 'additional_attributes': set()},
                               'BSE': {'services': ['1001'], 'routes': ['1001_0'], 'id': 'BSE', 'x': 529044.4274520243,
                                       'y': 182056.01144580863, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.5226864,
                                       'lon': -0.1413621, 's2_id': 5221390325135889957, 'additional_attributes': set()},
                               'BSN': {'services': ['1001'], 'routes': ['1001_0'], 'id': 'BSN', 'x': 529138.2570252238,
                                       'y': 181939.72009660664, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.5216199,
                                       'lon': -0.140053, 's2_id': 5221390684150342605, 'additional_attributes': set()}})

    assert set(s.route_ids()) == {'1001_0', '1002_0'}

    d_1001_0 = s.route('1001_0').__dict__
    del d_1001_0['_graph']
    assert_semantically_equal(d_1001_0,
                              {'ordered_stops': ['BSE', 'BSN'], 'route_short_name': 'BTR', 'mode': 'bus',
                               'trips': {'BT1': '03:21:00'}, 'arrival_offsets': ['0:00:00', '0:02:00'],
                               'departure_offsets': ['0:00:00', '0:02:00'], 'route_long_name': '', 'id': '1001_0',
                               'route': [], 'await_departure': [], 'epsg': 'epsg:27700'})

    d_1002_0 = s.route('1002_0').__dict__
    del d_1002_0['_graph']
    assert_semantically_equal(d_1002_0,
                              {'ordered_stops': ['RSN', 'RSE'], 'route_short_name': 'RTR', 'mode': 'rail',
                               'trips': {'RT1': '03:21:00'}, 'arrival_offsets': ['0:00:00', '0:02:00'],
                               'departure_offsets': ['0:00:00', '0:02:00'], 'route_long_name': '', 'id': '1002_0',
                               'route': [], 'await_departure': [], 'epsg': 'epsg:27700'})


def test_reading_gtfs_into_non_empty_schedule_gives_consistently_projected_stops(correct_schedule_dict_from_test_gtfs,
                                                                                 correct_stopdb_from_test_gtfs,
                                                                                 schedule, mocker):
    mocker.patch.object(gtfs_reader, 'read_to_dict_schedule_and_stopd_db',
                        return_value=(correct_schedule_dict_from_test_gtfs, correct_stopdb_from_test_gtfs))
    s = schedule
    s.read_gtfs_schedule('some_path_to_gtfs', 'day_for_gtfs')

    assert_semantically_equal(dict(s.graph().nodes(data=True)),
                              {'4': {'services': ['service2'], 'routes': ['3', '4'], 'id': '4', 'x': 529350.7866124967,
                                     'y': 182388.0201078112, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.52560003323918,
                                     'lon': -0.13682698708848137, 's2_id': 5221390668558830581,
                                     'additional_attributes': {'linkRefId'}, 'linkRefId': '4'},
                               '5': {'services': ['service2'], 'routes': ['4'], 'id': '5', 'x': 529350.7866124967,
                                     'y': 182388.0201078112, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.52560003323918,
                                     'lon': -0.13682698708848137, 's2_id': 5221390668558830581,
                                     'additional_attributes': {'linkRefId'}, 'linkRefId': '5'},
                               '3': {'services': ['service2'], 'routes': ['3'], 'id': '3', 'x': 529455.7452394223,
                                     'y': 182401.37630677427, 'epsg': 'epsg:27700', 'name': '',
                                     'lat': 51.525696033239186, 'lon': -0.13530998708775874,
                                     's2_id': 5221390668020036699, 'additional_attributes': {'linkRefId'},
                                     'linkRefId': '3'},
                               '2': {'services': ['service1'], 'routes': ['2'], 'id': '2', 'x': 529350.7866124967,
                                     'y': 182388.0201078112, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.52560003323918,
                                     'lon': -0.13682698708848137, 's2_id': 5221390668558830581,
                                     'additional_attributes': {'linkRefId'}, 'linkRefId': '2'},
                               '0': {'services': ['service1'], 'routes': ['1'], 'id': '0', 'x': 529455.7452394223,
                                     'y': 182401.37630677427, 'epsg': 'epsg:27700', 'name': '',
                                     'lat': 51.525696033239186, 'lon': -0.13530998708775874,
                                     's2_id': 5221390668020036699, 'additional_attributes': {'linkRefId'},
                                     'linkRefId': '0'},
                               '1': {'services': ['service1'], 'routes': ['2', '1'], 'id': '1', 'x': 529350.7866124967,
                                     'y': 182388.0201078112, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.52560003323918,
                                     'lon': -0.13682698708848137, 's2_id': 5221390668558830581,
                                     'additional_attributes': {'linkRefId'}, 'linkRefId': '1'},
                               'RSN': {'services': ['1002'], 'routes': ['1002_0'], 'id': 'RSN', 'x': 529061.7214134948,
                                       'y': 182106.20208785852, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.5231335,
                                       'lon': -0.1410946, 's2_id': 5221390332291192399, 'additional_attributes': set()},
                               'RSE': {'services': ['1002'], 'routes': ['1002_0'], 'id': 'RSE', 'x': 528998.7798063147,
                                       'y': 181673.74458124593, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.5192615,
                                       'lon': -0.1421595, 's2_id': 5221390324026756531, 'additional_attributes': set()},
                               'BSE': {'services': ['1001'], 'routes': ['1001_0'], 'id': 'BSE', 'x': 529044.4274520243,
                                       'y': 182056.01144580863, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.5226864,
                                       'lon': -0.1413621, 's2_id': 5221390325135889957, 'additional_attributes': set()},
                               'BSN': {'services': ['1001'], 'routes': ['1001_0'], 'id': 'BSN', 'x': 529138.2570252238,
                                       'y': 181939.72009660664, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.5216199,
                                       'lon': -0.140053, 's2_id': 5221390684150342605, 'additional_attributes': set()}})


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
    g.graph['routes'] = {'1': {'arrival_offsets':[], 'ordered_stops':[], 'route_short_name':'', 'mode':'',
                               'departure_offsets':[], 'trips':{}}}

    with pytest.raises(ScheduleElementGraphSchemaError) as e:
        verify_graph_schema(g)
    assert 'Graph is missing `services` attribute' in str(e.value)


def test_graph_schema_verification_throws_error_when_missing_service_attributes():
    g = DiGraph()
    g.add_node('1', x=1, y=2, id='1', epsg='epsg:27700')
    g.graph['routes'] = {'1': {'arrival_offsets':[], 'ordered_stops':[], 'route_short_name':'', 'mode':'',
                               'departure_offsets':[], 'trips':{}}}
    g.graph['services'] = {'1': {}}

    with pytest.raises(ScheduleElementGraphSchemaError) as e:
        verify_graph_schema(g)
    assert 'missing the following attributes:' in str(e.value)
