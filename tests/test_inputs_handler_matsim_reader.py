from pyproj import Proj, Transformer
from shapely.geometry import LineString
from genet.inputs_handler import matsim_reader, read
from tests.fixtures import *

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
pt2matsim_network_test_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "network.xml"))
pt2matsim_network_multiple_edges_test_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "network_multiple_edges.xml"))
pt2matsim_network_clashing_link_ids_test_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "network_clashing_link_ids.xml"))
pt2matsim_network_clashing_node_ids_test_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "network_clashing_node_ids.xml"))
matsim_output_network = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "matsim_output_network.xml"))
pt2matsim_network_with_geometry_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "network_with_geometry.xml"))
pt2matsim_network_with_singular_geometry_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "network_with_singular_geometry.xml"))
pt2matsim_NZ_network = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "NZ_network.xml"))
pt2matsim_schedule_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "schedule.xml"))
pt2matsim_vehicles_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "vehicles.xml"))


def test_read_network_builds_graph_with_correct_data_on_nodes_and_edges():
    correct_nodes = {
        '21667818': {'id': '21667818', 's2_id': 5221390302696205321, 'x': 528504.1342843144, 'y': 182155.7435136598,
                     'lon': -0.14910908709500162, 'lat': 51.52370573323939},
        '25508485': {'id': '25508485', 's2_id': 5221390301001263407, 'x': 528489.467895946, 'y': 182206.20303669578,
                     'lon': -0.14930198709481451, 'lat': 51.524162533239284}}

    correct_edges = {'25508485_21667818': {
        'id': "1", 'from': "25508485", 'to': "21667818", 'length': 52.765151087870265,
        's2_from': 5221390301001263407, 's2_to': 5221390302696205321,
        'freespeed': 4.166666666666667, 'capacity': 600.0, 'permlanes': 1.0, 'oneway': "1",
        'modes': {'subway', 'metro', 'walk', 'car'}, 'attributes': {
            'osm:way:access': {'name': 'osm:way:access', 'class': 'java.lang.String', 'text': 'permissive'},
            'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'unclassified'},
            'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long', 'text': '26997928'},
            'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String', 'text': 'Brunswick Place'}
        }}}

    transformer = Transformer.from_proj(Proj('epsg:27700'), Proj('epsg:4326'), always_xy=True)

    g, link_id_mapping, duplicated_nodes, duplicated_link_ids = matsim_reader.read_network(pt2matsim_network_test_file,
                                                                                           transformer)

    for u, data in g.nodes(data=True):
        assert str(u) in correct_nodes
        assert_semantically_equal(data, correct_nodes[str(u)])

    assert_semantically_equal(duplicated_nodes, {})

    for u, v, data in g.edges(data=True):
        edge = '{}_{}'.format(u, v)
        assert edge in correct_edges
        assert_semantically_equal(data, correct_edges[edge])

    assert_semantically_equal(duplicated_link_ids, {})


def test_reading_NZ_network():
    n = read.read_matsim(path_to_network=pt2matsim_NZ_network, epsg='epsg:2193')
    assert_semantically_equal(dict(n.nodes()), {
        '7872447671905026061': {'id': '7872447671905026061', 'x': 1789300.631705982, 'y': 5494320.626099871,
                                'lon': 175.23998223484716, 'lat': -40.68028521526985, 's2_id': 7872447671905026061},
        '7858001326813216825': {'id': '7858001326813216825', 'x': 1756643.5667029365, 'y': 5937269.480530882,
                                'lon': 174.75350860744126, 'lat': -36.697337065329855, 's2_id': 7858001326813216825}})
    assert_semantically_equal(dict(n.links()), {
        '1': {'id': '1', 'from': '7858001326813216825', 'to': '7872447671905026061', 'freespeed': 4.166666666666667,
              'capacity': 600.0, 'permlanes': 1.0, 'oneway': '1', 'modes': {'car', 'walk'},
              's2_from': 7858001326813216825, 's2_to': 7872447671905026061, 'attributes': {
                'osm:way:access': {'name': 'osm:way:access', 'class': 'java.lang.String', 'text': 'permissive'}},
              'length': 52.765151087870265}})


def test_read_network_builds_graph_with_multiple_edges_with_correct_data_on_nodes_and_edges():
    correct_nodes = {
        '21667818': {'id': '21667818', 's2_id': 5221390302696205321, 'x': 528504.1342843144, 'y': 182155.7435136598,
                     'lon': -0.14910908709500162, 'lat': 51.52370573323939},
        '25508485': {'id': '25508485', 's2_id': 5221390301001263407, 'x': 528489.467895946, 'y': 182206.20303669578,
                     'lon': -0.14930198709481451, 'lat': 51.524162533239284}}

    correct_edges = {'25508485_21667818': {
        0: {
            'id': "1", 'from': "25508485", 'to': "21667818", 'length': 52.765151087870265,
            's2_from': 5221390301001263407, 's2_to': 5221390302696205321,
            'freespeed': 4.166666666666667, 'capacity': 600.0, 'permlanes': 1.0, 'oneway': "1",
            'modes': {'walk', 'car'}, 'attributes': {
                'osm:way:access': {'name': 'osm:way:access', 'class': 'java.lang.String', 'text': 'permissive'},
                'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'unclassified'},
                'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long', 'text': '26997928'},
                'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String', 'text': 'Brunswick Place'}}
        },
        1: {
            'id': "2", 'from': "25508485", 'to': "21667818", 'length': 52.765151087870265,
            's2_from': 5221390301001263407, 's2_to': 5221390302696205321,
            'freespeed': 4.166666666666667, 'capacity': 600.0, 'permlanes': 1.0, 'oneway': "1",
            'modes': {'bus'}, 'attributes': {
                'osm:way:lanes': {'name': 'osm:way:lanes', 'class': 'java.lang.String', 'text': '1'},
                'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'unclassified'},
                'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long', 'text': '26997928'},
                'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String', 'text': 'Brunswick Place'},
                'osm:way:oneway': {'name': 'osm:way:oneway', 'class': 'java.lang.String', 'text': 'yes'},
                'osm:relation:route': {'class': 'java.lang.String', 'name': 'osm:relation:route',
                                       'text': {'bus', 'bicycle'}}
            }
        }}}

    correct_link_id_map = {'1': {'from': '25508485', 'to': '21667818', 'multi_edge_idx': 0},
                           '2': {'from': '25508485', 'to': '21667818', 'multi_edge_idx': 1}}

    transformer = Transformer.from_proj(Proj('epsg:27700'), Proj('epsg:4326'), always_xy=True)

    g, link_id_mapping, duplicated_nodes, duplicated_link_ids = matsim_reader.read_network(
        pt2matsim_network_multiple_edges_test_file, transformer)

    for u, data in g.nodes(data=True):
        assert str(u) in correct_nodes
        assert_semantically_equal(data, correct_nodes[str(u)])

    assert_semantically_equal(duplicated_nodes, {})

    for edge in g.edges:
        e = '{}_{}'.format(edge[0], edge[1])
        assert e in correct_edges
        assert edge[2] in correct_edges[e]
        assert_semantically_equal(g[edge[0]][edge[1]][edge[2]], correct_edges[e][edge[2]])

    assert correct_link_id_map == link_id_mapping
    assert_semantically_equal(duplicated_link_ids, {})


def test_read_network_builds_graph_with_unique_links_given_matsim_network_with_clashing_link_ids():
    correct_nodes = {
        '21667818': {'id': '21667818', 's2_id': 5221390302696205321, 'x': 528504.1342843144, 'y': 182155.7435136598,
                     'lon': -0.14910908709500162, 'lat': 51.52370573323939},
        '25508485': {'id': '25508485', 's2_id': 5221390301001263407, 'x': 528489.467895946, 'y': 182206.20303669578,
                     'lon': -0.14930198709481451, 'lat': 51.524162533239284}}

    correct_edges = {'25508485_21667818': {
        0: {
            'id': "1", 'from': "25508485", 'to': "21667818", 'length': 52.765151087870265,
            's2_from': 5221390301001263407, 's2_to': 5221390302696205321,
            'freespeed': 4.166666666666667, 'capacity': 600.0, 'permlanes': 1.0, 'oneway': "1",
            'modes': {'walk', 'car'}, 'attributes': {
                'osm:way:access': {'name': 'osm:way:access', 'class': 'java.lang.String', 'text': 'permissive'},
                'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'unclassified'},
                'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long', 'text': '26997928'},
                'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String', 'text': 'Brunswick Place'}}
        },
        1: {
            'id': "1_1", 'from': "25508485", 'to': "21667818", 'length': 52.765151087870265,
            's2_from': 5221390301001263407, 's2_to': 5221390302696205321,
            'freespeed': 4.166666666666667, 'capacity': 600.0, 'permlanes': 1.0, 'oneway': "1",
            'modes': {'bus'}, 'attributes': {
                'osm:way:lanes': {'name': 'osm:way:lanes', 'class': 'java.lang.String', 'text': '1'},
                'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'unclassified'},
                'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long', 'text': '26997928'},
                'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String', 'text': 'Brunswick Place'},
                'osm:way:oneway': {'name': 'osm:way:oneway', 'class': 'java.lang.String', 'text': 'yes'},
                'osm:relation:route': {'class': 'java.lang.String', 'name': 'osm:relation:route',
                                       'text': {'bus', 'bicycle'}}
            }
        }}}

    correct_link_id_map = {'1': {'from': '25508485', 'to': '21667818', 'multi_edge_idx': 0},
                           '1_1': {'from': '25508485', 'to': '21667818', 'multi_edge_idx': 1}}

    transformer = Transformer.from_proj(Proj('epsg:27700'), Proj('epsg:4326'), always_xy=True)

    g, link_id_mapping, duplicated_nodes, duplicated_link_ids = matsim_reader.read_network(
        pt2matsim_network_clashing_link_ids_test_file, transformer)

    assert len(g.nodes) == len(correct_nodes)
    for u, data in g.nodes(data=True):
        assert str(u) in correct_nodes
        assert_semantically_equal(data, correct_nodes[str(u)])

    assert_semantically_equal(duplicated_nodes, {})

    for edge in g.edges:
        e = '{}_{}'.format(edge[0], edge[1])
        assert e in correct_edges
        assert edge[2] in correct_edges[e]
        assert_semantically_equal(g[edge[0]][edge[1]][edge[2]], correct_edges[e][edge[2]])

    assert_semantically_equal(correct_link_id_map, link_id_mapping)
    assert_semantically_equal(duplicated_link_ids, {'1': ['1_1']})


def test_read_network_rejects_non_unique_nodes():
    correct_nodes = {
        '21667818': {'id': '21667818', 's2_id': 5221390302696205321, 'x': 528504.1342843144, 'y': 182155.7435136598,
                     'lon': -0.14910908709500162, 'lat': 51.52370573323939},
        '25508485': {'id': '25508485', 's2_id': 5221390301001263407, 'x': 528489.467895946, 'y': 182206.20303669578,
                     'lon': -0.14930198709481451, 'lat': 51.524162533239284}}

    correct_edges = {'25508485_21667818': {
        0: {
            'id': "1", 'from': "25508485", 'to': "21667818", 'length': 52.765151087870265,
            's2_from': 5221390301001263407, 's2_to': 5221390302696205321,
            'freespeed': 4.166666666666667, 'capacity': 600.0, 'permlanes': 1.0, 'oneway': "1",
            'modes': {'walk', 'car'}, 'attributes': {
                'osm:way:access': {'name': 'osm:way:access', 'class': 'java.lang.String', 'text': 'permissive'},
                'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'unclassified'},
                'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long', 'text': '26997928'},
                'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String', 'text': 'Brunswick Place'}}
        }}}

    correct_link_id_map = {'1': {'from': '25508485', 'to': '21667818', 'multi_edge_idx': 0}}

    transformer = Transformer.from_proj(Proj('epsg:27700'), Proj('epsg:4326'), always_xy=True)

    g, link_id_mapping, duplicated_nodes, duplicated_link_ids = matsim_reader.read_network(
        pt2matsim_network_clashing_node_ids_test_file, transformer)

    assert len(g.nodes) == len(correct_nodes)
    for u, data in g.nodes(data=True):
        assert str(u) in correct_nodes
        assert_semantically_equal(data, correct_nodes[str(u)])

    assert_semantically_equal(duplicated_nodes, {
        '21667818': [{'id': '21667818', 'x': 528504.1342843144, 'y': 182155.7435136598, 'lon': -0.14910908709500162,
                      'lat': 51.52370573323939, 's2_id': 5221390302696205321}]})

    assert len(g.edges) == len(correct_edges)
    for edge in g.edges:
        e = '{}_{}'.format(edge[0], edge[1])
        assert e in correct_edges
        assert edge[2] in correct_edges[e]
        assert_semantically_equal(g[edge[0]][edge[1]][edge[2]], correct_edges[e][edge[2]])

    assert_semantically_equal(correct_link_id_map, link_id_mapping)
    assert_semantically_equal(duplicated_link_ids, {})


def test_reading_matsim_output_network():
    n = read.read_matsim(path_to_network=matsim_output_network, epsg='epsg:27700')

    correct_nodes = {
        '21667818': {'id': '21667818', 's2_id': 5221390302696205321, 'x': 528504.1342843144, 'y': 182155.7435136598,
                     'lon': -0.14910908709500162, 'lat': 51.52370573323939},
        '25508485': {'id': '25508485', 's2_id': 5221390301001263407, 'x': 528489.467895946, 'y': 182206.20303669578,
                     'lon': -0.14930198709481451, 'lat': 51.524162533239284}}

    correct_edge = {'id': '1', 'from': '25508485', 'to': '21667818', 'freespeed': 4.166666666666667,
                    'capacity': 600.0, 'permlanes': 1.0, 'oneway': '1', 'modes': {'car', 'subway', 'metro', 'walk'},
                    's2_from': 5221390301001263407, 's2_to': 5221390302696205321, 'length': 52.765151087870265,
                    'attributes': {'osm:way:access': {'name': 'osm:way:access', 'class': 'java.lang.String',
                                                      'text': 'permissive'},
                                   'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String',
                                                       'text': 'unclassified'},
                                   'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long',
                                                  'text': '26997928'},
                                   'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String',
                                                    'text': 'Brunswick Place'}}}

    assert_semantically_equal(dict(n.graph.nodes(data=True)), correct_nodes)
    assert_semantically_equal(list(n.graph.edges(data=True))[0][2], correct_edge)


def test_reading_network_with_geometry_attributes():
    correct_links = {'1': {
        'id': "1", 'from': "25508485", 'to': "21667818", 'length': 52.765151087870265,
        's2_from': 5221390301001263407, 's2_to': 5221390302696205321,
        'freespeed': 4.166666666666667, 'capacity': 600.0, 'permlanes': 1.0, 'oneway': "1",
        'geometry': LineString([(1, 2), (2, 3), (3, 4)]),
        'modes': {'car'}, 'attributes': {
            'osm:way:access': {'name': 'osm:way:access', 'class': 'java.lang.String', 'text': 'permissive'},
            'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'unclassified'},
            'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long', 'text': '26997928'},
            'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String', 'text': 'Brunswick Place'}
        }},
        '2': {
            'id': "2", 'from': "25508485", 'to': "21667818", 'length': 52.765151087870265,
            's2_from': 5221390301001263407, 's2_to': 5221390302696205321,
            'freespeed': 4.166666666666667, 'capacity': 600.0, 'permlanes': 1.0, 'oneway': "1",
            'geometry': LineString([(1, 2), (2, 3), (3, 4)]),
            'modes': {'car'}, 'attributes': {
                'osm:way:access': {'name': 'osm:way:access', 'class': 'java.lang.String', 'text': 'permissive'},
                'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'unclassified'},
                'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long', 'text': '26997928'},
                'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String', 'text': 'Brunswick Place'}
            }}
    }
    n = read.read_matsim(path_to_network=pt2matsim_network_with_geometry_file, epsg='epsg:27700')

    assert_semantically_equal(dict(n.links()), correct_links)


def test_reading_network_with_singular_geometry_attribute_cleans_up_empty_attributes_dict():
    correct_links = {
        '1': {
            'id': "1", 'from': "25508485", 'to': "21667818", 'length': 52.765151087870265,
            's2_from': 5221390301001263407, 's2_to': 5221390302696205321,
            'freespeed': 4.166666666666667, 'capacity': 600.0, 'permlanes': 1.0, 'oneway': "1",
            'geometry': LineString([(1, 2), (2, 3), (3, 4)]),
            'modes': {'car'}
        },
        '2': {
            'id': "2", 'from': "25508485", 'to': "21667818", 'length': 52.765151087870265,
            's2_from': 5221390301001263407, 's2_to': 5221390302696205321,
            'freespeed': 4.166666666666667, 'capacity': 600.0, 'permlanes': 1.0, 'oneway': "1",
            'geometry': LineString([(1, 2), (2, 3), (3, 4)]),
            'modes': {'car'}
        }
    }
    n = read.read_matsim(path_to_network=pt2matsim_network_with_singular_geometry_file, epsg='epsg:27700')

    assert_semantically_equal(dict(n.links()), correct_links)


def test_read_schedule_reads_the_data_correctly(correct_services_from_test_pt2matsim_schedule):
    services, minimalTransferTimes = matsim_reader.read_schedule(pt2matsim_schedule_file, 'epsg:27700')

    correct_minimalTransferTimes = {
        '26997928P': {'stop': '26997928P.link:1', 'transferTime': 0.0},
    }

    assert correct_services_from_test_pt2matsim_schedule == services
    assert_semantically_equal(minimalTransferTimes, correct_minimalTransferTimes)


def test_reading_pt2matsim_vehicles():
    vehicles, vehicle_types = matsim_reader.read_vehicles(pt2matsim_vehicles_file)

    assert_semantically_equal(vehicles, {'veh_0_bus': {'type': 'bus'}})
    assert_semantically_equal(vehicle_types, {
        'bus': {'capacity': {'seats': {'persons': '71'}, 'standingRoom': {'persons': '1'}},
                'length': {'meter': '18.0'},
                'width': {'meter': '2.5'},
                'accessTime': {'secondsPerPerson': '0.5'},
                'egressTime': {'secondsPerPerson': '0.5'},
                'doorOperation': {'mode': 'serial'},
                'passengerCarEquivalents': {'pce': '2.8'}}})
