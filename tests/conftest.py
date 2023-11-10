import json
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

import dictdiffer
import importlib_resources
import lxml
import pandas as pd
import pytest
import xmltodict
from networkx import DiGraph, set_node_attributes
from pyproj import CRS

import genet.modify.change_log as change_log
from genet.core import Network
from genet.input import osm_reader, read
from genet.schedule_elements import Route, Schedule, Service, Stop

GENET_CONFIG_DIR = importlib_resources.files("genet") / "configs"
TEST_DATA_DIR = Path(__file__).parent / "test_data"


def pytest_configure(config):
    # pytest.test_data_dir can now be accessed in all other test files
    pytest.test_data_dir = TEST_DATA_DIR


pt2matsim_network_test_file = (TEST_DATA_DIR / "matsim" / "network.xml").absolute()
pt2matsim_schedule_file = (TEST_DATA_DIR / "matsim" / "schedule.xml").absolute()
pt2matsim_vehicles_file = (TEST_DATA_DIR / "matsim" / "vehicles.xml").absolute()


###########################################################
# helper functions
###########################################################
@pytest.fixture()
def deep_sort():
    def _deep_sort(obj):
        if isinstance(obj, dict):
            obj = OrderedDict(sorted(obj.items()))
            for k, v in obj.items():
                if isinstance(v, dict) or isinstance(v, list):
                    obj[k] = _deep_sort(v)

        if isinstance(obj, list):
            for i, v in enumerate(obj):
                if isinstance(v, dict) or isinstance(v, list):
                    obj[i] = _deep_sort(v)
            obj = sorted(obj, key=lambda x: json.dumps(x))

        return obj

    return _deep_sort


@pytest.fixture()
def assert_semantically_equal(deep_sort):
    def _assert_semantically_equal(dict1, dict2):
        # the tiny permissible tolerance is to account for cross-platform differences in
        # floating point lat/lon values, as witnessed in our CI build running on Ubuntu
        # Vs our own OSX laptops - lat/lon values within this tolerance can and should
        # be considered the same in practical terms
        diffs = list(dictdiffer.diff(deep_sort(dict1), deep_sort(dict2), tolerance=0.00000000001))
        assert diffs == [], diffs

    return _assert_semantically_equal


@pytest.fixture()
def assert_logging_warning_caught_with_message_containing():
    def _assert_logging_warning_caught_with_message_containing(clog, message):
        for record in clog.records:
            if message in record.message:
                return True
        return False

    return _assert_logging_warning_caught_with_message_containing


@pytest.fixture()
def time_somewhat_accurate():
    def _time_somewhat_accurate(t1: str, t2: str, tolerance_s: float = 5):
        """
        t1: "HH:MM:SS"
        t2: "HH:MM:SS"
        tolerance_s: seconds of tolerable difference

        returns: bool
        """
        dt1 = datetime.strptime(t1, "%H:%M:%S")
        dt2 = datetime.strptime(t2, "%H:%M:%S")
        return abs((dt1 - dt2).total_seconds()) <= tolerance_s

    return _time_somewhat_accurate


@pytest.fixture()
def list_of_times_somewhat_accurate(time_somewhat_accurate):
    def _list_of_times_somewhat_accurate(lt1: list[str], lt2: list[str], tolerance_s: float = 5):
        """
        lt1: list of times in str "HH:MM:SS"
        lt2: list of times in str "HH:MM:SS"
        tolerance_s: seconds of tolerable difference

        returns: bool
        """
        return all([time_somewhat_accurate(t1, t2, tolerance_s) for t1, t2 in zip(lt1, lt2)])

    return _list_of_times_somewhat_accurate


@pytest.fixture
def assert_xml_semantically_equal(deep_sort):
    def _xml_diffs(xml_file_1, xml_file_2):
        dict_1 = deep_sort(xmltodict.parse(xml_file_1.read_text()))
        dict_2 = deep_sort(xmltodict.parse(xml_file_2.read_text()))

        return list(dictdiffer.diff(dict_1, dict_2, tolerance=0.001))

    def _parse_string_list(str):
        return str.split(",")

    def _is_list_string(str):
        return "," in str

    def _filter_diffs(diff_list, filter_func):
        removals = []
        for diff in diff_list:
            diff_type, node_location, diff_detail = diff
            if diff_type != "change":
                continue
            if filter_func(diff_detail[0], diff_detail[1]):
                removals.append(diff)
        return [diff for diff in diff_list if diff not in removals]

    def _is_list_ordering_difference(diff_element_1, diff_element_2):
        if _is_list_string(diff_element_1) and _is_list_string(diff_element_2):
            # are these two lists semantically equal, but ordered differently?
            first_list = _parse_string_list(diff_element_1)
            second_list = _parse_string_list(diff_element_2)
            if sorted(first_list) == sorted(second_list):
                return True
        return False

    def _is_permissible_numerical_difference(diff_element_1, diff_element_2, tolerance=0.0001):
        try:
            first_num = float(diff_element_1)
            second_num = float(diff_element_2)
        except ValueError:
            # you ain't no number, bruv!
            return False
        ordered_numbers = sorted([first_num, second_num])
        numerical_difference = ordered_numbers[1] - ordered_numbers[0]
        tolerance_value = ordered_numbers[0] * tolerance
        if numerical_difference <= tolerance_value:
            print(
                "Numerical difference of {} between {} and {} - ignoring because smaller than {} tolerance".format(
                    numerical_difference, first_num, second_num, tolerance_value
                )
            )
            return True
        return False

    def _assert_semantically_equal(file_1_path, file_2_path):
        diffs = _xml_diffs(Path(file_1_path), Path(file_2_path))
        if len(diffs) != 0:
            diffs = _filter_diffs(diffs, _is_list_ordering_difference)
        if len(diffs) != 0:
            diffs = _filter_diffs(diffs, _is_permissible_numerical_difference)
        if len(diffs) == 0:
            print("{} and {} are semantically equal".format(file_1_path, file_2_path))
            return True
        else:
            from pprint import PrettyPrinter

            PrettyPrinter().pprint(diffs)
            raise AssertionError(
                "{} and {} are NOT semantically equal".format(file_1_path, file_2_path)
            )

    return _assert_semantically_equal


###########################################################
# core data structure examples
###########################################################


###########################################################
# networks
###########################################################
@pytest.fixture()
def network_object_from_test_data():
    return read.read_matsim(
        path_to_network=pt2matsim_network_test_file,
        path_to_schedule=pt2matsim_schedule_file,
        path_to_vehicles=pt2matsim_vehicles_file,
        epsg="epsg:27700",
    )


@pytest.fixture()
def network_with_additional_node_attrib():
    network = Network("epsg:27700")
    network.add_node("0", attribs={"id": "0", "x": 1, "y": 2, "attributes": {"osm:node:data": 3}})
    network.add_node("1", attribs={"id": "1", "x": 2, "y": 2})
    network.add_link(
        "0",
        "0",
        "1",
        attribs={
            "id": "0",
            "from": "0",
            "to": "1",
            "length": 1,
            "freespeed": 1,
            "capacity": 20,
            "permlanes": 1,
            "oneway": "1",
            "modes": ["car"],
        },
    )
    return network


@pytest.fixture()
def network_with_additional_node_attrib_xml_file():
    return (TEST_DATA_DIR / "matsim" / "network_with_additional_node_attrib.xml").absolute()


@pytest.fixture
def network_dtd():
    dtd_path = (TEST_DATA_DIR / "dtd" / "matsim" / "network_v2.dtd").absolute()
    yield lxml.etree.DTD(dtd_path)


###########################################################
# schedule
###########################################################


@pytest.fixture()
def stop_epsg_27700():
    return Stop(id="0", x=528504.1342843144, y=182155.7435136598, epsg="epsg:27700")


@pytest.fixture()
def test_service():
    return Service(
        id="service",
        routes=[
            Route(
                route_short_name="route",
                mode="bus",
                stops=[
                    Stop(id="0", x=528504.1342843144, y=182155.7435136598, epsg="epsg:27700"),
                    Stop(id="0", x=528504.1342843144, y=182155.7435136598, epsg="epsg:27700"),
                ],
                trips={
                    "trip_id": ["VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00"],
                    "trip_departure_time": ["04:40:00"],
                    "vehicle_id": ["veh_1_bus"],
                },
                arrival_offsets=["00:00:00", "00:02:00"],
                departure_offsets=["00:00:00", "00:02:00"],
            ),
            Route(
                route_short_name="route1",
                mode="bus",
                stops=[
                    Stop(id="1", x=528504.1342843144, y=182155.7435136598, epsg="epsg:27700"),
                    Stop(id="2", x=528504.1342843144, y=182155.7435136598, epsg="epsg:27700"),
                ],
                trips={
                    "trip_id": ["Blep_04:40:00"],
                    "trip_departure_time": ["05:40:00"],
                    "vehicle_id": ["veh_2_bus"],
                },
                arrival_offsets=["00:00:00", "00:03:00"],
                departure_offsets=["00:00:00", "00:05:00"],
            ),
        ],
    )


@pytest.fixture()
def service():
    route_1 = Route(
        id="1",
        route_short_name="name",
        mode="bus",
        stops=[
            Stop(id="1", x=4, y=2, epsg="epsg:27700", linkRefId="1"),
            Stop(id="2", x=1, y=2, epsg="epsg:27700", linkRefId="2"),
            Stop(id="3", x=3, y=3, epsg="epsg:27700", linkRefId="3"),
            Stop(id="4", x=7, y=5, epsg="epsg:27700", linkRefId="4"),
        ],
        trips={
            "trip_id": ["1", "2"],
            "trip_departure_time": ["13:00:00", "13:30:00"],
            "vehicle_id": ["veh_1_bus", "veh_2_bus"],
        },
        arrival_offsets=["00:00:00", "00:03:00", "00:07:00", "00:13:00"],
        departure_offsets=["00:00:00", "00:05:00", "00:09:00", "00:15:00"],
        route=["1", "2", "3", "4"],
    )
    route_2 = Route(
        id="2",
        route_short_name="name_2",
        mode="bus",
        stops=[
            Stop(id="5", x=4, y=2, epsg="epsg:27700", linkRefId="5"),
            Stop(id="6", x=1, y=2, epsg="epsg:27700", linkRefId="6"),
            Stop(id="7", x=3, y=3, epsg="epsg:27700", linkRefId="7"),
            Stop(id="8", x=7, y=5, epsg="epsg:27700", linkRefId="8"),
        ],
        trips={
            "trip_id": ["1", "2"],
            "trip_departure_time": ["11:00:00", "13:00:00"],
            "vehicle_id": ["veh_3_bus", "veh_4_bus"],
        },
        arrival_offsets=["00:00:00", "00:03:00", "00:07:00", "00:13:00"],
        departure_offsets=["00:00:00", "00:05:00", "00:09:00", "00:15:00"],
        route=["5", "6", "7", "8"],
    )
    return Service(id="service", routes=[route_1, route_2])


@pytest.fixture()
def correct_schedule():
    return Schedule(
        epsg="epsg:27700",
        services=[
            Service(
                id="service",
                routes=[
                    Route(
                        id="1",
                        route_short_name="route",
                        mode="bus",
                        stops=[
                            Stop(
                                id="0",
                                x=529455.7452394223,
                                y=182401.37630677427,
                                epsg="epsg:27700",
                                linkRefId="1",
                            ),
                            Stop(
                                id="1",
                                x=529350.7866124967,
                                y=182388.0201078112,
                                epsg="epsg:27700",
                                linkRefId="2",
                            ),
                        ],
                        trips={
                            "trip_id": ["VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00"],
                            "trip_departure_time": ["04:40:00"],
                            "vehicle_id": ["veh_1_bus"],
                        },
                        arrival_offsets=["00:00:00", "00:02:00"],
                        departure_offsets=["00:00:00", "00:02:00"],
                        route=["1", "2"],
                    ),
                    Route(
                        id="2",
                        route_short_name="route1",
                        mode="bus",
                        stops=[
                            Stop(
                                id="0",
                                x=529455.7452394223,
                                y=182401.37630677427,
                                epsg="epsg:27700",
                                linkRefId="1",
                            ),
                            Stop(
                                id="1",
                                x=529350.7866124967,
                                y=182388.0201078112,
                                epsg="epsg:27700",
                                linkRefId="2",
                            ),
                        ],
                        trips={
                            "trip_id": ["Blep_04:40:00"],
                            "trip_departure_time": ["05:40:00"],
                            "vehicle_id": ["veh_2_bus"],
                        },
                        arrival_offsets=["00:00:00", "00:03:00"],
                        departure_offsets=["00:00:00", "00:05:00"],
                        route=["1", "2"],
                    ),
                ],
            )
        ],
    )


@pytest.fixture()
def schedule_graph():
    graph = DiGraph(
        name="Schedule Graph",
        routes={
            "4": {
                "ordered_stops": ["4", "5"],
                "route_short_name": "route4",
                "mode": "rail",
                "trips": {
                    "trip_id": ["route4_05:40:00"],
                    "trip_departure_time": ["05:40:00"],
                    "vehicle_id": ["veh_0_bus"],
                },
                "arrival_offsets": ["00:00:00", "00:03:00"],
                "departure_offsets": ["00:00:00", "00:05:00"],
                "route_long_name": "",
                "id": "4",
                "route": ["4", "5"],
                "await_departure": [],
            },
            "3": {
                "ordered_stops": ["3", "4"],
                "route_short_name": "route3",
                "mode": "rail",
                "trips": {
                    "trip_id": ["route3_04:40:00"],
                    "trip_departure_time": ["04:40:00"],
                    "vehicle_id": ["veh_1_bus"],
                },
                "arrival_offsets": ["00:00:00", "00:02:00"],
                "departure_offsets": ["00:00:00", "00:02:00"],
                "route_long_name": "",
                "id": "3",
                "route": ["3", "4"],
                "await_departure": [],
            },
            "1": {
                "ordered_stops": ["0", "1"],
                "route_short_name": "route1",
                "mode": "bus",
                "trips": {
                    "trip_id": ["route1_04:40:00"],
                    "trip_departure_time": ["04:40:00"],
                    "vehicle_id": ["veh_2_bus"],
                },
                "arrival_offsets": ["00:00:00", "00:02:00"],
                "departure_offsets": ["00:00:00", "00:02:00"],
                "route_long_name": "",
                "id": "1",
                "route": ["0", "1"],
                "await_departure": [],
            },
            "2": {
                "ordered_stops": ["1", "2"],
                "route_short_name": "route2",
                "mode": "bus",
                "trips": {
                    "trip_id": ["route2_05:40:00"],
                    "trip_departure_time": ["05:40:00"],
                    "vehicle_id": ["veh_3_bus"],
                },
                "arrival_offsets": ["00:00:00", "00:03:00"],
                "departure_offsets": ["00:00:00", "00:05:00"],
                "route_long_name": "",
                "id": "2",
                "route": ["1", "2"],
                "await_departure": [],
            },
        },
        services={
            "service2": {"id": "service2", "name": "route3"},
            "service1": {"id": "service1", "name": "route1"},
        },
        route_to_service_map={"1": "service1", "2": "service1", "3": "service2", "4": "service2"},
        service_to_route_map={"service1": ["1", "2"], "service2": ["3", "4"]},
        crs=CRS("epsg:27700"),
    )
    nodes = {
        "4": {
            "services": {"service2"},
            "routes": {"3", "4"},
            "id": "4",
            "x": 529350.7866124967,
            "y": 182388.0201078112,
            "epsg": "epsg:27700",
            "name": "",
            "lat": 51.52560003323918,
            "lon": -0.13682698708848137,
            "s2_id": 5221390668558830581,
            "additional_attributes": {"linkRefId"},
            "linkRefId": "4",
        },
        "5": {
            "services": {"service2"},
            "routes": {"4"},
            "id": "5",
            "x": 529350.7866124967,
            "y": 182388.0201078112,
            "epsg": "epsg:27700",
            "name": "",
            "lat": 51.52560003323918,
            "lon": -0.13682698708848137,
            "s2_id": 5221390668558830581,
            "additional_attributes": {"linkRefId"},
            "linkRefId": "5",
        },
        "3": {
            "services": {"service2"},
            "routes": {"3"},
            "id": "3",
            "x": 529455.7452394223,
            "y": 182401.37630677427,
            "epsg": "epsg:27700",
            "name": "",
            "lat": 51.525696033239186,
            "lon": -0.13530998708775874,
            "s2_id": 5221390668020036699,
            "additional_attributes": {"linkRefId"},
            "linkRefId": "3",
        },
        "1": {
            "services": {"service1"},
            "routes": {"2", "1"},
            "id": "1",
            "x": 529350.7866124967,
            "y": 182388.0201078112,
            "epsg": "epsg:27700",
            "name": "",
            "lat": 51.52560003323918,
            "lon": -0.13682698708848137,
            "s2_id": 5221390668558830581,
            "additional_attributes": {"linkRefId"},
            "linkRefId": "1",
        },
        "2": {
            "services": {"service1"},
            "routes": {"2"},
            "id": "2",
            "x": 529350.7866124967,
            "y": 182388.0201078112,
            "epsg": "epsg:27700",
            "name": "",
            "lat": 51.52560003323918,
            "lon": -0.13682698708848137,
            "s2_id": 5221390668558830581,
            "additional_attributes": {"linkRefId"},
            "linkRefId": "2",
        },
        "0": {
            "services": {"service1"},
            "routes": {"1"},
            "id": "0",
            "x": 529455.7452394223,
            "y": 182401.37630677427,
            "epsg": "epsg:27700",
            "name": "",
            "lat": 51.525696033239186,
            "lon": -0.13530998708775874,
            "s2_id": 5221390668020036699,
            "additional_attributes": {"linkRefId"},
            "linkRefId": "0",
        },
    }
    edges = [
        ("4", "5", {"services": {"service2"}, "routes": {"4"}, "modes": {"rail"}}),
        ("3", "4", {"services": {"service2"}, "routes": {"3"}, "modes": {"rail"}}),
        ("1", "2", {"services": {"service1"}, "routes": {"2"}, "modes": {"bus"}}),
        ("0", "1", {"services": {"service1"}, "routes": {"1"}, "modes": {"bus"}}),
    ]
    graph.add_nodes_from(nodes)
    graph.add_edges_from(edges)
    set_node_attributes(graph, nodes)
    graph.graph["change_log"] = change_log.ChangeLog()
    return graph


@pytest.fixture()
def schedule_with_additional_attrib_stop():
    schedule = Schedule("epsg:27700")
    schedule.add_service(
        Service(
            id="s1",
            routes=[
                Route(
                    id="r1",
                    route_short_name="r1",
                    mode="bus",
                    arrival_offsets=["00:00:00", "00:01:00"],
                    departure_offsets=["00:00:00", "00:01:00"],
                    headway_spec={("07:00:00", "08:00:00"): 20},
                    stops=[
                        Stop(
                            "s1",
                            x=1,
                            y=1,
                            epsg="epsg:27700",
                            attributes={"carAccessible": "true", "accessLinkId_car": "linkID"},
                        ),
                        Stop("s2", x=1, y=1, epsg="epsg:27700"),
                    ],
                )
            ],
        )
    )
    return schedule


@pytest.fixture()
def schedule_with_additional_attrib_stop_xml_file():
    return (TEST_DATA_DIR / "matsim" / "schedule_stops_with_additional_attrib.xml").absolute()


@pytest.fixture()
def schedule_with_additional_attrib():
    schedule = Schedule("epsg:27700")
    schedule.attributes["additional_attrib"] = "attrib_value"
    schedule.add_service(
        Service(
            id="s1",
            routes=[
                Route(
                    id="r1",
                    route_short_name="r1",
                    mode="bus",
                    arrival_offsets=["00:00:00", "00:01:00"],
                    departure_offsets=["00:00:00", "00:01:00"],
                    headway_spec={("07:00:00", "08:00:00"): 20},
                    stops=[
                        Stop("s1", x=1, y=1, epsg="epsg:27700"),
                        Stop("s2", x=1, y=1, epsg="epsg:27700"),
                    ],
                )
            ],
        )
    )
    return schedule


@pytest.fixture()
def schedule_with_additional_attribs_xml_file():
    return (TEST_DATA_DIR / "matsim" / "schedule_with_additional_attrib.xml").absolute()


@pytest.fixture()
def schedule_with_additional_route_attrib():
    schedule = Schedule("epsg:27700")
    schedule.add_service(
        Service(
            id="s1",
            routes=[
                Route(
                    id="r1",
                    route_short_name="r1",
                    mode="bus",
                    arrival_offsets=["00:00:00", "00:01:00"],
                    departure_offsets=["00:00:00", "00:01:00"],
                    headway_spec={("07:00:00", "08:00:00"): 20},
                    attributes={"additional_attrib": "attrib_value"},
                    stops=[
                        Stop("s1", x=1, y=1, epsg="epsg:27700"),
                        Stop("s2", x=1, y=1, epsg="epsg:27700"),
                    ],
                )
            ],
        )
    )
    return schedule


@pytest.fixture()
def schedule_with_additional_route_attribs_xml_file():
    return (TEST_DATA_DIR / "matsim" / "schedule_route_with_additional_attrib.xml").absolute()


@pytest.fixture()
def schedule_with_additional_service_attrib():
    schedule = Schedule("epsg:27700")
    schedule.add_service(
        Service(
            id="s1",
            routes=[
                Route(
                    id="r1",
                    route_short_name="r1",
                    mode="bus",
                    arrival_offsets=["00:00:00", "00:01:00"],
                    departure_offsets=["00:00:00", "00:01:00"],
                    headway_spec={("07:00:00", "08:00:00"): 20},
                    stops=[
                        Stop("s1", x=1, y=1, epsg="epsg:27700"),
                        Stop("s2", x=1, y=1, epsg="epsg:27700"),
                    ],
                )
            ],
            attributes={"additional_attrib": "attrib_value"},
        )
    )
    return schedule


@pytest.fixture()
def schedule_with_additional_service_attribs_xml_file():
    return (TEST_DATA_DIR / "matsim" / "schedule_service_with_additional_attrib.xml").absolute()


###########################################################
# Route
###########################################################


@pytest.fixture()
def route():
    a = Stop(id="1", x=4, y=2, epsg="epsg:27700", linkRefId="1")
    b = Stop(id="2", x=1, y=2, epsg="epsg:27700", linkRefId="2")
    c = Stop(id="3", x=3, y=3, epsg="epsg:27700", linkRefId="3")
    d = Stop(id="4", x=7, y=5, epsg="epsg:27700", linkRefId="4")
    return Route(
        route_short_name="name",
        mode="bus",
        stops=[a, b, c, d],
        trips={
            "trip_id": ["1", "2"],
            "trip_departure_time": ["10:00:00", "20:00:00"],
            "vehicle_id": ["veh_1_bus", "veh_2_bus"],
        },
        arrival_offsets=["00:00:00", "00:03:00", "00:07:00", "00:13:00"],
        departure_offsets=["00:00:00", "00:05:00", "00:09:00", "00:15:00"],
        route=["1", "2", "3", "4"],
        id="1",
    )


@pytest.fixture()
def self_looping_route():
    return Route(
        route_short_name="name",
        mode="bus",
        stops=[
            Stop(id="1", x=4, y=2, epsg="epsg:27700"),
            Stop(id="1", x=4, y=2, epsg="epsg:27700"),
            Stop(id="3", x=3, y=3, epsg="epsg:27700"),
            Stop(id="4", x=7, y=5, epsg="epsg:27700"),
        ],
        trips={
            "trip_id": ["1", "2"],
            "trip_departure_time": ["10:00:00", "20:00:00"],
            "vehicle_id": ["veh_3_bus", "veh_4_bus"],
        },
        arrival_offsets=["00:00:00", "00:03:00", "00:07:00", "00:13:00"],
        departure_offsets=["00:00:00", "00:05:00", "00:09:00", "00:15:00"],
    )


@pytest.fixture()
def similar_non_exact_test_route():
    return Route(
        route_short_name="route",
        mode="bus",
        stops=[
            Stop(id="0", x=528504.1342843144, y=182155.7435136598, epsg="epsg:27700"),
            Stop(id="0", x=528504.1342843144, y=182155.7435136598, epsg="epsg:27700"),
        ],
        trips={
            "trip_id": ["Blep_04:40:00"],
            "trip_departure_time": ["05:40:00"],
            "vehicle_id": ["veh_1_bus"],
        },
        arrival_offsets=["00:00:00", "00:03:00"],
        departure_offsets=["00:00:00", "00:05:00"],
    )


###########################################################
# Intermodal access-egress
###########################################################
@pytest.fixture()
def network_for_intermodal_access_egress_testing():
    class NetworkForIntermodalAccessEgressTesting:
        def __init__(self):
            self.network = Network(epsg="epsg:27700")
            self.network.add_nodes(
                {
                    "A": {
                        "id": "A",
                        "x": "528704",
                        "y": "182068",
                        "lon": -0.14625948709424305,
                        "lat": 51.52287873323954,
                        "s2_id": 5221390329378179879,
                    },
                    "B": {
                        "id": "B",
                        "x": "528835",
                        "y": "182006",
                        "lon": -0.14439428709377497,
                        "lat": 51.52228713323965,
                        "s2_id": 5221390328605860387,
                    },
                }
            )
            self.network.add_links(
                {
                    "link_AB": {
                        "id": "link_AB",
                        "from": "A",
                        "to": "B",
                        "freespeed": 10,
                        "capacity": 600,
                        "permlanes": 1,
                        "oneway": "1",
                        "modes": ["car", "bus"],
                        "s2_from": 5221390329378179879,
                        "s2_to": 5221390328605860387,
                        "length": 53,
                    },
                    "link_BA": {
                        "id": "link_BA",
                        "from": "B",
                        "to": "A",
                        "freespeed": 10,
                        "capacity": 600,
                        "permlanes": 1,
                        "oneway": "1",
                        "modes": ["car", "bus"],
                        "s2_from": 5221390329378179879,
                        "s2_to": 5221390328605860387,
                        "length": 53,
                    },
                }
            )
            self.network.schedule = Schedule(
                epsg="epsg:27700",
                services=[
                    Service(
                        id="service",
                        routes=[
                            Route(
                                id="route",
                                route_short_name="route",
                                mode="bus",
                                stops=[
                                    Stop(
                                        id="Stop_A",
                                        x=528705,
                                        y=182069,
                                        epsg="epsg:27700",
                                        linkRefId="link_AB",
                                    ),
                                    Stop(
                                        id="Stop_B",
                                        x=528836,
                                        y=182007,
                                        epsg="epsg:27700",
                                        linkRefId="link_BA",
                                    ),
                                ],
                                trips={
                                    "trip_id": ["trip_id_04:40:00"],
                                    "trip_departure_time": ["04:40:00"],
                                    "vehicle_id": ["veh_1_bus"],
                                },
                                route=["link_AB", "link_BA"],
                                arrival_offsets=["00:00:00", "00:02:00"],
                                departure_offsets=["00:00:00", "00:02:00"],
                            )
                        ],
                    )
                ],
            )
            self.intermodal_access_egress_attribute_keys = []
            self.intermodal_access_egress_connections_dataframe = None
            self.invalid_intermodal_access_egress_connections = {}

        @property
        def expected_intermodal_access_egress_attribute_keys(self):
            return self.intermodal_access_egress_attribute_keys

        @property
        def expected_intermodal_access_egress_connections_dataframe(self):
            return self.intermodal_access_egress_connections_dataframe

        @property
        def expected_invalid_intermodal_access_egress_connections(self):
            return self.invalid_intermodal_access_egress_connections

        @property
        def schedule(self):
            return self.network.schedule

        def without_intermodal_access_egress(self):
            return self

        def with_valid_car_intermodal_access_egress(self):
            access_link_id_tag = "accessLinkId_car"
            accessible_tag = "carAccessible"
            distance_catchment_tag = "car_distance_catchment_tag"
            new_stops_data = {
                "Stop_A": {
                    "attributes": {
                        access_link_id_tag: "link_AB",
                        accessible_tag: "true",
                        distance_catchment_tag: 10,
                    }
                },
                "Stop_B": {
                    "attributes": {
                        access_link_id_tag: "link_BA",
                        accessible_tag: "true",
                        distance_catchment_tag: 10,
                    }
                },
            }
            self.schedule.apply_attributes_to_stops(new_stops_data)
            self.intermodal_access_egress_attribute_keys = [access_link_id_tag]
            self.intermodal_access_egress_connections_dataframe = pd.DataFrame(
                {"attributes::accessLinkId_car": {"Stop_A": "link_AB", "Stop_B": "link_BA"}}
            )
            self.invalid_intermodal_access_egress_connections = {
                "car": {
                    "stops_with_links_not_in_network": set(),
                    "stops_with_links_with_wrong_modes": set(),
                }
            }
            return self

        def with_invalid_intermodal_access_egress(self):
            access_link_id_tag = "accessLinkId_piggyback"
            accessible_tag = "piggybackAccessible"
            distance_catchment_tag = "piggyback_distance_catchment_tag"
            new_stops_data = {
                "Stop_A": {
                    "attributes": {
                        access_link_id_tag: "non_existent_link",  # stop with link that doesn't exist
                        accessible_tag: "true",
                        distance_catchment_tag: 10,
                    }
                },
                "Stop_B": {
                    "attributes": {
                        access_link_id_tag: "link_BA",  # stop with link that doesn't have the right mode on it
                        accessible_tag: "true",
                        distance_catchment_tag: 10,
                    }
                },
            }
            self.schedule.apply_attributes_to_stops(new_stops_data)
            self.intermodal_access_egress_attribute_keys = [access_link_id_tag]
            self.intermodal_access_egress_connections_dataframe = pd.DataFrame(
                {
                    "attributes::accessLinkId_piggyback": {
                        "Stop_A": "non_existent_link",
                        "Stop_B": "link_BA",
                    }
                }
            )
            self.invalid_intermodal_access_egress_connections = {
                "piggyback": {
                    "stops_with_links_not_in_network": {"Stop_A"},
                    "stops_with_links_with_wrong_modes": {"Stop_B"},
                }
            }
            return self

    return NetworkForIntermodalAccessEgressTesting()


@pytest.fixture
def network_without_intermodal_access_egress(network_for_intermodal_access_egress_testing):
    return network_for_intermodal_access_egress_testing.without_intermodal_access_egress()


@pytest.fixture
def network_with_valid_car_intermodal_access_egress(network_for_intermodal_access_egress_testing):
    return network_for_intermodal_access_egress_testing.with_valid_car_intermodal_access_egress()


@pytest.fixture
def network_with_invalid_intermodal_access_egress(network_for_intermodal_access_egress_testing):
    return network_for_intermodal_access_egress_testing.with_invalid_intermodal_access_egress()


###########################################################
# OSM reading configs
###########################################################


@pytest.fixture()
def full_fat_default_config_path():
    return (GENET_CONFIG_DIR / "OSM" / "default_config.yml").absolute()


@pytest.fixture()
def full_fat_default_config(full_fat_default_config_path):
    return osm_reader.Config(full_fat_default_config_path)


@pytest.fixture()
def osm_test_file():
    return (TEST_DATA_DIR / "osm" / "osm.xml").absolute()


###########################################################
# vehicle types configs
###########################################################


@pytest.fixture()
def vehicle_definitions_config_path():
    return (GENET_CONFIG_DIR / "vehicles" / "vehicle_definitions.yml").absolute()


###########################################################
# XML mocks
###########################################################
