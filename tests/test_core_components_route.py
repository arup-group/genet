import os

import pytest
from pandas import DataFrame, Timestamp
from pandas.testing import assert_frame_equal

from genet.exceptions import ServiceIndexError
from genet.schedule_elements import Route, Stop, verify_graph_schema
from genet.utils import plot
from tests.fixtures import (
    assert_logging_warning_caught_with_message_containing,
    assert_semantically_equal,
    stop_epsg_27700,  # noqa: F401
)


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
def strongly_connected_route():
    return Route(
        route_short_name="name",
        mode="bus",
        stops=[
            Stop(id="1", x=4, y=2, epsg="epsg:27700"),
            Stop(id="2", x=1, y=2, epsg="epsg:27700"),
            Stop(id="3", x=3, y=3, epsg="epsg:27700"),
            Stop(id="4", x=7, y=5, epsg="epsg:27700"),
            Stop(id="1", x=4, y=2, epsg="epsg:27700"),
        ],
        trips={
            "trip_id": ["1", "2"],
            "trip_departure_time": ["10:00:00", "20:00:00"],
            "vehicle_id": ["veh_3_bus", "veh_4_bus"],
        },
        arrival_offsets=["00:00:00", "00:03:00", "00:07:00", "00:13:00", "00:17:00"],
        departure_offsets=["00:00:00", "00:05:00", "00:09:00", "00:15:00", "00:18:00"],
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


def test_initiating_route(route):
    r = route
    assert_semantically_equal(
        dict(r._graph.nodes(data=True)),
        {
            "1": {
                "routes": {"1"},
                "id": "1",
                "x": 4.0,
                "y": 2.0,
                "epsg": "epsg:27700",
                "name": "",
                "lat": 49.76682779861249,
                "lon": -7.557106577683727,
                "s2_id": 5205973754090531959,
                "linkRefId": "1",
            },
            "2": {
                "routes": {"1"},
                "id": "2",
                "x": 1.0,
                "y": 2.0,
                "epsg": "epsg:27700",
                "name": "",
                "lat": 49.766825803756994,
                "lon": -7.557148039524952,
                "s2_id": 5205973754090365183,
                "linkRefId": "2",
            },
            "3": {
                "routes": {"1"},
                "id": "3",
                "x": 3.0,
                "y": 3.0,
                "epsg": "epsg:27700",
                "name": "",
                "lat": 49.76683608549253,
                "lon": -7.557121424907424,
                "s2_id": 5205973754090203369,
                "linkRefId": "3",
            },
            "4": {
                "routes": {"1"},
                "id": "4",
                "x": 7.0,
                "y": 5.0,
                "epsg": "epsg:27700",
                "name": "",
                "lat": 49.766856648946295,
                "lon": -7.5570681956375,
                "s2_id": 5205973754097123809,
                "linkRefId": "4",
            },
        },
    )
    assert_semantically_equal(
        r._graph.edges(data=True)._adjdict,
        {
            "1": {"2": {"routes": {"1"}}},
            "2": {"3": {"routes": {"1"}}},
            "3": {"4": {"routes": {"1"}}},
            "4": {},
        },
    )
    log = r._graph.graph.pop("change_log")
    assert log.empty
    assert_semantically_equal(
        r._graph.graph,
        {
            "name": "Route graph",
            "routes": {
                "1": {
                    "route_short_name": "name",
                    "mode": "bus",
                    "trips": {
                        "trip_id": ["1", "2"],
                        "trip_departure_time": ["10:00:00", "20:00:00"],
                        "vehicle_id": ["veh_1_bus", "veh_2_bus"],
                    },
                    "arrival_offsets": ["00:00:00", "00:03:00", "00:07:00", "00:13:00"],
                    "departure_offsets": ["00:00:00", "00:05:00", "00:09:00", "00:15:00"],
                    "route_long_name": "",
                    "id": "1",
                    "route": ["1", "2", "3", "4"],
                    "await_departure": [],
                    "ordered_stops": ["1", "2", "3", "4"],
                }
            },
            "services": {},
            "crs": "epsg:27700",
        },
    )


def test_initiating_route_with_headway_spec():
    r = Route(
        id="route_ID",
        route_short_name="name",
        mode="bus",
        stops=[
            Stop(id="1", x=4, y=2, epsg="epsg:27700"),
            Stop(id="1", x=4, y=2, epsg="epsg:27700"),
            Stop(id="3", x=3, y=3, epsg="epsg:27700"),
            Stop(id="4", x=7, y=5, epsg="epsg:27700"),
        ],
        headway_spec={("01:00:00", "02:00:00"): 20, ("02:00:00", "03:00:00"): 30},
        arrival_offsets=["00:00:00", "00:03:00", "00:07:00", "00:13:00"],
        departure_offsets=["00:00:00", "00:05:00", "00:09:00", "00:15:00"],
    )

    assert_semantically_equal(
        r.trips,
        {
            "trip_id": [
                "route_ID_01:00:00",
                "route_ID_01:20:00",
                "route_ID_01:40:00",
                "route_ID_02:00:00",
                "route_ID_02:30:00",
                "route_ID_03:00:00",
            ],
            "trip_departure_time": [
                "01:00:00",
                "01:20:00",
                "01:40:00",
                "02:00:00",
                "02:30:00",
                "03:00:00",
            ],
            "vehicle_id": [
                "veh_bus_route_ID_01:00:00",
                "veh_bus_route_ID_01:20:00",
                "veh_bus_route_ID_01:40:00",
                "veh_bus_route_ID_02:00:00",
                "veh_bus_route_ID_02:30:00",
                "veh_bus_route_ID_03:00:00",
            ],
        },
    )


def test_updating_route_trips_with_headway(route):
    route.generate_trips_from_headway({("01:00:00", "02:00:00"): 20, ("02:00:00", "03:00:00"): 30})
    assert_semantically_equal(
        route.trips,
        {
            "trip_id": [
                "1_01:00:00",
                "1_01:20:00",
                "1_01:40:00",
                "1_02:00:00",
                "1_02:30:00",
                "1_03:00:00",
            ],
            "trip_departure_time": [
                "01:00:00",
                "01:20:00",
                "01:40:00",
                "02:00:00",
                "02:30:00",
                "03:00:00",
            ],
            "vehicle_id": [
                "veh_bus_1_01:00:00",
                "veh_bus_1_01:20:00",
                "veh_bus_1_01:40:00",
                "veh_bus_1_02:00:00",
                "veh_bus_1_02:30:00",
                "veh_bus_1_03:00:00",
            ],
        },
    )


def test_generating_trips_from_headway_preserves_graph_schema(route):
    verify_graph_schema(route.graph())

    route.generate_trips_from_headway({("01:00:00", "02:00:00"): 20, ("02:00:00", "03:00:00"): 30})

    verify_graph_schema(route.graph())


def test__repr__shows_stops_and_trips_length(route):
    assert str(len(route.ordered_stops)) in route.__repr__()
    assert str(len(route.trips["trip_id"])) in route.__repr__()


def test__str__shows_info(route):
    assert route.id in route.__str__()
    assert route.route_short_name in route.__str__()


def test_print_shows_info(mocker, route):
    mocker.patch.object(Route, "info")
    route.print()
    Route.info.assert_called_once()


def test_info_shows_id_name_and_len_of_stops_and_trips(route):
    info = route.info()
    assert route.id in info
    assert route.route_short_name in info
    assert str(len(route.ordered_stops)) in info
    assert str(len(route.trips["trip_id"])) in info


def test_plot_delegates_to_util_plot_plot_graph_routes(mocker, route):
    mocker.patch.object(plot, "plot_geodataframes_on_kepler_map")
    route.plot()
    plot.plot_geodataframes_on_kepler_map.assert_called_once()


def test_plot_saves_to_the_specified_directory(tmpdir, route):
    filename = f"route_{route.id}_map"
    expected_plot_path = os.path.join(tmpdir, filename + ".html")
    assert not os.path.exists(expected_plot_path)

    route.plot(output_dir=tmpdir)

    assert os.path.exists(expected_plot_path)


def test_build_graph_builds_correct_graph():
    route = Route(
        route_short_name="name",
        mode="bus",
        stops=[
            Stop(id="1", x=4, y=2, epsg="epsg:27700"),
            Stop(id="2", x=1, y=2, epsg="epsg:27700"),
            Stop(id="3", x=3, y=3, epsg="epsg:27700"),
            Stop(id="4", x=7, y=5, epsg="epsg:27700"),
        ],
        trips={
            "trip_id": ["1", "2"],
            "trip_departure_time": ["1", "2"],
            "vehicle_id": ["veh_3_bus", "veh_4_bus"],
        },
        arrival_offsets=["1", "2"],
        departure_offsets=["1", "2"],
    )
    g = route.graph()
    assert_semantically_equal(
        dict(g.nodes(data=True)),
        {
            "1": {
                "routes": {""},
                "id": "1",
                "x": 4.0,
                "y": 2.0,
                "epsg": "epsg:27700",
                "lat": 49.76682779861249,
                "lon": -7.557106577683727,
                "s2_id": 5205973754090531959,
                "name": "",
            },
            "2": {
                "routes": {""},
                "id": "2",
                "x": 1.0,
                "y": 2.0,
                "epsg": "epsg:27700",
                "lat": 49.766825803756994,
                "lon": -7.557148039524952,
                "s2_id": 5205973754090365183,
                "name": "",
            },
            "3": {
                "routes": {""},
                "id": "3",
                "x": 3.0,
                "y": 3.0,
                "epsg": "epsg:27700",
                "lat": 49.76683608549253,
                "lon": -7.557121424907424,
                "s2_id": 5205973754090203369,
                "name": "",
            },
            "4": {
                "routes": {""},
                "id": "4",
                "x": 7.0,
                "y": 5.0,
                "epsg": "epsg:27700",
                "lat": 49.766856648946295,
                "lon": -7.5570681956375,
                "s2_id": 5205973754097123809,
                "name": "",
            },
        },
    )
    assert_semantically_equal(
        g.edges(data=True)._adjdict,
        {
            "1": {"2": {"routes": {""}}},
            "2": {"3": {"routes": {""}}},
            "3": {"4": {"routes": {""}}},
            "4": {},
        },
    )


def test_routes_equal(stop_epsg_27700):
    a = Route(
        route_short_name="route",
        mode="bus",
        stops=[stop_epsg_27700, stop_epsg_27700],
        trips={
            "trip_id": ["VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00"],
            "trip_departure_time": ["04:40:00"],
            "vehicle_id": ["veh_1_bus"],
        },
        arrival_offsets=["00:00:00", "00:02:00"],
        departure_offsets=["00:00:00", "00:02:00"],
    )

    b = Route(
        route_short_name="route",
        mode="bus",
        stops=[stop_epsg_27700, stop_epsg_27700],
        trips={
            "trip_id": ["VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00"],
            "trip_departure_time": ["04:40:00"],
            "vehicle_id": ["veh_1_bus"],
        },
        arrival_offsets=["00:00:00", "00:02:00"],
        departure_offsets=["00:00:00", "00:02:00"],
    )

    assert a == b


def test_routes_exact(stop_epsg_27700):
    a = Route(
        route_short_name="route",
        mode="bus",
        stops=[stop_epsg_27700, stop_epsg_27700],
        trips={
            "trip_id": ["VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00"],
            "trip_departure_time": ["04:40:00"],
            "vehicle_id": ["veh_1_bus"],
        },
        arrival_offsets=["00:00:00", "00:02:00"],
        departure_offsets=["00:00:00", "00:02:00"],
    )

    b = Route(
        route_short_name="route",
        mode="bus",
        stops=[stop_epsg_27700, stop_epsg_27700],
        trips={
            "trip_id": ["VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00"],
            "trip_departure_time": ["04:40:00"],
            "vehicle_id": ["veh_1_bus"],
        },
        arrival_offsets=["00:00:00", "00:02:00"],
        departure_offsets=["00:00:00", "00:02:00"],
    )

    assert a.is_exact(b)


def test_route_isin_exact_list(route):
    a = route
    assert a.isin_exact([route, route, route])


def test_route_is_not_in_exact_list(route, stop_epsg_27700):
    a = Route(
        route_short_name="route",
        mode="bus",
        stops=[stop_epsg_27700, stop_epsg_27700],
        trips={},
        arrival_offsets=[],
        departure_offsets=[],
    )

    assert not a.isin_exact([route, route, route])


def test_is_strongly_connected_with_strongly_connected_route(strongly_connected_route):
    assert strongly_connected_route.is_strongly_connected()


def test_is_strongly_connected_with_not_strongly_connected_route(route):
    assert not route.is_strongly_connected()


def test_has_self_loops_with_self_has_self_looping_route(self_looping_route):
    assert self_looping_route.has_self_loops()


def test_has_self_loops_returns_self_looping_stops(self_looping_route):
    loop_nodes = self_looping_route.has_self_loops()
    assert loop_nodes == ["1"]


def test_has_self_loops_with_non_looping_route(route):
    assert not route.has_self_loops()


def test_has_more_than_one_stop_with_regular_route(route):
    assert route.has_more_than_one_stop()


def test_has_more_than_one_stop_with_route_with_single_stop():
    route = Route(
        route_short_name="name",
        mode="bus",
        stops=[Stop(id="1", x=4, y=2, epsg="epsg:27700")],
        trips={},
        arrival_offsets=[],
        departure_offsets=[],
    )
    assert not route.has_more_than_one_stop()


def test_has_network_route_with_route_that_has_a_network_route(route):
    assert route.has_network_route()


def test_has_network_route_with_route_without_a_network_route(route):
    route.route = []
    assert not route.has_network_route()


def test_dividing_typical_network_route():
    A = Stop(id="A", x=4, y=2, epsg="epsg:27700", linkRefId="a-a")
    B = Stop(id="B", x=1, y=2, epsg="epsg:27700", linkRefId="b-b")
    C = Stop(id="C", x=3, y=3, epsg="epsg:27700", linkRefId="c-c")
    r = Route(
        route_short_name="1",
        mode="bus",
        stops=[A, B, C],
        headway_spec={("00:07:00", "08:00:00"): 30},
        arrival_offsets=["00:00:00", "00:03:00", "00:07:00"],
        departure_offsets=["00:00:00", "00:05:00", "00:09:00"],
        route=["a-a", "a-b", "b-b", "b-c", "c-c"],
        id="1",
    )
    assert r.divide_network_route_between_stops() == [["a-a", "a-b", "b-b"], ["b-b", "b-c", "c-c"]]


def test_dividing_network_route_with_a_shared_linkrefid():
    A = Stop(id="A", x=4, y=2, epsg="epsg:27700", linkRefId="a-a")
    B1 = Stop(id="B1", x=1, y=2, epsg="epsg:27700", linkRefId="b-b")
    B2 = Stop(id="B2", x=1, y=2, epsg="epsg:27700", linkRefId="b-b")
    C = Stop(id="C", x=3, y=3, epsg="epsg:27700", linkRefId="c-c")
    r = Route(
        route_short_name="1",
        mode="bus",
        stops=[A, B1, B2, C],
        headway_spec={("00:07:00", "08:00:00"): 30},
        arrival_offsets=["00:00:00", "00:03:00", "00:07:00"],
        departure_offsets=["00:00:00", "00:05:00", "00:09:00"],
        route=["a-a", "a-b", "b-b", "b-c", "c-c"],
        id="1",
    )
    assert r.divide_network_route_between_stops() == [
        ["a-a", "a-b", "b-b"],
        ["b-b"],
        ["b-b", "b-c", "c-c"],
    ]


def test_dividing_network_route_with_a_longer_invalid_route_cuts_off_the_route():
    A = Stop(id="A", x=4, y=2, epsg="epsg:27700", linkRefId="a-a")
    B = Stop(id="B", x=1, y=2, epsg="epsg:27700", linkRefId="b-b")
    C = Stop(id="C", x=3, y=3, epsg="epsg:27700", linkRefId="c-c")
    r = Route(
        route_short_name="1",
        mode="bus",
        stops=[A, B, C],
        headway_spec={("00:07:00", "08:00:00"): 30},
        arrival_offsets=["00:00:00", "00:03:00", "00:07:00"],
        departure_offsets=["00:00:00", "00:05:00", "00:09:00"],
        route=["a-a", "a-b", "b-b", "b-c", "c-c", "c-d"],
        id="1",
    )
    assert r.divide_network_route_between_stops() == [["a-a", "a-b", "b-b"], ["b-b", "b-c", "c-c"]]


def test_has_correctly_ordered_route_with_a_correct_route():
    a = Stop(id="1", x=4, y=2, epsg="epsg:27700")
    a.add_additional_attributes({"linkRefId": "10"})
    b = Stop(id="2", x=4, y=2, epsg="epsg:27700")
    b.add_additional_attributes({"linkRefId": "20"})
    c = Stop(id="3", x=4, y=2, epsg="epsg:27700")
    c.add_additional_attributes({"linkRefId": "30"})

    r = Route(
        route_short_name="name",
        mode="bus",
        stops=[a, b, c],
        trips={
            "trip_id": ["1", "2"],
            "trip_departure_time": ["10:00:00", "20:00:00"],
            "vehicle_id": ["veh_1_bus", "veh_2_bus"],
        },
        arrival_offsets=["1", "2"],
        departure_offsets=["1", "2"],
        route=["10", "15", "20", "25", "30"],
        id="1",
    )
    assert r.has_correctly_ordered_route()


def test_does_not_have_a_correctly_ordered_route_with_disordered_route():
    a = Stop(id="1", x=4, y=2, epsg="epsg:27700")
    a.add_additional_attributes({"linkRefId": "10"})
    b = Stop(id="2", x=4, y=2, epsg="epsg:27700")
    b.add_additional_attributes({"linkRefId": "20"})
    c = Stop(id="3", x=4, y=2, epsg="epsg:27700")
    c.add_additional_attributes({"linkRefId": "30"})

    r = Route(
        route_short_name="name",
        mode="bus",
        stops=[a, b, c],
        trips={
            "trip_id": ["1", "2"],
            "trip_departure_time": ["10:00:00", "20:00:00"],
            "vehicle_id": ["veh_1_bus", "veh_2_bus"],
        },
        arrival_offsets=["1", "2"],
        departure_offsets=["1", "2"],
        route=["10", "15", "30", "25", "20"],
        id="1",
    )
    assert not r.has_correctly_ordered_route()


def test_does_not_have_a_correctly_ordered_route_with_stop_missing_linkrefid():
    a = Stop(id="1", x=4, y=2, epsg="epsg:27700")
    a.add_additional_attributes({"linkRefId": "10"})
    b = Stop(id="2", x=4, y=2, epsg="epsg:27700")
    b.add_additional_attributes({"linkRefId": "20"})
    c = Stop(id="3", x=4, y=2, epsg="epsg:27700")

    r = Route(
        route_short_name="name",
        mode="bus",
        stops=[a, b, c],
        trips={
            "trip_id": ["1", "2"],
            "trip_departure_time": ["10:00:00", "20:00:00"],
            "vehicle_id": ["veh_1_bus", "veh_2_bus"],
        },
        arrival_offsets=["1", "2"],
        departure_offsets=["1", "2"],
        route=["10", "15", "30", "25", "20"],
        id="1",
    )
    assert not r.has_correctly_ordered_route()


def test_does_not_have_a_correctly_ordered_route_with_no_route():
    a = Stop(id="1", x=4, y=2, epsg="epsg:27700")
    a.add_additional_attributes({"linkRefId": "10"})
    b = Stop(id="2", x=4, y=2, epsg="epsg:27700")
    b.add_additional_attributes({"linkRefId": "20"})
    c = Stop(id="3", x=4, y=2, epsg="epsg:27700")
    c.add_additional_attributes({"linkRefId": "30"})

    r = Route(
        route_short_name="name",
        mode="bus",
        stops=[a, b, c],
        trips={
            "trip_id": ["1", "2"],
            "trip_departure_time": ["10:00:00", "20:00:00"],
            "vehicle_id": ["veh_1_bus", "veh_2_bus"],
        },
        arrival_offsets=["1", "2"],
        departure_offsets=["1", "2"],
        route=[],
        id="1",
    )
    assert not r.has_correctly_ordered_route()


def test_has_valid_offsets_with_valid_route(route):
    assert route.has_valid_offsets()


def test_has_valid_offsets_with_route_with_invalid_offsets(route):
    route.departure_offsets = []
    route.arrival_offsets = []
    assert not route.has_valid_offsets()


def test_has_valid_offsets_with_route_with_wrong_number_of_offsets(route):
    route.departure_offsets = ["00:00:00", "00:03:00", "00:07:00"]
    route.arrival_offsets = ["00:00:00", "00:03:00", "00:07:00"]
    assert not route.has_valid_offsets()


def test_has_valid_offsets_with_route_with_empty_offsets(route):
    route.departure_offsets = []
    route.arrival_offsets = []
    assert not route.has_valid_offsets()


def test_has_id(route):
    assert route.has_id()


def test_is_valid_with_valid_route(route):
    assert route.is_valid_route()


def test_is_valid_with_looping_route(self_looping_route):
    assert not self_looping_route.is_valid_route()


def test_is_valid_with_non_network_route(route):
    route.route = []
    assert not route.is_valid_route()


def test_is_valid_with_single_stop_network():
    route = Route(
        route_short_name="name",
        mode="bus",
        stops=[Stop(id="1", x=4, y=2, epsg="epsg:27700")],
        trips={},
        arrival_offsets=[],
        departure_offsets=[],
    )
    assert not route.is_valid_route()


def test_building_trips_dataframe_with_stops_accepts_backwards_compatibility(route, mocker, caplog):
    mocker.patch.object(Route, "trips_with_stops_to_dataframe")
    route.trips_with_stops_to_dataframe(route.trips_to_dataframe())
    route.trips_with_stops_to_dataframe.assert_called_once()
    assert_logging_warning_caught_with_message_containing(
        caplog, "`route_trips_with_stops_to_dataframe` method is deprecated"
    )


def test_building_trips_dataframe_with_stops(route):
    df = route.trips_with_stops_to_dataframe()

    correct_df = DataFrame(
        {
            "departure_time": {
                0: Timestamp("1970-01-01 10:00:00"),
                1: Timestamp("1970-01-01 10:05:00"),
                2: Timestamp("1970-01-01 10:09:00"),
                3: Timestamp("1970-01-01 20:00:00"),
                4: Timestamp("1970-01-01 20:05:00"),
                5: Timestamp("1970-01-01 20:09:00"),
            },
            "arrival_time": {
                0: Timestamp("1970-01-01 10:03:00"),
                1: Timestamp("1970-01-01 10:07:00"),
                2: Timestamp("1970-01-01 10:13:00"),
                3: Timestamp("1970-01-01 20:03:00"),
                4: Timestamp("1970-01-01 20:07:00"),
                5: Timestamp("1970-01-01 20:13:00"),
            },
            "from_stop": {0: "1", 1: "2", 2: "3", 3: "1", 4: "2", 5: "3"},
            "to_stop": {0: "2", 1: "3", 2: "4", 3: "2", 4: "3", 5: "4"},
            "trip_id": {0: "1", 1: "1", 2: "1", 3: "2", 4: "2", 5: "2"},
            "vehicle_id": {
                0: "veh_1_bus",
                1: "veh_1_bus",
                2: "veh_1_bus",
                3: "veh_2_bus",
                4: "veh_2_bus",
                5: "veh_2_bus",
            },
            "route_id": {0: "1", 1: "1", 2: "1", 3: "1", 4: "1", 5: "1"},
            "route_name": {0: "name", 1: "name", 2: "name", 3: "name", 4: "name", 5: "name"},
            "mode": {0: "bus", 1: "bus", 2: "bus", 3: "bus", 4: "bus", 5: "bus"},
            "from_stop_name": {0: "", 1: "", 2: "", 3: "", 4: "", 5: ""},
            "to_stop_name": {0: "", 1: "", 2: "", 3: "", 4: "", 5: ""},
        }
    )

    assert_frame_equal(df, correct_df)


def test_generating_trips_dataframe(route):
    df = route.trips_to_dataframe()

    assert_frame_equal(
        df,
        DataFrame(
            {
                "trip_id": {0: "1", 1: "2"},
                "trip_departure_time": {
                    0: Timestamp("1970-01-01 10:00:00"),
                    1: Timestamp("1970-01-01 20:00:00"),
                },
                "vehicle_id": {0: "veh_1_bus", 1: "veh_2_bus"},
                "route_id": {0: "1", 1: "1"},
                "mode": {0: "bus", 1: "bus"},
            }
        ),
    )


def test_vehicles(route):
    assert route.vehicles() == {"veh_1_bus", "veh_2_bus"}


def test_service_attribute_data_under_keys_throws_error_from_route_object(route):
    with pytest.raises(ServiceIndexError):
        route.service_attribute_data(keys=["name"])


def test_route_attribute_data_under_key(route):
    df = route.route_attribute_data(keys="route_short_name").sort_index()
    assert_frame_equal(df, DataFrame({"route_short_name": {"1": "name"}}))


def test_route_attribute_data_under_keys(route):
    df = route.route_attribute_data(keys=["route_short_name", "mode"]).sort_index()
    assert_frame_equal(df, DataFrame({"route_short_name": {"1": "name"}, "mode": {"1": "bus"}}))


def test_stop_attribute_data_under_key(route):
    df = route.stop_attribute_data(keys="x").sort_index()
    assert_frame_equal(df, DataFrame({"x": {"1": 4.0, "2": 1.0, "3": 3.0, "4": 7.0}}))


def test_stop_attribute_data_under_keys(route):
    df = route.stop_attribute_data(keys=["x", "y"]).sort_index()
    assert_frame_equal(
        df,
        DataFrame(
            {
                "x": {"1": 4.0, "2": 1.0, "3": 3.0, "4": 7.0},
                "y": {"1": 2.0, "2": 2.0, "3": 3.0, "4": 5.0},
            }
        ),
    )
