import os
import pytest
from genet.outputs_handler import geojson
from genet import Network, Schedule, Service, Route, Stop
from tests.fixtures import assert_semantically_equal, correct_schedule


@pytest.fixture()
def network(correct_schedule):
    n = Network('epsg:27700')
    n.add_node('0', attribs={'x': 528704.1425925883, 'y': 182068.78193707118})
    n.add_node('1', attribs={'x': 528804.1425925883, 'y': 182168.78193707118})
    n.add_link('link_0', '0', '1', attribs={'length': 123, 'modes': ['car', 'walk'], 'freespeed': 10, 'capacity': 5})
    n.add_link('link_1', '0', '1', attribs={'length': 123, 'modes': ['bike']})
    n.add_link('link_2', '1', '0', attribs={'length': 123, 'modes': ['rail']})

    n.schedule = correct_schedule
    return n


def test_generating_network_graph_geodataframe(network):
    nodes, links = geojson.generate_geodataframes(network.graph)
    correct_nodes = {
        'x': {'0': 528704.1425925883, '1': 528804.1425925883},
        'y': {'0': 182068.78193707118, '1': 182168.78193707118}}
    correct_links = {'length': {0: 123, 1: 123, 2: 123},
                     'modes': {0: ['car', 'walk'], 1: ['bike'], 2: ['rail']},
                     'freespeed': {0: 10.0, 1: float('nan'), 2: float('nan')},
                     'capacity': {0: 5.0, 1: float('nan'), 2: float('nan')},
                     'from': {0: '0', 1: '0', 2: '1'}, 'to': {0: '1', 1: '1', 2: '0'},
                     'id': {0: 'link_0', 1: 'link_1', 2: 'link_2'}, 'u': {0: '0', 1: '0', 2: '1'},
                     'v': {0: '1', 1: '1', 2: '0'}, 'key': {0: 0, 1: 1, 2: 0}}

    assert_semantically_equal(nodes[set(nodes.columns) - {'geometry'}].to_dict(), correct_nodes)
    assert_semantically_equal(links[set(links.columns) - {'geometry'}].to_dict(), correct_links)

    assert round(nodes.loc['0', 'geometry'].coords[:][0][0], 7) == round(-0.14625948709424305, 7)
    assert round(nodes.loc['0', 'geometry'].coords[:][0][1], 7) == round(51.52287873323954, 7)
    assert round(nodes.loc['1', 'geometry'].coords[:][0][0], 7) == round(-0.14478238148334213, 7)
    assert round(nodes.loc['1', 'geometry'].coords[:][0][1], 7) == round(51.523754629002234, 7)

    points = links.loc[0, 'geometry'].coords[:]
    assert round(points[0][0], 7) == round(-0.14625948709424305, 7)
    assert round(points[0][1], 7) == round(51.52287873323954, 7)
    assert round(points[1][0], 7) == round(-0.14478238148334213, 7)
    assert round(points[1][1], 7) == round(51.523754629002234, 7)

    assert nodes.crs == "EPSG:4326"
    assert links.crs == "EPSG:4326"


def test_generating_schedule_graph_geodataframe(network):
    nodes, links = geojson.generate_geodataframes(network.schedule.graph())
    correct_nodes = {'services': {'0': ['service'], '1': ['service']},
                     'routes': {'0': ['1', '2'], '1': ['1', '2']},
                     'id': {'0': '0', '1': '1'}, 'x': {'0': 529455.7452394223, '1': 529350.7866124967},
                     'y': {'0': 182401.37630677427, '1': 182388.0201078112},
                     'epsg': {'0': 'epsg:27700', '1': 'epsg:27700'},
                     'lat': {'0': 51.525696033239186, '1': 51.52560003323918},
                     'lon': {'0': -0.13530998708775874, '1': -0.13682698708848137},
                     's2_id': {'0': 5221390668020036699, '1': 5221390668558830581},
                     'additional_attributes': {'0': ['linkRefId'], '1': ['linkRefId']},
                     'linkRefId': {'0': '1', '1': '2'}}
    correct_links = {'services': {0: ['service']},
                     'routes': {0: ['1', '2']},
                     'modes': {0: ['bus']},
                     'u': {0: '0'},
                     'v': {0: '1'},
                     'key': {0: 0}}

    assert_semantically_equal(nodes[set(nodes.columns) - {'geometry'}].to_dict(), correct_nodes)
    assert_semantically_equal(links[set(links.columns) - {'geometry'}].to_dict(), correct_links)

    assert round(nodes.loc['0', 'geometry'].coords[:][0][0], 7) == round(-0.13530998708775874, 7)
    assert round(nodes.loc['0', 'geometry'].coords[:][0][1], 7) == round(51.525696033239186, 7)
    assert round(nodes.loc['1', 'geometry'].coords[:][0][0], 7) == round(-0.13682698708848137, 7)
    assert round(nodes.loc['1', 'geometry'].coords[:][0][1], 7) == round(51.52560003323918, 7)

    points = links.loc[0, 'geometry'].coords[:]
    assert round(points[0][0], 7) == round(-0.13530998708775874, 7)
    assert round(points[0][1], 7) == round(51.525696033239186, 7)
    assert round(points[1][0], 7) == round(-0.13682698708848137, 7)
    assert round(points[1][1], 7) == round(51.52560003323918, 7)

    assert nodes.crs == "EPSG:4326"
    assert links.crs == "EPSG:4326"


def test_modal_subset(network):
    nodes, links = geojson.generate_geodataframes(network.graph)
    car = links[links.apply(lambda x: geojson.modal_subset(x, {'car'}), axis=1)]

    assert len(car) == 1
    assert car.loc[0, 'modes'] == ['car', 'walk']


def test_save_to_geojson(network, tmpdir):
    assert os.listdir(tmpdir) == []
    network.save_network_to_geojson(tmpdir)
    assert set(os.listdir(tmpdir)) == {
        'network_nodes.geojson', 'network_links.geojson', 'network_links_geometry_only.geojson',
        'network_nodes_geometry_only.geojson', 'schedule_nodes.geojson', 'schedule_links.geojson',
        'schedule_links_geometry_only.geojson', 'schedule_nodes_geometry_only.geojson'}


def test_generating_standard_outputs(network, tmpdir):
    network.schedule = Schedule(epsg='epsg:27700', services=[
        Service(id='bus_service',
                routes=[
                    Route(id='1', route_short_name='route', mode='bus',
                          stops=[
                              Stop(id='0', x=529455.7452394223, y=182401.37630677427, epsg='epsg:27700', linkRefId='1'),
                              Stop(id='1', x=529350.7866124967, y=182388.0201078112, epsg='epsg:27700', linkRefId='2')],
                          trips={'VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00': '04:40:00'},
                          arrival_offsets=['00:00:00', '00:02:00'],
                          departure_offsets=['00:00:00', '00:02:00'],
                          route=['1', '2']),
                    Route(id='2', route_short_name='route1', mode='bus',
                          stops=[
                              Stop(id='0', x=529455.7452394223, y=182401.37630677427, epsg='epsg:27700', linkRefId='1'),
                              Stop(id='1', x=529350.7866124967, y=182388.0201078112, epsg='epsg:27700', linkRefId='2')],
                          trips={'1_05:40:00': '05:40:00',
                                 '2_05:45:00': '05:45:00',
                                 '3_05:50:00': '05:50:00',
                                 '4_06:40:00': '06:40:00',
                                 '5_06:46:00': '06:46:00'},
                          arrival_offsets=['00:00:00', '00:03:00'],
                          departure_offsets=['00:00:00', '00:05:00'],
                          route=['1', '2'])
                ]),
        Service(id='rail_service',
                routes=[Route(
                    route_short_name='RTR',
                    mode='rail',
                    stops=[Stop(id='RSN', x=-0.1410946, y=51.5231335, epsg='epsg:4326'),
                           Stop(id='RSE', x=-0.1421595, y=51.5192615, epsg='epsg:4326')],
                    trips={'RT1': '03:21:00', 'RT2': '03:31:00', 'RT3': '03:41:00', 'RT4': '03:51:00'},
                    arrival_offsets=['0:00:00', '0:02:00'],
                    departure_offsets=['0:00:00', '0:02:00']
                )])
    ])
    assert os.listdir(tmpdir) == []
    network.generate_standard_outputs(tmpdir)
    assert set(os.listdir(tmpdir)) == {'car_capacity_subgraph.geojson',
                                       'car_freespeed_subgraph.geojson',
                                       'schedule_subgraph_links_bus.geojson',
                                       'schedule_subgraph_links_rail.geojson',
                                       'schedule_subgraph_nodes_bus.geojson',
                                       'schedule_subgraph_nodes_rail.geojson',
                                       'subgraph_geometry_bike.geojson',
                                       'subgraph_geometry_car.geojson',
                                       'subgraph_geometry_rail.geojson',
                                       'subgraph_geometry_walk.geojson',
                                       'vehicles_per_hour_all_modes.geojson',
                                       'vehicles_per_hour_all_modes_within_6:30-7:30.geojson',
                                       'vehicles_per_hour_bus.geojson',
                                       'vehicles_per_hour_rail.geojson',
                                       'aggregate_vph_per_stop',
                                       'aggregate_vph_per_service'}

    assert set(os.listdir(os.path.join(tmpdir, 'aggregate_vph_per_service'))) == {'aggregate_vph_route.png',
                                                                                  'aggregate_vph_RTR.png'}

    assert set(os.listdir(os.path.join(tmpdir, 'aggregate_vph_per_stop'))) == {'aggregate_vph_RSE.png',
                                                                                  'aggregate_vph_RSN.png',
                                                                                  'aggregate_vph_1.png',
                                                                                  'aggregate_vph_0.png'}

    assert os.path.exists(tmpdir + '.zip')
