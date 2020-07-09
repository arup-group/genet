import pytest
import json
from requests.models import Response
from genet.utils import google_directions
from genet.utils import secrets_vault
from genet.core import Network
from tests.fixtures import assert_semantically_equal


@pytest.fixture()
def request_path():
    pass


@pytest.fixture()
def google_directions_api_response():
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
                    }
                ],
                "overview_polyline": {
                    "points": "ekmyH~nYbBzF"
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


def test_queries_build_correctly():
    request = google_directions.make_request(
        origin_attributes={'lat': 1, 'lon': 2},
        destination_attributes={'lat': 3, 'lon': 4},
        key='super_awesome_key'
    )
    result = request.result()
    assert result.status_code == 200
    assert result.url == 'https://maps.googleapis.com/maps/api/directions/json?origin=1%2C2&destination=3%2C4&key=super_awesome_key'


def test_generating_requests_on_non_simplified_graphs():
    n = Network()
    n.add_link('0', 1, 2)
    n.add_link('1', 2, 3)
    n.add_link('2', 4, 3)
    n.add_link('3', 5, 4)
    n.add_link('4', 1, 10)

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
                  'destination': {'lat': 1, 'lon': 2}, 'request': google_directions_api_response},
        (1, 3): {'path_nodes': [1, 2, 3], 'path_polyline': '_ibE_seK????', 'origin': {'lat': 1, 'lon': 2},
                 'destination': {'lat': 1, 'lon': 2}, 'request': google_directions_api_response},
        (5, 3): {'path_nodes': [5, 4, 3], 'path_polyline': '_ibE_seK????', 'origin': {'lat': 1, 'lon': 2},
                 'destination': {'lat': 1, 'lon': 2}, 'request': google_directions_api_response}})


def test_sending_requests_throws_error_if_key_not_found(mocker):
    mocker.patch.object(secrets_vault, 'get_google_directions_api_key', return_value=None)
    with pytest.raises(RuntimeError) as e:
        google_directions.send_requests({})
    assert 'API key was not found' in str(e.value)


def test_parsing_routes_with_a_good_response(google_directions_api_response, request_path):
    data = google_directions.parse_routes(google_directions_api_response, request_path)
    assert_semantically_equal(data, {'google_speed': 2.3636363636363638, 'google_polyline': 'ekmyH~nYbBzF'})


def test_parsing_routes_with_multiple_legs_response(google_directions_api_response_multiple_legs, request_path):
    data = google_directions.parse_routes(google_directions_api_response_multiple_legs, request_path)
    assert_semantically_equal(data, {'google_speed': 4.7272727272727275, 'google_polyline': 'ekmyH~nYbBzFblahblah'})


def test_parsing_routes_with_a_bad_response(request_denied_google_directions_api_response, request_path):
    data = google_directions.parse_routes(request_denied_google_directions_api_response, request_path)
    assert_semantically_equal(data, {})
