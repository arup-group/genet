import pytest

from genet import Route, Schedule, Service, Stop
from genet.validate import schedule as schedule_validation
from tests.fixtures import assert_semantically_equal, test_schedule  # noqa: F401


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


def test_generate_validation_report_for_correct_schedule(correct_schedule):
    correct_report = {
        "schedule_level": {
            "is_valid_schedule": True,
            "invalid_stages": [],
            "has_valid_services": True,
            "invalid_services": [],
            "headways": {"has_zero_min_headways": False},
            "speeds": {},
        },
        "service_level": {
            "service": {
                "is_valid_service": True,
                "invalid_stages": [],
                "has_valid_routes": True,
                "invalid_routes": [],
            }
        },
        "route_level": {
            "service": {
                "1": {
                    "is_valid_route": True,
                    "invalid_stages": [],
                    "headway_stats": {
                        "mean_headway_mins": float("nan"),
                        "std_headway_mins": float("nan"),
                        "max_headway_mins": float("nan"),
                        "min_headway_mins": float("nan"),
                    },
                },
                "2": {
                    "is_valid_route": True,
                    "invalid_stages": [],
                    "headway_stats": {
                        "mean_headway_mins": float("nan"),
                        "std_headway_mins": float("nan"),
                        "max_headway_mins": float("nan"),
                        "min_headway_mins": float("nan"),
                    },
                },
            }
        },
        "vehicle_level": {
            "vehicle_definitions_valid": True,
            "vehicle_definitions_validity_components": {
                "missing_vehicles": {"missing_vehicles_types": set(), "vehicles_affected": {}},
                "multiple_use_vehicles": {},
                "unused_vehicles": set(),
            },
        },
    }

    report = schedule_validation.generate_validation_report(correct_schedule)
    assert_semantically_equal(report, correct_report)


def test_generate_validation_report_for_incorrect_schedule(test_schedule):
    correct_report = {
        "schedule_level": {
            "is_valid_schedule": False,
            "invalid_stages": ["not_has_valid_services"],
            "has_valid_services": False,
            "invalid_services": ["service"],
            "headways": {"has_zero_min_headways": False},
            "speeds": {"0_m/s": {"routes": ["service_0", "service_1"]}},
        },
        "service_level": {
            "service": {
                "is_valid_service": False,
                "invalid_stages": ["not_has_valid_routes"],
                "has_valid_routes": False,
                "invalid_routes": ["service_0", "service_1"],
            }
        },
        "route_level": {
            "service": {
                "service_0": {
                    "is_valid_route": False,
                    "invalid_stages": ["not_has_correctly_ordered_route", "has_self_loops"],
                    "headway_stats": {
                        "mean_headway_mins": float("nan"),
                        "std_headway_mins": float("nan"),
                        "max_headway_mins": float("nan"),
                        "min_headway_mins": float("nan"),
                    },
                },
                "service_1": {
                    "is_valid_route": False,
                    "invalid_stages": ["not_has_correctly_ordered_route", "has_self_loops"],
                    "headway_stats": {
                        "mean_headway_mins": float("nan"),
                        "std_headway_mins": float("nan"),
                        "max_headway_mins": float("nan"),
                        "min_headway_mins": float("nan"),
                    },
                },
            }
        },
        "vehicle_level": {
            "vehicle_definitions_valid": True,
            "vehicle_definitions_validity_components": {
                "missing_vehicles": {"missing_vehicles_types": set(), "vehicles_affected": {}},
                "multiple_use_vehicles": {},
                "unused_vehicles": set(),
            },
        },
    }
    report = schedule_validation.generate_validation_report(test_schedule)
    assert_semantically_equal(report, correct_report)


@pytest.fixture()
def schedule_with_incomplete_vehicle_definition():
    s = Schedule(
        epsg="epsg:27700",
        services=[
            Service(
                id="service",
                routes=[
                    Route(
                        route_short_name="route",
                        mode="bus",
                        stops=[
                            Stop(
                                id="0", x=528504.1342843144, y=182155.7435136598, epsg="epsg:27700"
                            ),
                            Stop(
                                id="0", x=528504.1342843144, y=182155.7435136598, epsg="epsg:27700"
                            ),
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
                            Stop(
                                id="0", x=528504.1342843144, y=182155.7435136598, epsg="epsg:27700"
                            ),
                            Stop(
                                id="0", x=528504.1342843144, y=182155.7435136598, epsg="epsg:27700"
                            ),
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
        ],
    )
    s.vehicle_types = {}
    return s


def test_generate_validation_report_with_schedule_incomplete_vehicle_definitions(
    schedule_with_incomplete_vehicle_definition,
):
    correct_vehicle_report = {
        "vehicle_definitions_valid": False,
        "vehicle_definitions_validity_components": {
            "missing_vehicles": {
                "missing_vehicles_types": {"bus"},
                "vehicles_affected": {"veh_1_bus": {"type": "bus"}, "veh_2_bus": {"type": "bus"}},
            },
            "multiple_use_vehicles": {},
            "unused_vehicles": set(),
        },
    }

    report = schedule_validation.generate_validation_report(
        schedule_with_incomplete_vehicle_definition
    )
    assert_semantically_equal(report["vehicle_level"], correct_vehicle_report)


def test_schedule_with_no_unused_vehicles(correct_schedule):
    correct_output = set()
    actual_output = correct_schedule.unused_vehicles()

    assert_semantically_equal(correct_output, actual_output)


@pytest.fixture()
def schedule_with_unused_vehicles():
    s = Schedule(
        epsg="epsg:27700",
        services=[
            Service(
                id="service",
                routes=[
                    Route(
                        id="r1",
                        route_short_name="route",
                        mode="bus",
                        stops=[
                            Stop(
                                id="0", x=528504.1342843144, y=182155.7435136598, epsg="epsg:27700"
                            ),
                            Stop(
                                id="0", x=528504.1342843144, y=182155.7435136598, epsg="epsg:27700"
                            ),
                        ],
                        trips={
                            "trip_id": ["VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00"],
                            "trip_departure_time": ["04:40:00"],
                            "vehicle_id": ["veh_1_bus"],
                        },
                        arrival_offsets=["00:00:00", "00:02:00"],
                        departure_offsets=["00:00:00", "00:02:00"],
                    )
                ],
            )
        ],
    )

    s.vehicles = {"veh_2_bus": {"type": "bus"}, "veh_1_bus": {"type": "bus"}}

    return s


def test_schedule_with_unused_vehicles(schedule_with_unused_vehicles):
    unused_correct = set({"veh_2_bus"})
    unused_actual = schedule_with_unused_vehicles.unused_vehicles()

    assert_semantically_equal(unused_correct, unused_actual)


def test_schedule_with_no_multiple_use_vehicles(correct_schedule):
    correct_output = {}
    actual_output = correct_schedule.check_vehicle_uniqueness()

    assert_semantically_equal(correct_output, actual_output)


@pytest.fixture()
def schedule_with_multiple_use_vehicles():
    s = Schedule(
        epsg="epsg:27700",
        services=[
            Service(
                id="service",
                routes=[
                    Route(
                        route_short_name="route",
                        mode="bus",
                        stops=[
                            Stop(
                                id="0", x=528504.1342843144, y=182155.7435136598, epsg="epsg:27700"
                            ),
                            Stop(
                                id="0", x=528504.1342843144, y=182155.7435136598, epsg="epsg:27700"
                            ),
                        ],
                        trips={
                            "trip_id": ["VJ00938baa194cee94700312812d208fe79f3297ee_044000"],
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
                            Stop(
                                id="0", x=528504.1342843144, y=182155.7435136598, epsg="epsg:27700"
                            ),
                            Stop(
                                id="0", x=528504.1342843144, y=182155.7435136598, epsg="epsg:27700"
                            ),
                        ],
                        trips={
                            "trip_id": ["Blep_044000"],
                            "trip_departure_time": ["05:40:00"],
                            "vehicle_id": ["veh_1_bus"],
                        },
                        arrival_offsets=["00:00:00", "00:03:00"],
                        departure_offsets=["00:00:00", "00:05:00"],
                    ),
                ],
            )
        ],
    )
    return s


def test_schedule_with_multiple_use_vehicles(schedule_with_multiple_use_vehicles):
    correct_output = {}
    correct_output["veh_1_bus"] = []
    correct_output["veh_1_bus"].append("VJ00938baa194cee94700312812d208fe79f3297ee_044000")
    correct_output["veh_1_bus"].append("Blep_044000")
    actual_output = schedule_with_multiple_use_vehicles.check_vehicle_uniqueness()

    assert_semantically_equal(correct_output, actual_output)


@pytest.fixture()
def nice_schedule_for_testing_headway_reporting():
    headway_mins = 10
    return {
        "schedule": Schedule(
            epsg="epsg:27700",
            services=[
                Service(
                    id="service",
                    routes=[
                        Route(
                            route_short_name="route",
                            mode="bus",
                            stops=[
                                Stop(
                                    id="0",
                                    x=528504.1342843144,
                                    y=182155.7435136598,
                                    epsg="epsg:27700",
                                ),
                                Stop(
                                    id="1",
                                    x=528504.1342843144,
                                    y=182155.7435136598,
                                    epsg="epsg:27700",
                                ),
                            ],
                            headway_spec={("07:00:00", "08:00:00"): headway_mins},
                            arrival_offsets=["00:00:00", "00:02:00"],
                            departure_offsets=["00:00:00", "00:02:00"],
                        )
                    ],
                )
            ],
        ),
        "headways": {"has_zero_min_headways": False},
        "headway_stats": {
            "mean_headway_mins": headway_mins,
            "std_headway_mins": 0.0,
            "max_headway_mins": headway_mins,
            "min_headway_mins": headway_mins,
        },
    }


def test_nice_schedules_global_headway_evaluation_in_validation_report(
    nice_schedule_for_testing_headway_reporting,
):
    rep = nice_schedule_for_testing_headway_reporting["schedule"].generate_validation_report()
    rep["schedule_level"]["headway_stats"] = nice_schedule_for_testing_headway_reporting[
        "headway_stats"
    ]


def test_nice_schedules_headway_stats_in_validation_report(
    nice_schedule_for_testing_headway_reporting,
):
    rep = nice_schedule_for_testing_headway_reporting["schedule"].generate_validation_report()
    rep["route_level"]["service"]["service_0"] = nice_schedule_for_testing_headway_reporting[
        "headway_stats"
    ]


@pytest.fixture()
def bad_schedule_for_testing_headway_reporting():
    headway_mins = 0.0
    return {
        "schedule": Schedule(
            epsg="epsg:27700",
            services=[
                Service(
                    id="service",
                    routes=[
                        Route(
                            route_short_name="route",
                            mode="bus",
                            stops=[
                                Stop(
                                    id="0",
                                    x=528504.1342843144,
                                    y=182155.7435136598,
                                    epsg="epsg:27700",
                                ),
                                Stop(
                                    id="1",
                                    x=528504.1342843144,
                                    y=182155.7435136598,
                                    epsg="epsg:27700",
                                ),
                            ],
                            trips={
                                "trip_id": ["t1", "t2", "t3"],
                                "trip_departure_time": ["05:40:00", "05:40:00", "05:40:00"],
                                "vehicle_id": ["veh_1_bus", "veh_2_bus", "veh_3_bus"],
                            },
                            arrival_offsets=["00:00:00", "00:02:00"],
                            departure_offsets=["00:00:00", "00:02:00"],
                        )
                    ],
                )
            ],
        ),
        "headways": {
            "has_zero_min_headways": True,
            "routes": {"number_of_affected": 1, "ids": ["service_0"]},
            "services": {"number_of_affected": 1, "ids": ["service"]},
        },
        "headway_stats": {
            "mean_headway_mins": headway_mins,
            "std_headway_mins": 0.0,
            "max_headway_mins": headway_mins,
            "min_headway_mins": headway_mins,
        },
    }


def test_bad_schedules_global_headway_evaluation_in_validation_report(
    bad_schedule_for_testing_headway_reporting,
):
    rep = bad_schedule_for_testing_headway_reporting["schedule"].generate_validation_report()
    rep["schedule_level"]["headway_stats"] = bad_schedule_for_testing_headway_reporting[
        "headway_stats"
    ]


def test_bad_schedules_headway_stats_in_validation_report(
    bad_schedule_for_testing_headway_reporting,
):
    rep = bad_schedule_for_testing_headway_reporting["schedule"].generate_validation_report()
    rep["route_level"]["service"]["service_0"] = bad_schedule_for_testing_headway_reporting[
        "headway_stats"
    ]
