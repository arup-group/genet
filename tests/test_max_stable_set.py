import pytest
from pandas import DataFrame
from networkx import is_empty
import genet.utils.spatial as spatial
from genet import MaxStableSet, Network, Schedule, Service, Route, Stop
from tests.fixtures import assert_semantically_equal
from genet.exceptions import EmptySpatialTree


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
                            's2_id': 5205973754096518199}}, silent=True)
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
         }, silent=True)

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
                                                trips={'trip_id': ['trip_1'],
                                                       'trip_departure_time': ['15:30:00'],
                                                       'vehicle_id': ['veh_bus_0']},
                                                arrival_offsets=['00:00:00', '00:02:00', '00:05:00'],
                                                departure_offsets=['00:00:00', '00:03:00', '00:07:00']
                                                ),
                                          Route(id='service_1_route_2',
                                                route_short_name='',
                                                mode='bus',
                                                stops=[Stop(epsg='epsg:27700', id='stop_3', x=5.5, y=2),
                                                       Stop(epsg='epsg:27700', id='stop_2', x=2, y=2.5),
                                                       Stop(epsg='epsg:27700', id='stop_1', x=1, y=2.5)],
                                                trips={'trip_id': ['trip_2'],
                                                       'trip_departure_time': ['16:30:00'],
                                                       'vehicle_id': ['veh_bus_1']},
                                                arrival_offsets=['00:00:00', '00:02:00', '00:05:00'],
                                                departure_offsets=['00:00:00', '00:03:00', '00:07:00']
                                                )
                                      ])])
    return n


@pytest.fixture()
def network_spatial_tree(network):
    return spatial.SpatialTree(network)


def test_all_stops_have_nearest_links_returns_False_with_missing_closest_links(mocker, network, network_spatial_tree):
    closest_links = DataFrame({
        'id': {0: 'stop_2', 1: 'stop_2', 2: 'stop_3', 3: 'stop_3'},
        'link_id': {0: 'link_4_5_car', 1: 'link_5_6_car', 2: 'link_7_8_car', 3: 'link_8_9_car'},
    }).set_index('id', drop=False)
    closest_links.index.rename(name='index', inplace=True)
    mocker.patch.object(spatial.SpatialTree, 'closest_links',
                        return_value=closest_links)

    mss = MaxStableSet(pt_graph=network.schedule['bus_service'].graph(),
                       network_spatial_tree=network_spatial_tree,
                       modes={'car', 'bus'},
                       step_size=10,
                       distance_threshold=10
                       )
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


def test_buidling_mss_with_nothing_to_snap_to(network):
    mss = MaxStableSet(pt_graph=network.schedule['bus_service'].graph(),
                       network_spatial_tree=spatial.SpatialTree(),
                       modes={'car', 'bus'},
                       distance_threshold=10,
                       step_size=10)
    assert is_empty(mss.problem_graph)


def test_empty_mss_produces_completely_artificial_but_sensible_results(network):
    mss = MaxStableSet(pt_graph=network.schedule['bus_service'].graph(),
                       network_spatial_tree=spatial.SpatialTree(),
                       modes={'car', 'bus'},
                       distance_threshold=10,
                       step_size=10)
    mss.solve()
    mss.route_edges()
    mss.fill_in_solution_artificially()
    assert_semantically_equal(
        mss.solution,
        {'stop_3': 'artificial_link===from:stop_3===to:stop_3',
         'stop_1': 'artificial_link===from:stop_1===to:stop_1',
         'stop_2': 'artificial_link===from:stop_2===to:stop_2'})
    assert_semantically_equal(
        mss.pt_edges[['u', 'v', 'shortest_path']].to_dict(),
        {'u': {0: 'stop_3', 1: 'stop_2', 2: 'stop_2', 3: 'stop_1'},
         'v': {0: 'stop_2', 1: 'stop_1', 2: 'stop_3', 3: 'stop_2'},
         'shortest_path': {
             0: ['artificial_link===from:stop_3===to:stop_3',
                 'artificial_link===from:stop_3===to:stop_2',
                 'artificial_link===from:stop_2===to:stop_2'],
             1: ['artificial_link===from:stop_2===to:stop_2',
                 'artificial_link===from:stop_2===to:stop_1',
                 'artificial_link===from:stop_1===to:stop_1'],
             2: ['artificial_link===from:stop_2===to:stop_2',
                 'artificial_link===from:stop_2===to:stop_3',
                 'artificial_link===from:stop_3===to:stop_3'],
             3: ['artificial_link===from:stop_1===to:stop_1',
                 'artificial_link===from:stop_1===to:stop_2',
                 'artificial_link===from:stop_2===to:stop_2']}}
    )


def test_build_graph_for_maximum_stable_set_problem_with_non_trivial_closest_link_selection_pool(mocker, network,
                                                                                                 network_spatial_tree):
    closest_links = DataFrame({
        'id': {0: 'stop_2', 1: 'stop_2', 2: 'stop_3', 3: 'stop_3', 4: 'stop_1', 5: 'stop_1',
               6: 'stop_1'},
        'link_id': {0: 'link_4_5_car', 1: 'link_5_6_car', 2: 'link_7_8_car', 3: 'link_8_9_car',
                    4: 'link_1_2_car', 5: 'link_1_2_bus', 6: 'link_2_3_car'},
    }).set_index('id', drop=False)
    closest_links.index.rename(name='index', inplace=True)
    mocker.patch.object(spatial.SpatialTree, 'closest_links',
                        return_value=closest_links)

    mss = MaxStableSet(pt_graph=network.schedule['bus_service'].graph(),
                       network_spatial_tree=network_spatial_tree,
                       modes={'car', 'bus'},
                       distance_threshold=10,
                       step_size=10)
    assert_semantically_equal(dict(mss.problem_graph.nodes()),
                              {'stop_2.link:link_4_5_car': {'id': 'stop_2', 'link_id': 'link_4_5_car', 'catchment': 10,
                                                            'coeff': 0.2777777777777778},
                               'stop_2.link:link_5_6_car': {'id': 'stop_2', 'link_id': 'link_5_6_car', 'catchment': 10,
                                                            'coeff': 0.2631578947368421},
                               'stop_3.link:link_7_8_car': {'id': 'stop_3', 'link_id': 'link_7_8_car', 'catchment': 10,
                                                            'coeff': 0.2857142857142857},
                               'stop_3.link:link_8_9_car': {'id': 'stop_3', 'link_id': 'link_8_9_car', 'catchment': 10,
                                                            'coeff': 0.2222222222222222},
                               'stop_1.link:link_1_2_car': {'id': 'stop_1', 'link_id': 'link_1_2_car', 'catchment': 10,
                                                            'coeff': 0.2857142857142857},
                               'stop_1.link:link_1_2_bus': {'id': 'stop_1', 'link_id': 'link_1_2_bus', 'catchment': 10,
                                                            'coeff': 0.2857142857142857},
                               'stop_1.link:link_2_3_car': {'id': 'stop_1', 'link_id': 'link_2_3_car', 'catchment': 10,
                                                            'coeff': 0.2857142857142857}})
    assert_semantically_equal(list(mss.problem_graph.edges()),
                              [('stop_2.link:link_4_5_car', 'stop_2.link:link_5_6_car'),
                               ('stop_3.link:link_7_8_car', 'stop_3.link:link_8_9_car'),
                               ('stop_1.link:link_1_2_car', 'stop_1.link:link_1_2_bus'),
                               ('stop_1.link:link_1_2_car', 'stop_1.link:link_2_3_car'),
                               ('stop_1.link:link_1_2_bus', 'stop_1.link:link_2_3_car')])


def test_build_graph_for_maximum_stable_set_problem_with_no_path_between_isolated_node(mocker, network):
    closest_links = DataFrame({
        'id': {0: 'stop_2', 1: 'stop_2', 2: 'stop_3', 3: 'stop_3', 4: 'stop_1', 5: 'stop_1',
               6: 'stop_1'},
        'link_id': {0: 'link_4_5_car', 1: 'link_5_6_car', 2: 'link_7_8_car', 3: 'link_8_9_car',
                    4: 'isolated_link', 5: 'link_1_2_bus', 6: 'link_2_3_car'},
    }).set_index('id', drop=False)
    closest_links.index.rename(name='index', inplace=True)
    mocker.patch.object(spatial.SpatialTree, 'closest_links',
                        return_value=closest_links)

    network.add_nodes({'node_iso_1': {'id': 'node_iso_1', 'x': 10, 'y': 20, 'lat': 49.8, 'lon': -7.5,
                                      's2_id': 5205973754090365183},
                       'node_iso_2': {'id': 'node_iso_2', 'x': 10, 'y': 30, 'lat': 49.9, 'lon': -7.6,
                                      's2_id': 5205973754090333257}})
    network.add_link('isolated_link', u='node_iso_1', v='node_iso_2', attribs={'modes': {'car', 'bus'}})

    mss = MaxStableSet(pt_graph=network.schedule['bus_service'].graph(),
                       network_spatial_tree=spatial.SpatialTree(network),
                       modes={'car', 'bus'},
                       distance_threshold=10,
                       step_size=10)
    assert_semantically_equal(dict(mss.problem_graph.nodes()),
                              {'stop_2.link:link_4_5_car': {'id': 'stop_2', 'link_id': 'link_4_5_car', 'catchment': 10,
                                                            'coeff': 0.26666666666666666},
                               'stop_2.link:link_5_6_car': {'id': 'stop_2', 'link_id': 'link_5_6_car', 'catchment': 10,
                                                            'coeff': 0.26666666666666666},
                               'stop_3.link:link_7_8_car': {'id': 'stop_3', 'link_id': 'link_7_8_car', 'catchment': 10,
                                                            'coeff': 0.2857142857142857},
                               'stop_3.link:link_8_9_car': {'id': 'stop_3', 'link_id': 'link_8_9_car', 'catchment': 10,
                                                            'coeff': 0.2222222222222222},
                               'stop_1.link:link_1_2_bus': {'id': 'stop_1', 'link_id': 'link_1_2_bus', 'catchment': 10,
                                                            'coeff': 0.2857142857142857},
                               'stop_1.link:link_2_3_car': {'id': 'stop_1', 'link_id': 'link_2_3_car', 'catchment': 10,
                                                            'coeff': 0.2857142857142857}})
    assert_semantically_equal(list(mss.problem_graph.edges()),
                              [('stop_2.link:link_4_5_car', 'stop_2.link:link_5_6_car'),
                               ('stop_3.link:link_7_8_car', 'stop_3.link:link_8_9_car'),
                               ('stop_1.link:link_1_2_bus', 'stop_1.link:link_2_3_car')])


def test_problem_with_distinct_catchments_is_viable(mocker, network, network_spatial_tree):
    closest_links = DataFrame({
        'id': {0: 'stop_2', 1: 'stop_2', 2: 'stop_3', 3: 'stop_3', 4: 'stop_1', 5: 'stop_1',
               6: 'stop_1'},
        'link_id': {0: 'link_4_5_car', 1: 'link_5_6_car', 2: 'link_7_8_car', 3: 'link_8_9_car',
                    4: 'link_1_2_car', 5: 'link_1_2_bus', 6: 'link_2_3_car'},
    }).set_index('id', drop=False)
    closest_links.index.rename(name='index', inplace=True)
    mocker.patch.object(spatial.SpatialTree, 'closest_links',
                        return_value=closest_links)

    mss = MaxStableSet(pt_graph=network.schedule['bus_service'].graph(),
                       network_spatial_tree=network_spatial_tree,
                       modes={'car', 'bus'},
                       distance_threshold=10,
                       step_size=10)

    assert mss.is_viable()


def test_problem_with_isolated_catchment_is_not_viable(mocker, network):
    closest_links = DataFrame({
        'id': {0: 'stop_2', 1: 'stop_2', 2: 'stop_3', 3: 'stop_3', 4: 'stop_1', 5: 'stop_1'},
        'link_id': {0: 'link_4_5_car', 1: 'link_5_6_car', 2: 'link_7_8_car', 3: 'link_8_9_car',
                    4: 'isolated_link_1', 5: 'isolated_link_2'},
    }).set_index('id', drop=False)
    closest_links.index.rename(name='index', inplace=True)
    mocker.patch.object(spatial.SpatialTree, 'closest_links',
                        return_value=closest_links)

    network.add_nodes({'node_iso_1': {'id': 'node_iso_1', 'x': 10, 'y': 20, 'lat': 49.8, 'lon': -7.5,
                                      's2_id': 5205973754090365183},
                       'node_iso_2': {'id': 'node_iso_2', 'x': 10, 'y': 30, 'lat': 49.9, 'lon': -7.6,
                                      's2_id': 5205973754090333257}})
    network.add_link('isolated_link_1', u='node_iso_1', v='node_iso_2', attribs={'modes': {'car', 'bus'}})
    network.add_link('isolated_link_2', u='node_iso_2', v='node_iso_1', attribs={'modes': {'car', 'bus'}})

    mss = MaxStableSet(pt_graph=network.schedule['bus_service'].graph(),
                       network_spatial_tree=spatial.SpatialTree(network),
                       modes={'car', 'bus'},
                       distance_threshold=10,
                       step_size=10)

    assert not mss.is_viable()


def test_problem_with_isolated_catchment_is_partially_viable(mocker, network):
    closest_links = DataFrame({
        'id': {0: 'stop_2', 1: 'stop_2', 2: 'stop_3', 3: 'stop_3', 4: 'stop_1', 5: 'stop_1'},
        'link_id': {0: 'link_4_5_car', 1: 'link_5_6_car', 2: 'link_7_8_car', 3: 'link_8_9_car',
                    4: 'isolated_link_1', 5: 'isolated_link_2'},
    }).set_index('id', drop=False)
    closest_links.index.rename(name='index', inplace=True)
    mocker.patch.object(spatial.SpatialTree, 'closest_links',
                        return_value=closest_links)

    network.add_nodes({'node_iso_1': {'id': 'node_iso_1', 'x': 10, 'y': 20, 'lat': 49.8, 'lon': -7.5,
                                      's2_id': 5205973754090365183},
                       'node_iso_2': {'id': 'node_iso_2', 'x': 10, 'y': 30, 'lat': 49.9, 'lon': -7.6,
                                      's2_id': 5205973754090333257}})
    network.add_link('isolated_link_1', u='node_iso_1', v='node_iso_2', attribs={'modes': {'car', 'bus'}})
    network.add_link('isolated_link_2', u='node_iso_2', v='node_iso_1', attribs={'modes': {'car', 'bus'}})

    mss = MaxStableSet(pt_graph=network.schedule['bus_service'].graph(),
                       network_spatial_tree=spatial.SpatialTree(network),
                       modes={'car', 'bus'},
                       distance_threshold=10,
                       step_size=10)

    assert mss.is_partially_viable()


def test_solving_problem_with_isolated_catchments(mocker, network, network_spatial_tree):
    closest_links = DataFrame({
        'id': {0: 'stop_2', 1: 'stop_2', 2: 'stop_3', 3: 'stop_3', 4: 'stop_1', 5: 'stop_1', 6: 'stop_1'},
        'link_id': {0: 'link_4_5_car', 1: 'link_5_6_car', 2: 'link_7_8_car', 3: 'link_8_9_car', 4: 'link_1_2_car',
                    5: 'link_1_2_bus', 6: 'link_2_3_car'}
    }).set_index('id', drop=False)
    closest_links.index.rename(name='index', inplace=True)
    mocker.patch.object(spatial.SpatialTree, 'closest_links',
                        return_value=closest_links)

    mss = MaxStableSet(pt_graph=network.schedule['bus_service'].graph(),
                       network_spatial_tree=network_spatial_tree,
                       modes={'car', 'bus'})
    mss.solve()
    assert mss.solution == {'stop_1': 'link_1_2_bus', 'stop_2': 'link_4_5_car', 'stop_3': 'link_7_8_car'}
    assert_semantically_equal(mss.artificial_stops, {
        'stop_1.link:link_1_2_bus': {'services': {'bus_service'}, 'routes': {'service_1_route_2', 'service_1_route_1'},
                                     'id': 'stop_1.link:link_1_2_bus', 'x': 1.0, 'y': 2.5, 'epsg': 'epsg:27700',
                                     'name': '',
                                     'lon': -7.557148552832129, 'lat': 49.76683027967191, 's2_id': 5205973754090340691,
                                     'linkRefId': 'link_1_2_bus', 'stop_id': 'stop_1'},
        'stop_2.link:link_4_5_car': {'services': {'bus_service'}, 'routes': {'service_1_route_2', 'service_1_route_1'},
                                     'id': 'stop_2.link:link_4_5_car', 'x': 2.0, 'y': 2.5, 'epsg': 'epsg:27700',
                                     'name': '',
                                     'lon': -7.557134732217642, 'lat': 49.76683094462549, 's2_id': 5205973754090230267,
                                     'linkRefId': 'link_4_5_car', 'stop_id': 'stop_2'},
        'stop_3.link:link_7_8_car': {'services': {'bus_service'}, 'routes': {'service_1_route_2', 'service_1_route_1'},
                                     'id': 'stop_3.link:link_7_8_car', 'x': 5.5, 'y': 2.0, 'epsg': 'epsg:27700',
                                     'name': '',
                                     'lon': -7.55708584676138, 'lat': 49.76682879603468, 's2_id': 5205973754096513977,
                                     'linkRefId': 'link_7_8_car', 'stop_id': 'stop_3'}})


def test_problem_with_isolated_catchment_finds_solution_for_viable_stops(mocker, network):
    closest_links = DataFrame({
        'id': {0: 'stop_2', 1: 'stop_2', 2: 'stop_3', 3: 'stop_3', 4: 'stop_1', 5: 'stop_1'},
        'link_id': {0: 'link_4_5_car', 1: 'link_5_6_car', 2: 'link_7_8_car', 3: 'link_8_9_car',
                    4: 'isolated_link_1', 5: 'isolated_link_2'},
    }).set_index('id', drop=False)
    closest_links.index.rename(name='index', inplace=True)
    mocker.patch.object(spatial.SpatialTree, 'closest_links',
                        return_value=closest_links)

    network.add_nodes({'node_iso_1': {'id': 'node_iso_1', 'x': 10, 'y': 20, 'lat': 49.8, 'lon': -7.5,
                                      's2_id': 5205973754090365183},
                       'node_iso_2': {'id': 'node_iso_2', 'x': 10, 'y': 30, 'lat': 49.9, 'lon': -7.6,
                                      's2_id': 5205973754090333257}})
    network.add_link('isolated_link_1', u='node_iso_1', v='node_iso_2', attribs={'modes': {'car', 'bus'}})
    network.add_link('isolated_link_2', u='node_iso_2', v='node_iso_1', attribs={'modes': {'car', 'bus'}})

    mss = MaxStableSet(pt_graph=network.schedule['bus_service'].graph(),
                       network_spatial_tree=spatial.SpatialTree(network),
                       modes={'car', 'bus'},
                       distance_threshold=10,
                       step_size=10)
    mss.solve()
    assert mss.solution == {'stop_2': 'link_5_6_car', 'stop_3': 'link_7_8_car'}
    assert_semantically_equal(mss.artificial_stops, {
        'stop_2.link:link_5_6_car': {'services': {'bus_service'}, 'routes': {'service_1_route_2', 'service_1_route_1'},
                                     'id': 'stop_2.link:link_5_6_car', 'x': 2.0, 'y': 2.5, 'epsg': 'epsg:27700',
                                     'name': '',
                                     'lon': -7.557134732217642, 'lat': 49.76683094462549, 's2_id': 5205973754090230267,
                                     'linkRefId': 'link_5_6_car', 'stop_id': 'stop_2'},
        'stop_3.link:link_7_8_car': {'services': {'bus_service'}, 'routes': {'service_1_route_2', 'service_1_route_1'},
                                     'id': 'stop_3.link:link_7_8_car', 'x': 5.5, 'y': 2.0, 'epsg': 'epsg:27700',
                                     'name': '',
                                     'lon': -7.55708584676138, 'lat': 49.76682879603468, 's2_id': 5205973754096513977,
                                     'linkRefId': 'link_7_8_car', 'stop_id': 'stop_3'}})


@pytest.fixture()
def partial_mss(network):
    mss = MaxStableSet(pt_graph=network.schedule['bus_service'].graph(),
                       network_spatial_tree=spatial.SpatialTree(network),
                       modes={'car', 'bus'},
                       distance_threshold=10,
                       step_size=10)
    mss.solution = {'stop_2': 'link_5_6_car',
                    'stop_3': 'link_7_8_car',
                    'stop_1': 'artificial_link===from:stop_1===to:stop_1'}
    mss.artificial_stops = {
        'stop_2.link:link_5_6_car': {'services': {'bus_service'}, 'routes': {'service_1_route_1', 'service_1_route_2'},
                                     'id': 'stop_2.link:link_5_6_car', 'x': 2.0, 'y': 2.5, 'epsg': 'epsg:27700',
                                     'name': '', 'lon': -7.557134732217642, 'lat': 49.76683094462549,
                                     's2_id': 5205973754090230267, 'additional_attributes': set(),
                                     'linkRefId': 'link_5_6_car', 'stop_id': 'stop_2'},
        'stop_3.link:link_7_8_car': {'services': {'bus_service'}, 'routes': {'service_1_route_1', 'service_1_route_2'},
                                     'id': 'stop_3.link:link_7_8_car', 'x': 5.5, 'y': 2.0, 'epsg': 'epsg:27700',
                                     'name': '', 'lon': -7.55708584676138, 'lat': 49.76682879603468,
                                     's2_id': 5205973754096513977, 'additional_attributes': set(),
                                     'linkRefId': 'link_7_8_car', 'stop_id': 'stop_3'},
        'stop_1.link:artificial_link===from:stop_1===to:stop_1': {'services': {'bus_service'},
                                                                  'routes': {'service_1_route_1', 'service_1_route_2'},
                                                                  'id': 'stop_1.link:artificial_link===from:stop_1===to:stop_1',
                                                                  'x': 1.0, 'y': 2.5, 'epsg': 'epsg:27700', 'name': '',
                                                                  'lon': -7.557148552832129, 'lat': 49.76683027967191,
                                                                  's2_id': 5205973754090340691,
                                                                  'additional_attributes': set(),
                                                                  'linkRefId': 'artificial_link===from:stop_1===to:stop_1',
                                                                  'stop_id': 'stop_1'}}
    mss.artificial_links = {
        'artificial_link===from:stop_1===to:stop_1': {'from': 'stop_1', 'to': 'stop_1', 'modes': {'bus'}},
        'artificial_link===from:node_6===to:stop_1': {'from': 'node_6', 'to': 'stop_1', 'modes': {'bus'}},
        'artificial_link===from:stop_1===to:node_5': {'from': 'stop_1', 'to': 'node_5', 'modes': {'bus'}}}
    mss.pt_edges = DataFrame(
        {'services': {0: {'bus_service'}, 1: {'bus_service'}, 2: {'bus_service'}, 3: {'bus_service'}},
         'routes': {0: {'service_1_route_2'}, 1: {'service_1_route_2'}, 2: {'service_1_route_1'},
                    3: {'service_1_route_1'}},
         'u': {0: 'stop_3', 1: 'stop_2', 2: 'stop_2', 3: 'stop_1'},
         'v': {0: 'stop_2', 1: 'stop_1', 2: 'stop_3', 3: 'stop_2'},
         'key': {0: 0, 1: 0, 2: 0, 3: 0},
         'linkRefId_u': {0: 'link_7_8_car', 1: 'link_5_6_car', 2: 'link_5_6_car',
                         3: 'artificial_link===from:stop_1===to:stop_1'},
         'linkRefId_v': {0: 'link_5_6_car', 1: 'artificial_link===from:stop_1===to:stop_1', 2: 'link_7_8_car',
                         3: 'link_5_6_car'},
         'shortest_path': {0: ['link_7_8_car', 'link_8_7_car', 'link_7_6_car', 'link_6_5_car', 'link_5_6_car'],
                           1: ['link_5_6_car', 'artificial_link===from:node_6===to:stop_1',
                               'artificial_link===from:stop_1===to:stop_1'],
                           2: ['link_5_6_car', 'link_6_7_car', 'link_7_8_car'],
                           3: ['artificial_link===from:stop_1===to:stop_1', 'artificial_link===from:stop_1===to:node_5',
                               'link_5_6_car']}})
    mss.unsolved_stops = {'stop_1'}
    return mss


def test_generating_changeset_from_partial_mss_problem(partial_mss):
    changeset = partial_mss.to_changeset(
        DataFrame({'ordered_stops': {'service_1_route_2': ['stop_3', 'stop_2', 'stop_1'],
                                     'service_1_route_1': ['stop_1', 'stop_2', 'stop_3']}})
    )
    assert_semantically_equal(
        changeset.df_route_data.to_dict(),
        {'ordered_stops': {
            'service_1_route_1': ['stop_1.link:artificial_link===from:stop_1===to:stop_1', 'stop_2.link:link_5_6_car',
                                  'stop_3.link:link_7_8_car'],
            'service_1_route_2': ['stop_3.link:link_7_8_car', 'stop_2.link:link_5_6_car',
                                  'stop_1.link:artificial_link===from:stop_1===to:stop_1']}, 'route': {
            'service_1_route_1': ['artificial_link===from:stop_1===to:stop_1',
                                  'artificial_link===from:stop_1===to:node_5', 'link_5_6_car', 'link_6_7_car',
                                  'link_7_8_car'],
            'service_1_route_2': ['link_7_8_car', 'link_8_7_car', 'link_7_6_car', 'link_6_5_car', 'link_5_6_car',
                                  'artificial_link===from:node_6===to:stop_1',
                                  'artificial_link===from:stop_1===to:stop_1']}})
    assert_semantically_equal(
        changeset.additional_links_modes,
        {'link_5_6_car': {'modes': ['bus', 'car']}, 'link_6_5_car': {'modes': ['bus', 'car']},
         'link_6_7_car': {'modes': ['bus', 'car']}, 'link_7_6_car': {'modes': ['bus', 'car']},
         'link_7_8_car': {'modes': ['bus', 'car']}, 'link_8_7_car': {'modes': ['bus', 'car']}}
    )
    assert_semantically_equal(
        changeset.new_links,
        {'artificial_link===from:stop_1===to:stop_1': {'from': 'stop_1', 'to': 'stop_1', 'modes': {'bus'}},
         'artificial_link===from:node_6===to:stop_1': {'from': 'node_6', 'to': 'stop_1', 'modes': {'bus'}},
         'artificial_link===from:stop_1===to:node_5': {'from': 'stop_1', 'to': 'node_5', 'modes': {'bus'}}})
    assert_semantically_equal(
        changeset.new_nodes,
        {'stop_1': {'id': 'stop_1', 'x': 1.0, 'y': 2.5, 'name': '', 'lon': -7.557148552832129, 'lat': 49.76683027967191,
                    's2_id': 5205973754090340691}})
    assert_semantically_equal(
        changeset.new_stops,
        {'stop_2.link:link_5_6_car': {'services': {'bus_service'}, 'routes': {'service_1_route_1', 'service_1_route_2'},
                                      'id': 'stop_2.link:link_5_6_car', 'x': 2.0, 'y': 2.5, 'epsg': 'epsg:27700',
                                      'name': '', 'lon': -7.557134732217642, 'lat': 49.76683094462549,
                                      's2_id': 5205973754090230267, 'additional_attributes': set(),
                                      'linkRefId': 'link_5_6_car', 'stop_id': 'stop_2'},
         'stop_3.link:link_7_8_car': {'services': {'bus_service'}, 'routes': {'service_1_route_1', 'service_1_route_2'},
                                      'id': 'stop_3.link:link_7_8_car', 'x': 5.5, 'y': 2.0, 'epsg': 'epsg:27700',
                                      'name': '', 'lon': -7.55708584676138, 'lat': 49.76682879603468,
                                      's2_id': 5205973754096513977, 'additional_attributes': set(),
                                      'linkRefId': 'link_7_8_car', 'stop_id': 'stop_3'},
         'stop_1.link:artificial_link===from:stop_1===to:stop_1': {'services': {'bus_service'},
                                                                   'routes': {'service_1_route_1', 'service_1_route_2'},
                                                                   'id': 'stop_1.link:artificial_link===from:stop_1===to:stop_1',
                                                                   'x': 1.0, 'y': 2.5, 'epsg': 'epsg:27700', 'name': '',
                                                                   'lon': -7.557148552832129, 'lat': 49.76683027967191,
                                                                   's2_id': 5205973754090340691,
                                                                   'additional_attributes': set(),
                                                                   'linkRefId': 'artificial_link===from:stop_1===to:stop_1',
                                                                   'stop_id': 'stop_1'}})
    changeset.new_pt_edges.sort()
    assert changeset.new_pt_edges == [('stop_1.link:artificial_link===from:stop_1===to:stop_1',
                                       'stop_2.link:link_5_6_car',
                                       {'services': {'bus_service'}, 'routes': {'service_1_route_1'}}), (
                                      'stop_2.link:link_5_6_car',
                                      'stop_1.link:artificial_link===from:stop_1===to:stop_1',
                                      {'services': {'bus_service'}, 'routes': {'service_1_route_2'}}), (
                                      'stop_2.link:link_5_6_car', 'stop_3.link:link_7_8_car',
                                      {'services': {'bus_service'}, 'routes': {'service_1_route_1'}}), (
                                      'stop_3.link:link_7_8_car', 'stop_2.link:link_5_6_car',
                                      {'services': {'bus_service'}, 'routes': {'service_1_route_2'}})]
    assert_semantically_equal(
        changeset.minimal_transfer_times,
        {('stop_1', 'stop_1.link:artificial_link===from:stop_1===to:stop_1'): 0.0,
         ('stop_2', 'stop_2.link:link_5_6_car'): 0.0, ('stop_3', 'stop_3.link:link_7_8_car'): 0.0,
         ('stop_1.link:artificial_link===from:stop_1===to:stop_1', 'stop_1'): 0.0,
         ('stop_2.link:link_5_6_car', 'stop_2'): 0.0, ('stop_3.link:link_7_8_car', 'stop_3'): 0.0}
    )


def test_combining_two_changesets_with_overlap(partial_mss):
    service_1_route_1_pt_edges = partial_mss.pt_edges[
        partial_mss.pt_edges['routes'].apply(lambda x: 'service_1_route_1' in x)]
    service_1_route_2_pt_edges = partial_mss.pt_edges[
        partial_mss.pt_edges['routes'].apply(lambda x: 'service_1_route_2' in x)]

    partial_mss.pt_edges = service_1_route_2_pt_edges
    changeset = partial_mss.to_changeset(
        DataFrame({'ordered_stops': {'service_1_route_2': ['stop_3', 'stop_2', 'stop_1']}}))

    partial_mss.solution['stop_2'] = 'link_6_5_car'
    del partial_mss.artificial_stops['stop_2.link:link_5_6_car']
    partial_mss.artificial_stops['stop_2.link:link_6_5_car'] = {
        'services': {'bus_service'}, 'routes': {'service_1_route_1'},
        'id': 'stop_2.link:link_6_5_car', 'x': 2.0, 'y': 2.5, 'epsg': 'epsg:27700',
        'name': '', 'lon': -7.557134732217642, 'lat': 49.76683094462549,
        's2_id': 5205973754090230267, 'additional_attributes': set(),
        'linkRefId': 'link_6_5_car', 'stop_id': 'stop_2'}
    partial_mss.artificial_links = {
        'artificial_link===from:stop_1===to:stop_1': {'from': 'stop_1', 'to': 'stop_1', 'modes': {'bus'}},
        'artificial_link===from:node_5===to:stop_1': {'from': 'node_5', 'to': 'stop_1', 'modes': {'bus'}},
        'artificial_link===from:stop_1===to:node_6': {'from': 'stop_1', 'to': 'node_6', 'modes': {'bus'}}}
    partial_mss.pt_edges = service_1_route_1_pt_edges

    changeset += partial_mss.to_changeset(
        DataFrame({'ordered_stops': {'service_1_route_1': ['stop_1', 'stop_2', 'stop_3']}}))

    assert_semantically_equal(
        changeset.df_route_data.to_dict(),
        {'ordered_stops': {'service_1_route_2': ['stop_3.link:link_7_8_car', 'stop_2.link:link_5_6_car',
                                                 'stop_1.link:artificial_link===from:stop_1===to:stop_1'],
                           'service_1_route_1': ['stop_1.link:artificial_link===from:stop_1===to:stop_1',
                                                 'stop_2.link:link_6_5_car', 'stop_3.link:link_7_8_car']}, 'route': {
            'service_1_route_2': ['link_7_8_car', 'link_8_7_car', 'link_7_6_car', 'link_6_5_car', 'link_5_6_car',
                                  'artificial_link===from:node_6===to:stop_1',
                                  'artificial_link===from:stop_1===to:stop_1'],
            'service_1_route_1': ['artificial_link===from:stop_1===to:stop_1',
                                  'artificial_link===from:stop_1===to:node_5', 'link_5_6_car', 'link_6_7_car',
                                  'link_7_8_car']}})
    assert_semantically_equal(
        changeset.additional_links_modes,
        {'link_5_6_car': {'modes': ['bus', 'car']}, 'link_6_5_car': {'modes': ['bus', 'car']},
         'link_6_7_car': {'modes': ['bus', 'car']}, 'link_7_6_car': {'modes': ['bus', 'car']},
         'link_7_8_car': {'modes': ['bus', 'car']}, 'link_8_7_car': {'modes': ['bus', 'car']}}
    )
    assert_semantically_equal(
        changeset.new_links,
        {'artificial_link===from:stop_1===to:stop_1': {'from': 'stop_1', 'to': 'stop_1', 'modes': {'bus'}},
         'artificial_link===from:node_6===to:stop_1': {'from': 'node_6', 'to': 'stop_1', 'modes': {'bus'}},
         'artificial_link===from:stop_1===to:node_5': {'from': 'stop_1', 'to': 'node_5', 'modes': {'bus'}},
         'artificial_link===from:node_5===to:stop_1': {'from': 'node_5', 'to': 'stop_1', 'modes': {'bus'}},
         'artificial_link===from:stop_1===to:node_6': {'from': 'stop_1', 'to': 'node_6', 'modes': {'bus'}}}
    )
    assert_semantically_equal(
        changeset.new_nodes,
        {'stop_1': {'id': 'stop_1', 'x': 1.0, 'y': 2.5, 'name': '', 'lon': -7.557148552832129, 'lat': 49.76683027967191,
                    's2_id': 5205973754090340691}}
    )
    assert_semantically_equal(
        changeset.new_stops,
        {'stop_2.link:link_5_6_car': {'services': {'bus_service'}, 'routes': {'service_1_route_2'},
                                      'id': 'stop_2.link:link_5_6_car', 'x': 2.0, 'y': 2.5, 'epsg': 'epsg:27700',
                                      'name': '', 'lon': -7.557134732217642, 'lat': 49.76683094462549,
                                      's2_id': 5205973754090230267, 'additional_attributes': set(),
                                      'linkRefId': 'link_5_6_car', 'stop_id': 'stop_2'},
         'stop_3.link:link_7_8_car': {'services': {'bus_service'}, 'routes': {'service_1_route_2', 'service_1_route_1'},
                                      'id': 'stop_3.link:link_7_8_car', 'x': 5.5, 'y': 2.0, 'epsg': 'epsg:27700',
                                      'name': '', 'lon': -7.55708584676138, 'lat': 49.76682879603468,
                                      's2_id': 5205973754096513977, 'additional_attributes': set(),
                                      'linkRefId': 'link_7_8_car', 'stop_id': 'stop_3'},
         'stop_1.link:artificial_link===from:stop_1===to:stop_1': {'services': {'bus_service'},
                                                                   'routes': {'service_1_route_2', 'service_1_route_1'},
                                                                   'id': 'stop_1.link:artificial_link===from:stop_1===to:stop_1',
                                                                   'x': 1.0, 'y': 2.5, 'epsg': 'epsg:27700', 'name': '',
                                                                   'lon': -7.557148552832129, 'lat': 49.76683027967191,
                                                                   's2_id': 5205973754090340691,
                                                                   'additional_attributes': set(),
                                                                   'linkRefId': 'artificial_link===from:stop_1===to:stop_1',
                                                                   'stop_id': 'stop_1'},
         'stop_2.link:link_6_5_car': {'services': {'bus_service'}, 'routes': {'service_1_route_1'},
                                      'id': 'stop_2.link:link_6_5_car', 'x': 2.0, 'y': 2.5, 'epsg': 'epsg:27700',
                                      'name': '', 'lon': -7.557134732217642, 'lat': 49.76683094462549,
                                      's2_id': 5205973754090230267, 'additional_attributes': set(),
                                      'linkRefId': 'link_6_5_car', 'stop_id': 'stop_2'}}
    )

    changeset.new_pt_edges.sort()
    assert changeset.new_pt_edges == [('stop_1.link:artificial_link===from:stop_1===to:stop_1',
                                       'stop_2.link:link_5_6_car',
                                       {'services': {'bus_service'}, 'routes': {'service_1_route_1'}}), (
                                          'stop_1.link:artificial_link===from:stop_1===to:stop_1',
                                          'stop_2.link:link_6_5_car',
                                          {'services': {'bus_service'}, 'routes': {'service_1_route_1'}}), (
                                          'stop_2.link:link_5_6_car',
                                          'stop_1.link:artificial_link===from:stop_1===to:stop_1',
                                          {'services': {'bus_service'}, 'routes': {'service_1_route_2'}}), (
                                          'stop_2.link:link_5_6_car', 'stop_3.link:link_7_8_car',
                                          {'services': {'bus_service'}, 'routes': {'service_1_route_1'}}), (
                                          'stop_2.link:link_6_5_car',
                                          'stop_1.link:artificial_link===from:stop_1===to:stop_1',
                                          {'services': {'bus_service'}, 'routes': {'service_1_route_2'}}), (
                                          'stop_2.link:link_6_5_car', 'stop_3.link:link_7_8_car',
                                          {'services': {'bus_service'}, 'routes': {'service_1_route_1'}}), (
                                          'stop_3.link:link_7_8_car', 'stop_2.link:link_5_6_car',
                                          {'services': {'bus_service'}, 'routes': {'service_1_route_2'}}), (
                                          'stop_3.link:link_7_8_car', 'stop_2.link:link_6_5_car',
                                          {'services': {'bus_service'}, 'routes': {'service_1_route_2'}})]
    assert_semantically_equal(
        changeset.minimal_transfer_times,
        {('stop_1', 'stop_1.link:artificial_link===from:stop_1===to:stop_1'): 0.0,
         ('stop_2', 'stop_2.link:link_5_6_car'): 0.0,
         ('stop_3', 'stop_3.link:link_7_8_car'): 0.0,
         ('stop_1.link:artificial_link===from:stop_1===to:stop_1', 'stop_1'): 0.0,
         ('stop_2.link:link_5_6_car', 'stop_2'): 0.0,
         ('stop_3.link:link_7_8_car', 'stop_3'): 0.0,
         ('stop_2', 'stop_2.link:link_6_5_car'): 0.0,
         ('stop_2.link:link_6_5_car', 'stop_2'): 0.0}
    )
