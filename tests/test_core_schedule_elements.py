import pytest
from networkx import Graph
from genet.schedule_elements import Schedule, Service, Route, Stop


def assert_all_elements_share_graph(elem):
    if isinstance(elem, Schedule):
        master_graph = id(elem.graph())
        for service in elem.services.values():
            assert master_graph == id(service._graph)
            for route in service.routes.values():
                assert master_graph == id(route._graph)
    elif isinstance(elem, Service):
        master_graph = id(elem.graph())
        for route in elem.routes.values():
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
                              Stop(id='30', x=529455.7452394223, y=182401.37630677427, epsg='epsg:27700', linkRefId='0'),
                              Stop(id='31', x=529350.7866124967, y=182388.0201078112, epsg='epsg:27700', linkRefId='1')],
                          trips={'route1_04:40:00': '04:40:00'},
                          arrival_offsets=['00:00:00', '00:02:00'],
                          departure_offsets=['00:00:00', '00:02:00'],
                          route=['0', '1']),
                    Route(id='32', route_short_name='3route2', mode='bus',
                          stops=[
                              Stop(id='31', x=529455.7452394223, y=182401.37630677427, epsg='epsg:27700', linkRefId='1'),
                              Stop(id='32', x=529350.7866124967, y=182388.0201078112, epsg='epsg:27700', linkRefId='2')],
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
