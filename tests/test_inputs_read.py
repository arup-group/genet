from genet.inputs_handler import read
from tests.fixtures import *
from shapely.geometry import LineString


json_test_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_data", "json"))

def test_reading_json():
    n = read.read_json(network_path=os.path.join(json_test_folder, 'network.json'),
                       schedule_path=os.path.join(json_test_folder, 'schedule.json'),
                       epsg='epsg:27700')
    assert_semantically_equal(
        dict(n.nodes()),
        {'25508485': {'x': 528489.467895946, 'y': 182206.20303669575, 'lat': 51.52416253323928,
                      'lon': -0.14930198709481451, 's2_id': 5.221390301001263e+18, 'id': '25508485'},
         '21667818': {'x': 528504.1342843144, 'y': 182155.7435136598, 'lat': 51.523705733239396,
                      'lon': -0.14910908709500162, 's2_id': 5.221390302696205e+18, 'id': '21667818'},
         '295927764': {'x': 528358.873300625, 'y': 182147.63137142852, 'lat': 51.52366583323935,
                       'lon': -0.15120468709594614, 's2_id': 5.221390299830573e+18, 'id': '295927764'},
         '200048': {'x': 528364.6182191424, 'y': 182094.16422237465, 'lat': 51.52318403323943,
                    'lon': -0.1511413870962065, 's2_id': 5.221390299873156e+18, 'id': '200048'}}
    )
    assert_semantically_equal(
        dict(n.links()),
        {'1': {'from': '25508485', 'modes': {'car'}, 'oneway': '1', 's2_to': 5221390302696205321,
             'attributes': {
                 'osm:way:access': {'name': 'osm:way:access', 'class': 'java.lang.String', 'text': 'permissive'},
                 'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'unclassified'},
                 'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long', 'text': '26997928'},
                 'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String', 'text': 'Brunswick Place'}},
             'capacity': 600.0, 'freespeed': 4.166666666666667, 'to': '21667818', 'length': 52.76515108787025,
             'geometry': LineString([(528489.4679, 182206.20304), (528504.13428, 182155.74351)]),
             'permlanes': 1.0, 'id': '1', 's2_from': 5221390301001263407},
         '10': {'from': '200048', 'modes': {'car'}, 'oneway': '1', 's2_to': 5221390299830573099,
              'attributes': {
                  'osm:way:access': {'name': 'osm:way:access', 'class': 'java.lang.String', 'text': 'permissive'},
                  'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'unclassified'},
                  'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long', 'text': '26997927'},
                  'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String', 'text': 'Macfarren Place'}},
              'capacity': 600.0, 'freespeed': 4.166666666666667, 'to': '295927764', 'length': 53.775084358791744,
              'geometry': LineString([(528364.61822, 182094.16422), (528358.8733, 182147.63137)]),
              'permlanes': 1.0, 'id': '10', 's2_from': 5221390299873156021}}
    )
    g = n.schedule._graph.graph
    del g['change_log']
    assert_semantically_equal(
        n.schedule._graph.graph,
        {'name': 'Schedule graph', 'route_to_service_map': {'VJ6c64ab7b477e201cae950efde5bd0cb4e2e8888e': '20274'},
         'service_to_route_map': {'20274': ['VJ6c64ab7b477e201cae950efde5bd0cb4e2e8888e']},
         'routes': {'VJ6c64ab7b477e201cae950efde5bd0cb4e2e8888e':
                        {'route_short_name': 'N55', 'mode': 'bus',
                         'trips': {'trip_id': ['VJ4e00b97ca9c6c0c96da8f793dfbd37b11f647fa7_03:40:00'],
                                   'trip_departure_time': ['03:40:00'],
                                   'vehicle_id': ['veh_0_bus']},
                         'arrival_offsets': ['00:00:00', '00:02:20'],
                         'departure_offsets': ['00:00:00', '00:02:20'],
                         'route_long_name': '',
                         'id': 'VJ6c64ab7b477e201cae950efde5bd0cb4e2e8888e',
                         'route': ['1', '10'],
                         'await_departure': [True, True],
                         'ordered_stops': ['490000235X.link:1', '490000235YB.link:10']}},
         'services': {'20274': {'id': '20274', 'name': 'N55'}}, 'crs': {'init': 'epsg:27700'}}
    )
    assert_semantically_equal(
        dict(n.schedule._graph.nodes(data=True)),
        {'490000235X.link:1': {'services': {'20274'}, 'routes': {'VJ6c64ab7b477e201cae950efde5bd0cb4e2e8888e'},
                               'id': '490000235X.link:1', 'x': 529981.7958802709, 'y': 181412.0975758662,
                               'epsg': 'epsg:27700', 'name': 'Tottenham Court Road Station (Stop X)',
                               'lat': -0.12809598708996447, 'lon': 51.51668503324075, 's2_id': 2507584377443783851,
                               'additional_attributes': {'isBlocking', 'linkRefId'}, 'isBlocking': 'false',
                               'linkRefId': '1'},
         '490000235YB.link:10': {'services': {'20274'}, 'routes': {'VJ6c64ab7b477e201cae950efde5bd0cb4e2e8888e'},
                                 'id': '490000235YB.link:10', 'x': 529570.7813227688, 'y': 181336.2815925331,
                                 'epsg': 'epsg:27700', 'name': 'Oxford Street  Soho Street (Stop YB)',
                                 'lat': -0.13404398709291862, 'lon': 51.51609803324078, 's2_id': 2507584474601580133,
                                 'additional_attributes': {'isBlocking', 'linkRefId'}, 'isBlocking': 'false',
                                 'linkRefId': '10'}}
    )


geojson_test_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_data", "geojson"))

def test_reading_geojson():
    n = read.read_geojson_network(nodes_path=os.path.join(geojson_test_folder, 'network_nodes.geojson'),
                                  links_path=os.path.join(geojson_test_folder, 'network_links.geojson'),
                                  epsg='epsg:27700')
    assert_semantically_equal(
        dict(n.nodes()),
        {'25508485': {'x': 528489.467895946, 'y': 182206.20303669575, 'lat': 51.52416253323928,
                      'lon': -0.14930198709481451, 's2_id': 5.221390301001263e+18, 'id': '25508485'},
         '21667818': {'x': 528504.1342843144, 'y': 182155.7435136598, 'lat': 51.523705733239396,
                      'lon': -0.14910908709500162, 's2_id': 5.221390302696205e+18, 'id': '21667818'},
         '295927764': {'x': 528358.873300625, 'y': 182147.63137142852, 'lat': 51.52366583323935,
                       'lon': -0.15120468709594614, 's2_id': 5.221390299830573e+18, 'id': '295927764'},
         '200048': {'x': 528364.6182191424, 'y': 182094.16422237465, 'lat': 51.52318403323943,
                    'lon': -0.1511413870962065, 's2_id': 5.221390299873156e+18, 'id': '200048'}}
    )
    links = dict(n.links())
    assert [(round(x, 6), round(y, 6)) for x,y in links['1']['geometry'].coords] == [(528489.467896, 182206.203037), (528504.134284, 182155.743514)]
    assert [(round(x, 6), round(y, 6)) for x,y in links['10']['geometry'].coords] == [(528364.618219, 182094.164222), (528358.873301, 182147.631371)]
    del links['1']['geometry']
    del links['10']['geometry']
    assert_semantically_equal(
        links,
        {'1': {'from': '25508485', 'modes': {'car'}, 'oneway': '1', 's2_to': 5221390302696205321,
               'attributes': {
                   'osm:way:access': {'name': 'osm:way:access', 'class': 'java.lang.String', 'text': 'permissive'},
                   'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'unclassified'},
                   'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long', 'text': '26997928'},
                   'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String', 'text': 'Brunswick Place'}},
               'capacity': 600.0, 'freespeed': 4.166666666666667, 'to': '21667818', 'length': 52.76515108787025,
               'permlanes': 1.0, 'id': '1', 's2_from': 5221390301001263407},
         '10': {'from': '200048', 'modes': {'car'}, 'oneway': '1', 's2_to': 5221390299830573099,
                'attributes': {
                    'osm:way:access': {'name': 'osm:way:access', 'class': 'java.lang.String', 'text': 'permissive'},
                    'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'unclassified'},
                    'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long', 'text': '26997927'},
                    'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String', 'text': 'Macfarren Place'}},
                'capacity': 600.0, 'freespeed': 4.166666666666667, 'to': '295927764', 'length': 53.775084358791744,
                'permlanes': 1.0, 'id': '10', 's2_from': 5221390299873156021}}
    )


csv_test_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_data", "csv"))


def test_reading_network_csv():
    n = read.read_csv(os.path.join(csv_test_folder, 'nodes.csv'), os.path.join(csv_test_folder, 'links.csv'),
                      'epsg:27700')
    assert_semantically_equal(
        dict(n.nodes()),
        {'25508485': {'x': 528489.467895946, 'y': 182206.20303669575, 'lat': 51.52416253323928,
                      'lon': -0.14930198709481451, 's2_id': 5.221390301001263e+18, 'id': '25508485'},
         '21667818': {'x': 528504.1342843144, 'y': 182155.7435136598, 'lat': 51.523705733239396,
                      'lon': -0.14910908709500162, 's2_id': 5.221390302696205e+18, 'id': '21667818'},
         '295927764': {'x': 528358.873300625, 'y': 182147.63137142852, 'lat': 51.52366583323935,
                       'lon': -0.15120468709594614, 's2_id': 5.221390299830573e+18, 'id': '295927764'},
         '200048': {'x': 528364.6182191424, 'y': 182094.16422237465, 'lat': 51.52318403323943,
                    'lon': -0.1511413870962065, 's2_id': 5.221390299873156e+18, 'id': '200048'}}
    )
    assert_semantically_equal(
        dict(n.links()),
        {'1': {'from': '25508485', 'modes': {'car'}, 'oneway': 1, 's2_to': 5221390302696205321,
             'attributes': {
                 'osm:way:access': {'name': 'osm:way:access', 'class': 'java.lang.String', 'text': 'permissive'},
                 'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'unclassified'},
                 'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long', 'text': '26997928'},
                 'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String', 'text': 'Brunswick Place'}},
             'capacity': 600.0, 'freespeed': 4.166666666666667, 'to': '21667818', 'length': 52.76515108787025,
             'geometry': LineString([(528489.4679, 182206.20304), (528504.13428, 182155.74351)]),
             'permlanes': 1.0, 'id': '1', 's2_from': 5221390301001263407},
         '10': {'from': '200048', 'modes': {'car'}, 'oneway': 1, 's2_to': 5221390299830573099,
              'attributes': {
                  'osm:way:access': {'name': 'osm:way:access', 'class': 'java.lang.String', 'text': 'permissive'},
                  'osm:way:highway': {'name': 'osm:way:highway', 'class': 'java.lang.String', 'text': 'unclassified'},
                  'osm:way:id': {'name': 'osm:way:id', 'class': 'java.lang.Long', 'text': '26997927'},
                  'osm:way:name': {'name': 'osm:way:name', 'class': 'java.lang.String', 'text': 'Macfarren Place'}},
              'capacity': 600.0, 'freespeed': 4.166666666666667, 'to': '295927764', 'length': 53.775084358791744,
              'geometry': LineString([(528364.61822, 182094.16422), (528358.8733, 182147.63137)]),
              'permlanes': 1.0, 'id': '10', 's2_from': 5221390299873156021}}
    )


gtfs_test_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_data", "gtfs"))


def test_read_gtfs_returns_expected_schedule(correct_stops_to_service_mapping_from_test_gtfs,
                                             correct_stops_to_route_mapping_from_test_gtfs):
    schedule = read.read_gtfs(gtfs_test_folder, '20190604')

    assert schedule['1001'] == Service(
        '1001',
        [Route(
            route_short_name='BTR',
            mode='bus',
            stops=[Stop(id='BSE', x=-0.1413621, y=51.5226864, epsg='epsg:4326'),
                   Stop(id='BSN', x=-0.140053, y=51.5216199, epsg='epsg:4326')],
            trips={'trip_id': ['BT1'], 'trip_departure_time': ['03:21:00'], 'vehicle_id': ['veh_0_bus']},
            arrival_offsets=['0:00:00', '0:02:00'],
            departure_offsets=['0:00:00', '0:02:00']
        )])
    assert schedule['1002'] == Service(
        '1002',
        [Route(
            route_short_name='RTR',
            mode='rail',
            stops=[Stop(id='RSN', x=-0.1410946, y=51.5231335, epsg='epsg:4326'),
                   Stop(id='RSE', x=-0.1421595, y=51.5192615, epsg='epsg:4326')],
            trips={'trip_id': ['RT1'], 'trip_departure_time': ['03:21:00'], 'vehicle_id': ['veh_1_rail']},
            arrival_offsets=['0:00:00', '0:02:00'],
            departure_offsets=['0:00:00', '0:02:00']
        )])
    assert_semantically_equal(schedule.stop_to_service_ids_map(), correct_stops_to_service_mapping_from_test_gtfs)
    assert_semantically_equal(schedule.stop_to_route_ids_map(), correct_stops_to_route_mapping_from_test_gtfs)
