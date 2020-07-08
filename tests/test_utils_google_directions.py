import pytest
import json
from requests.models import Response
from genet.utils import google_directions
from genet.utils import secrets_vault
from genet.core import Network
from tests.fixtures import assert_semantically_equal

@pytest.fixture()
def google_directions_api_response():
    response = Response()
    response.status_code = 200
    response._content = json.dumps({
       "geocoded_waypoints" : [
          {
             "geocoder_status" : "OK",
             "place_id" : "ChIJ1Yc8ntUadkgRYF4zXGTLoF0",
             "types" : [ "street_address" ]
          },
          {
             "geocoder_status" : "OK",
             "place_id" : "ChIJX4MiydIadkgRwWtgavBSS1s",
             "types" : [
                "cafe",
                "establishment",
                "food",
                "point_of_interest",
                "restaurant",
                "store"
             ]
          }
       ],
       "routes" : [
          {
             "bounds" : {
                "northeast" : {
                   "lat" : 51.5182106,
                   "lng" : -0.1397926
                },
                "southwest" : {
                   "lat" : 51.5115875,
                   "lng" : -0.1431377
                }
             },
             "copyrights" : "Map data ©2020",
             "legs" : [
                {
                   "distance" : {
                      "text" : "1.3 km",
                      "value" : 1291
                   },
                   "duration" : {
                      "text" : "8 mins",
                      "value" : 480
                   },
                   "end_address" : "15 Maddox St, Mayfair, London W1S 2QQ, UK",
                   "end_location" : {
                      "lat" : 51.5132727,
                      "lng" : -0.1418639
                   },
                   "start_address" : "76 Mortimer St, Marylebone, London W1W 7SA, UK",
                   "start_location" : {
                      "lat" : 51.5177699,
                      "lng" : -0.1422432
                   },
                   "steps" : [
                      {
                         "distance" : {
                            "text" : "56 m",
                            "value" : 56
                         },
                         "duration" : {
                            "text" : "1 min",
                            "value" : 24
                         },
                         "end_location" : {
                            "lat" : 51.5182106,
                            "lng" : -0.1422747
                         },
                         "html_instructions" : "Head \u003cb\u003enorth-east\u003c/b\u003e towards \u003cb\u003eRiding House St\u003c/b\u003e",
                         "polyline" : {
                            "points" : "aamyH~wZAE?G?AAA?AAAAAC?C?k@PE@EBOD"
                         },
                         "start_location" : {
                            "lat" : 51.5177699,
                            "lng" : -0.1422432
                         },
                         "travel_mode" : "DRIVING"
                      },
                      {
                         "distance" : {
                            "text" : "78 m",
                            "value" : 78
                         },
                         "duration" : {
                            "text" : "1 min",
                            "value" : 27
                         },
                         "end_location" : {
                            "lat" : 51.5178155,
                            "lng" : -0.1431377
                         },
                         "html_instructions" : "Turn \u003cb\u003eleft\u003c/b\u003e onto \u003cb\u003eRiding House St\u003c/b\u003e\u003cdiv style=\"font-size:0.9em\"\u003eEntering toll zone\u003c/div\u003e",
                         "maneuver" : "turn-left",
                         "polyline" : {
                            "points" : "ycmyHdxZJ~@@N@H@D@DBDDFPNBDJPLP"
                         },
                         "start_location" : {
                            "lat" : 51.5182106,
                            "lng" : -0.1422747
                         },
                         "travel_mode" : "DRIVING"
                      },
                      {
                         "distance" : {
                            "text" : "0.6 km",
                            "value" : 556
                         },
                         "duration" : {
                            "text" : "4 mins",
                            "value" : 225
                         },
                         "end_location" : {
                            "lat" : 51.5131276,
                            "lng" : -0.1405909
                         },
                         "html_instructions" : "Turn \u003cb\u003eleft\u003c/b\u003e onto \u003cb\u003eLangham Pl\u003c/b\u003e/\u003cwbr/\u003e\u003cb\u003eA4201\u003c/b\u003e\u003cdiv style=\"font-size:0.9em\"\u003eContinue to follow A4201\u003c/div\u003e",
                         "maneuver" : "turn-left",
                         "polyline" : {
                            "points" : "kamyHr}ZDGBCBCDEDCBANIJE\\MdA]RIVK`@Mb@O@?hAc@HI@A@APGz@Sx@SJC`@Ih@Mz@Sf@KRITIHGLIFMHIHIBCHEJIHK\\Wb@a@v@q@"
                         },
                         "start_location" : {
                            "lat" : 51.5178155,
                            "lng" : -0.1431377
                         },
                         "travel_mode" : "DRIVING"
                      },
                      {
                         "distance" : {
                            "text" : "0.1 km",
                            "value" : 128
                         },
                         "duration" : {
                            "text" : "1 min",
                            "value" : 33
                         },
                         "end_location" : {
                            "lat" : 51.5122919,
                            "lng" : -0.1418294
                         },
                         "html_instructions" : "Turn \u003cb\u003eright\u003c/b\u003e onto \u003cb\u003eConduit St\u003c/b\u003e/\u003cwbr/\u003e\u003cb\u003eB406\u003c/b\u003e\u003cdiv style=\"font-size:0.9em\"\u003eLeaving toll zone\u003c/div\u003e\u003cdiv style=\"font-size:0.9em\"\u003eEntering toll zone\u003c/div\u003e",
                         "maneuver" : "turn-right",
                         "polyline" : {
                            "points" : "adlyHtmZFV@J@D@D@B@D@BT\\HHd@r@JLX`@B@X\\HL"
                         },
                         "start_location" : {
                            "lat" : 51.5131276,
                            "lng" : -0.1405909
                         },
                         "travel_mode" : "DRIVING"
                      },
                      {
                         "distance" : {
                            "text" : "0.1 km",
                            "value" : 100
                         },
                         "duration" : {
                            "text" : "1 min",
                            "value" : 25
                         },
                         "end_location" : {
                            "lat" : 51.5115875,
                            "lng" : -0.141035
                         },
                         "html_instructions" : "Turn \u003cb\u003eleft\u003c/b\u003e onto \u003cb\u003eSavile Row\u003c/b\u003e",
                         "maneuver" : "turn-left",
                         "polyline" : {
                            "points" : "y~kyHluZBDHSBI@GHMDKBC?CROn@i@FGHILO"
                         },
                         "start_location" : {
                            "lat" : 51.5122919,
                            "lng" : -0.1418294
                         },
                         "travel_mode" : "DRIVING"
                      },
                      {
                         "distance" : {
                            "text" : "0.1 km",
                            "value" : 101
                         },
                         "duration" : {
                            "text" : "1 min",
                            "value" : 36
                         },
                         "end_location" : {
                            "lat" : 51.5120557,
                            "lng" : -0.1397926
                         },
                         "html_instructions" : "Turn \u003cb\u003eleft\u003c/b\u003e onto \u003cb\u003eNew Burlington St\u003c/b\u003e",
                         "maneuver" : "turn-left",
                         "polyline" : {
                            "points" : "mzkyHnpZK_@GSc@aBQq@Sq@"
                         },
                         "start_location" : {
                            "lat" : 51.5115875,
                            "lng" : -0.141035
                         },
                         "travel_mode" : "DRIVING"
                      },
                      {
                         "distance" : {
                            "text" : "0.2 km",
                            "value" : 209
                         },
                         "duration" : {
                            "text" : "1 min",
                            "value" : 80
                         },
                         "end_location" : {
                            "lat" : 51.5136973,
                            "lng" : -0.1412745
                         },
                         "html_instructions" : "Turn \u003cb\u003eleft\u003c/b\u003e onto \u003cb\u003eRegent St\u003c/b\u003e/\u003cwbr/\u003e\u003cb\u003eA4201\u003c/b\u003e",
                         "maneuver" : "turn-left",
                         "polyline" : {
                            "points" : "k}kyHthZMJmAdAg@`@iAbA_Ax@A@YVSPIH"
                         },
                         "start_location" : {
                            "lat" : 51.5120557,
                            "lng" : -0.1397926
                         },
                         "travel_mode" : "DRIVING"
                      },
                      {
                         "distance" : {
                            "text" : "63 m",
                            "value" : 63
                         },
                         "duration" : {
                            "text" : "1 min",
                            "value" : 30
                         },
                         "end_location" : {
                            "lat" : 51.5132727,
                            "lng" : -0.1418639
                         },
                         "html_instructions" : "Turn \u003cb\u003eleft\u003c/b\u003e onto \u003cb\u003eMaddox St\u003c/b\u003e\u003cdiv style=\"font-size:0.9em\"\u003eDestination will be on the left\u003c/div\u003e",
                         "maneuver" : "turn-left",
                         "polyline" : {
                            "points" : "sglyH|qZLVFLXb@DD^d@"
                         },
                         "start_location" : {
                            "lat" : 51.5136973,
                            "lng" : -0.1412745
                         },
                         "travel_mode" : "DRIVING"
                      }
                   ],
                   "traffic_speed_entry" : [],
                   "via_waypoint" : []
                }
             ],
             "overview_polyline" : {
                "points" : "aamyH~wZCQCEy@RUHLnAHZf@n@LPDGFG^Uh@SxAg@~Ai@hAc@HIBCrCs@fCk@z@U^QTWRSb@_@`Ay@v@q@FVBPBHb@p@nAdBb@j@BDHSDQNYBGbAy@PQLOK_@k@uBe@cBmEvDoBdBIHLV`@p@d@j@"
             },
             "summary" : "A4201",
             "warnings" : [],
             "waypoint_order" : []
          }
       ],
       "status" : "OK"
    }).encode('utf-8')
    return response


@pytest.fixture()
def empty_response():
    response = Response()
    response.status_code = 200
    response._content = b"{\"geocoded_waypoints\": [{}, {}], \"routes\": [], \"status\": \"ZERO_RESULTS\"}"
    return response


@pytest.fixture()
def request_denied_google_directions_api_response():
    response = Response()
    response.status_code = 200
    response._content = b"{'error_message': 'The provided API key is invalid.', 'routes': [], 'status': 'REQUEST_DENIED'}"
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


def test_generating_requests_on_non_simplified_graphs(mocker):
    mocker.patch.object(secrets_vault, 'get_google_directions_api_key', return_value='super_awesome_key')
    n = Network()
    n.add_link('0', 1, 2)
    n.add_link('1', 2, 3)
    n.add_link('2', 4, 3)
    n.add_link('3', 5, 4)
    n.add_link('4', 1, 10)

    for node in n.graph.nodes:
        n.apply_attributes_to_node(node, {'lat': 'lat', 'lon': 'lon'})

    api_request_paths, api_requests = google_directions.generate_requests(n)

    assert_semantically_equal(api_request_paths, {(1, 10): (1, 10), (1, 3): [1, 2, 3], (5, 3): [5, 4, 3]})


def test_parsing_routes_with_a_good_response(google_directions_api_response):
    data = google_directions.parse_routes(google_directions_api_response)
    assert_semantically_equal(data, {})


# def test_parsing_routes_with_a_bad_response(request_denied_google_directions_api_response):
#     data = google_directions.parse_routes(request_denied_google_directions_api_response)
#     assert_semantically_equal(data, {})
