import pytest
import json
import polyline
import logging
import time
import os
import sys
from requests.models import Response
from requests_futures.sessions import FuturesSession
from genet.utils import google_directions
from genet.utils import secrets_vault
from genet.core import Network
from tests.fixtures import assert_semantically_equal, assert_logging_warning_caught_with_message_containing

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
example_google_speed_data = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "example_google_speed_data"))


@pytest.fixture()
def generated_request():
    nodes = {'107316': {'lat': 51.5188864, 'lon': -0.1369442},
             '2440643031': {'lat': 51.5189281, 'lon': -0.1370038},
             '4307345276': {'lat': 51.5195381, 'lon': -0.1376626},
             '107317': {'lat': 51.5195849, 'lon': -0.1377132},
             '4307345495': {'lat': 51.5198314, 'lon': -0.1379737},
             '4307345497': {'lat': 51.5198582, 'lon': -0.138002},
             '25495448': {'lat': 51.5199079, 'lon': -0.1380552},
             '2503102618': {'lat': 51.5199476, 'lon': -0.1380787},
             '107351': {'lat': 51.5202242, 'lon': -0.1384011},
             '5411344775': {'lat': 51.5203194, 'lon': -0.138511},
             '2440651577': {'lat': 51.5207157, 'lon': -0.1389682},
             '2440651556': {'lat': 51.5207519, 'lon': -0.1390114},
             '2440651552': {'lat': 51.520783, 'lon': -0.1390444},
             '107352': {'lat': 51.5208299, 'lon': -0.1391027}}
    path = ['107316', '2440643031', '4307345276', '107317', '4307345495', '4307345497', '25495448', '2503102618',
            '107351', '5411344775', '2440651577', '2440651556', '2440651552', '107352']
    encoded_polyline = polyline.encode([(nodes[node]['lat'], nodes[node]['lon']) for node in path])
    return {'path_nodes': path,
            'path_polyline': encoded_polyline,
            'origin': nodes[path[0]],
            'destination': nodes[path[-1]]}


@pytest.fixture()
def google_directions_api_response():
    response = Response()
    response.status_code = 200
    response._content = json.dumps({
        "geocoded_waypoints": [
            {
                "geocoder_status": "OK",
                "place_id": "ChIJQbcuHzwbdkgRamIMZzZGjxg",
                "types": ["cafe", "establishment", "food", "point_of_interest"]
            },
            {
                "geocoder_status": "OK",
                "place_id": "ChIJi8rZjSkbdkgRBluJBmAZK1w",
                "types": ["street_address"]
            }
        ],
        "routes": [
            {
                "bounds": {
                    "northeast": {
                        "lat": 51.5208376,
                        "lng": -0.1369381
                    },
                    "southwest": {
                        "lat": 51.5188908,
                        "lng": -0.1391098
                    }
                },
                "copyrights": "Map data ©2020 Google",
                "legs": [
                    {
                        "distance": {
                            "text": "0.3 km",
                            "value": 264
                        },
                        "duration": {
                            "text": "1 min",
                            "value": 71
                        },
                        "end_address": "65 Cleveland St, Fitzrovia, London W1T 4JZ, UK",
                        "end_location": {
                            "lat": 51.5208376,
                            "lng": -0.1391098
                        },
                        "start_address": "49 Newman St, Fitzrovia, London W1T 3DZ, UK",
                        "start_location": {
                            "lat": 51.5188908,
                            "lng": -0.1369381
                        },
                        "steps": [
                            {
                                "distance": {
                                    "text": "0.3 km",
                                    "value": 264
                                },
                                "duration": {
                                    "text": "1 min",
                                    "value": 71
                                },
                                "end_location": {
                                    "lat": 51.5208376,
                                    "lng": -0.1391098
                                },
                                "html_instructions": "Head \u003cb\u003enorth-west\u003c/b\u003e on \u003cb\u003eCleveland St\u003c/b\u003e towards \u003cb\u003eTottenham St\u003c/b\u003e",
                                "polyline": {
                                    "points": "ahmyHzvYCBCFs@t@oAtAaAdAy@bAA@WX_AjAc@f@"
                                },
                                "start_location": {
                                    "lat": 51.5188908,
                                    "lng": -0.1369381
                                },
                                "travel_mode": "DRIVING"
                            }
                        ],
                        "traffic_speed_entry": [],
                        "via_waypoint": []
                    }
                ],
                "overview_polyline": {
                    "points": "ahmyHzvYkCvCuCdDcBrB"
                },
                "summary": "Cleveland St",
                "warnings": [],
                "waypoint_order": []
            }
        ],
        "status": "OK"
    }).encode('utf-8')
    return response


@pytest.fixture()
def google_directions_api_response_multiple_legs():
    response = Response()
    response.status_code = 200
    response._content = json.dumps({
        "geocoded_waypoints": [
            {
                "geocoder_status": "OK",
                "place_id": "ChIJOTfQ9isbdkgR_-PC_VFWNUs",
                "types": ["street_address"]
            },
            {
                "geocoder_status": "OK",
                "place_id": "ChIJQbcuHzwbdkgRamIMZzZGjxg",
                "types": ["cafe", "establishment", "food", "point_of_interest"]
            }
        ],
        "routes": [
            {
                "bounds": {
                    "northeast": {
                        "lat": 51.5193916,
                        "lng": -0.1356769
                    },
                    "southwest": {
                        "lat": 51.5188908,
                        "lng": -0.1369381
                    }
                },
                "copyrights": "Map data ©2020 Google",
                "legs": [
                    {
                        "distance": {
                            "text": "0.1 km",
                            "value": 104
                        },
                        "duration": {
                            "text": "1 min",
                            "value": 44
                        },
                        "end_address": "49 Newman St, Fitzrovia, London W1T 3DZ, UK",
                        "end_location": {
                            "lat": 51.5188908,
                            "lng": -0.1369381
                        },
                        "start_address": "42 Charlotte St, Fitzrovia, London W1T 2NP, UK",
                        "start_location": {
                            "lat": 51.5193916,
                            "lng": -0.1356769
                        },
                        "steps": [
                            {
                                "distance": {
                                    "text": "0.1 km",
                                    "value": 104
                                },
                                "duration": {
                                    "text": "1 min",
                                    "value": 44
                                },
                                "end_location": {
                                    "lat": 51.5188908,
                                    "lng": -0.1369381
                                },
                                "html_instructions": "Head \u003cb\u003esouth-west\u003c/b\u003e on \u003cb\u003eGoodge St\u003c/b\u003e/\u003cwbr/\u003e\u003cb\u003eA5204\u003c/b\u003e towards \u003cb\u003eCharlotte Pl\u003c/b\u003e",
                                "polyline": {
                                    "points": "ekmyH~nYRp@Rp@?@DLRr@Rp@L`@"
                                },
                                "start_location": {
                                    "lat": 51.5193916,
                                    "lng": -0.1356769
                                },
                                "travel_mode": "DRIVING"
                            }
                        ],
                        "traffic_speed_entry": [],
                        "via_waypoint": []
                    },
                    {
                        "distance": {
                            "text": "0.1 km",
                            "value": 104
                        },
                        "duration": {
                            "text": "1 min",
                            "value": 44
                        },
                        "end_address": "49 Newman St, Fitzrovia, London W1T 3DZ, UK",
                        "end_location": {
                            "lat": 51.5188908,
                            "lng": -0.1369381
                        },
                        "start_address": "42 Charlotte St, Fitzrovia, London W1T 2NP, UK",
                        "start_location": {
                            "lat": 51.5193916,
                            "lng": -0.1356769
                        },
                        "steps": [
                            {
                                "distance": {
                                    "text": "0.1 km",
                                    "value": 104
                                },
                                "duration": {
                                    "text": "1 min",
                                    "value": 44
                                },
                                "end_location": {
                                    "lat": 51.5188908,
                                    "lng": -0.1369381
                                },
                                "html_instructions": "Head \u003cb\u003esouth-west\u003c/b\u003e on \u003cb\u003eGoodge St\u003c/b\u003e/\u003cwbr/\u003e\u003cb\u003eA5204\u003c/b\u003e towards \u003cb\u003eCharlotte Pl\u003c/b\u003e",
                                "polyline": {
                                    "points": "ekmyH~nYRp@Rp@?@DLRr@Rp@L`@"
                                },
                                "start_location": {
                                    "lat": 51.5193916,
                                    "lng": -0.1356769
                                },
                                "travel_mode": "DRIVING"
                            }
                        ],
                        "traffic_speed_entry": [],
                        "via_waypoint": []
                    }
                ],
                "overview_polyline": {
                    "points": "ekmyH~nYbBzFblahblah"
                },
                "summary": "Goodge St/A5204",
                "warnings": [],
                "waypoint_order": []
            }
        ],
        "status": "OK"
    }).encode('utf-8')
    return response


@pytest.fixture()
def empty_response():
    response = Response()
    response.status_code = 200
    response._content = json.dumps({"geocoded_waypoints": [{}, {}], "routes": [], "status": "ZERO_RESULTS"}).encode(
        'utf-8')
    return response


@pytest.fixture()
def request_denied_google_directions_api_response():
    response = Response()
    response.status_code = 200
    response._content = json.dumps(
        {'error_message': 'The provided API key is invalid.', 'routes': [], 'status': 'REQUEST_DENIED'}).encode('utf-8')
    return response


@pytest.fixture()
def bad_request_google_directions_api_response():
    response = Response()
    response.status_code = 400
    response._content = json.dumps({'error_message': 'Bad Request'}).encode('utf-8')
    return response


def test_send_requests_for_road_network(mocker, tmpdir, generated_request):
    mocker.patch.object(google_directions, 'generate_requests', return_value=generated_request)
    mocker.patch.object(google_directions, 'send_requests',
                        return_value={**generated_request,
                                      **{'request': google_directions_api_response, 'timestamp': 12345}})
    mocker.patch.object(google_directions, 'parse_results', return_value={})

    n = Network('epsg:27700')
    google_directions.send_requests_for_network(n, 10, tmpdir)
    google_directions.generate_requests.assert_called_once_with(n)
    google_directions.send_requests.assert_called_once_with(google_directions.generate_requests.return_value, None,
                                                            None, None, False)
    google_directions.parse_results.assert_called_once_with(google_directions.send_requests.return_value, tmpdir)


def test_read_saved_api_results():
    api_requests = google_directions.read_saved_api_results(example_google_speed_data)
    assert_semantically_equal(api_requests, {
        ('9791490', '4698712638'): {'path_nodes': ('9791490', '4698712638'), 'path_polyline': 'mvmyHpqYb@lA',
                                    'origin': {'id': '9791490', 'x': 529414.5591563961, 'y': 181898.4902840198,
                                               'lat': 51.5211862, 'lon': -0.1360879, 's2_id': 5221390682074967291},
                                    'destination': {'id': '4698712638', 'x': 529387.9166476472, 'y': 181877.74867097137,
                                                    'lat': 51.5210059, 'lon': -0.1364793, 's2_id': 5221390682013665023},
                                    'timestamp': 1594385229.635254,
                                    'parsed_response': {'google_speed': 6.8, 'google_polyline': 'mvmyHpqYb@pA'}}})


def test_queries_build_correctly_without_traffic():
    request = google_directions.make_request(
        origin_attributes={'lat': 1, 'lon': 2},
        destination_attributes={'lat': 3, 'lon': 4},
        key='super_awesome_key',
        traffic=False
    )
    result = request.result()
    assert result.status_code == 200
    assert result.url == 'https://maps.googleapis.com/maps/api/directions/json?origin=1%2C2&destination=3%2C4&key=super_awesome_key'


def test_queries_build_correctly_with_traffic():
    request = google_directions.make_request(
        origin_attributes={'lat': 1, 'lon': 2},
        destination_attributes={'lat': 3, 'lon': 4},
        key='super_awesome_key',
        traffic=True
    )
    result = request.result()
    assert result.status_code == 200
    assert result.url == 'https://maps.googleapis.com/maps/api/directions/json?origin=1%2C2&destination=3%2C4&key=super_awesome_key&departure_time=now'


def test_generating_requests_on_non_simplified_graphs():
    n = Network('epsg:27700')
    n.add_link('0', 1, 2, attribs={'modes': ['car']})
    n.add_link('1', 2, 3, attribs={'modes': ['car']})
    n.add_link('2', 4, 3, attribs={'modes': ['car']})
    n.add_link('3', 5, 4, attribs={'modes': ['car']})
    n.add_link('4', 1, 10, attribs={'modes': ['car']})

    for node in n.graph.nodes:
        n.apply_attributes_to_node(node, {'lat': 1, 'lon': 2})

    api_requests = google_directions.generate_requests(n)

    assert_semantically_equal(api_requests, {
        (1, 10): {'path_nodes': (1, 10), 'path_polyline': '_ibE_seK??', 'origin': {'lat': 1, 'lon': 2},
                  'destination': {'lat': 1, 'lon': 2}},
        (1, 3): {'path_nodes': [1, 2, 3], 'path_polyline': '_ibE_seK????', 'origin': {'lat': 1, 'lon': 2},
                 'destination': {'lat': 1, 'lon': 2}},
        (5, 3): {'path_nodes': [5, 4, 3], 'path_polyline': '_ibE_seK????', 'origin': {'lat': 1, 'lon': 2},
                 'destination': {'lat': 1, 'lon': 2}}})


def test_sending_requests(mocker, google_directions_api_response):
    mocker.patch.object(time, 'time', return_value=12345)
    mocker.patch.object(secrets_vault, 'get_google_directions_api_key', return_value='super_awesome_key')
    mocker.patch.object(google_directions, 'make_request', return_value=google_directions_api_response)

    api_requests = {
        (1, 10): {'path_nodes': (1, 10), 'path_polyline': '_ibE_seK??', 'origin': {'lat': 1, 'lon': 2},
                  'destination': {'lat': 1, 'lon': 2}},
        (1, 3): {'path_nodes': [1, 2, 3], 'path_polyline': '_ibE_seK????', 'origin': {'lat': 1, 'lon': 2},
                 'destination': {'lat': 1, 'lon': 2}},
        (5, 3): {'path_nodes': [5, 4, 3], 'path_polyline': '_ibE_seK????', 'origin': {'lat': 1, 'lon': 2},
                 'destination': {'lat': 1, 'lon': 2}}}

    api_requests = google_directions.send_requests(api_requests)

    assert_semantically_equal(api_requests, {
        (1, 10): {'path_nodes': (1, 10), 'path_polyline': '_ibE_seK??', 'origin': {'lat': 1, 'lon': 2},
                  'destination': {'lat': 1, 'lon': 2}, 'request': google_directions_api_response,
                  'timestamp': 12345},
        (1, 3): {'path_nodes': [1, 2, 3], 'path_polyline': '_ibE_seK????', 'origin': {'lat': 1, 'lon': 2},
                 'destination': {'lat': 1, 'lon': 2}, 'request': google_directions_api_response,
                 'timestamp': 12345},
        (5, 3): {'path_nodes': [5, 4, 3], 'path_polyline': '_ibE_seK????', 'origin': {'lat': 1, 'lon': 2},
                 'destination': {'lat': 1, 'lon': 2}, 'request': google_directions_api_response,
                 'timestamp': 12345}})


def test_sending_requests_throws_error_if_key_not_found(mocker):
    mocker.patch.object(secrets_vault, 'get_google_directions_api_key', return_value=None)
    with pytest.raises(RuntimeError) as e:
        google_directions.send_requests({})
    assert 'API key was not found' in str(e.value)


def test_parsing_routes_with_a_good_response(google_directions_api_response, generated_request):
    data = google_directions.parse_routes(google_directions_api_response, generated_request['path_polyline'])
    assert_semantically_equal(data, {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCvCuCdDcBrB'})


def test_parsing_routes_with_multiple_legs_response(google_directions_api_response_multiple_legs, generated_request):
    data = google_directions.parse_routes(google_directions_api_response_multiple_legs,
                                          generated_request['path_polyline'])
    assert_semantically_equal(data, {'google_speed': 2.3636363636363638, 'google_polyline': 'ekmyH~nYbBzFblahblah'})


def test_parsing_routes_with_a_bad_response(caplog, request_denied_google_directions_api_response, generated_request):
    with caplog.at_level(logging.INFO):
        data = google_directions.parse_routes(request_denied_google_directions_api_response,
                                              generated_request['path_polyline'])
    assert_semantically_equal(data, {})
    assert_logging_warning_caught_with_message_containing(caplog, 'Error message: The provided API key is invalid.')


def test_parsing_routes_with_multiple_routes_selects_the_one_closest(mocker, google_directions_api_response,
                                                                     generated_request):
    mocker.patch.object(Response, 'json', return_value={'routes': [1, 2]})
    mocker.patch.object(google_directions, 'parse_route', side_effect=[
        {'google_speed': 2, 'google_polyline': 'ahmyHzvYeDz@m@bIqDp@'},
        {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCvCuCdDcBrB'}])
    data = google_directions.parse_routes(google_directions_api_response, generated_request['path_polyline'])

    assert_semantically_equal(data, {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCvCuCdDcBrB',
                                     'polyline_proximity': 1.306345084680333})


def test_parsing_routes_with_bad_request(caplog, bad_request_google_directions_api_response):
    with caplog.at_level(logging.INFO):
        data = google_directions.parse_routes(bad_request_google_directions_api_response, 'ahmyHzvYkCvCuCdDcBrB')
    assert_semantically_equal(data, {})
    assert_logging_warning_caught_with_message_containing(caplog, 'Request was not successful.')


def test_parse_results(mocker, tmpdir, generated_request, google_directions_api_response):
    request = FuturesSession(max_workers=1).get('http://hello.com')
    mocker.patch.object(request, 'result', return_value=google_directions_api_response)
    o_d = generated_request['path_nodes'][0], generated_request['path_nodes'][-1]
    api_requests = {o_d: generated_request}
    api_requests[o_d]['request'] = request
    api_requests[o_d]['timestamp'] = 12345

    api_requests = google_directions.parse_results(api_requests, tmpdir)
    assert_semantically_equal(api_requests, {('107316', '107352'): {
        'path_nodes': ['107316', '2440643031', '4307345276', '107317', '4307345495', '4307345497', '25495448',
                       '2503102618', '107351', '5411344775', '2440651577', '2440651556', '2440651552', '107352'],
        'path_polyline': 'ahmyHzvYGJyBbCGHq@r@EDIJGBu@~@SToAzAEFEDIJ', 'origin': {'lat': 51.5188864, 'lon': -0.1369442},
        'destination': {'lat': 51.5208299, 'lon': -0.1391027}, 'timestamp': 12345,
        'parsed_response': {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCvCuCdDcBrB'}}})


def test_mapping_results_to_edges_with_singular_route_data():
    api_requests = {('107316', '107352'): {
        'path_nodes': ['107316', '2440643031', '4307345276', '107317', '4307345495', '4307345497', '25495448',
                       '2503102618', '107351', '5411344775', '2440651577', '2440651556', '2440651552', '107352'],
        'path_polyline': 'ahmyHzvYGJyBbCGHq@r@EDIJGBu@~@SToAzAEFEDIJ', 'origin': {'lat': 51.5188864, 'lon': -0.1369442},
        'destination': {'lat': 51.5208299, 'lon': -0.1391027}, 'timestamp': 12345,
        'parsed_response': {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCvCuCdDcBrB'}}}

    google_edge_data = google_directions.map_results_to_edges(api_requests)
    assert_semantically_equal(google_edge_data, {
        ('2440643031', '4307345276'): {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCvCuCdDcBrB'},
        ('4307345276', '107317'): {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCvCuCdDcBrB'},
        ('25495448', '2503102618'): {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCvCuCdDcBrB'},
        ('107316', '2440643031'): {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCvCuCdDcBrB'},
        ('4307345495', '4307345497'): {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCvCuCdDcBrB'},
        ('2440651556', '2440651552'): {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCvCuCdDcBrB'},
        ('107317', '4307345495'): {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCvCuCdDcBrB'},
        ('107351', '5411344775'): {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCvCuCdDcBrB'},
        ('2440651577', '2440651556'): {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCvCuCdDcBrB'},
        ('2503102618', '107351'): {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCvCuCdDcBrB'},
        ('4307345497', '25495448'): {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCvCuCdDcBrB'},
        ('2440651552', '107352'): {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCvCuCdDcBrB'},
        ('5411344775', '2440651577'): {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCvCuCdDcBrB'}})


def test_mapping_results_to_edges_with_overlapping_edges():
    api_requests = {('107316', '107352'): {
        'path_nodes': ['107316', '2440643031', '4307345276', '107317', '4307345495', '4307345497', '25495448',
                       '2503102618', '107351', '5411344775', '2440651577', '2440651556', '2440651552', '107352'],
        'path_polyline': 'ahmyHzvYGJyBbCGHq@r@EDIJGBu@~@SToAzAEFEDIJ', 'origin': {'lat': 51.5188864, 'lon': -0.1369442},
        'destination': {'lat': 51.5208299, 'lon': -0.1391027}, 'timestamp': 12345,
        'parsed_response': {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCvCuCdDcBrB'}},
        ('107316', '4307345276'): {
            'path_nodes': ['107316', '2440643031', '4307345276'],
            'path_polyline': 'ahmyHzvYkC',
            'origin': {'lat': 51.5188864, 'lon': -0.1369442},
            'destination': {'lat': 51.5195381, 'lon': -0.1376626},
            'parsed_response': {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCv'}
        }}

    google_dir_api_edge_data = google_directions.map_results_to_edges(api_requests)
    assert_semantically_equal(google_dir_api_edge_data, {
        ('2440643031', '4307345276'): {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCvCuCdDcBrB'},
        ('4307345276', '107317'): {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCvCuCdDcBrB'},
        ('25495448', '2503102618'): {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCvCuCdDcBrB'},
        ('107316', '2440643031'): {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCvCuCdDcBrB'},
        ('4307345495', '4307345497'): {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCvCuCdDcBrB'},
        ('2440651556', '2440651552'): {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCvCuCdDcBrB'},
        ('107317', '4307345495'): {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCvCuCdDcBrB'},
        ('107351', '5411344775'): {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCvCuCdDcBrB'},
        ('2440651577', '2440651556'): {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCvCuCdDcBrB'},
        ('2503102618', '107351'): {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCvCuCdDcBrB'},
        ('4307345497', '25495448'): {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCvCuCdDcBrB'},
        ('2440651552', '107352'): {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCvCuCdDcBrB'},
        ('5411344775', '2440651577'): {'google_speed': 3.7183098591549295, 'google_polyline': 'ahmyHzvYkCvCuCdDcBrB'}})


def test_saved_results_appear_in_directory(tmpdir, generated_request):
    o_d = generated_request['path_nodes'][0], generated_request['path_nodes'][-1]
    api_requests = {o_d: generated_request}
    api_requests[o_d]['request'] = 'request'
    api_requests[o_d]['timestamp'] = 12345
    api_requests[o_d]['parsed_response'] = {'google_speed': 3.7183098591549295,
                                            'google_polyline': 'ahmyHzvYkCvCuCdDcBrB'}

    expected_file_path = os.path.join(tmpdir, '12345_ahmyHzvYkCvCuCdDcBrB.pickle')

    assert not os.path.exists(expected_file_path)
    google_directions.pickle_result(api_requests[o_d], tmpdir)
    assert os.path.exists(expected_file_path)
