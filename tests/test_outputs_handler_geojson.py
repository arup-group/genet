import os
import pytest
from genet.outputs_handler import geojson as gngeojson
from genet import Network, Schedule, Service, Route, Stop
from tests.fixtures import assert_semantically_equal, correct_schedule


@pytest.fixture()
def network(correct_schedule):
    n = Network('epsg:27700')
    n.add_node('0', attribs={'x': 528704.1425925883, 'y': 182068.78193707118})
    n.add_node('1', attribs={'x': 528804.1425925883, 'y': 182168.78193707118})
    n.add_link('link_0', '0', '1', attribs={'length': 123, 'modes': ['car', 'walk'], 'freespeed': 10, 'capacity': 5})
    n.add_link('link_1', '0', '1', attribs={'length': 123, 'modes': ['bike'],
                                            'attributes': {'osm:way:highway': {'name': 'osm:way:highway',
                                                                               'class': 'java.lang.String',
                                                                               'text': 'unclassified'}}})
    n.add_link('link_2', '1', '0', attribs={'length': 123, 'modes': ['rail']})

    n.schedule = correct_schedule
    return n


def test_saving_values_which_result_in_overflow(tmpdir):
    n = Network('epsg:27700')
    n.add_node('0', attribs={'x': 528704.1425925883, 'y': 182068.78193707118, 's2_id': 7860190995130875979})
    n.add_node('1', attribs={'x': 528804.1425925883, 'y': 182168.78193707118, 's2_id': 12118290696817869383})
    n.add_link('link_0', '0', '1', attribs={'length': 123, 'modes': ['car', 'walk'], 'ids': ['1', '2']})
    n.write_to_geojson(tmpdir)


def test_generating_network_graph_geodataframe(network):
    gdfs = gngeojson.generate_geodataframes(network.graph)
    nodes, links = gdfs['nodes'], gdfs['links']
    correct_nodes = {
        'x': {'0': 528704.1425925883, '1': 528804.1425925883},
        'y': {'0': 182068.78193707118, '1': 182168.78193707118}}
    correct_links = {'u': {'link_0': '0', 'link_1': '0', 'link_2': '1'},
                     'v': {'link_0': '1', 'link_1': '1', 'link_2': '0'},
                     'length': {'link_0': 123, 'link_1': 123, 'link_2': 123},
                     'attributes': {'link_0': float('nan'), 'link_1': {
                         'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String',
                                             'text': 'unclassified'}}, 'link_2': float('nan')},
                     'to': {'link_0': '1', 'link_1': '1', 'link_2': '0'},
                     'from': {'link_0': '0', 'link_1': '0', 'link_2': '1'},
                     'freespeed': {'link_0': 10.0, 'link_1': float('nan'), 'link_2': float('nan')},
                     'id': {'link_0': 'link_0', 'link_1': 'link_1', 'link_2': 'link_2'},
                     'capacity': {'link_0': 5.0, 'link_1': float('nan'), 'link_2': float('nan')},
                     'modes': {'link_0': ['car', 'walk'], 'link_1': ['bike'], 'link_2': ['rail']}}

    assert_semantically_equal(nodes[set(nodes.columns) - {'geometry'}].to_dict(), correct_nodes)
    assert_semantically_equal(links[set(links.columns) - {'geometry'}].to_dict(), correct_links)

    assert round(nodes.loc['0', 'geometry'].coords[:][0][0], 7) == round(528704.1425925883, 7)
    assert round(nodes.loc['0', 'geometry'].coords[:][0][1], 7) == round(182068.78193707118, 7)
    assert round(nodes.loc['1', 'geometry'].coords[:][0][0], 7) == round(528804.1425925883, 7)
    assert round(nodes.loc['1', 'geometry'].coords[:][0][1], 7) == round(182168.78193707118, 7)

    points = links.loc['link_0', 'geometry'].coords[:]
    assert round(points[0][0], 7) == round(528704.1425925883, 7)
    assert round(points[0][1], 7) == round(182068.78193707118, 7)
    assert round(points[1][0], 7) == round(528804.1425925883, 7)
    assert round(points[1][1], 7) == round(182168.78193707118, 7)

    assert nodes.crs == "EPSG:27700"
    assert links.crs == "EPSG:27700"


def test_generating_schedule_graph_geodataframe(network):
    gdfs = gngeojson.generate_geodataframes(network.schedule.graph())
    nodes, links = gdfs['nodes'], gdfs['links']
    correct_nodes = {'services': {'0': {'service'}, '1': {'service'}},
                     'routes': {'0': {'1', '2'}, '1': {'1', '2'}},
                     'id': {'0': '0', '1': '1'}, 'x': {'0': 529455.7452394223, '1': 529350.7866124967},
                     'y': {'0': 182401.37630677427, '1': 182388.0201078112},
                     'epsg': {'0': 'epsg:27700', '1': 'epsg:27700'},
                     'lat': {'0': 51.525696033239186, '1': 51.52560003323918},
                     'lon': {'0': -0.13530998708775874, '1': -0.13682698708848137},
                     's2_id': {'0': 5221390668020036699, '1': 5221390668558830581},
                     'additional_attributes': {'0': {'linkRefId'}, '1': {'linkRefId'}},
                     'linkRefId': {'0': '1', '1': '2'},
                     'name': {'0': '', '1': ''}
                     }
    correct_links = {'services': {0: {'service'}},
                     'routes': {0: {'1', '2'}},
                     'u': {0: '0'},
                     'v': {0: '1'}}

    assert_semantically_equal(nodes[set(nodes.columns) - {'geometry'}].to_dict(), correct_nodes)
    assert_semantically_equal(links[set(links.columns) - {'geometry'}].to_dict(), correct_links)

    assert round(nodes.loc['0', 'geometry'].coords[:][0][0], 7) == round(529455.7452394223, 7)
    assert round(nodes.loc['0', 'geometry'].coords[:][0][1], 7) == round(182401.37630677427, 7)
    assert round(nodes.loc['1', 'geometry'].coords[:][0][0], 7) == round(529350.7866124967, 7)
    assert round(nodes.loc['1', 'geometry'].coords[:][0][1], 7) == round(182388.0201078112, 7)

    points = links.loc[0, 'geometry'].coords[:]
    assert round(points[0][0], 7) == round(529455.7452394223, 7)
    assert round(points[0][1], 7) == round(182401.37630677427, 7)
    assert round(points[1][0], 7) == round(529350.7866124967, 7)
    assert round(points[1][1], 7) == round(182388.0201078112, 7)

    assert nodes.crs == "EPSG:27700"
    assert links.crs == "EPSG:27700"


def test_modal_subset(network):
    gdfs = gngeojson.generate_geodataframes(network.graph)
    nodes, links = gdfs['nodes'], gdfs['links']
    car = links[links.apply(lambda x: gngeojson.modal_subset(x, {'car'}), axis=1)]

    assert len(car) == 1
    assert car.loc['link_0', 'modes'] == ['car', 'walk']


def test_generating_standard_outputs_after_modifying_modes_in_schedule(network, tmpdir):
    network.schedule.apply_attributes_to_routes({'1': {'mode': 'different_bus'}, '2': {'mode': 'other_bus'}})
    gngeojson.generate_standard_outputs_for_schedule(network.schedule, tmpdir)


def test_save_to_geojson(network, tmpdir):
    assert os.listdir(tmpdir) == []
    network.write_to_geojson(tmpdir)
    assert set(os.listdir(tmpdir)) == {'schedule_nodes.geojson', 'schedule_links.geojson', 'network_nodes.geojson',
                                       'schedule_nodes_geometry_only.geojson', 'network_nodes_geometry_only.geojson',
                                       'schedule_links_geometry_only.geojson', 'network_links_geometry_only.geojson',
                                       'network_links.geojson', 'network_change_log.csv', 'schedule_change_log.csv'}


def test_generating_standard_outputs(network, tmpdir):
    network.schedule = Schedule(epsg='epsg:27700', services=[
        Service(id='bus_service',
                routes=[
                    Route(id='1', route_short_name='', mode='bus',
                          stops=[
                              Stop(id='0', x=529455.7452394223, y=182401.37630677427, epsg='epsg:27700', linkRefId='1'),
                              Stop(id='1', x=529350.7866124967, y=182388.0201078112, epsg='epsg:27700', linkRefId='2')],
                          trips={'trip_id': ['VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00'],
                                 'trip_departure_time': ['04:40:00'],
                                 'vehicle_id': ['veh_1_bus']},
                          arrival_offsets=['00:00:00', '00:02:00'],
                          departure_offsets=['00:00:00', '00:02:00'],
                          route=['1', '2']),
                    Route(id='2', route_short_name='route2', mode='bus',
                          stops=[
                              Stop(id='0', x=529455.7452394223, y=182401.37630677427, epsg='epsg:27700', linkRefId='1'),
                              Stop(id='1', x=529350.7866124967, y=182388.0201078112, epsg='epsg:27700', linkRefId='2')],
                          trips={'trip_id': ['1_05:40:00', '2_05:45:00', '3_05:50:00', '4_06:40:00', '5_06:46:00'],
                                 'trip_departure_time': ['05:40:00', '05:45:00', '05:50:00', '06:40:00', '06:46:00'],
                                 'vehicle_id': ['veh_2_bus', 'veh_3_bus', 'veh_4_bus', 'veh_5_bus', 'veh_6_bus']},
                          arrival_offsets=['00:00:00', '00:03:00'],
                          departure_offsets=['00:00:00', '00:05:00'],
                          route=['1', '2'])
                ]),
        Service(id='rail_service',
                routes=[Route(
                    route_short_name="RTR_I/love\_being//difficult",
                    mode='rail',
                    stops=[
                        Stop(id='RSN', x=-0.1410946, y=51.5231335, epsg='epsg:4326', name="I/love\_being//difficult"),
                        Stop(id='RSE', x=-0.1421595, y=51.5192615, epsg='epsg:4326')],
                    trips={'trip_id': ['RT1', 'RT2', 'RT3', 'RT4'],
                           'trip_departure_time': ['03:21:00', '03:31:00', '03:41:00', '03:51:00'],
                           'vehicle_id': ['veh_7_rail', 'veh_8_rail', 'veh_9_rail', 'veh_10_rail']},
                    arrival_offsets=['0:00:00', '0:02:00'],
                    departure_offsets=['0:00:00', '0:02:00']
                )])
    ])
    assert os.listdir(tmpdir) == []
    network.generate_standard_outputs(tmpdir, include_shp_files=True)
    assert set(os.listdir(tmpdir)) == {'graph', 'schedule_links_geometry_only.geojson',
                                       'network_nodes_geometry_only.geojson', 'network_links.geojson',
                                       'network_links_geometry_only.geojson', 'schedule_nodes.geojson',
                                       'schedule_nodes_geometry_only.geojson', 'schedule', 'network_nodes.geojson',
                                       'schedule_links.geojson', 'network_change_log.csv', 'schedule_change_log.csv'}
    assert set(os.listdir(os.path.join(tmpdir, 'graph'))) == {'car_capacity_subgraph.geojson',
                                                              'car_freespeed_subgraph.geojson',
                                                              'car_osm_highway_unclassified.geojson',
                                                              'geometry_only_subgraphs', 'shp_files'}
    assert set(os.listdir(os.path.join(tmpdir, 'graph', 'shp_files'))) == {'car_osm_highway_unclassified.dbf',
                                                                           'car_capacity_subgraph.cpg',
                                                                           'car_freespeed_subgraph.shx',
                                                                           'car_freespeed_subgraph.cpg',
                                                                           'car_capacity_subgraph.prj',
                                                                           'car_osm_highway_unclassified.prj',
                                                                           'car_osm_highway_unclassified.shp',
                                                                           'car_freespeed_subgraph.prj',
                                                                           'car_osm_highway_unclassified.shx',
                                                                           'car_capacity_subgraph.shp',
                                                                           'car_capacity_subgraph.dbf',
                                                                           'car_capacity_subgraph.shx',
                                                                           'car_freespeed_subgraph.dbf',
                                                                           'car_freespeed_subgraph.shp',
                                                                           'car_osm_highway_unclassified.cpg'}
    assert set(os.listdir(os.path.join(tmpdir, 'graph', 'geometry_only_subgraphs'))) == {
        'subgraph_geometry_walk.geojson', 'subgraph_geometry_rail.geojson', 'subgraph_geometry_car.geojson',
        'shp_files',
        'subgraph_geometry_bike.geojson'}
    assert set(os.listdir(os.path.join(tmpdir, 'graph', 'geometry_only_subgraphs', 'shp_files'))) == {
        'subgraph_geometry_walk.shp', 'subgraph_geometry_rail.prj', 'subgraph_geometry_bike.dbf',
        'subgraph_geometry_rail.shx', 'subgraph_geometry_car.cpg', 'subgraph_geometry_car.dbf',
        'subgraph_geometry_car.shp',
        'subgraph_geometry_bike.shp', 'subgraph_geometry_walk.dbf', 'subgraph_geometry_bike.shx',
        'subgraph_geometry_rail.cpg', 'subgraph_geometry_bike.cpg', 'subgraph_geometry_car.shx',
        'subgraph_geometry_walk.cpg', 'subgraph_geometry_car.prj', 'subgraph_geometry_rail.dbf',
        'subgraph_geometry_walk.prj', 'subgraph_geometry_walk.shx', 'subgraph_geometry_bike.prj',
        'subgraph_geometry_rail.shp'}

    assert set(os.listdir(os.path.join(tmpdir, 'schedule'))) == {'vehicles_per_hour', 'subgraphs',
                                                                 'trips_per_day_per_service.csv',
                                                                 'trips_per_day_per_route.csv',
                                                                 'trips_per_day_per_route_aggregated_per_stop_id_pair.csv',
                                                                 'trips_per_day_per_route_aggregated_per_stop_name_pair.csv'
                                                                 }
    assert set(os.listdir(os.path.join(tmpdir, 'schedule', 'vehicles_per_hour'))) == {'vph_per_service.csv',
                                                                                      'vehicles_per_hour_all_modes.geojson',
                                                                                      'vph_per_stop_departing_from.csv',
                                                                                      'vph_all_modes_within_6:30-7:30.geojson',
                                                                                      'vph_per_stop_arriving_at.csv',
                                                                                      'shp_files',
                                                                                      'vehicles_per_hour_bus.geojson',
                                                                                      'vehicles_per_hour_rail.geojson'}
    assert set(os.listdir(os.path.join(tmpdir, 'schedule', 'vehicles_per_hour', 'shp_files'))) == {
        'vehicles_per_hour_all_modes.cpg', 'vph_all_modes_within_6:30-7:30.shx', 'vehicles_per_hour_rail.prj',
        'vehicles_per_hour_bus.shp', 'vehicles_per_hour_bus.dbf', 'vehicles_per_hour_rail.shx',
    'vehicles_per_hour_bus.prj',
        'vehicles_per_hour_all_modes.prj', 'vehicles_per_hour_bus.shx', 'vehicles_per_hour_rail.dbf',
        'vph_all_modes_within_6:30-7:30.dbf', 'vehicles_per_hour_rail.cpg', 'vph_all_modes_within_6:30-7:30.shp',
        'vehicles_per_hour_rail.shp', 'vehicles_per_hour_all_modes.shx', 'vehicles_per_hour_bus.cpg',
        'vehicles_per_hour_all_modes.shp', 'vph_all_modes_within_6:30-7:30.prj', 'vehicles_per_hour_all_modes.dbf',
        'vph_all_modes_within_6:30-7:30.cpg'}
    assert set(os.listdir(os.path.join(tmpdir, 'schedule', 'subgraphs'))) == {'schedule_subgraph_links_bus.geojson',
                                                                              'schedule_subgraph_links_rail.geojson',
                                                                              'shp_files',
                                                                              'schedule_subgraph_nodes_bus.geojson',
                                                                              'schedule_subgraph_nodes_rail.geojson'}
    assert set(os.listdir(os.path.join(tmpdir, 'schedule', 'subgraphs', 'shp_files'))) == {
    'schedule_subgraph_nodes_rail.prj', 'schedule_subgraph_links_bus.shx', 'schedule_subgraph_links_bus.prj',
    'schedule_subgraph_nodes_rail.dbf', 'schedule_subgraph_nodes_rail.shx', 'schedule_subgraph_links_rail.dbf',
    'schedule_subgraph_links_rail.shx', 'schedule_subgraph_nodes_bus.cpg', 'schedule_subgraph_links_rail.shp',
    'schedule_subgraph_nodes_bus.prj', 'schedule_subgraph_nodes_bus.dbf', 'schedule_subgraph_links_rail.cpg',
    'schedule_subgraph_links_bus.dbf', 'schedule_subgraph_links_bus.shp', 'schedule_subgraph_links_rail.prj',
    'schedule_subgraph_nodes_bus.shx', 'schedule_subgraph_links_bus.cpg', 'schedule_subgraph_nodes_bus.shp',
    'schedule_subgraph_nodes_rail.cpg', 'schedule_subgraph_nodes_rail.shp'}
    assert os.path.exists(tmpdir + '.zip')
