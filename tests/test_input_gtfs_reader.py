import pytest
from genet.input import gtfs_reader
from genet.schedule_elements import change_log
from pandas import DataFrame
from pandas.testing import assert_frame_equal

gtfs_test_file = pytest.test_data_dir / "gtfs"
gtfs_test_zip_file = pytest.test_data_dir / "gtfs.zip"


@pytest.fixture()
def correct_stop_times_db():
    return DataFrame(
        {
            "trip_id": {0: "BT1", 1: "BT1", 2: "RT1", 3: "RT1"},
            "arrival_time": {0: "03:21:00", 1: "03:23:00", 2: "03:21:00", 3: "03:23:00"},
            "departure_time": {0: "03:21:00", 1: "03:23:00", 2: "03:21:00", 3: "03:23:00"},
            "stop_id": {0: "BSE", 1: "BSN", 2: "RSN", 3: "RSE"},
            "stop_sequence": {0: 0, 1: 1, 2: 0, 3: 1},
            "stop_headsign": {0: float("nan"), 1: float("nan"), 2: float("nan"), 3: float("nan")},
            "pickup_type": {0: 0, 1: 0, 2: 0, 3: 0},
            "drop_off_type": {0: 1, 1: 0, 2: 0, 3: 1},
            "timepoint": {0: 1, 1: 0, 2: 0, 3: 1},
            "stop_direction_name": {
                0: float("nan"),
                1: float("nan"),
                2: float("nan"),
                3: float("nan"),
            },
        }
    )


@pytest.fixture()
def correct_stops_db():
    return DataFrame(
        {
            "stop_id": {0: "BSE", 1: "BSN", 2: "RSE", 3: "RSN"},
            "stop_code": {0: float("nan"), 1: float("nan"), 2: float("nan"), 3: float("nan")},
            "stop_name": {
                0: "Bus Stop snap to edge",
                1: "Bus Stop snap to node",
                2: "Rail Stop snap to edge",
                3: "Rail Stop snap to node",
            },
            "stop_lat": {0: 51.5226864, 1: 51.5216199, 2: 51.5192615, 3: 51.5231335},
            "stop_lon": {
                0: -0.14136210000000002,
                1: -0.140053,
                2: -0.1421595,
                3: -0.14109460000000001,
            },
            "wheelchair_boarding": {
                0: float("nan"),
                1: float("nan"),
                2: float("nan"),
                3: float("nan"),
            },
            "stop_timezone": {0: float("nan"), 1: float("nan"), 2: float("nan"), 3: float("nan")},
            "location_type": {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0},
            "parent_station": {0: "210G433", 1: "210G432", 2: "210G431", 3: "210G430"},
            "platform_code": {0: float("nan"), 1: float("nan"), 2: float("nan"), 3: float("nan")},
        }
    )


@pytest.fixture()
def correct_trips_db():
    return DataFrame(
        {
            "route_id": {0: "1001", 1: "1002"},
            "service_id": {0: "6630", 1: "6631"},
            "trip_id": {0: "BT1", 1: "RT1"},
            "trip_headsign": {0: "Bus Test trip", 1: "Rail Test trip"},
            "block_id": {0: float("nan"), 1: float("nan")},
            "wheelchair_accessible": {0: 0, 1: 0},
            "trip_direction_name": {0: float("nan"), 1: float("nan")},
            "exceptional": {0: float("nan"), 1: float("nan")},
        }
    )


@pytest.fixture()
def correct_routes_db():
    return DataFrame(
        {
            "route_id": {0: "1001", 1: "1002"},
            "agency_id": {0: "OP550", 1: "OP550"},
            "route_short_name": {0: "BTR", 1: "RTR"},
            "route_long_name": {0: "Bus Test Route", 1: "Rail Test Route"},
            "route_type": {0: 3, 1: 2},
            "route_url": {0: float("nan"), 1: float("nan")},
            "route_color": {0: "CE312D", 1: "CE312D"},
            "route_text_color": {0: "FFFFFF", 1: "FFFFFF"},
            "checkin_duration": {0: float("nan"), 1: float("nan")},
        }
    )


@pytest.fixture()
def correct_schedule_graph_nodes_from_test_gtfs():
    return {
        "BSN": {
            "stop_code": float("nan"),
            "name": "Bus Stop snap to node",
            "lat": 51.5216199,
            "lon": -0.140053,
            "wheelchair_boarding": float("nan"),
            "stop_timezone": float("nan"),
            "location_type": 0.0,
            "parent_station": "210G432",
            "platform_code": float("nan"),
            "id": "BSN",
            "x": -0.140053,
            "y": 51.5216199,
            "epsg": "epsg:4326",
            "s2_id": 5221390684150342605,
            "routes": {"1001_0"},
            "services": {"1001"},
        },
        "RSE": {
            "stop_code": float("nan"),
            "name": "Rail Stop snap to edge",
            "lat": 51.5192615,
            "lon": -0.1421595,
            "wheelchair_boarding": float("nan"),
            "stop_timezone": float("nan"),
            "location_type": 0.0,
            "parent_station": "210G431",
            "platform_code": float("nan"),
            "id": "RSE",
            "x": -0.1421595,
            "y": 51.5192615,
            "epsg": "epsg:4326",
            "s2_id": 5221390324026756531,
            "routes": {"1002_0"},
            "services": {"1002"},
        },
        "RSN": {
            "stop_code": float("nan"),
            "name": "Rail Stop snap to node",
            "lat": 51.5231335,
            "lon": -0.14109460000000001,
            "wheelchair_boarding": float("nan"),
            "stop_timezone": float("nan"),
            "location_type": 0.0,
            "parent_station": "210G430",
            "platform_code": float("nan"),
            "id": "RSN",
            "x": -0.14109460000000001,
            "y": 51.5231335,
            "epsg": "epsg:4326",
            "s2_id": 5221390332291192399,
            "routes": {"1002_0"},
            "services": {"1002"},
        },
        "BSE": {
            "stop_code": float("nan"),
            "name": "Bus Stop snap to edge",
            "lat": 51.5226864,
            "lon": -0.14136210000000002,
            "wheelchair_boarding": float("nan"),
            "stop_timezone": float("nan"),
            "location_type": 0.0,
            "parent_station": "210G433",
            "platform_code": float("nan"),
            "id": "BSE",
            "x": -0.14136210000000002,
            "y": 51.5226864,
            "epsg": "epsg:4326",
            "s2_id": 5221390325135889957,
            "routes": {"1001_0"},
            "services": {"1001"},
        },
    }


@pytest.fixture()
def correct_schedule_graph_edges_from_test_gtfs():
    return {
        "BSN": {},
        "RSE": {},
        "RSN": {"RSE": {"routes": {"1002_0"}, "services": {"1002"}}},
        "BSE": {"BSN": {"routes": {"1001_0"}, "services": {"1001"}}},
    }


@pytest.fixture()
def correct_schedule_graph_data_from_test_gtfs():
    return {
        "name": "Schedule graph",
        "crs": "epsg:4326",
        "route_to_service_map": {"1001_0": "1001", "1002_0": "1002"},
        "service_to_route_map": {"1001": ["1001_0"], "1002": ["1002_0"]},
        "change_log": change_log.ChangeLog(),
        "routes": {
            "1001_0": {
                "departure_offsets": ["00:00:00", "00:02:00"],
                "arrival_offsets": ["00:00:00", "00:02:00"],
                "route_url": float("nan"),
                "route_text_color": "FFFFFF",
                "route_type": 3,
                "route_color": "CE312D",
                "route_short_name": "BTR",
                "checkin_duration": float("nan"),
                "route_long_name": "Bus Test Route",
                "ordered_stops": ["BSE", "BSN"],
                "mode": "bus",
                "agency_id": "OP550",
                "trips": {
                    "trip_id": ["BT1"],
                    "trip_departure_time": ["03:21:00"],
                    "vehicle_id": ["veh_0"],
                },
                "service_id": "1001",
                "id": "1001_0",
            },
            "1002_0": {
                "departure_offsets": ["00:00:00", "00:02:00"],
                "arrival_offsets": ["00:00:00", "00:02:00"],
                "route_url": float("nan"),
                "route_text_color": "FFFFFF",
                "route_type": 2,
                "route_color": "CE312D",
                "route_short_name": "RTR",
                "checkin_duration": float("nan"),
                "route_long_name": "Rail Test Route",
                "ordered_stops": ["RSN", "RSE"],
                "mode": "rail",
                "agency_id": "OP550",
                "trips": {
                    "trip_id": ["RT1"],
                    "trip_departure_time": ["03:21:00"],
                    "vehicle_id": ["veh_1"],
                },
                "service_id": "1002",
                "id": "1002_0",
            },
        },
        "services": {"1001": {"id": "1001", "name": "BTR"}, "1002": {"id": "1002", "name": "RTR"}},
    }


def test_read_services_from_calendar_correct():
    services = gtfs_reader.read_services_from_calendar(gtfs_test_file, "20190604")
    assert services == ["6630", "6631"]


def test_read_gtfs_to_db_like_tables_correct(
    correct_stop_times_db, correct_stops_db, correct_trips_db, correct_routes_db
):
    stop_times_db, stops_db, trips_db, routes_db = gtfs_reader.read_gtfs_to_db_like_tables(
        gtfs_test_file
    )

    assert_frame_equal(stop_times_db, correct_stop_times_db)
    assert_frame_equal(stops_db, correct_stops_db)
    assert_frame_equal(trips_db, correct_trips_db)
    assert_frame_equal(routes_db, correct_routes_db)


def test_read_gtfs_calendar_with_spaces_fills_in_with_character():
    services = gtfs_reader.read_services_from_calendar(
        pytest.test_data_dir / "gtfs_with_spaces", "20190604"
    )
    assert services == ["663_0", "663_1"]


def test_read_gtfs_with_spaces_fills_in_with_character():
    stop_times_db, stops_db, trips_db, routes_db = gtfs_reader.read_gtfs_to_db_like_tables(
        pytest.test_data_dir / "gtfs_with_spaces"
    )

    assert_frame_equal(
        stop_times_db,
        DataFrame(
            {
                "trip_id": {0: "BT_1", 1: "BT_1", 2: "RT_1", 3: "RT_1"},
                "arrival_time": {0: "03:21:00", 1: "03:23:00", 2: "03:21:00", 3: "03:23:00"},
                "departure_time": {0: "03:21:00", 1: "03:23:00", 2: "03:21:00", 3: "03:23:00"},
                "stop_id": {0: "BS_E", 1: "BS_N", 2: "RS_N", 3: "RS_E"},
                "stop_sequence": {0: 0, 1: 1, 2: 0, 3: 1},
                "stop_headsign": {
                    0: float("nan"),
                    1: float("nan"),
                    2: float("nan"),
                    3: float("nan"),
                },
                "pickup_type": {0: 0, 1: 0, 2: 0, 3: 0},
                "drop_off_type": {0: 1, 1: 0, 2: 0, 3: 1},
                "timepoint": {0: 1, 1: 0, 2: 0, 3: 1},
                "stop_direction_name": {
                    0: float("nan"),
                    1: float("nan"),
                    2: float("nan"),
                    3: float("nan"),
                },
            }
        ),
    )
    assert_frame_equal(
        stops_db,
        DataFrame(
            {
                "stop_id": {0: "BS_E", 1: "BS_N", 2: "RS_E", 3: "RS_N"},
                "stop_code": {0: float("nan"), 1: float("nan"), 2: float("nan"), 3: float("nan")},
                "stop_name": {
                    0: "Bus Stop snap to edge",
                    1: "Bus Stop snap to node",
                    2: "Rail Stop snap to edge",
                    3: "Rail Stop snap to node",
                },
                "stop_lat": {0: 51.5226864, 1: 51.5216199, 2: 51.5192615, 3: 51.5231335},
                "stop_lon": {
                    0: -0.14136210000000002,
                    1: -0.140053,
                    2: -0.1421595,
                    3: -0.14109460000000001,
                },
                "wheelchair_boarding": {
                    0: float("nan"),
                    1: float("nan"),
                    2: float("nan"),
                    3: float("nan"),
                },
                "stop_timezone": {
                    0: float("nan"),
                    1: float("nan"),
                    2: float("nan"),
                    3: float("nan"),
                },
                "location_type": {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0},
                "parent_station": {0: "210G433", 1: "210G432", 2: "210G431", 3: "210G430"},
                "platform_code": {
                    0: float("nan"),
                    1: float("nan"),
                    2: float("nan"),
                    3: float("nan"),
                },
            }
        ),
    )
    assert_frame_equal(
        trips_db,
        DataFrame(
            {
                "route_id": {0: "100_1", 1: "100_2"},
                "service_id": {0: "663_0", 1: "663_1"},
                "trip_id": {0: "BT_1", 1: "RT_1"},
                "trip_headsign": {0: "Bus Test trip", 1: "Rail Test trip"},
                "block_id": {0: float("nan"), 1: float("nan")},
                "wheelchair_accessible": {0: 0, 1: 0},
                "trip_direction_name": {0: float("nan"), 1: float("nan")},
                "exceptional": {0: float("nan"), 1: float("nan")},
            }
        ),
    )
    assert_frame_equal(
        routes_db,
        DataFrame(
            {
                "route_id": {0: "100_1", 1: "100_2"},
                "agency_id": {0: "OP550", 1: "OP550"},
                "route_short_name": {0: "BTR", 1: "RTR"},
                "route_long_name": {0: "Bus Test Route", 1: "Rail Test Route"},
                "route_type": {0: 3, 1: 2},
                "route_url": {0: float("nan"), 1: float("nan")},
                "route_color": {0: "CE312D", 1: "CE312D"},
                "route_text_color": {0: "FFFFFF", 1: "FFFFFF"},
                "checkin_duration": {0: float("nan"), 1: float("nan")},
            }
        ),
    )


def test_get_mode_returns_mode_if_given_int():
    assert gtfs_reader.get_mode(3) == "bus"


def test_get_mode_returns_mode_if_given_str():
    assert gtfs_reader.get_mode("3") == "bus"


def test_get_mode_returns_other_if_doesnt_recognise():
    assert gtfs_reader.get_mode("99999999") == "other"


def test_read_to_schedule_correct(
    assert_semantically_equal,
    correct_schedule_graph_nodes_from_test_gtfs,
    correct_schedule_graph_edges_from_test_gtfs,
    correct_schedule_graph_data_from_test_gtfs,
):
    schedule_graph = gtfs_reader.read_gtfs_to_schedule_graph(gtfs_test_file, "20190604")
    assert_semantically_equal(
        dict(schedule_graph.nodes(data=True)), correct_schedule_graph_nodes_from_test_gtfs
    )
    assert_semantically_equal(
        schedule_graph.edges._adjdict, correct_schedule_graph_edges_from_test_gtfs
    )
    del schedule_graph.graph["change_log"]
    del correct_schedule_graph_data_from_test_gtfs["change_log"]
    assert_semantically_equal(schedule_graph.graph, correct_schedule_graph_data_from_test_gtfs)


def test_zip_read_to_schedule_correct(
    assert_semantically_equal,
    correct_schedule_graph_nodes_from_test_gtfs,
    correct_schedule_graph_edges_from_test_gtfs,
    correct_schedule_graph_data_from_test_gtfs,
):
    schedule_graph = gtfs_reader.read_gtfs_to_schedule_graph(gtfs_test_file, "20190604")
    assert_semantically_equal(
        dict(schedule_graph.nodes(data=True)), correct_schedule_graph_nodes_from_test_gtfs
    )
    assert_semantically_equal(
        schedule_graph.edges._adjdict, correct_schedule_graph_edges_from_test_gtfs
    )
    del schedule_graph.graph["change_log"]
    del correct_schedule_graph_data_from_test_gtfs["change_log"]
    assert_semantically_equal(schedule_graph.graph, correct_schedule_graph_data_from_test_gtfs)


def test_reading_loopy_gtfs_removes_duplicated_stops():
    schedule_graph = gtfs_reader.read_gtfs_to_schedule_graph(
        pytest.test_data_dir / "loopy_gtfs", "20190604"
    )
    assert schedule_graph.graph["routes"]["1001_0"]["ordered_stops"] == ["BSE", "BSN", "BSE", "BSN"]
