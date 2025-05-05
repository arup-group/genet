import os
from pathlib import Path

import pytest

from genet import Network, Route, Schedule, Service, Stop
from genet.output import spatial as spatial_output


@pytest.fixture()
def network(correct_schedule):
    n = Network("epsg:27700")
    n.add_node("0", attribs={"x": 528704.1425925883, "y": 182068.78193707118})
    n.add_node("1", attribs={"x": 528804.1425925883, "y": 182168.78193707118})
    n.add_link(
        "link_0",
        "0",
        "1",
        attribs={"length": 123, "modes": ["car", "walk"], "freespeed": 10, "capacity": 5},
    )
    n.add_link(
        "link_1",
        "0",
        "1",
        attribs={
            "length": 123,
            "modes": ["bike"],
            "attributes": {"osm:way:highway": "unclassified"},
        },
    )
    n.add_link("link_2", "1", "0", attribs={"length": 123, "modes": ["rail"]})

    n.schedule = correct_schedule
    return n


def test_saving_values_which_result_in_overflow(tmpdir):
    n = Network("epsg:27700")
    n.add_node(
        "0", attribs={"x": 528704.1425925883, "y": 182068.78193707118, "s2_id": 7860190995130875979}
    )
    n.add_node(
        "1",
        attribs={"x": 528804.1425925883, "y": 182168.78193707118, "s2_id": 12118290696817869383},
    )
    n.add_link(
        "link_0", "0", "1", attribs={"length": 123, "modes": ["car", "walk"], "ids": ["1", "2"]}
    )
    n.write_spatial(tmpdir, filetype="geojson")


def test_generating_network_graph_geodataframe(assert_semantically_equal, network):
    gdfs = spatial_output.generate_geodataframes(network.graph)
    nodes, links = gdfs["nodes"], gdfs["links"]
    correct_nodes = {
        "id": {"0": "0", "1": "1"},
        "x": {"0": 528704.1425925883, "1": 528804.1425925883},
        "y": {"0": 182068.78193707118, "1": 182168.78193707118},
        "s2_id": {"0": 5221390329378179879, "1": 5221390328997426875},
        "lat": {"0": 51.52287873323954, "1": 51.523754629002234},
        "lon": {"0": -0.14625948709424305, "1": -0.14478238148334213},
    }
    correct_links = {
        "u": {"link_0": "0", "link_1": "0", "link_2": "1"},
        "v": {"link_0": "1", "link_1": "1", "link_2": "0"},
        "length": {"link_0": 123, "link_1": 123, "link_2": 123},
        "attributes": {
            "link_0": float("nan"),
            "link_1": {"osm:way:highway": "unclassified"},
            "link_2": float("nan"),
        },
        "to": {"link_0": "1", "link_1": "1", "link_2": "0"},
        "from": {"link_0": "0", "link_1": "0", "link_2": "1"},
        "freespeed": {"link_0": 10.0, "link_1": float("nan"), "link_2": float("nan")},
        "id": {"link_0": "link_0", "link_1": "link_1", "link_2": "link_2"},
        "capacity": {"link_0": 5.0, "link_1": float("nan"), "link_2": float("nan")},
        "modes": {"link_0": ["car", "walk"], "link_1": ["bike"], "link_2": ["rail"]},
    }

    assert_semantically_equal(
        nodes.drop("geometry", axis=1, errors="ignore").to_dict(), correct_nodes
    )
    assert_semantically_equal(
        links.drop("geometry", axis=1, errors="ignore").to_dict(), correct_links
    )

    assert round(nodes.loc["0", "geometry"].coords[:][0][0], 7) == round(528704.1425925883, 7)
    assert round(nodes.loc["0", "geometry"].coords[:][0][1], 7) == round(182068.78193707118, 7)
    assert round(nodes.loc["1", "geometry"].coords[:][0][0], 7) == round(528804.1425925883, 7)
    assert round(nodes.loc["1", "geometry"].coords[:][0][1], 7) == round(182168.78193707118, 7)

    points = links.loc["link_0", "geometry"].coords[:]
    assert round(points[0][0], 7) == round(528704.1425925883, 7)
    assert round(points[0][1], 7) == round(182068.78193707118, 7)
    assert round(points[1][0], 7) == round(528804.1425925883, 7)
    assert round(points[1][1], 7) == round(182168.78193707118, 7)

    assert nodes.crs == "EPSG:27700"
    assert links.crs == "EPSG:27700"


def test_generating_schedule_graph_geodataframe(assert_semantically_equal, network):
    gdfs = spatial_output.generate_geodataframes(network.schedule.graph())
    nodes, links = gdfs["nodes"], gdfs["links"]
    correct_nodes = {
        "services": {"0": {"service"}, "1": {"service"}},
        "routes": {"0": {"1", "2"}, "1": {"1", "2"}},
        "id": {"0": "0", "1": "1"},
        "x": {"0": 529455.7452394223, "1": 529350.7866124967},
        "y": {"0": 182401.37630677427, "1": 182388.0201078112},
        "epsg": {"0": "epsg:27700", "1": "epsg:27700"},
        "lat": {"0": 51.525696033239186, "1": 51.52560003323918},
        "lon": {"0": -0.13530998708775874, "1": -0.13682698708848137},
        "s2_id": {"0": 5221390668020036699, "1": 5221390668558830581},
        "linkRefId": {"0": "1", "1": "2"},
        "name": {"0": "", "1": ""},
    }
    correct_links = {
        "services": {0: {"service"}},
        "routes": {0: {"1", "2"}},
        "u": {0: "0"},
        "v": {0: "1"},
    }

    assert_semantically_equal(nodes.drop("geometry", axis=1).to_dict(), correct_nodes)
    assert_semantically_equal(links.drop("geometry", axis=1).to_dict(), correct_links)

    assert round(nodes.loc["0", "geometry"].coords[:][0][0], 7) == round(529455.7452394223, 7)
    assert round(nodes.loc["0", "geometry"].coords[:][0][1], 7) == round(182401.37630677427, 7)
    assert round(nodes.loc["1", "geometry"].coords[:][0][0], 7) == round(529350.7866124967, 7)
    assert round(nodes.loc["1", "geometry"].coords[:][0][1], 7) == round(182388.0201078112, 7)

    points = links.loc[0, "geometry"].coords[:]
    assert round(points[0][0], 7) == round(529455.7452394223, 7)
    assert round(points[0][1], 7) == round(182401.37630677427, 7)
    assert round(points[1][0], 7) == round(529350.7866124967, 7)
    assert round(points[1][1], 7) == round(182388.0201078112, 7)

    assert nodes.crs == "EPSG:27700"
    assert links.crs == "EPSG:27700"


def test_modal_subset(network):
    gdfs = spatial_output.generate_geodataframes(network.graph)
    links = gdfs["links"]
    car = links[links.apply(lambda x: spatial_output.modal_subset(x, {"car"}), axis=1)]

    assert len(car) == 1
    assert car.loc["link_0", "modes"] == ["car", "walk"]


def test_generating_standard_outputs_after_modifying_modes_in_schedule(network, tmpdir):
    network.schedule.apply_attributes_to_routes(
        {"1": {"mode": "different_bus"}, "2": {"mode": "other_bus"}}
    )
    spatial_output.generate_standard_outputs_for_schedule(network.schedule, tmpdir)


def test_save_to_geojson_generates_files(network, tmpdir):
    assert os.listdir(tmpdir) == []
    network.write_spatial(tmpdir, filetype="geojson")
    assert set(os.listdir(tmpdir)) == {
        "network_nodes.geojson",
        "network_nodes_geometry_only.geojson",
        "network_links.geojson",
        "network_links_geometry_only.geojson",
        "schedule_nodes.geojson",
        "schedule_nodes_geometry_only.geojson",
        "schedule_links.geojson",
        "schedule_links_geometry_only.geojson",
        "network_change_log.csv",
        "schedule_change_log.csv",
    }


def test_save_to_parquet_generates_files(network, tmpdir):
    assert os.listdir(tmpdir) == []
    network.write_spatial(tmpdir, filetype="parquet")
    assert set(os.listdir(tmpdir)) == {
        "network_nodes.parquet",
        "network_nodes_geometry_only.parquet",
        "network_links.parquet",
        "network_links_geometry_only.parquet",
        "schedule_nodes.parquet",
        "schedule_nodes_geometry_only.parquet",
        "schedule_links.parquet",
        "schedule_links_geometry_only.parquet",
        "network_change_log.csv",
        "schedule_change_log.csv",
    }


def test_save_to_shp_generates_files(network, tmpdir):
    assert os.listdir(tmpdir) == []

    network.write_spatial(tmpdir, filetype="shp")

    assert set(os.listdir(tmpdir)) == {
        f"{file}.{ext}"
        for file in {
            "network_nodes",
            "network_nodes_geometry_only",
            "network_links",
            "network_links_geometry_only",
            "schedule_nodes",
            "schedule_nodes_geometry_only",
            "schedule_links",
            "schedule_links_geometry_only",
        }
        for ext in {"cpg", "shx", "shp", "prj", "dbf"}
    } | {"schedule_change_log.csv", "network_change_log.csv"}


@pytest.mark.parametrize(
    ["requested_file_type", "expected_file_extensions"],
    [
        ("parquet", ["parquet"]),
        ("geoparquet", ["parquet"]),
        ("geojson", ["geojson"]),
        ("shp", ["shp", "shx", "prj", "dbf", "cpg"]),
        ("shapefile", ["shp", "shx", "prj", "dbf", "cpg"]),
    ],
)
def test_generating_standard_outputs_produces_expected_files(
    network, tmpdir, requested_file_type, expected_file_extensions
):
    network.schedule = Schedule(
        epsg="epsg:27700",
        services=[
            Service(
                id="bus_service",
                routes=[
                    Route(
                        id="1",
                        route_short_name="",
                        mode="bus",
                        stops=[
                            Stop(
                                id="0",
                                x=529455.7452394223,
                                y=182401.37630677427,
                                epsg="epsg:27700",
                                linkRefId="link_1",
                            ),
                            Stop(
                                id="1",
                                x=529350.7866124967,
                                y=182388.0201078112,
                                epsg="epsg:27700",
                                linkRefId="link_2",
                            ),
                        ],
                        trips={
                            "trip_id": ["VJ00938baa194cee94700312812d208fe79f3297ee_04:40:00"],
                            "trip_departure_time": ["04:40:00"],
                            "vehicle_id": ["veh_1_bus"],
                        },
                        arrival_offsets=["00:00:00", "00:02:00"],
                        departure_offsets=["00:00:00", "00:02:00"],
                        network_links=["link_1", "link_2"],
                    ),
                    Route(
                        id="2",
                        route_short_name="route2",
                        mode="bus",
                        stops=[
                            Stop(
                                id="0",
                                x=529455.7452394223,
                                y=182401.37630677427,
                                epsg="epsg:27700",
                                linkRefId="link_1",
                            ),
                            Stop(
                                id="1",
                                x=529350.7866124967,
                                y=182388.0201078112,
                                epsg="epsg:27700",
                                linkRefId="link_2",
                            ),
                        ],
                        trips={
                            "trip_id": [
                                "1_05:40:00",
                                "2_05:45:00",
                                "3_05:50:00",
                                "4_06:40:00",
                                "5_06:46:00",
                            ],
                            "trip_departure_time": [
                                "05:40:00",
                                "05:45:00",
                                "05:50:00",
                                "06:40:00",
                                "06:46:00",
                            ],
                            "vehicle_id": [
                                "veh_2_bus",
                                "veh_3_bus",
                                "veh_4_bus",
                                "veh_5_bus",
                                "veh_6_bus",
                            ],
                        },
                        arrival_offsets=["00:00:00", "00:03:00"],
                        departure_offsets=["00:00:00", "00:05:00"],
                        network_links=["link_1", "link_2"],
                    ),
                ],
            ),
            Service(
                id="rail_service",
                routes=[
                    Route(
                        route_short_name=r"RTR_I/love\_being//difficult",
                        mode="rail",
                        stops=[
                            Stop(
                                id="RSN",
                                x=-0.1410946,
                                y=51.5231335,
                                epsg="epsg:4326",
                                linkRefId="link_0",
                                name=r"I/love\_being//difficult",
                            ),
                            Stop(
                                id="RSE",
                                x=-0.1421595,
                                y=51.5192615,
                                epsg="epsg:4326",
                                linkRefId="link_2",
                            ),
                        ],
                        trips={
                            "trip_id": ["RT1", "RT2", "RT3", "RT4"],
                            "trip_departure_time": ["03:21:00", "03:31:00", "03:41:00", "03:51:00"],
                            "vehicle_id": ["veh_7_rail", "veh_8_rail", "veh_9_rail", "veh_10_rail"],
                        },
                        arrival_offsets=["0:00:00", "0:02:00"],
                        departure_offsets=["0:00:00", "0:02:00"],
                        network_links=["link_0", "link_1", "link_2"],
                    )
                ],
            ),
        ],
    )
    assert os.listdir(tmpdir) == []

    network.generate_standard_outputs(tmpdir, filetype=requested_file_type)

    expected_files = set()
    for extension in expected_file_extensions:
        expected_files |= {
            Path(tmpdir) / f"schedule_links_geometry_only.{extension}",
            Path(tmpdir) / f"network_nodes_geometry_only.{extension}",
            Path(tmpdir) / f"network_links.{extension}",
            Path(tmpdir) / f"network_links_geometry_only.{extension}",
            Path(tmpdir) / f"schedule_nodes.{extension}",
            Path(tmpdir) / f"schedule_nodes_geometry_only.{extension}",
            Path(tmpdir) / f"network_nodes.{extension}",
            Path(tmpdir) / f"schedule_links.{extension}",
            Path(tmpdir) / "network_change_log.csv",
            Path(tmpdir) / "schedule_change_log.csv",
            Path(tmpdir) / "summary_report.json",
            Path(tmpdir) / "graph" / f"car_capacity_subgraph.{extension}",
            Path(tmpdir) / "graph" / f"car_freespeed_subgraph.{extension}",
            Path(tmpdir) / "graph" / f"car_osm_highway_unclassified.{extension}",
            Path(tmpdir)
            / "graph"
            / "geometry_only_subgraphs"
            / f"subgraph_geometry_walk.{extension}",
            Path(tmpdir)
            / "graph"
            / "geometry_only_subgraphs"
            / f"subgraph_geometry_rail.{extension}",
            Path(tmpdir)
            / "graph"
            / "geometry_only_subgraphs"
            / f"subgraph_geometry_car.{extension}",
            Path(tmpdir)
            / "graph"
            / "geometry_only_subgraphs"
            / f"subgraph_geometry_bike.{extension}",
            Path(tmpdir)
            / "graph"
            / "geometry_only_subgraphs"
            / f"subgraph_geometry_bike.{extension}",
            Path(tmpdir)
            / "graph"
            / "geometry_only_subgraphs"
            / f"subgraph_geometry_bike.{extension}",
            Path(tmpdir) / "schedule" / "trips_per_day_per_service.csv",
            Path(tmpdir) / "schedule" / "trips_per_day_per_route.csv",
            Path(tmpdir) / "schedule" / "trips_per_day_per_route_aggregated_per_stop_id_pair.csv",
            Path(tmpdir) / "schedule" / "trips_per_day_per_route_aggregated_per_stop_name_pair.csv",
            Path(tmpdir) / "schedule" / "speed" / f"pt_speeds.{extension}",
            Path(tmpdir) / "schedule" / "speed" / f"pt_network_speeds.{extension}",
            Path(tmpdir) / "schedule" / "vehicles_per_hour" / "vph_per_service.csv",
            Path(tmpdir)
            / "schedule"
            / "vehicles_per_hour"
            / f"vehicles_per_hour_all_modes.{extension}",
            Path(tmpdir) / "schedule" / "vehicles_per_hour" / "vph_per_stop_departing_from.csv",
            Path(tmpdir) / "schedule" / "vehicles_per_hour" / "vph_per_stop_arriving_at.csv",
            Path(tmpdir)
            / "schedule"
            / "vehicles_per_hour"
            / f"vph_all_modes_within_6_30-7_30.{extension}",
            Path(tmpdir) / "schedule" / "vehicles_per_hour" / f"vehicles_per_hour_bus.{extension}",
            Path(tmpdir) / "schedule" / "vehicles_per_hour" / f"vehicles_per_hour_rail.{extension}",
            Path(tmpdir) / "schedule" / "subgraphs" / f"schedule_subgraph_links_bus.{extension}",
            Path(tmpdir) / "schedule" / "subgraphs" / f"schedule_subgraph_links_rail.{extension}",
            Path(tmpdir) / "schedule" / "subgraphs" / f"schedule_subgraph_nodes_bus.{extension}",
            Path(tmpdir) / "schedule" / "subgraphs" / f"schedule_subgraph_nodes_rail.{extension}",
            Path(tmpdir) / "routing" / f"schedule_network_routes_geodataframe.{extension}",
        }

    assert {path for path in Path(tmpdir).glob("**/*") if path.is_file()} == expected_files
    assert os.path.exists(tmpdir + ".zip")
