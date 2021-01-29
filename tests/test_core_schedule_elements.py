import pytest
from networkx import Graph
from genet.schedule_elements import Schedule, Service, Route, Stop
from genet.inputs_handler import gtfs_reader
from tests.fixtures import assert_semantically_equal, correct_schedule_dict_from_test_gtfs, \
    correct_stopdb_from_test_gtfs


def assert_all_elements_share_graph(elem):
    if isinstance(elem, Schedule):
        master_graph = id(elem.graph())
        for service in elem.services.values():
            assert master_graph == id(service._graph)
            for route in service._routes.values():
                assert master_graph == id(route._graph)
    elif isinstance(elem, Service):
        master_graph = id(elem.graph())
        for route in elem._routes.values():
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


def test_all_elements_in_schedule_share_the_same_graph(schedule):
    assert_all_elements_share_graph(schedule)


def test_updating_graph_results_in_shared_new_graph_for_all_elems(schedule):
    different_g = Graph()
    schedule._update_graph(different_g)
    assert_all_elements_share_graph(schedule)


def test_reindexing_route(schedule):
    r = schedule.route('1')
    r.reindex('new_index_for_route_1')
    assert_all_elements_share_graph(schedule)
    assert r.id == 'new_index_for_route_1'
    for node in r.reference_nodes:
        assert 'new_index_for_route_1' in schedule._graph.nodes[node]['routes']
        assert not '1' in schedule._graph.nodes[node]['routes']


def test_reindexing_service(schedule):
    s = schedule['service1']
    s.reindex('new_index_for_service1')
    assert_all_elements_share_graph(schedule)
    assert s.id == 'new_index_for_service1'
    for node in s.reference_nodes:
        assert 'new_index_for_service1' in schedule._graph.nodes[node]['services']
        assert not 'service1' in schedule._graph.nodes[node]['services']


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
                              [('1', '2', {'services': ['service1'], 'routes': ['2'], 'modes': ['bus']}),
                               ('0', '1', {'services': ['service1'], 'routes': ['1'], 'modes': ['bus']})])

    assert_semantically_equal(dict(sub_g.nodes(data=True)),
                              {'1': {'services': ['service1'], 'routes': ['2', '1'], 'id': '1', 'x': 529350.7866124967,
                                     'y': 182388.0201078112, 'epsg': 'epsg:27700', 'lat': 51.52560003323918,
                                     'lon': -0.13682698708848137, 's2_id': 5221390668558830581,
                                     'additional_attributes': ['linkRefId'], 'linkRefId': '1'},
                               '2': {'services': ['service1'], 'routes': ['2'], 'id': '2', 'x': 529350.7866124967,
                                     'y': 182388.0201078112, 'epsg': 'epsg:27700', 'lat': 51.52560003323918,
                                     'lon': -0.13682698708848137, 's2_id': 5221390668558830581,
                                     'additional_attributes': ['linkRefId'], 'linkRefId': '2'},
                               '0': {'services': ['service1'], 'routes': ['1'], 'id': '0', 'x': 529455.7452394223,
                                     'y': 182401.37630677427, 'epsg': 'epsg:27700', 'lat': 51.525696033239186,
                                     'lon': -0.13530998708775874, 's2_id': 5221390668020036699,
                                     'additional_attributes': ['linkRefId'], 'linkRefId': '0'}})


def test_schedule_subgraph(schedule):
    sub_g = schedule['service1'].subgraph({('0', '1')})

    assert_semantically_equal(list(sub_g.edges(data=True)),
                              [('0', '1', {'services': ['service1'], 'routes': ['1'], 'modes': ['bus']})])

    assert_semantically_equal(dict(sub_g.nodes(data=True)),
                              {'1': {'services': ['service1'], 'routes': ['2', '1'], 'id': '1', 'x': 529350.7866124967,
                                     'y': 182388.0201078112, 'epsg': 'epsg:27700', 'lat': 51.52560003323918,
                                     'lon': -0.13682698708848137, 's2_id': 5221390668558830581,
                                     'additional_attributes': ['linkRefId'], 'linkRefId': '1'},
                               '0': {'services': ['service1'], 'routes': ['1'], 'id': '0', 'x': 529455.7452394223,
                                     'y': 182401.37630677427, 'epsg': 'epsg:27700', 'lat': 51.525696033239186,
                                     'lon': -0.13530998708775874, 's2_id': 5221390668020036699,
                                     'additional_attributes': ['linkRefId'], 'linkRefId': '0'}})


def test_schedule_subgraph(schedule):
    sub_g = schedule.route('1').subgraph({('0', '1')})

    assert_semantically_equal(list(sub_g.edges(data=True)),
                              [('0', '1', {'services': ['service1'], 'routes': ['1'], 'modes': ['bus']})])

    assert_semantically_equal(dict(sub_g.nodes(data=True)),
                              {'1': {'services': ['service1'], 'routes': ['2', '1'], 'id': '1', 'x': 529350.7866124967,
                                     'y': 182388.0201078112, 'epsg': 'epsg:27700', 'lat': 51.52560003323918,
                                     'lon': -0.13682698708848137, 's2_id': 5221390668558830581,
                                     'additional_attributes': ['linkRefId'], 'linkRefId': '1', 'name': ''},
                               '0': {'services': ['service1'], 'routes': ['1'], 'id': '0', 'x': 529455.7452394223,
                                     'y': 182401.37630677427, 'epsg': 'epsg:27700', 'lat': 51.525696033239186,
                                     'lon': -0.13530998708775874, 's2_id': 5221390668020036699,
                                     'additional_attributes': ['linkRefId'], 'linkRefId': '0', 'name': ''}})


def test_reading_gtfs_into_schedule(correct_schedule_dict_from_test_gtfs, correct_stopdb_from_test_gtfs, mocker):
    mocker.patch.object(gtfs_reader, 'read_to_dict_schedule_and_stopd_db',
                        return_value=(correct_schedule_dict_from_test_gtfs, correct_stopdb_from_test_gtfs))
    s = Schedule('epsg:27700')
    s.read_gtfs_schedule('some_path_to_gtfs', 'day_for_gtfs')

    assert_semantically_equal(dict(s.graph().nodes(data=True)),
                              {'RSN': {'services': ['1002'], 'routes': ['1002_0'], 'id': 'RSN', 'x': 529061.7214134948,
                                       'y': 182106.20208785852, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.5231335,
                                       'lon': -0.1410946, 's2_id': 5221390332291192399, 'additional_attributes': []},
                               'RSE': {'services': ['1002'], 'routes': ['1002_0'], 'id': 'RSE', 'x': 528998.7798063147,
                                       'y': 181673.74458124593, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.5192615,
                                       'lon': -0.1421595, 's2_id': 5221390324026756531, 'additional_attributes': []},
                               'BSE': {'services': ['1001'], 'routes': ['1001_0'], 'id': 'BSE', 'x': 529044.4274520243,
                                       'y': 182056.01144580863, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.5226864,
                                       'lon': -0.1413621, 's2_id': 5221390325135889957, 'additional_attributes': []},
                               'BSN': {'services': ['1001'], 'routes': ['1001_0'], 'id': 'BSN', 'x': 529138.2570252238,
                                       'y': 181939.72009660664, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.5216199,
                                       'lon': -0.140053, 's2_id': 5221390684150342605, 'additional_attributes': []}})

    assert {r.id for _id, r in s.routes()} == {'1001_0', '1002_0'}

    d_1001_0 = s.route('1001_0').__dict__
    del d_1001_0['_graph']
    assert_semantically_equal(d_1001_0,
                              {'ordered_stops': ['BSE', 'BSN'], 'route_short_name': 'BTR', 'mode': 'bus',
                               'trips': {'BT1': '03:21:00'}, 'arrival_offsets': ['0:00:00', '0:02:00'],
                               'departure_offsets': ['0:00:00', '0:02:00'], 'route_long_name': '', 'id': '1001_0',
                               'route': [], 'await_departure': [], 'reference_nodes': ['BSE', 'BSN'],
                               'reference_edges': [('BSE', 'BSN')], 'epsg': 'epsg:4326'})

    d_1002_0 = s.route('1002_0').__dict__
    del d_1002_0['_graph']
    assert_semantically_equal(d_1002_0,
                              {'ordered_stops': ['RSN', 'RSE'], 'route_short_name': 'RTR', 'mode': 'rail',
                               'trips': {'RT1': '03:21:00'}, 'arrival_offsets': ['0:00:00', '0:02:00'],
                               'departure_offsets': ['0:00:00', '0:02:00'], 'route_long_name': '', 'id': '1002_0',
                               'route': [], 'await_departure': [], 'reference_nodes': ['RSN', 'RSE'],
                               'reference_edges': [('RSN', 'RSE')], 'epsg': 'epsg:4326'})


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
                                     'additional_attributes': ['linkRefId'], 'linkRefId': '4'},
                               '5': {'services': ['service2'], 'routes': ['4'], 'id': '5', 'x': 529350.7866124967,
                                     'y': 182388.0201078112, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.52560003323918,
                                     'lon': -0.13682698708848137, 's2_id': 5221390668558830581,
                                     'additional_attributes': ['linkRefId'], 'linkRefId': '5'},
                               '3': {'services': ['service2'], 'routes': ['3'], 'id': '3', 'x': 529455.7452394223,
                                     'y': 182401.37630677427, 'epsg': 'epsg:27700', 'name': '',
                                     'lat': 51.525696033239186, 'lon': -0.13530998708775874,
                                     's2_id': 5221390668020036699, 'additional_attributes': ['linkRefId'],
                                     'linkRefId': '3'},
                               '2': {'services': ['service1'], 'routes': ['2'], 'id': '2', 'x': 529350.7866124967,
                                     'y': 182388.0201078112, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.52560003323918,
                                     'lon': -0.13682698708848137, 's2_id': 5221390668558830581,
                                     'additional_attributes': ['linkRefId'], 'linkRefId': '2'},
                               '0': {'services': ['service1'], 'routes': ['1'], 'id': '0', 'x': 529455.7452394223,
                                     'y': 182401.37630677427, 'epsg': 'epsg:27700', 'name': '',
                                     'lat': 51.525696033239186, 'lon': -0.13530998708775874,
                                     's2_id': 5221390668020036699, 'additional_attributes': ['linkRefId'],
                                     'linkRefId': '0'},
                               '1': {'services': ['service1'], 'routes': ['2', '1'], 'id': '1', 'x': 529350.7866124967,
                                     'y': 182388.0201078112, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.52560003323918,
                                     'lon': -0.13682698708848137, 's2_id': 5221390668558830581,
                                     'additional_attributes': ['linkRefId'], 'linkRefId': '1'},
                               'RSN': {'services': ['1002'], 'routes': ['1002_0'], 'id': 'RSN', 'x': 529061.7214134948,
                                       'y': 182106.20208785852, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.5231335,
                                       'lon': -0.1410946, 's2_id': 5221390332291192399, 'additional_attributes': []},
                               'RSE': {'services': ['1002'], 'routes': ['1002_0'], 'id': 'RSE', 'x': 528998.7798063147,
                                       'y': 181673.74458124593, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.5192615,
                                       'lon': -0.1421595, 's2_id': 5221390324026756531, 'additional_attributes': []},
                               'BSE': {'services': ['1001'], 'routes': ['1001_0'], 'id': 'BSE', 'x': 529044.4274520243,
                                       'y': 182056.01144580863, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.5226864,
                                       'lon': -0.1413621, 's2_id': 5221390325135889957, 'additional_attributes': []},
                               'BSN': {'services': ['1001'], 'routes': ['1001_0'], 'id': 'BSN', 'x': 529138.2570252238,
                                       'y': 181939.72009660664, 'epsg': 'epsg:27700', 'name': '', 'lat': 51.5216199,
                                       'lon': -0.140053, 's2_id': 5221390684150342605, 'additional_attributes': []}})
