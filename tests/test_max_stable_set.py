import pytest
from pandas import DataFrame
import genet.utils.spatial as spatial
from genet import MaxStableSet, Network, Schedule, Service, Route, Stop
from tests.fixtures import assert_semantically_equal


@pytest.fixture()
def network():
    n = Network('epsg:27700')
    n.add_nodes({'node_1': {'id': 'node_1', 'x': 1, 'y': 2, 'lat': 49.766825803756994, 'lon': -7.557148039524952,
                            's2_id': 5205973754090365183},
                 'node_2': {'id': 'node_2', 'x': 1, 'y': 3, 'lat': 49.766834755586814, 'lon': -7.557149066139435,
                            's2_id': 5205973754090333257},
                 'node_3': {'id': 'node_3', 'x': 2, 'y': 3, 'lat': 49.766835420540474, 'lon': -7.557135245523688,
                            's2_id': 5205973754090257181},
                 'node_4': {'id': 'node_4', 'x': 2, 'y': 2, 'lat': 49.766826468710484, 'lon': -7.557134218911724,
                            's2_id': 5205973754090480551},
                 'node_5': {'id': 'node_5', 'x': 3, 'y': 2, 'lat': 49.76682713366229, 'lon': -7.557120398297983,
                            's2_id': 5205973754090518939},
                 'node_6': {'id': 'node_6', 'x': 4, 'y': 2, 'lat': 49.76682779861249, 'lon': -7.557106577683727,
                            's2_id': 5205973754090531959},
                 'node_7': {'id': 'node_7', 'x': 5, 'y': 2, 'lat': 49.76682846356101, 'lon': -7.557092757068958,
                            's2_id': 5205973754096484927},
                 'node_8': {'id': 'node_8', 'x': 6, 'y': 2, 'lat': 49.766829128507936, 'lon': -7.55707893645368,
                            's2_id': 5205973754096518199},
                 'node_9': {'id': 'node_9', 'x': 6, 'y': 2, 'lat': 49.766829128507936, 'lon': -7.55707893645368,
                            's2_id': 5205973754096518199}})
    n.add_links(
        {'link_1_2_car': {'length': 1, 'modes': ['car'], 'freespeed': 1, 'from': 'node_1', 'to': 'node_2',
                          'id': 'link_1_2_car'},
         'link_2_1_car': {'length': 1, 'modes': ['car'], 'freespeed': 1, 'from': 'node_2', 'to': 'node_1',
                          'id': 'link_2_1_car'},
         'link_1_2_bus': {'length': 1, 'modes': ['bus'], 'freespeed': 1, 'from': 'node_1', 'to': 'node_2',
                          'id': 'link_1_2_bus'},
         'link_2_1_bus': {'length': 1, 'modes': ['bus'], 'freespeed': 1, 'from': 'node_2', 'to': 'node_1',
                          'id': 'link_2_1_bus'},
         'link_2_3_car': {'length': 1, 'modes': ['car'], 'freespeed': 1, 'from': 'node_2', 'to': 'node_3',
                          'id': 'link_2_3_car'},
         'link_3_2_car': {'length': 1, 'modes': ['car'], 'freespeed': 1, 'from': 'node_3', 'to': 'node_2',
                          'id': 'link_3_2_car'},
         'link_3_4_car': {'length': 1, 'modes': ['car'], 'freespeed': 1, 'from': 'node_3', 'to': 'node_4',
                          'id': 'link_3_4_car'},
         'link_4_3_car': {'length': 1, 'modes': ['car'], 'freespeed': 1, 'from': 'node_4', 'to': 'node_3',
                          'id': 'link_4_3_car'},
         'link_1_4_bus': {'length': 1, 'modes': ['bus'], 'freespeed': 1, 'from': 'node_1', 'to': 'node_4',
                          'id': 'link_1_4_bus'},
         'link_4_1_bus': {'length': 1, 'modes': ['bus'], 'freespeed': 1, 'from': 'node_4', 'to': 'node_1',
                          'id': 'link_4_1_bus'},
         'link_4_5_car': {'length': 1, 'modes': ['car'], 'freespeed': 1, 'from': 'node_4', 'to': 'node_5',
                          'id': 'link_4_5_car'},
         'link_5_4_car': {'length': 1, 'modes': ['car'], 'freespeed': 1, 'from': 'node_5', 'to': 'node_4',
                          'id': 'link_5_4_car'},
         'link_5_6_car': {'length': 1, 'modes': ['car'], 'freespeed': 1, 'from': 'node_5', 'to': 'node_6',
                          'id': 'link_5_6_car'},
         'link_6_5_car': {'length': 1, 'modes': ['car'], 'freespeed': 1, 'from': 'node_6', 'to': 'node_5',
                          'id': 'link_6_5_car'},
         'link_6_7_car': {'length': 1, 'modes': ['car'], 'freespeed': 1, 'from': 'node_6', 'to': 'node_7',
                          'id': 'link_6_7_car'},
         'link_7_6_car': {'length': 1, 'modes': ['car'], 'freespeed': 1, 'from': 'node_7', 'to': 'node_6',
                          'id': 'link_7_6_car'},
         'link_7_8_car': {'length': 1, 'modes': ['car'], 'freespeed': 1, 'from': 'node_7', 'to': 'node_8',
                          'id': 'link_7_8_car'},
         'link_8_7_car': {'length': 1, 'modes': ['car'], 'freespeed': 1, 'from': 'node_8', 'to': 'node_7',
                          'id': 'link_8_7_car'},
         'link_8_9_car': {'length': 1, 'modes': ['car'], 'freespeed': 1, 'from': 'node_8', 'to': 'node_9',
                          'id': 'link_8_9_car'},
         'link_9_8_car': {'length': 1, 'modes': ['car'], 'freespeed': 1, 'from': 'node_9', 'to': 'node_8',
                          'id': 'link_9_8_car'}
         })

    n.schedule = Schedule(epsg='epsg:27700',
                          services=[
                              Service(id='bus_service',
                                      routes=[
                                          Route(id='service_1_route_1',
                                                route_short_name='',
                                                mode='bus',
                                                stops=[Stop(epsg='epsg:27700', id='stop_1', x=1, y=2.5),
                                                       Stop(epsg='epsg:27700', id='stop_2', x=2, y=2.5),
                                                       Stop(epsg='epsg:27700', id='stop_3', x=5.5, y=2)],
                                                trips={'trip_1': '15:30:00'},
                                                arrival_offsets=['00:00:00', '00:02:00', '00:05:00'],
                                                departure_offsets=['00:00:00', '00:03:00', '00:07:00']
                                                ),
                                          Route(id='service_1_route_2',
                                                route_short_name='',
                                                mode='bus',
                                                stops=[Stop(epsg='epsg:27700', id='stop_3', x=5.5, y=2),
                                                       Stop(epsg='epsg:27700', id='stop_2', x=2, y=2.5),
                                                       Stop(epsg='epsg:27700', id='stop_1', x=1, y=2.5)],
                                                trips={'trip_1': '16:30:00'},
                                                arrival_offsets=['00:00:00', '00:02:00', '00:05:00'],
                                                departure_offsets=['00:00:00', '00:03:00', '00:07:00']
                                                )
                                      ])])
    return n


@pytest.fixture()
def network_spatial_tree(network):
    return spatial.SpatialTree(network)


def test_all_stops_have_nearest_links_returns_False_with_missing_closest_links(mocker, network, network_spatial_tree):
    mocker.patch.object(spatial.SpatialTree, 'closest_links',
                        return_value=DataFrame({
                            'id': {0: 'stop_2', 1: 'stop_2', 2: 'stop_3', 3: 'stop_3'},
                            'link_id': {0: 'link_4_5_car', 1: 'link_5_6_car', 2: 'link_7_8_car', 3: 'link_8_9_car'},
                        }))
    mss = MaxStableSet(pt_graph=network.schedule['bus_service'].graph(),
                       network_spatial_tree=network_spatial_tree,
                       modes={'car', 'bus'})
    assert not mss.all_stops_have_nearest_links()


def test_stops_missing_nearest_links_identifies_stops_with_missing_closest_links(mocker, network, network_spatial_tree):
    mocker.patch.object(spatial.SpatialTree, 'closest_links',
                        return_value=DataFrame({
                            'id': {0: 'stop_2', 1: 'stop_2', 2: 'stop_3', 3: 'stop_3'},
                            'link_id': {0: 'link_4_5_car', 1: 'link_5_6_car', 2: 'link_7_8_car', 3: 'link_8_9_car'},
                        }))
    mss = MaxStableSet(pt_graph=network.schedule['bus_service'].graph(),
                       network_spatial_tree=network_spatial_tree,
                       modes={'car', 'bus'})
    assert mss.stops_missing_nearest_links() == {'stop_1'}


def test_build_graph_for_maximum_stable_set_problem_with_non_trivial_closest_link_selection_pool(mocker, network,
                                                                                                 network_spatial_tree):
    mocker.patch.object(spatial.SpatialTree, 'closest_links',
                        return_value=DataFrame({
                            'id': {0: 'stop_2', 1: 'stop_2', 2: 'stop_3', 3: 'stop_3', 4: 'stop_1', 5: 'stop_1',
                                   6: 'stop_1'},
                            'link_id': {0: 'link_4_5_car', 1: 'link_5_6_car', 2: 'link_7_8_car', 3: 'link_8_9_car',
                                        4: 'link_1_2_car', 5: 'link_1_2_bus', 6: 'link_2_3_car'},
                        }))

    mss = MaxStableSet(pt_graph=network.schedule['bus_service'].graph(),
                       network_spatial_tree=network_spatial_tree,
                       modes={'car', 'bus'},
                       distance_threshold=30,
                       step_size=10)
    assert_semantically_equal(dict(mss.problem_graph.nodes()),
                              {'stop_2.link:link_4_5_car': {'id': 'stop_2', 'link_id': 'link_4_5_car',
                                                            'coeff': 0.2777777777777778},
                               'stop_2.link:link_5_6_car': {'id': 'stop_2', 'link_id': 'link_5_6_car',
                                                            'coeff': 0.2631578947368421},
                               'stop_3.link:link_7_8_car': {'id': 'stop_3', 'link_id': 'link_7_8_car',
                                                            'coeff': 0.2857142857142857},
                               'stop_3.link:link_8_9_car': {'id': 'stop_3', 'link_id': 'link_8_9_car',
                                                            'coeff': 0.2222222222222222},
                               'stop_1.link:link_1_2_car': {'id': 'stop_1', 'link_id': 'link_1_2_car',
                                                            'coeff': 0.2857142857142857},
                               'stop_1.link:link_1_2_bus': {'id': 'stop_1', 'link_id': 'link_1_2_bus',
                                                            'coeff': 0.2857142857142857},
                               'stop_1.link:link_2_3_car': {'id': 'stop_1', 'link_id': 'link_2_3_car',
                                                            'coeff': 0.2857142857142857}})
    assert_semantically_equal(list(mss.problem_graph.edges()),
                              [('stop_2.link:link_4_5_car', 'stop_2.link:link_5_6_car'),
                               ('stop_3.link:link_7_8_car', 'stop_3.link:link_8_9_car'),
                               ('stop_1.link:link_1_2_car', 'stop_1.link:link_1_2_bus'),
                               ('stop_1.link:link_1_2_car', 'stop_1.link:link_2_3_car'),
                               ('stop_1.link:link_1_2_bus', 'stop_1.link:link_2_3_car')])


def test_build_graph_for_maximum_stable_set_problem_with_no_path_between_isolated_node(mocker, network):
    mocker.patch.object(spatial.SpatialTree, 'closest_links',
                        return_value=DataFrame({
                            'id': {0: 'stop_2', 1: 'stop_2', 2: 'stop_3', 3: 'stop_3', 4: 'stop_1', 5: 'stop_1',
                                   6: 'stop_1'},
                            'link_id': {0: 'link_4_5_car', 1: 'link_5_6_car', 2: 'link_7_8_car', 3: 'link_8_9_car',
                                        4: 'isolated_link', 5: 'link_1_2_bus', 6: 'link_2_3_car'},
                        }))
    network.add_nodes({'node_iso_1': {'id': 'node_iso_1', 'x': 10, 'y': 20, 'lat': 49.8, 'lon': -7.5,
                                      's2_id': 5205973754090365183},
                       'node_iso_2': {'id': 'node_iso_2', 'x': 10, 'y': 30, 'lat': 49.9, 'lon': -7.6,
                                      's2_id': 5205973754090333257}})
    network.add_link('isolated_link', u='node_iso_1', v='node_iso_2', attribs={'modes': {'car', 'bus'}})

    mss = MaxStableSet(pt_graph=network.schedule['bus_service'].graph(),
                       network_spatial_tree=spatial.SpatialTree(network),
                       modes={'car', 'bus'},
                       distance_threshold=30,
                       step_size=10)
    assert_semantically_equal(dict(mss.problem_graph.nodes()),
                              {'stop_2.link:link_4_5_car': {'id': 'stop_2', 'link_id': 'link_4_5_car',
                                                            'coeff': 0.26666666666666666},
                               'stop_2.link:link_5_6_car': {'id': 'stop_2', 'link_id': 'link_5_6_car',
                                                            'coeff': 0.26666666666666666},
                               'stop_3.link:link_7_8_car': {'id': 'stop_3', 'link_id': 'link_7_8_car',
                                                            'coeff': 0.2857142857142857},
                               'stop_3.link:link_8_9_car': {'id': 'stop_3', 'link_id': 'link_8_9_car',
                                                            'coeff': 0.2222222222222222},
                               'stop_1.link:link_1_2_bus': {'id': 'stop_1', 'link_id': 'link_1_2_bus',
                                                            'coeff': 0.2857142857142857},
                               'stop_1.link:link_2_3_car': {'id': 'stop_1', 'link_id': 'link_2_3_car',
                                                            'coeff': 0.2857142857142857}})
    assert_semantically_equal(list(mss.problem_graph.edges()),
                              [('stop_2.link:link_4_5_car', 'stop_2.link:link_5_6_car'),
                               ('stop_3.link:link_7_8_car', 'stop_3.link:link_8_9_car'),
                               ('stop_1.link:link_1_2_bus', 'stop_1.link:link_2_3_car')])


def test_problem_with_distinct_catchments_is_viable(mocker, network, network_spatial_tree):
    mocker.patch.object(spatial.SpatialTree, 'closest_links',
                        return_value=DataFrame({
                            'id': {0: 'stop_2', 1: 'stop_2', 2: 'stop_3', 3: 'stop_3', 4: 'stop_1', 5: 'stop_1',
                                   6: 'stop_1'},
                            'link_id': {0: 'link_4_5_car', 1: 'link_5_6_car', 2: 'link_7_8_car', 3: 'link_8_9_car',
                                        4: 'link_1_2_car', 5: 'link_1_2_bus', 6: 'link_2_3_car'},
                        }))

    mss = MaxStableSet(pt_graph=network.schedule['bus_service'].graph(),
                       network_spatial_tree=network_spatial_tree,
                       modes={'car', 'bus'},
                       distance_threshold=30,
                       step_size=10)

    assert mss.is_viable()


def test_problem_with_isolated_catchment_is_not_viable(mocker, network):
    mocker.patch.object(spatial.SpatialTree, 'closest_links',
                        return_value=DataFrame({
                            'id': {0: 'stop_2', 1: 'stop_2', 2: 'stop_3', 3: 'stop_3', 4: 'stop_1', 5: 'stop_1'},
                            'link_id': {0: 'link_4_5_car', 1: 'link_5_6_car', 2: 'link_7_8_car', 3: 'link_8_9_car',
                                        4: 'isolated_link_1', 5: 'isolated_link_2'},
                        }))
    network.add_nodes({'node_iso_1': {'id': 'node_iso_1', 'x': 10, 'y': 20, 'lat': 49.8, 'lon': -7.5,
                                      's2_id': 5205973754090365183},
                       'node_iso_2': {'id': 'node_iso_2', 'x': 10, 'y': 30, 'lat': 49.9, 'lon': -7.6,
                                      's2_id': 5205973754090333257}})
    network.add_link('isolated_link_1', u='node_iso_1', v='node_iso_2', attribs={'modes': {'car', 'bus'}})
    network.add_link('isolated_link_2', u='node_iso_2', v='node_iso_1', attribs={'modes': {'car', 'bus'}})

    mss = MaxStableSet(pt_graph=network.schedule['bus_service'].graph(),
                       network_spatial_tree=spatial.SpatialTree(network),
                       modes={'car', 'bus'},
                       distance_threshold=30,
                       step_size=10)

    assert not mss.is_viable()


def test_problem_with_isolated_catchment_is_partially_viable(mocker, network):
    mocker.patch.object(spatial.SpatialTree, 'closest_links',
                        return_value=DataFrame({
                            'id': {0: 'stop_2', 1: 'stop_2', 2: 'stop_3', 3: 'stop_3', 4: 'stop_1', 5: 'stop_1'},
                            'link_id': {0: 'link_4_5_car', 1: 'link_5_6_car', 2: 'link_7_8_car', 3: 'link_8_9_car',
                                        4: 'isolated_link_1', 5: 'isolated_link_2'},
                        }))
    network.add_nodes({'node_iso_1': {'id': 'node_iso_1', 'x': 10, 'y': 20, 'lat': 49.8, 'lon': -7.5,
                                      's2_id': 5205973754090365183},
                       'node_iso_2': {'id': 'node_iso_2', 'x': 10, 'y': 30, 'lat': 49.9, 'lon': -7.6,
                                      's2_id': 5205973754090333257}})
    network.add_link('isolated_link_1', u='node_iso_1', v='node_iso_2', attribs={'modes': {'car', 'bus'}})
    network.add_link('isolated_link_2', u='node_iso_2', v='node_iso_1', attribs={'modes': {'car', 'bus'}})

    mss = MaxStableSet(pt_graph=network.schedule['bus_service'].graph(),
                       network_spatial_tree=spatial.SpatialTree(network),
                       modes={'car', 'bus'},
                       distance_threshold=30,
                       step_size=10)

    assert mss.is_partially_viable()
