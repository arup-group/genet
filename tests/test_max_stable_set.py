import shutil

import genet.utils.spatial as spatial
import networkx as nx
import pyomo.environ as pe
import pytest
from genet import MaxStableSet, Network, Route, Schedule, Service, Stop
from genet.max_stable_set import get_indices_of_chosen_problem_graph_nodes
from pandas import DataFrame


@pytest.fixture()
def network():
    n = Network("epsg:27700")
    n.add_nodes(
        {
            "node_1": {
                "id": "node_1",
                "x": 1,
                "y": 2,
                "lat": 49.766825803756994,
                "lon": -7.557148039524952,
                "s2_id": 5205973754090365183,
            },
            "node_2": {
                "id": "node_2",
                "x": 1,
                "y": 3,
                "lat": 49.766834755586814,
                "lon": -7.557149066139435,
                "s2_id": 5205973754090333257,
            },
            "node_3": {
                "id": "node_3",
                "x": 2,
                "y": 3,
                "lat": 49.766835420540474,
                "lon": -7.557135245523688,
                "s2_id": 5205973754090257181,
            },
            "node_4": {
                "id": "node_4",
                "x": 2,
                "y": 2,
                "lat": 49.766826468710484,
                "lon": -7.557134218911724,
                "s2_id": 5205973754090480551,
            },
            "node_5": {
                "id": "node_5",
                "x": 3,
                "y": 2,
                "lat": 49.76682713366229,
                "lon": -7.557120398297983,
                "s2_id": 5205973754090518939,
            },
            "node_6": {
                "id": "node_6",
                "x": 4,
                "y": 2,
                "lat": 49.76682779861249,
                "lon": -7.557106577683727,
                "s2_id": 5205973754090531959,
            },
            "node_7": {
                "id": "node_7",
                "x": 5,
                "y": 2,
                "lat": 49.76682846356101,
                "lon": -7.557092757068958,
                "s2_id": 5205973754096484927,
            },
            "node_8": {
                "id": "node_8",
                "x": 6,
                "y": 2,
                "lat": 49.766829128507936,
                "lon": -7.55707893645368,
                "s2_id": 5205973754096518199,
            },
            "node_9": {
                "id": "node_9",
                "x": 6,
                "y": 2,
                "lat": 49.766829128507936,
                "lon": -7.55707893645368,
                "s2_id": 5205973754096518199,
            },
        },
        silent=True,
    )
    n.add_links(
        {
            "link_1_2_car": {
                "length": 1,
                "modes": ["car"],
                "freespeed": 1,
                "from": "node_1",
                "to": "node_2",
                "id": "link_1_2_car",
            },
            "link_2_1_car": {
                "length": 1,
                "modes": ["car"],
                "freespeed": 1,
                "from": "node_2",
                "to": "node_1",
                "id": "link_2_1_car",
            },
            "link_1_2_bus": {
                "length": 1,
                "modes": ["bus"],
                "freespeed": 1,
                "from": "node_1",
                "to": "node_2",
                "id": "link_1_2_bus",
            },
            "link_2_1_bus": {
                "length": 1,
                "modes": ["bus"],
                "freespeed": 1,
                "from": "node_2",
                "to": "node_1",
                "id": "link_2_1_bus",
            },
            "link_2_3_car": {
                "length": 1,
                "modes": ["car"],
                "freespeed": 1,
                "from": "node_2",
                "to": "node_3",
                "id": "link_2_3_car",
            },
            "link_3_2_car": {
                "length": 1,
                "modes": ["car"],
                "freespeed": 1,
                "from": "node_3",
                "to": "node_2",
                "id": "link_3_2_car",
            },
            "link_3_4_car": {
                "length": 1,
                "modes": ["car"],
                "freespeed": 1,
                "from": "node_3",
                "to": "node_4",
                "id": "link_3_4_car",
            },
            "link_4_3_car": {
                "length": 1,
                "modes": ["car"],
                "freespeed": 1,
                "from": "node_4",
                "to": "node_3",
                "id": "link_4_3_car",
            },
            "link_1_4_bus": {
                "length": 1,
                "modes": ["bus"],
                "freespeed": 1,
                "from": "node_1",
                "to": "node_4",
                "id": "link_1_4_bus",
            },
            "link_4_1_bus": {
                "length": 1,
                "modes": ["bus"],
                "freespeed": 1,
                "from": "node_4",
                "to": "node_1",
                "id": "link_4_1_bus",
            },
            "link_4_5_car": {
                "length": 1,
                "modes": ["car"],
                "freespeed": 1,
                "from": "node_4",
                "to": "node_5",
                "id": "link_4_5_car",
            },
            "link_5_4_car": {
                "length": 1,
                "modes": ["car"],
                "freespeed": 1,
                "from": "node_5",
                "to": "node_4",
                "id": "link_5_4_car",
            },
            "link_5_6_car": {
                "length": 1,
                "modes": ["car"],
                "freespeed": 1,
                "from": "node_5",
                "to": "node_6",
                "id": "link_5_6_car",
            },
            "link_6_5_car": {
                "length": 1,
                "modes": ["car"],
                "freespeed": 1,
                "from": "node_6",
                "to": "node_5",
                "id": "link_6_5_car",
            },
            "link_6_7_car": {
                "length": 1,
                "modes": ["car"],
                "freespeed": 1,
                "from": "node_6",
                "to": "node_7",
                "id": "link_6_7_car",
            },
            "link_7_6_car": {
                "length": 1,
                "modes": ["car"],
                "freespeed": 1,
                "from": "node_7",
                "to": "node_6",
                "id": "link_7_6_car",
            },
            "link_7_8_car": {
                "length": 1,
                "modes": ["car"],
                "freespeed": 1,
                "from": "node_7",
                "to": "node_8",
                "id": "link_7_8_car",
            },
            "link_8_7_car": {
                "length": 1,
                "modes": ["car"],
                "freespeed": 1,
                "from": "node_8",
                "to": "node_7",
                "id": "link_8_7_car",
            },
            "link_8_9_car": {
                "length": 1,
                "modes": ["car"],
                "freespeed": 1,
                "from": "node_8",
                "to": "node_9",
                "id": "link_8_9_car",
            },
            "link_9_8_car": {
                "length": 1,
                "modes": ["car"],
                "freespeed": 1,
                "from": "node_9",
                "to": "node_8",
                "id": "link_9_8_car",
            },
        },
        silent=True,
    )

    n.schedule = Schedule(
        epsg="epsg:27700",
        services=[
            Service(
                id="bus_service",
                routes=[
                    Route(
                        id="service_1_route_1",
                        route_short_name="",
                        mode="bus",
                        stops=[
                            Stop(epsg="epsg:27700", id="stop_1", x=1, y=2.5),
                            Stop(epsg="epsg:27700", id="stop_2", x=2, y=2.5),
                            Stop(epsg="epsg:27700", id="stop_3", x=5.5, y=2),
                        ],
                        trips={
                            "trip_id": ["trip_1"],
                            "trip_departure_time": ["15:30:00"],
                            "vehicle_id": ["veh_bus_0"],
                        },
                        arrival_offsets=["00:00:00", "00:02:00", "00:05:00"],
                        departure_offsets=["00:00:00", "00:03:00", "00:07:00"],
                    ),
                    Route(
                        id="service_1_route_2",
                        route_short_name="",
                        mode="bus",
                        stops=[
                            Stop(epsg="epsg:27700", id="stop_3", x=5.5, y=2),
                            Stop(epsg="epsg:27700", id="stop_2", x=2, y=2.5),
                            Stop(epsg="epsg:27700", id="stop_1", x=1, y=2.5),
                        ],
                        trips={
                            "trip_id": ["trip_2"],
                            "trip_departure_time": ["16:30:00"],
                            "vehicle_id": ["veh_bus_1"],
                        },
                        arrival_offsets=["00:00:00", "00:02:00", "00:05:00"],
                        departure_offsets=["00:00:00", "00:03:00", "00:07:00"],
                    ),
                ],
            )
        ],
    )
    return n


@pytest.fixture()
def network_spatial_tree(network):
    return spatial.SpatialTree(network)


def test_detects_stops_that_lack_nearest_links(mocker, network, network_spatial_tree):
    closest_links = DataFrame(
        {
            "id": {0: "stop_2", 1: "stop_2", 2: "stop_3", 3: "stop_3"},
            "link_id": {0: "link_4_5_car", 1: "link_5_6_car", 2: "link_7_8_car", 3: "link_8_9_car"},
        }
    ).set_index("id", drop=False)
    closest_links.index.rename(name="index", inplace=True)
    mocker.patch.object(spatial.SpatialTree, "closest_links", return_value=closest_links)

    mss = MaxStableSet(
        pt_graph=network.schedule["bus_service"].graph(),
        network_spatial_tree=network_spatial_tree,
        modes={"car", "bus"},
        step_size=10,
        distance_threshold=10,
    )
    assert not mss.all_stops_have_nearest_links()


def test_stops_missing_nearest_links_identifies_stops_with_missing_closest_links(
    mocker, network, network_spatial_tree
):
    mocker.patch.object(
        spatial.SpatialTree,
        "closest_links",
        return_value=DataFrame(
            {
                "id": {0: "stop_2", 1: "stop_2", 2: "stop_3", 3: "stop_3"},
                "link_id": {
                    0: "link_4_5_car",
                    1: "link_5_6_car",
                    2: "link_7_8_car",
                    3: "link_8_9_car",
                },
            }
        ),
    )
    mss = MaxStableSet(
        pt_graph=network.schedule["bus_service"].graph(),
        network_spatial_tree=network_spatial_tree,
        modes={"car", "bus"},
    )
    assert mss.stops_missing_nearest_links() == {"stop_1"}


def test_build_graph_for_maximum_stable_set_problem_with_non_trivial_closest_link_selection_pool(
    assert_semantically_equal, mocker, network, network_spatial_tree
):
    closest_links = DataFrame(
        {
            "id": {
                0: "stop_2",
                1: "stop_2",
                2: "stop_3",
                3: "stop_3",
                4: "stop_1",
                5: "stop_1",
                6: "stop_1",
            },
            "link_id": {
                0: "link_4_5_car",
                1: "link_5_6_car",
                2: "link_7_8_car",
                3: "link_8_9_car",
                4: "link_1_2_car",
                5: "link_1_2_bus",
                6: "link_2_3_car",
            },
        }
    ).set_index("id", drop=False)
    closest_links.index.rename(name="index", inplace=True)
    mocker.patch.object(spatial.SpatialTree, "closest_links", return_value=closest_links)

    mss = MaxStableSet(
        pt_graph=network.schedule["bus_service"].graph(),
        network_spatial_tree=network_spatial_tree,
        modes={"car", "bus"},
        distance_threshold=10,
        step_size=10,
    )
    assert_semantically_equal(
        dict(mss.problem_graph.nodes()),
        {
            "stop_2.link:link_4_5_car": {
                "id": "stop_2",
                "link_id": "link_4_5_car",
                "catchment": 10,
                "coeff": 0.2777777777777778,
            },
            "stop_2.link:link_5_6_car": {
                "id": "stop_2",
                "link_id": "link_5_6_car",
                "catchment": 10,
                "coeff": 0.2631578947368421,
            },
            "stop_3.link:link_7_8_car": {
                "id": "stop_3",
                "link_id": "link_7_8_car",
                "catchment": 10,
                "coeff": 0.2857142857142857,
            },
            "stop_3.link:link_8_9_car": {
                "id": "stop_3",
                "link_id": "link_8_9_car",
                "catchment": 10,
                "coeff": 0.2222222222222222,
            },
            "stop_1.link:link_1_2_car": {
                "id": "stop_1",
                "link_id": "link_1_2_car",
                "catchment": 10,
                "coeff": 0.2857142857142857,
            },
            "stop_1.link:link_1_2_bus": {
                "id": "stop_1",
                "link_id": "link_1_2_bus",
                "catchment": 10,
                "coeff": 0.2857142857142857,
            },
            "stop_1.link:link_2_3_car": {
                "id": "stop_1",
                "link_id": "link_2_3_car",
                "catchment": 10,
                "coeff": 0.2857142857142857,
            },
        },
    )
    assert_semantically_equal(
        list(mss.problem_graph.edges()),
        [
            ("stop_2.link:link_4_5_car", "stop_2.link:link_5_6_car"),
            ("stop_3.link:link_7_8_car", "stop_3.link:link_8_9_car"),
            ("stop_1.link:link_1_2_car", "stop_1.link:link_1_2_bus"),
            ("stop_1.link:link_1_2_car", "stop_1.link:link_2_3_car"),
            ("stop_1.link:link_1_2_bus", "stop_1.link:link_2_3_car"),
        ],
    )


def test_build_graph_for_maximum_stable_set_problem_with_no_path_between_isolated_node(
    assert_semantically_equal, mocker, network
):
    closest_links = DataFrame(
        {
            "id": {
                0: "stop_2",
                1: "stop_2",
                2: "stop_3",
                3: "stop_3",
                4: "stop_1",
                5: "stop_1",
                6: "stop_1",
            },
            "link_id": {
                0: "link_4_5_car",
                1: "link_5_6_car",
                2: "link_7_8_car",
                3: "link_8_9_car",
                4: "isolated_link",
                5: "link_1_2_bus",
                6: "link_2_3_car",
            },
        }
    ).set_index("id", drop=False)
    closest_links.index.rename(name="index", inplace=True)
    mocker.patch.object(spatial.SpatialTree, "closest_links", return_value=closest_links)

    network.add_nodes(
        {
            "node_iso_1": {
                "id": "node_iso_1",
                "x": 10,
                "y": 20,
                "lat": 49.8,
                "lon": -7.5,
                "s2_id": 5205973754090365183,
            },
            "node_iso_2": {
                "id": "node_iso_2",
                "x": 10,
                "y": 30,
                "lat": 49.9,
                "lon": -7.6,
                "s2_id": 5205973754090333257,
            },
        }
    )
    network.add_link(
        "isolated_link", u="node_iso_1", v="node_iso_2", attribs={"modes": {"car", "bus"}}
    )

    mss = MaxStableSet(
        pt_graph=network.schedule["bus_service"].graph(),
        network_spatial_tree=spatial.SpatialTree(network),
        modes={"car", "bus"},
        distance_threshold=10,
        step_size=10,
    )
    assert_semantically_equal(
        dict(mss.problem_graph.nodes()),
        {
            "stop_2.link:link_4_5_car": {
                "id": "stop_2",
                "link_id": "link_4_5_car",
                "catchment": 10,
                "coeff": 0.26666666666666666,
            },
            "stop_2.link:link_5_6_car": {
                "id": "stop_2",
                "link_id": "link_5_6_car",
                "catchment": 10,
                "coeff": 0.26666666666666666,
            },
            "stop_3.link:link_7_8_car": {
                "id": "stop_3",
                "link_id": "link_7_8_car",
                "catchment": 10,
                "coeff": 0.2857142857142857,
            },
            "stop_3.link:link_8_9_car": {
                "id": "stop_3",
                "link_id": "link_8_9_car",
                "catchment": 10,
                "coeff": 0.2222222222222222,
            },
            "stop_1.link:link_1_2_bus": {
                "id": "stop_1",
                "link_id": "link_1_2_bus",
                "catchment": 10,
                "coeff": 0.2857142857142857,
            },
            "stop_1.link:link_2_3_car": {
                "id": "stop_1",
                "link_id": "link_2_3_car",
                "catchment": 10,
                "coeff": 0.2857142857142857,
            },
        },
    )
    assert_semantically_equal(
        list(mss.problem_graph.edges()),
        [
            ("stop_2.link:link_4_5_car", "stop_2.link:link_5_6_car"),
            ("stop_3.link:link_7_8_car", "stop_3.link:link_8_9_car"),
            ("stop_1.link:link_1_2_bus", "stop_1.link:link_2_3_car"),
        ],
    )


def test_problem_with_distinct_catchments_is_viable(mocker, network, network_spatial_tree):
    closest_links = DataFrame(
        {
            "id": {
                0: "stop_2",
                1: "stop_2",
                2: "stop_3",
                3: "stop_3",
                4: "stop_1",
                5: "stop_1",
                6: "stop_1",
            },
            "link_id": {
                0: "link_4_5_car",
                1: "link_5_6_car",
                2: "link_7_8_car",
                3: "link_8_9_car",
                4: "link_1_2_car",
                5: "link_1_2_bus",
                6: "link_2_3_car",
            },
        }
    ).set_index("id", drop=False)
    closest_links.index.rename(name="index", inplace=True)
    mocker.patch.object(spatial.SpatialTree, "closest_links", return_value=closest_links)

    mss = MaxStableSet(
        pt_graph=network.schedule["bus_service"].graph(),
        network_spatial_tree=network_spatial_tree,
        modes={"car", "bus"},
        distance_threshold=10,
        step_size=10,
    )

    assert mss.is_viable()


def test_problem_with_isolated_catchment_is_not_viable(mocker, network):
    closest_links = DataFrame(
        {
            "id": {0: "stop_2", 1: "stop_2", 2: "stop_3", 3: "stop_3", 4: "stop_1", 5: "stop_1"},
            "link_id": {
                0: "link_4_5_car",
                1: "link_5_6_car",
                2: "link_7_8_car",
                3: "link_8_9_car",
                4: "isolated_link_1",
                5: "isolated_link_2",
            },
        }
    ).set_index("id", drop=False)
    closest_links.index.rename(name="index", inplace=True)
    mocker.patch.object(spatial.SpatialTree, "closest_links", return_value=closest_links)

    network.add_nodes(
        {
            "node_iso_1": {
                "id": "node_iso_1",
                "x": 10,
                "y": 20,
                "lat": 49.8,
                "lon": -7.5,
                "s2_id": 5205973754090365183,
            },
            "node_iso_2": {
                "id": "node_iso_2",
                "x": 10,
                "y": 30,
                "lat": 49.9,
                "lon": -7.6,
                "s2_id": 5205973754090333257,
            },
        }
    )
    network.add_link(
        "isolated_link_1", u="node_iso_1", v="node_iso_2", attribs={"modes": {"car", "bus"}}
    )
    network.add_link(
        "isolated_link_2", u="node_iso_2", v="node_iso_1", attribs={"modes": {"car", "bus"}}
    )

    mss = MaxStableSet(
        pt_graph=network.schedule["bus_service"].graph(),
        network_spatial_tree=spatial.SpatialTree(network),
        modes={"car", "bus"},
        distance_threshold=10,
        step_size=10,
    )

    assert not mss.is_viable()


def test_problem_with_isolated_catchment_is_partially_viable(mocker, network):
    closest_links = DataFrame(
        {
            "id": {0: "stop_2", 1: "stop_2", 2: "stop_3", 3: "stop_3", 4: "stop_1", 5: "stop_1"},
            "link_id": {
                0: "link_4_5_car",
                1: "link_5_6_car",
                2: "link_7_8_car",
                3: "link_8_9_car",
                4: "isolated_link_1",
                5: "isolated_link_2",
            },
        }
    ).set_index("id", drop=False)
    closest_links.index.rename(name="index", inplace=True)
    mocker.patch.object(spatial.SpatialTree, "closest_links", return_value=closest_links)

    network.add_nodes(
        {
            "node_iso_1": {
                "id": "node_iso_1",
                "x": 10,
                "y": 20,
                "lat": 49.8,
                "lon": -7.5,
                "s2_id": 5205973754090365183,
            },
            "node_iso_2": {
                "id": "node_iso_2",
                "x": 10,
                "y": 30,
                "lat": 49.9,
                "lon": -7.6,
                "s2_id": 5205973754090333257,
            },
        }
    )
    network.add_link(
        "isolated_link_1", u="node_iso_1", v="node_iso_2", attribs={"modes": {"car", "bus"}}
    )
    network.add_link(
        "isolated_link_2", u="node_iso_2", v="node_iso_1", attribs={"modes": {"car", "bus"}}
    )

    mss = MaxStableSet(
        pt_graph=network.schedule["bus_service"].graph(),
        network_spatial_tree=spatial.SpatialTree(network),
        modes={"car", "bus"},
        distance_threshold=10,
        step_size=10,
    )

    assert mss.is_partially_viable()


def path_lengths_with_clear_preference(*args, **kwargs):
    path_lengths = {
        # stop_1 candidates, `link_1_2_bus` is preferred
        "link_1_2_car": {"link_4_5_car": 9, "link_5_6_car": 9},
        "link_1_2_bus": {"link_4_5_car": 1, "link_5_6_car": 1},
        "link_2_3_car": {"link_4_5_car": 9, "link_5_6_car": 9},
        # stop_2 candidates, `link_4_5_car` is preferred
        "link_4_5_car": {
            "link_1_2_car": 1,
            "link_1_2_bus": 1,
            "link_2_3_car": 1,
            "link_7_8_car": 1,
            "link_8_9_car": 1,
        },
        "link_5_6_car": {
            "link_1_2_car": 9,
            "link_1_2_bus": 9,
            "link_2_3_car": 9,
            "link_7_8_car": 9,
            "link_8_9_car": 9,
        },
        # stop_3 candidates, `link_7_8_car` is preferred
        "link_7_8_car": {"link_4_5_car": 1, "link_5_6_car": 1},
        "link_8_9_car": {"link_4_5_car": 9, "link_5_6_car": 9},
    }
    return path_lengths[kwargs["source"]][kwargs["target"]]


def test_solving_problem_with_isolated_catchments(
    mocker, assert_semantically_equal, network, network_spatial_tree
):
    if not shutil.which("cbc"):
        pytest.skip("CBC solver not installed")

    closest_links = DataFrame(
        {
            "id": {
                0: "stop_2",
                1: "stop_2",
                2: "stop_3",
                3: "stop_3",
                4: "stop_1",
                5: "stop_1",
                6: "stop_1",
            },
            "link_id": {
                0: "link_4_5_car",
                1: "link_5_6_car",
                2: "link_7_8_car",
                3: "link_8_9_car",
                4: "link_1_2_car",
                5: "link_1_2_bus",
                6: "link_2_3_car",
            },
        }
    ).set_index("id", drop=False)
    closest_links.index.rename(name="index", inplace=True)
    mocker.patch.object(spatial.SpatialTree, "closest_links", return_value=closest_links)
    mocker.patch.object(nx, "dijkstra_path_length", side_effect=path_lengths_with_clear_preference)

    mss = MaxStableSet(
        pt_graph=network.schedule["bus_service"].graph(),
        network_spatial_tree=network_spatial_tree,
        modes={"car", "bus"},
    )
    mss.solve()

    assert mss.solution == {
        "stop_1": "link_1_2_bus",
        "stop_2": "link_4_5_car",
        "stop_3": "link_7_8_car",
    }
    assert_semantically_equal(
        mss.artificial_stops,
        {
            "stop_1.link:link_1_2_bus": {
                "services": {"bus_service"},
                "routes": {"service_1_route_2", "service_1_route_1"},
                "id": "stop_1.link:link_1_2_bus",
                "x": 1.0,
                "y": 2.5,
                "epsg": "epsg:27700",
                "name": "",
                "lon": -7.557148552832129,
                "lat": 49.76683027967191,
                "s2_id": 5205973754090340691,
                "linkRefId": "link_1_2_bus",
                "stop_id": "stop_1",
            },
            "stop_2.link:link_4_5_car": {
                "services": {"bus_service"},
                "routes": {"service_1_route_2", "service_1_route_1"},
                "id": "stop_2.link:link_4_5_car",
                "x": 2.0,
                "y": 2.5,
                "epsg": "epsg:27700",
                "name": "",
                "lon": -7.557134732217642,
                "lat": 49.76683094462549,
                "s2_id": 5205973754090230267,
                "linkRefId": "link_4_5_car",
                "stop_id": "stop_2",
            },
            "stop_3.link:link_7_8_car": {
                "services": {"bus_service"},
                "routes": {"service_1_route_2", "service_1_route_1"},
                "id": "stop_3.link:link_7_8_car",
                "x": 5.5,
                "y": 2.0,
                "epsg": "epsg:27700",
                "name": "",
                "lon": -7.55708584676138,
                "lat": 49.76682879603468,
                "s2_id": 5205973754096513977,
                "linkRefId": "link_7_8_car",
                "stop_id": "stop_3",
            },
        },
    )


def test_problem_with_isolated_catchment_finds_solution_for_viable_stops(
    assert_semantically_equal, mocker, network
):
    if not shutil.which("cbc"):
        pytest.skip("CBC solver not installed")
    closest_links = DataFrame(
        {
            "id": {0: "stop_2", 1: "stop_2", 2: "stop_3", 3: "stop_3", 4: "stop_1", 5: "stop_1"},
            "link_id": {
                0: "link_4_5_car",
                1: "link_5_6_car",
                2: "link_7_8_car",
                3: "link_8_9_car",
                4: "isolated_link_1",
                5: "isolated_link_2",
            },
        }
    ).set_index("id", drop=False)
    closest_links.index.rename(name="index", inplace=True)
    mocker.patch.object(spatial.SpatialTree, "closest_links", return_value=closest_links)

    network.add_nodes(
        {
            "node_iso_1": {
                "id": "node_iso_1",
                "x": 10,
                "y": 20,
                "lat": 49.8,
                "lon": -7.5,
                "s2_id": 5205973754090365183,
            },
            "node_iso_2": {
                "id": "node_iso_2",
                "x": 10,
                "y": 30,
                "lat": 49.9,
                "lon": -7.6,
                "s2_id": 5205973754090333257,
            },
        }
    )
    network.add_link(
        "isolated_link_1", u="node_iso_1", v="node_iso_2", attribs={"modes": {"car", "bus"}}
    )
    network.add_link(
        "isolated_link_2", u="node_iso_2", v="node_iso_1", attribs={"modes": {"car", "bus"}}
    )

    mss = MaxStableSet(
        pt_graph=network.schedule["bus_service"].graph(),
        network_spatial_tree=spatial.SpatialTree(network),
        modes={"car", "bus"},
        distance_threshold=10,
        step_size=10,
    )
    mss.solve()
    assert mss.solution == {"stop_2": "link_5_6_car", "stop_3": "link_7_8_car"}
    assert_semantically_equal(
        mss.artificial_stops,
        {
            "stop_2.link:link_5_6_car": {
                "services": {"bus_service"},
                "routes": {"service_1_route_2", "service_1_route_1"},
                "id": "stop_2.link:link_5_6_car",
                "x": 2.0,
                "y": 2.5,
                "epsg": "epsg:27700",
                "name": "",
                "lon": -7.557134732217642,
                "lat": 49.76683094462549,
                "s2_id": 5205973754090230267,
                "linkRefId": "link_5_6_car",
                "stop_id": "stop_2",
            },
            "stop_3.link:link_7_8_car": {
                "services": {"bus_service"},
                "routes": {"service_1_route_2", "service_1_route_1"},
                "id": "stop_3.link:link_7_8_car",
                "x": 5.5,
                "y": 2.0,
                "epsg": "epsg:27700",
                "name": "",
                "lon": -7.55708584676138,
                "lat": 49.76682879603468,
                "s2_id": 5205973754096513977,
                "linkRefId": "link_7_8_car",
                "stop_id": "stop_3",
            },
        },
    )


@pytest.fixture()
def partial_mss(network):
    mss = MaxStableSet(
        pt_graph=network.schedule["bus_service"].graph(),
        network_spatial_tree=spatial.SpatialTree(network),
        modes={"car", "bus"},
        distance_threshold=10,
        step_size=10,
    )
    mss.solution = {
        "stop_2": "link_5_6_car",
        "stop_3": "link_7_8_car",
        "stop_1": "artificial_link===from:stop_1===to:stop_1",
    }
    mss.artificial_stops = {
        "stop_2.link:link_5_6_car": {
            "services": {"bus_service"},
            "routes": {"service_1_route_1", "service_1_route_2"},
            "id": "stop_2.link:link_5_6_car",
            "x": 2.0,
            "y": 2.5,
            "epsg": "epsg:27700",
            "name": "",
            "lon": -7.557134732217642,
            "lat": 49.76683094462549,
            "s2_id": 5205973754090230267,
            "additional_attributes": set(),
            "linkRefId": "link_5_6_car",
            "stop_id": "stop_2",
        },
        "stop_3.link:link_7_8_car": {
            "services": {"bus_service"},
            "routes": {"service_1_route_1", "service_1_route_2"},
            "id": "stop_3.link:link_7_8_car",
            "x": 5.5,
            "y": 2.0,
            "epsg": "epsg:27700",
            "name": "",
            "lon": -7.55708584676138,
            "lat": 49.76682879603468,
            "s2_id": 5205973754096513977,
            "additional_attributes": set(),
            "linkRefId": "link_7_8_car",
            "stop_id": "stop_3",
        },
        "stop_1.link:artificial_link===from:stop_1===to:stop_1": {
            "services": {"bus_service"},
            "routes": {"service_1_route_1", "service_1_route_2"},
            "id": "stop_1.link:artificial_link===from:stop_1===to:stop_1",
            "x": 1.0,
            "y": 2.5,
            "epsg": "epsg:27700",
            "name": "",
            "lon": -7.557148552832129,
            "lat": 49.76683027967191,
            "s2_id": 5205973754090340691,
            "additional_attributes": set(),
            "linkRefId": "artificial_link===from:stop_1===to:stop_1",
            "stop_id": "stop_1",
        },
    }
    mss.artificial_links = {
        "artificial_link===from:stop_1===to:stop_1": {
            "from": "stop_1",
            "to": "stop_1",
            "modes": {"bus"},
        },
        "artificial_link===from:node_6===to:stop_1": {
            "from": "node_6",
            "to": "stop_1",
            "modes": {"bus"},
        },
        "artificial_link===from:stop_1===to:node_5": {
            "from": "stop_1",
            "to": "node_5",
            "modes": {"bus"},
        },
    }
    mss.pt_edges = DataFrame(
        {
            "services": {
                0: {"bus_service"},
                1: {"bus_service"},
                2: {"bus_service"},
                3: {"bus_service"},
            },
            "routes": {
                0: {"service_1_route_2"},
                1: {"service_1_route_2"},
                2: {"service_1_route_1"},
                3: {"service_1_route_1"},
            },
            "u": {0: "stop_3", 1: "stop_2", 2: "stop_2", 3: "stop_1"},
            "v": {0: "stop_2", 1: "stop_1", 2: "stop_3", 3: "stop_2"},
            "key": {0: 0, 1: 0, 2: 0, 3: 0},
            "linkRefId_u": {
                0: "link_7_8_car",
                1: "link_5_6_car",
                2: "link_5_6_car",
                3: "artificial_link===from:stop_1===to:stop_1",
            },
            "linkRefId_v": {
                0: "link_5_6_car",
                1: "artificial_link===from:stop_1===to:stop_1",
                2: "link_7_8_car",
                3: "link_5_6_car",
            },
            "shortest_path": {
                0: ["link_7_8_car", "link_8_7_car", "link_7_6_car", "link_6_5_car", "link_5_6_car"],
                1: [
                    "link_5_6_car",
                    "artificial_link===from:node_6===to:stop_1",
                    "artificial_link===from:stop_1===to:stop_1",
                ],
                2: ["link_5_6_car", "link_6_7_car", "link_7_8_car"],
                3: [
                    "artificial_link===from:stop_1===to:stop_1",
                    "artificial_link===from:stop_1===to:node_5",
                    "link_5_6_car",
                ],
            },
        }
    )
    mss.unsolved_stops = {"stop_1"}
    return mss


def test_partial_mss_problem_generates_correct_network_routes(
    assert_semantically_equal, partial_mss
):
    changeset = partial_mss.to_changeset(
        DataFrame(
            {
                "ordered_stops": {
                    "service_1_route_2": ["stop_3", "stop_2", "stop_1"],
                    "service_1_route_1": ["stop_1", "stop_2", "stop_3"],
                }
            }
        )
    )
    assert_semantically_equal(
        changeset.df_route_data.to_dict(),
        {
            "ordered_stops": {
                "service_1_route_1": [
                    "stop_1.link:artificial_link===from:stop_1===to:stop_1",
                    "stop_2.link:link_5_6_car",
                    "stop_3.link:link_7_8_car",
                ],
                "service_1_route_2": [
                    "stop_3.link:link_7_8_car",
                    "stop_2.link:link_5_6_car",
                    "stop_1.link:artificial_link===from:stop_1===to:stop_1",
                ],
            },
            "network_links": {
                "service_1_route_1": [
                    "artificial_link===from:stop_1===to:stop_1",
                    "artificial_link===from:stop_1===to:node_5",
                    "link_5_6_car",
                    "link_6_7_car",
                    "link_7_8_car",
                ],
                "service_1_route_2": [
                    "link_7_8_car",
                    "link_8_7_car",
                    "link_7_6_car",
                    "link_6_5_car",
                    "link_5_6_car",
                    "artificial_link===from:node_6===to:stop_1",
                    "artificial_link===from:stop_1===to:stop_1",
                ],
            },
        },
    )


def test_partial_mss_problem_generates_updated_modes_for_links(
    assert_semantically_equal, partial_mss
):
    changeset = partial_mss.to_changeset(
        DataFrame(
            {
                "ordered_stops": {
                    "service_1_route_2": ["stop_3", "stop_2", "stop_1"],
                    "service_1_route_1": ["stop_1", "stop_2", "stop_3"],
                }
            }
        )
    )
    assert_semantically_equal(
        changeset.additional_links_modes,
        {
            "link_5_6_car": {"modes": {"bus", "car"}},
            "link_6_5_car": {"modes": {"bus", "car"}},
            "link_6_7_car": {"modes": {"bus", "car"}},
            "link_7_6_car": {"modes": {"bus", "car"}},
            "link_7_8_car": {"modes": {"bus", "car"}},
            "link_8_7_car": {"modes": {"bus", "car"}},
        },
    )


def test_partial_mss_problem_generates_new_artificial_links(assert_semantically_equal, partial_mss):
    changeset = partial_mss.to_changeset(
        DataFrame(
            {
                "ordered_stops": {
                    "service_1_route_2": ["stop_3", "stop_2", "stop_1"],
                    "service_1_route_1": ["stop_1", "stop_2", "stop_3"],
                }
            }
        )
    )
    assert_semantically_equal(
        changeset.new_links,
        {
            "artificial_link===from:stop_1===to:stop_1": {
                "from": "stop_1",
                "to": "stop_1",
                "modes": {"bus"},
            },
            "artificial_link===from:node_6===to:stop_1": {
                "from": "node_6",
                "to": "stop_1",
                "modes": {"bus"},
            },
            "artificial_link===from:stop_1===to:node_5": {
                "from": "stop_1",
                "to": "node_5",
                "modes": {"bus"},
            },
        },
    )


def test_partial_mss_problem_generates_new_network_nodes_from_unsnapped_stops(
    assert_semantically_equal, partial_mss
):
    changeset = partial_mss.to_changeset(
        DataFrame(
            {
                "ordered_stops": {
                    "service_1_route_2": ["stop_3", "stop_2", "stop_1"],
                    "service_1_route_1": ["stop_1", "stop_2", "stop_3"],
                }
            }
        )
    )
    assert_semantically_equal(
        changeset.new_nodes,
        {
            "stop_1": {
                "id": "stop_1",
                "x": 1.0,
                "y": 2.5,
                "name": "",
                "lon": -7.557148552832129,
                "lat": 49.76683027967191,
                "s2_id": 5205973754090340691,
            }
        },
    )


def test_partial_mss_problem_genrates_new_stops_with_linkrefids(
    assert_semantically_equal, partial_mss
):
    changeset = partial_mss.to_changeset(
        DataFrame(
            {
                "ordered_stops": {
                    "service_1_route_2": ["stop_3", "stop_2", "stop_1"],
                    "service_1_route_1": ["stop_1", "stop_2", "stop_3"],
                }
            }
        )
    )
    assert_semantically_equal(
        changeset.new_stops,
        {
            "stop_2.link:link_5_6_car": {
                "services": {"bus_service"},
                "routes": {"service_1_route_1", "service_1_route_2"},
                "id": "stop_2.link:link_5_6_car",
                "x": 2.0,
                "y": 2.5,
                "epsg": "epsg:27700",
                "name": "",
                "lon": -7.557134732217642,
                "lat": 49.76683094462549,
                "s2_id": 5205973754090230267,
                "additional_attributes": set(),
                "linkRefId": "link_5_6_car",
                "stop_id": "stop_2",
            },
            "stop_3.link:link_7_8_car": {
                "services": {"bus_service"},
                "routes": {"service_1_route_1", "service_1_route_2"},
                "id": "stop_3.link:link_7_8_car",
                "x": 5.5,
                "y": 2.0,
                "epsg": "epsg:27700",
                "name": "",
                "lon": -7.55708584676138,
                "lat": 49.76682879603468,
                "s2_id": 5205973754096513977,
                "additional_attributes": set(),
                "linkRefId": "link_7_8_car",
                "stop_id": "stop_3",
            },
            "stop_1.link:artificial_link===from:stop_1===to:stop_1": {
                "services": {"bus_service"},
                "routes": {"service_1_route_1", "service_1_route_2"},
                "id": "stop_1.link:artificial_link===from:stop_1===to:stop_1",
                "x": 1.0,
                "y": 2.5,
                "epsg": "epsg:27700",
                "name": "",
                "lon": -7.557148552832129,
                "lat": 49.76683027967191,
                "s2_id": 5205973754090340691,
                "additional_attributes": set(),
                "linkRefId": "artificial_link===from:stop_1===to:stop_1",
                "stop_id": "stop_1",
            },
        },
    )


def test_partial_mss_problem_generates_edge_update_for_schedule(partial_mss):
    changeset = partial_mss.to_changeset(
        DataFrame(
            {
                "ordered_stops": {
                    "service_1_route_2": ["stop_3", "stop_2", "stop_1"],
                    "service_1_route_1": ["stop_1", "stop_2", "stop_3"],
                }
            }
        )
    )
    changeset.new_pt_edges.sort()
    assert changeset.new_pt_edges == [
        (
            "stop_1.link:artificial_link===from:stop_1===to:stop_1",
            "stop_2.link:link_5_6_car",
            {"services": {"bus_service"}, "routes": {"service_1_route_1"}},
        ),
        (
            "stop_2.link:link_5_6_car",
            "stop_1.link:artificial_link===from:stop_1===to:stop_1",
            {"services": {"bus_service"}, "routes": {"service_1_route_2"}},
        ),
        (
            "stop_2.link:link_5_6_car",
            "stop_3.link:link_7_8_car",
            {"services": {"bus_service"}, "routes": {"service_1_route_1"}},
        ),
        (
            "stop_3.link:link_7_8_car",
            "stop_2.link:link_5_6_car",
            {"services": {"bus_service"}, "routes": {"service_1_route_2"}},
        ),
    ]


def test_combining_two_changesets_with_overlap(assert_semantically_equal, partial_mss):
    service_1_route_1_pt_edges = partial_mss.pt_edges[
        partial_mss.pt_edges["routes"].apply(lambda x: "service_1_route_1" in x)
    ]
    service_1_route_2_pt_edges = partial_mss.pt_edges[
        partial_mss.pt_edges["routes"].apply(lambda x: "service_1_route_2" in x)
    ]

    partial_mss.pt_edges = service_1_route_2_pt_edges
    partial_mss.pt_graph.remove_edges_from([("stop_1", "stop_2"), ("stop_2", "stop_3")])
    changeset = partial_mss.to_changeset(
        DataFrame({"ordered_stops": {"service_1_route_2": ["stop_3", "stop_2", "stop_1"]}})
    )

    partial_mss.solution["stop_2"] = "link_6_5_car"
    del partial_mss.artificial_stops["stop_2.link:link_5_6_car"]
    partial_mss.artificial_stops["stop_2.link:link_6_5_car"] = {
        "services": {"bus_service"},
        "routes": {"service_1_route_1"},
        "id": "stop_2.link:link_6_5_car",
        "x": 2.0,
        "y": 2.5,
        "epsg": "epsg:27700",
        "name": "",
        "lon": -7.557134732217642,
        "lat": 49.76683094462549,
        "s2_id": 5205973754090230267,
        "additional_attributes": set(),
        "linkRefId": "link_6_5_car",
        "stop_id": "stop_2",
    }
    partial_mss.artificial_links = {
        "artificial_link===from:stop_1===to:stop_1": {
            "from": "stop_1",
            "to": "stop_1",
            "modes": {"bus"},
        },
        "artificial_link===from:node_5===to:stop_1": {
            "from": "node_5",
            "to": "stop_1",
            "modes": {"bus"},
        },
        "artificial_link===from:stop_1===to:node_6": {
            "from": "stop_1",
            "to": "node_6",
            "modes": {"bus"},
        },
    }
    partial_mss.pt_edges = service_1_route_1_pt_edges
    partial_mss.pt_graph.remove_edges_from([("stop_3", "stop_2"), ("stop_2", "stop_1")])
    partial_mss.pt_graph.add_edges_from(
        [
            ("stop_1", "stop_2", {"services": {"bus_service"}, "routes": {"service_1_route_1"}}),
            ("stop_2", "stop_3", {"services": {"bus_service"}, "routes": {"service_1_route_1"}}),
        ]
    )

    changeset += partial_mss.to_changeset(
        DataFrame({"ordered_stops": {"service_1_route_1": ["stop_1", "stop_2", "stop_3"]}})
    )

    assert_semantically_equal(
        changeset.df_route_data.to_dict(),
        {
            "ordered_stops": {
                "service_1_route_2": [
                    "stop_3.link:link_7_8_car",
                    "stop_2.link:link_5_6_car",
                    "stop_1.link:artificial_link===from:stop_1===to:stop_1",
                ],
                "service_1_route_1": [
                    "stop_1.link:artificial_link===from:stop_1===to:stop_1",
                    "stop_2.link:link_6_5_car",
                    "stop_3.link:link_7_8_car",
                ],
            },
            "network_links": {
                "service_1_route_2": [
                    "link_7_8_car",
                    "link_8_7_car",
                    "link_7_6_car",
                    "link_6_5_car",
                    "link_5_6_car",
                    "artificial_link===from:node_6===to:stop_1",
                    "artificial_link===from:stop_1===to:stop_1",
                ],
                "service_1_route_1": [
                    "artificial_link===from:stop_1===to:stop_1",
                    "artificial_link===from:stop_1===to:node_5",
                    "link_5_6_car",
                    "link_6_7_car",
                    "link_7_8_car",
                ],
            },
        },
    )
    assert_semantically_equal(
        changeset.additional_links_modes,
        {
            "link_5_6_car": {"modes": {"bus", "car"}},
            "link_6_5_car": {"modes": {"bus", "car"}},
            "link_6_7_car": {"modes": {"bus", "car"}},
            "link_7_6_car": {"modes": {"bus", "car"}},
            "link_7_8_car": {"modes": {"bus", "car"}},
            "link_8_7_car": {"modes": {"bus", "car"}},
        },
    )
    assert_semantically_equal(
        changeset.new_links,
        {
            "artificial_link===from:stop_1===to:stop_1": {
                "from": "stop_1",
                "to": "stop_1",
                "modes": {"bus"},
            },
            "artificial_link===from:node_6===to:stop_1": {
                "from": "node_6",
                "to": "stop_1",
                "modes": {"bus"},
            },
            "artificial_link===from:stop_1===to:node_5": {
                "from": "stop_1",
                "to": "node_5",
                "modes": {"bus"},
            },
            "artificial_link===from:node_5===to:stop_1": {
                "from": "node_5",
                "to": "stop_1",
                "modes": {"bus"},
            },
            "artificial_link===from:stop_1===to:node_6": {
                "from": "stop_1",
                "to": "node_6",
                "modes": {"bus"},
            },
        },
    )
    assert_semantically_equal(
        changeset.new_nodes,
        {
            "stop_1": {
                "id": "stop_1",
                "x": 1.0,
                "y": 2.5,
                "name": "",
                "lon": -7.557148552832129,
                "lat": 49.76683027967191,
                "s2_id": 5205973754090340691,
            }
        },
    )
    assert_semantically_equal(
        changeset.new_stops,
        {
            "stop_2.link:link_5_6_car": {
                "services": {"bus_service"},
                "routes": {"service_1_route_2"},
                "id": "stop_2.link:link_5_6_car",
                "x": 2.0,
                "y": 2.5,
                "epsg": "epsg:27700",
                "name": "",
                "lon": -7.557134732217642,
                "lat": 49.76683094462549,
                "s2_id": 5205973754090230267,
                "additional_attributes": set(),
                "linkRefId": "link_5_6_car",
                "stop_id": "stop_2",
            },
            "stop_3.link:link_7_8_car": {
                "services": {"bus_service"},
                "routes": {"service_1_route_2", "service_1_route_1"},
                "id": "stop_3.link:link_7_8_car",
                "x": 5.5,
                "y": 2.0,
                "epsg": "epsg:27700",
                "name": "",
                "lon": -7.55708584676138,
                "lat": 49.76682879603468,
                "s2_id": 5205973754096513977,
                "additional_attributes": set(),
                "linkRefId": "link_7_8_car",
                "stop_id": "stop_3",
            },
            "stop_1.link:artificial_link===from:stop_1===to:stop_1": {
                "services": {"bus_service"},
                "routes": {"service_1_route_2", "service_1_route_1"},
                "id": "stop_1.link:artificial_link===from:stop_1===to:stop_1",
                "x": 1.0,
                "y": 2.5,
                "epsg": "epsg:27700",
                "name": "",
                "lon": -7.557148552832129,
                "lat": 49.76683027967191,
                "s2_id": 5205973754090340691,
                "additional_attributes": set(),
                "linkRefId": "artificial_link===from:stop_1===to:stop_1",
                "stop_id": "stop_1",
            },
            "stop_2.link:link_6_5_car": {
                "services": {"bus_service"},
                "routes": {"service_1_route_1"},
                "id": "stop_2.link:link_6_5_car",
                "x": 2.0,
                "y": 2.5,
                "epsg": "epsg:27700",
                "name": "",
                "lon": -7.557134732217642,
                "lat": 49.76683094462549,
                "s2_id": 5205973754090230267,
                "additional_attributes": set(),
                "linkRefId": "link_6_5_car",
                "stop_id": "stop_2",
            },
        },
    )

    changeset.new_pt_edges.sort()
    assert changeset.new_pt_edges == [
        (
            "stop_1.link:artificial_link===from:stop_1===to:stop_1",
            "stop_2.link:link_6_5_car",
            {"routes": {"service_1_route_1"}, "services": {"bus_service"}},
        ),
        (
            "stop_2.link:link_5_6_car",
            "stop_1.link:artificial_link===from:stop_1===to:stop_1",
            {"routes": {"service_1_route_2"}, "services": {"bus_service"}},
        ),
        (
            "stop_2.link:link_6_5_car",
            "stop_3.link:link_7_8_car",
            {"routes": {"service_1_route_1"}, "services": {"bus_service"}},
        ),
        (
            "stop_3.link:link_7_8_car",
            "stop_2.link:link_5_6_car",
            {"routes": {"service_1_route_2"}, "services": {"bus_service"}},
        ),
    ]


@pytest.mark.parametrize(
    "case_name,stop_ids",
    [
        ("simple stops", ["stop_3.link:link_7_8_car", "stop_1.link:link_4_5_car"]),
        (
            "stops with x in name",
            ["x_stop.link:1234", "stopx.link:1234", "stxop.link:1234", "stop.link:1234x"],
        ),
    ],
)
def test_indices_of_chosen_variables_remain_unchanged_during_solution_extraction(
    case_name, stop_ids
):
    model = pe.ConcreteModel()
    model.x = pe.Var(stop_ids, within=pe.Binary)
    # set all variables as chosen, we only care about their indices being correct
    for v in model.component_data_objects(pe.Var):
        v.value = 1.0

    assert get_indices_of_chosen_problem_graph_nodes(model) == stop_ids


def test_indices_of_expected_solution_nodes_are_extracted_from_the_model():
    solution_nodes = ["stop_3.link:link_7_8_car", "bababooey"]
    zero_value_nodes = ["some_zero_node"]
    none_value_nodes = ["some_none_node"]

    model = pe.ConcreteModel()
    model.x = pe.Var(solution_nodes + zero_value_nodes + none_value_nodes, within=pe.Binary)
    # set expected variable values (fake a solution)
    for v in model.component_data_objects(pe.Var):
        if v.index() in solution_nodes:
            v.value = 1.0
        elif v.index() in zero_value_nodes:
            v.value = 0.0
        elif v.index() in none_value_nodes:
            v.value = None
        else:
            raise RuntimeError(f"Unrecognised variable: {v.index()}")

    assert get_indices_of_chosen_problem_graph_nodes(model) == solution_nodes
