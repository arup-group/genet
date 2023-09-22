import os
import sys

import pytest
from pyproj import Proj, Transformer
from shapely.geometry import LineString

from genet.input import matsim_reader, read
from genet.utils import java_dtypes

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
pt2matsim_network_test_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "network.xml")
)
pt2matsim_network_multiple_edges_test_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "network_multiple_edges.xml")
)
pt2matsim_network_clashing_link_ids_test_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "network_clashing_link_ids.xml")
)
pt2matsim_network_clashing_node_ids_test_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "network_clashing_node_ids.xml")
)
matsim_output_network_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "matsim_output_network.xml")
)
pt2matsim_network_with_geometry_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "network_with_geometry.xml")
)
pt2matsim_network_with_singular_geometry_file = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "test_data", "matsim", "network_with_singular_geometry.xml"
    )
)
pt2matsim_NZ_network = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "NZ_network.xml")
)
pt2matsim_schedule_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "schedule.xml")
)
pt2matsim_vehicles_file = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "test_data", "matsim", "vehicles.xml")
)


def test_read_network_builds_graph_with_correct_data_on_nodes_and_edges(assert_semantically_equal):
    correct_nodes = {
        "21667818": {
            "id": "21667818",
            "s2_id": 5221390302696205321,
            "x": 528504.1342843144,
            "y": 182155.7435136598,
            "lon": -0.14910908709500162,
            "lat": 51.52370573323939,
        },
        "25508485": {
            "id": "25508485",
            "s2_id": 5221390301001263407,
            "x": 528489.467895946,
            "y": 182206.20303669578,
            "lon": -0.14930198709481451,
            "lat": 51.524162533239284,
        },
    }

    correct_edges = {
        "25508485_21667818": {
            "id": "1",
            "from": "25508485",
            "to": "21667818",
            "length": 52.765151087870265,
            "s2_from": 5221390301001263407,
            "s2_to": 5221390302696205321,
            "freespeed": 4.166666666666667,
            "capacity": 600.0,
            "permlanes": 1.0,
            "oneway": "1",
            "modes": {"subway", "metro", "walk", "car"},
            "attributes": {
                "osm:way:access": "permissive",
                "osm:way:highway": "unclassified",
                "osm:way:id": 26997928.0,
                "osm:way:name": "Brunswick Place",
            },
        }
    }

    transformer = Transformer.from_proj(Proj("epsg:27700"), Proj("epsg:4326"), always_xy=True)

    (
        g,
        link_id_mapping,
        duplicated_nodes,
        duplicated_link_ids,
        attributes,
    ) = matsim_reader.read_network(pt2matsim_network_test_file, transformer)

    for u, data in g.nodes(data=True):
        assert str(u) in correct_nodes
        assert_semantically_equal(data, correct_nodes[str(u)])

    assert_semantically_equal(duplicated_nodes, {})

    for u, v, data in g.edges(data=True):
        edge = "{}_{}".format(u, v)
        assert edge in correct_edges
        assert_semantically_equal(data, correct_edges[edge])

    assert_semantically_equal(duplicated_link_ids, {})


def test_reading_NZ_network(assert_semantically_equal):
    n = read.read_matsim(path_to_network=pt2matsim_NZ_network, epsg="epsg:2193")
    assert_semantically_equal(
        dict(n.nodes()),
        {
            "7872447671905026061": {
                "id": "7872447671905026061",
                "x": 1789300.631705982,
                "y": 5494320.626099871,
                "lon": 175.23998223484716,
                "lat": -40.68028521526985,
                "s2_id": 7872447671905026061,
            },
            "7858001326813216825": {
                "id": "7858001326813216825",
                "x": 1756643.5667029365,
                "y": 5937269.480530882,
                "lon": 174.75350860744126,
                "lat": -36.697337065329855,
                "s2_id": 7858001326813216825,
            },
        },
    )
    assert_semantically_equal(
        dict(n.links()),
        {
            "1": {
                "id": "1",
                "from": "7858001326813216825",
                "to": "7872447671905026061",
                "freespeed": 4.166666666666667,
                "capacity": 600.0,
                "permlanes": 1.0,
                "oneway": "1",
                "modes": {"car", "walk"},
                "s2_from": 7858001326813216825,
                "s2_to": 7872447671905026061,
                "attributes": {"osm:way:access": "permissive"},
                "length": 52.765151087870265,
            }
        },
    )


def test_read_network_builds_graph_with_multiple_edges_with_correct_data_on_nodes_and_edges(
    assert_semantically_equal,
):
    correct_nodes = {
        "21667818": {
            "id": "21667818",
            "s2_id": 5221390302696205321,
            "x": 528504.1342843144,
            "y": 182155.7435136598,
            "lon": -0.14910908709500162,
            "lat": 51.52370573323939,
        },
        "25508485": {
            "id": "25508485",
            "s2_id": 5221390301001263407,
            "x": 528489.467895946,
            "y": 182206.20303669578,
            "lon": -0.14930198709481451,
            "lat": 51.524162533239284,
        },
    }

    correct_edges = {
        "25508485_21667818": {
            0: {
                "id": "1",
                "from": "25508485",
                "to": "21667818",
                "length": 52.765151087870265,
                "s2_from": 5221390301001263407,
                "s2_to": 5221390302696205321,
                "freespeed": 4.166666666666667,
                "capacity": 600.0,
                "permlanes": 1.0,
                "oneway": "1",
                "modes": {"walk", "car"},
                "attributes": {
                    "osm:way:access": "permissive",
                    "osm:way:highway": "unclassified",
                    "osm:way:id": 26997928.0,
                    "osm:way:name": "Brunswick Place",
                },
            },
            1: {
                "id": "2",
                "from": "25508485",
                "to": "21667818",
                "length": 52.765151087870265,
                "s2_from": 5221390301001263407,
                "s2_to": 5221390302696205321,
                "freespeed": 4.166666666666667,
                "capacity": 600.0,
                "permlanes": 1.0,
                "oneway": "1",
                "modes": {"bus"},
                "attributes": {
                    "osm:way:lanes": "1",
                    "osm:way:highway": "unclassified",
                    "osm:way:id": 26997928.0,
                    "osm:way:name": "Brunswick Place",
                    "osm:way:oneway": "yes",
                    "osm:relation:route": {"bus", "bicycle"},
                },
            },
        }
    }

    correct_link_id_map = {
        "1": {"from": "25508485", "to": "21667818", "multi_edge_idx": 0},
        "2": {"from": "25508485", "to": "21667818", "multi_edge_idx": 1},
    }

    transformer = Transformer.from_proj(Proj("epsg:27700"), Proj("epsg:4326"), always_xy=True)

    (
        g,
        link_id_mapping,
        duplicated_nodes,
        duplicated_link_ids,
        attributes,
    ) = matsim_reader.read_network(pt2matsim_network_multiple_edges_test_file, transformer)

    for u, data in g.nodes(data=True):
        assert str(u) in correct_nodes
        assert_semantically_equal(data, correct_nodes[str(u)])

    assert_semantically_equal(duplicated_nodes, {})

    for edge in g.edges:
        e = "{}_{}".format(edge[0], edge[1])
        assert e in correct_edges
        assert edge[2] in correct_edges[e]
        assert_semantically_equal(g[edge[0]][edge[1]][edge[2]], correct_edges[e][edge[2]])

    assert correct_link_id_map == link_id_mapping
    assert_semantically_equal(duplicated_link_ids, {})


def test_read_network_builds_graph_with_unique_links_given_matsim_network_with_clashing_link_ids(
    assert_semantically_equal,
):
    correct_nodes = {
        "21667818": {
            "id": "21667818",
            "s2_id": 5221390302696205321,
            "x": 528504.1342843144,
            "y": 182155.7435136598,
            "lon": -0.14910908709500162,
            "lat": 51.52370573323939,
        },
        "25508485": {
            "id": "25508485",
            "s2_id": 5221390301001263407,
            "x": 528489.467895946,
            "y": 182206.20303669578,
            "lon": -0.14930198709481451,
            "lat": 51.524162533239284,
        },
    }

    correct_edges = {
        "25508485_21667818": {
            0: {
                "id": "1",
                "from": "25508485",
                "to": "21667818",
                "length": 52.765151087870265,
                "s2_from": 5221390301001263407,
                "s2_to": 5221390302696205321,
                "freespeed": 4.166666666666667,
                "capacity": 600.0,
                "permlanes": 1.0,
                "oneway": "1",
                "modes": {"walk", "car"},
                "attributes": {
                    "osm:way:access": "permissive",
                    "osm:way:highway": "unclassified",
                    "osm:way:id": 26997928.0,
                    "osm:way:name": "Brunswick Place",
                },
            },
            1: {
                "id": "1_1",
                "from": "25508485",
                "to": "21667818",
                "length": 52.765151087870265,
                "s2_from": 5221390301001263407,
                "s2_to": 5221390302696205321,
                "freespeed": 4.166666666666667,
                "capacity": 600.0,
                "permlanes": 1.0,
                "oneway": "1",
                "modes": {"bus"},
                "attributes": {
                    "osm:way:lanes": "1",
                    "osm:way:highway": "unclassified",
                    "osm:way:id": 26997928.0,
                    "osm:way:name": "Brunswick Place",
                    "osm:way:oneway": "yes",
                    "osm:relation:route": {"bus", "bicycle"},
                },
            },
        }
    }

    correct_link_id_map = {
        "1": {"from": "25508485", "to": "21667818", "multi_edge_idx": 0},
        "1_1": {"from": "25508485", "to": "21667818", "multi_edge_idx": 1},
    }

    transformer = Transformer.from_proj(Proj("epsg:27700"), Proj("epsg:4326"), always_xy=True)

    (
        g,
        link_id_mapping,
        duplicated_nodes,
        duplicated_link_ids,
        attributes,
    ) = matsim_reader.read_network(pt2matsim_network_clashing_link_ids_test_file, transformer)

    assert len(g.nodes) == len(correct_nodes)
    for u, data in g.nodes(data=True):
        assert str(u) in correct_nodes
        assert_semantically_equal(data, correct_nodes[str(u)])

    assert_semantically_equal(duplicated_nodes, {})

    for edge in g.edges:
        e = "{}_{}".format(edge[0], edge[1])
        assert e in correct_edges
        assert edge[2] in correct_edges[e]
        assert_semantically_equal(g[edge[0]][edge[1]][edge[2]], correct_edges[e][edge[2]])

    assert_semantically_equal(correct_link_id_map, link_id_mapping)
    assert_semantically_equal(duplicated_link_ids, {"1": ["1_1"]})


def test_read_network_rejects_non_unique_nodes(assert_semantically_equal):
    correct_nodes = {
        "21667818": {
            "id": "21667818",
            "s2_id": 5221390302696205321,
            "x": 528504.1342843144,
            "y": 182155.7435136598,
            "lon": -0.14910908709500162,
            "lat": 51.52370573323939,
        },
        "25508485": {
            "id": "25508485",
            "s2_id": 5221390301001263407,
            "x": 528489.467895946,
            "y": 182206.20303669578,
            "lon": -0.14930198709481451,
            "lat": 51.524162533239284,
        },
    }

    correct_edges = {
        "25508485_21667818": {
            0: {
                "id": "1",
                "from": "25508485",
                "to": "21667818",
                "length": 52.765151087870265,
                "s2_from": 5221390301001263407,
                "s2_to": 5221390302696205321,
                "freespeed": 4.166666666666667,
                "capacity": 600.0,
                "permlanes": 1.0,
                "oneway": "1",
                "modes": {"walk", "car"},
                "attributes": {
                    "osm:way:access": "permissive",
                    "osm:way:highway": "unclassified",
                    "osm:way:id": 26997928.0,
                    "osm:way:name": "Brunswick Place",
                },
            }
        }
    }

    correct_link_id_map = {"1": {"from": "25508485", "to": "21667818", "multi_edge_idx": 0}}

    transformer = Transformer.from_proj(Proj("epsg:27700"), Proj("epsg:4326"), always_xy=True)

    (
        g,
        link_id_mapping,
        duplicated_nodes,
        duplicated_link_ids,
        attributes,
    ) = matsim_reader.read_network(pt2matsim_network_clashing_node_ids_test_file, transformer)

    assert len(g.nodes) == len(correct_nodes)
    for u, data in g.nodes(data=True):
        assert str(u) in correct_nodes
        assert_semantically_equal(data, correct_nodes[str(u)])

    assert_semantically_equal(
        duplicated_nodes,
        {
            "21667818": [
                {
                    "id": "21667818",
                    "x": 528504.1342843144,
                    "y": 182155.7435136598,
                    "lon": -0.14910908709500162,
                    "lat": 51.52370573323939,
                    "s2_id": 5221390302696205321,
                }
            ]
        },
    )

    assert len(g.edges) == len(correct_edges)
    for edge in g.edges:
        e = "{}_{}".format(edge[0], edge[1])
        assert e in correct_edges
        assert edge[2] in correct_edges[e]
        assert_semantically_equal(g[edge[0]][edge[1]][edge[2]], correct_edges[e][edge[2]])

    assert_semantically_equal(correct_link_id_map, link_id_mapping)
    assert_semantically_equal(duplicated_link_ids, {})


@pytest.fixture()
def matsim_output_network():
    return {
        "file_path": matsim_output_network_path,
        "expected_nodes": {
            "21667818": {
                "id": "21667818",
                "s2_id": 5221390302696205321,
                "x": 528504.1342843144,
                "y": 182155.7435136598,
                "lon": -0.14910908709500162,
                "lat": 51.52370573323939,
            },
            "25508485": {
                "id": "25508485",
                "s2_id": 5221390301001263407,
                "x": 528489.467895946,
                "y": 182206.20303669578,
                "lon": -0.14930198709481451,
                "lat": 51.524162533239284,
            },
        },
        "expected_edges": {
            "id": "1",
            "from": "25508485",
            "to": "21667818",
            "freespeed": 4.166666666666667,
            "capacity": 600.0,
            "permlanes": 1.0,
            "oneway": "1",
            "modes": {"car", "subway", "metro", "walk"},
            "s2_from": 5221390301001263407,
            "s2_to": 5221390302696205321,
            "length": 52.765151087870265,
            "attributes": {
                "osm:way:access": "permissive",
                "osm:way:highway": "unclassified",
                "osm:way:id": 26997928.0,
                "osm:way:name": "Brunswick Place",
            },
        },
        "expected_network_level_attributes": {
            "coordinateReferenceSystem": "EPSG:27700",
            "crs": "epsg:27700",
        },
    }


def test_reading_matsim_output_network(assert_semantically_equal, matsim_output_network):
    n = read.read_matsim(path_to_network=matsim_output_network["file_path"], epsg="epsg:27700")

    assert_semantically_equal(
        dict(n.graph.nodes(data=True)), matsim_output_network["expected_nodes"]
    )
    assert_semantically_equal(
        list(n.graph.edges(data=True))[0][2], matsim_output_network["expected_edges"]
    )
    assert_semantically_equal(
        n.attributes, matsim_output_network["expected_network_level_attributes"]
    )


def test_reading_network_with_geometry_attributes(assert_semantically_equal):
    correct_links = {
        "1": {
            "id": "1",
            "from": "25508485",
            "to": "21667818",
            "length": 52.765151087870265,
            "s2_from": 5221390301001263407,
            "s2_to": 5221390302696205321,
            "freespeed": 4.166666666666667,
            "capacity": 600.0,
            "permlanes": 1.0,
            "oneway": "1",
            "geometry": LineString([(1, 2), (2, 3), (3, 4)]),
            "modes": {"car"},
            "attributes": {
                "osm:way:access": "permissive",
                "osm:way:highway": "unclassified",
                "osm:way:id": 26997928.0,
                "osm:way:name": "Brunswick Place",
            },
        },
        "2": {
            "id": "2",
            "from": "25508485",
            "to": "21667818",
            "length": 52.765151087870265,
            "s2_from": 5221390301001263407,
            "s2_to": 5221390302696205321,
            "freespeed": 4.166666666666667,
            "capacity": 600.0,
            "permlanes": 1.0,
            "oneway": "1",
            "geometry": LineString([(1, 2), (2, 3), (3, 4)]),
            "modes": {"car"},
            "attributes": {
                "osm:way:access": "permissive",
                "osm:way:highway": "unclassified",
                "osm:way:id": 26997928.0,
                "osm:way:name": "Brunswick Place",
            },
        },
    }
    n = read.read_matsim(path_to_network=pt2matsim_network_with_geometry_file, epsg="epsg:27700")

    assert_semantically_equal(dict(n.links()), correct_links)


def test_reading_network_with_singular_geometry_attribute_cleans_up_empty_attributes_dict(
    assert_semantically_equal,
):
    correct_links = {
        "1": {
            "id": "1",
            "from": "25508485",
            "to": "21667818",
            "length": 52.765151087870265,
            "s2_from": 5221390301001263407,
            "s2_to": 5221390302696205321,
            "freespeed": 4.166666666666667,
            "capacity": 600.0,
            "permlanes": 1.0,
            "oneway": "1",
            "geometry": LineString([(1, 2), (2, 3), (3, 4)]),
            "modes": {"car"},
        },
        "2": {
            "id": "2",
            "from": "25508485",
            "to": "21667818",
            "length": 52.765151087870265,
            "s2_from": 5221390301001263407,
            "s2_to": 5221390302696205321,
            "freespeed": 4.166666666666667,
            "capacity": 600.0,
            "permlanes": 1.0,
            "oneway": "1",
            "geometry": LineString([(1, 2), (2, 3), (3, 4)]),
            "modes": {"car"},
        },
    }
    n = read.read_matsim(
        path_to_network=pt2matsim_network_with_singular_geometry_file, epsg="epsg:27700"
    )

    assert_semantically_equal(dict(n.links()), correct_links)


def test_network_with_additional_attributes_logs_warning_when_long_form_is_forced(caplog):
    read.read_matsim(
        path_to_network=pt2matsim_network_test_file,
        epsg="epsg:27700",
        force_long_form_attributes=True,
    )
    assert caplog.records[0].levelname == "WARNING"
    assert (
        "Network-level additional attributes are always read into short form"
        in caplog.records[0].message
    )


def test_forcing_long_form_in_network_with_additional_link_attributes_reads_links_data_correctly(
    assert_semantically_equal,
):
    n = read.read_matsim(
        path_to_network=pt2matsim_network_test_file,
        epsg="epsg:27700",
        force_long_form_attributes=True,
    )
    assert_semantically_equal(
        n.link("1")["attributes"],
        {
            "osm:way:access": {
                "name": "osm:way:access",
                "class": "java.lang.String",
                "text": "permissive",
            },
            "osm:way:highway": {
                "name": "osm:way:highway",
                "class": "java.lang.String",
                "text": "unclassified",
            },
            "osm:way:id": {"name": "osm:way:id", "class": "java.lang.Float", "text": "26997928.0"},
            "osm:way:name": {
                "name": "osm:way:name",
                "class": "java.lang.String",
                "text": "Brunswick Place",
            },
        },
    )


def test_forcing_long_form_in_network_with_additional_link_attributes_reads_network_level_attributes_to_short_form(
    assert_semantically_equal,
):
    n = read.read_matsim(
        path_to_network=pt2matsim_network_test_file,
        epsg="epsg:27700",
        force_long_form_attributes=True,
    )
    assert_semantically_equal(n.attributes, {"crs": "epsg:27700"})


def test_network_with_additional_node_attributes_reads_data_correctly(
    assert_semantically_equal,
    network_with_additional_node_attrib_xml_file,
    network_with_additional_node_attrib,
):
    n = read.read_matsim(
        path_to_network=network_with_additional_node_attrib_xml_file, epsg="epsg:27700"
    )
    data_from_xml = dict(n.nodes())
    # remove lat, lon, s2id which are generated upon read from x and y values
    assert_semantically_equal(data_from_xml, dict(network_with_additional_node_attrib.nodes()))


def test_forcing_long_form_in_network_with_additional_node_attributes_reads_nodes_data_correctly(
    assert_semantically_equal, network_with_additional_node_attrib_xml_file
):
    n = read.read_matsim(
        path_to_network=network_with_additional_node_attrib_xml_file,
        epsg="epsg:27700",
        force_long_form_attributes=True,
    )
    assert_semantically_equal(
        n.node("0")["attributes"],
        {"osm:node:data": {"name": "osm:node:data", "class": "java.lang.Integer", "text": "3"}},
    )


def test_forcing_long_form_in_network_with_additional_node_attributes_reads_network_level_attributes_to_short_form(
    assert_semantically_equal, network_with_additional_node_attrib_xml_file
):
    n = read.read_matsim(
        path_to_network=network_with_additional_node_attrib_xml_file,
        epsg="epsg:27700",
        force_long_form_attributes=True,
    )
    assert_semantically_equal(n.attributes, {"crs": "epsg:27700"})


def test_read_schedule_reads_the_data_correctly(
    assert_semantically_equal, correct_services_from_test_pt2matsim_schedule
):
    (
        services,
        minimalTransferTimes,
        transit_stop_id_mapping,
        schedule_attribs,
    ) = matsim_reader.read_schedule(pt2matsim_schedule_file, "epsg:27700")

    correct_minimalTransferTimes = {
        "26997928P": {"26997928P.link:1": 0.0},
        "26997928P.link:1": {"26997928P": 0.0},
    }

    assert correct_services_from_test_pt2matsim_schedule == services
    assert_semantically_equal(minimalTransferTimes, correct_minimalTransferTimes)


def test_schedule_with_additional_stop_attributes_reads_data_correctly(
    assert_semantically_equal,
    schedule_with_additional_attrib_stop_xml_file,
    schedule_with_additional_attrib_stop,
):
    s = read.read_matsim_schedule(schedule_with_additional_attrib_stop_xml_file, "epsg:27700")
    data_from_xml = dict(s.graph().nodes())
    assert_semantically_equal(
        data_from_xml, dict(schedule_with_additional_attrib_stop.graph().nodes())
    )


def test_forcing_long_form_in_schedule_with_additional_stop_attributes_reads_data_correctly(
    assert_semantically_equal, schedule_with_additional_attrib_stop_xml_file
):
    s = read.read_matsim_schedule(
        schedule_with_additional_attrib_stop_xml_file, "epsg:27700", force_long_form_attributes=True
    )
    assert_semantically_equal(
        s.stop("s1").attributes,
        {
            "carAccessible": {"name": "carAccessible", "class": "java.lang.String", "text": "true"},
            "accessLinkId_car": {
                "name": "accessLinkId_car",
                "class": "java.lang.String",
                "text": "linkID",
            },
        },
    )


def test_forcing_long_form_in_schedule_with_additional_stop_attributes_reads_schedule_level_attributes_to_short_form(
    assert_semantically_equal, schedule_with_additional_attrib_stop_xml_file
):
    s = read.read_matsim_schedule(
        schedule_with_additional_attrib_stop_xml_file, "epsg:27700", force_long_form_attributes=True
    )
    assert_semantically_equal(s.attributes, {"crs": "epsg:27700"})


def test_schedule_with_additional_route_attributes_reads_data_correctly(
    assert_semantically_equal,
    schedule_with_additional_route_attribs_xml_file,
    schedule_with_additional_route_attrib,
):
    s = read.read_matsim_schedule(schedule_with_additional_route_attribs_xml_file, "epsg:27700")
    assert s.route("r1").has_attrib("attributes")
    assert_semantically_equal(
        s.route("r1").attributes, schedule_with_additional_route_attrib.route("r1").attributes
    )


def test_forcing_long_form_in_schedule_with_additional_route_attributes_reads_data_correctly(
    assert_semantically_equal, schedule_with_additional_route_attribs_xml_file
):
    s = read.read_matsim_schedule(
        schedule_with_additional_route_attribs_xml_file,
        "epsg:27700",
        force_long_form_attributes=True,
    )
    assert_semantically_equal(
        s.route("r1").attributes,
        {
            "additional_attrib": {
                "name": "additional_attrib",
                "class": "java.lang.String",
                "text": "attrib_value",
            }
        },
    )


def test_forcing_long_form_in_schedule_with_additional_route_attributes_reads_schedule_level_attributes_to_short_form(
    assert_semantically_equal, schedule_with_additional_route_attribs_xml_file
):
    s = read.read_matsim_schedule(
        schedule_with_additional_route_attribs_xml_file,
        "epsg:27700",
        force_long_form_attributes=True,
    )
    assert_semantically_equal(s.attributes, {"crs": "epsg:27700"})


def test_schedule_with_additional_service_attributes_reads_data_correctly(
    assert_semantically_equal,
    schedule_with_additional_service_attribs_xml_file,
    schedule_with_additional_service_attrib,
):
    s = read.read_matsim_schedule(schedule_with_additional_service_attribs_xml_file, "epsg:27700")
    assert s["s1"].has_attrib("attributes")
    assert_semantically_equal(
        s["s1"].attributes, schedule_with_additional_service_attrib["s1"].attributes
    )


def test_forcing_long_form_in_schedule_with_additional_service_attributes_reads_data_correctly(
    assert_semantically_equal, schedule_with_additional_service_attribs_xml_file
):
    s = read.read_matsim_schedule(
        schedule_with_additional_service_attribs_xml_file,
        "epsg:27700",
        force_long_form_attributes=True,
    )
    assert_semantically_equal(
        s["s1"].attributes,
        {
            "additional_attrib": {
                "name": "additional_attrib",
                "class": "java.lang.String",
                "text": "attrib_value",
            }
        },
    )


def test_forcing_long_form_in_schedule_with_additional_service_attributes_reads_schedule_level_attributes_to_short_form(
    assert_semantically_equal, schedule_with_additional_service_attribs_xml_file
):
    s = read.read_matsim_schedule(
        schedule_with_additional_service_attribs_xml_file,
        "epsg:27700",
        force_long_form_attributes=True,
    )
    assert_semantically_equal(s.attributes, {"crs": "epsg:27700"})


def test_schedule_with_additional_attributes_reads_data_correctly(
    assert_semantically_equal,
    schedule_with_additional_attribs_xml_file,
    schedule_with_additional_attrib,
):
    s = read.read_matsim_schedule(schedule_with_additional_attribs_xml_file, "epsg:27700")
    assert s.has_attrib("attributes")
    assert_semantically_equal(s.attributes, schedule_with_additional_attrib.attributes)


def test_schedule_with_additional_attributes_persists_to_short_form_when_long_form_is_forced(
    assert_semantically_equal, schedule_with_additional_attribs_xml_file
):
    s = read.read_matsim_schedule(
        schedule_with_additional_attribs_xml_file, "epsg:27700", force_long_form_attributes=True
    )
    assert_semantically_equal(
        s.attributes, {"crs": "epsg:27700", "additional_attrib": "attrib_value"}
    )


def test_schedule_with_additional_attributes_logs_warning_when_long_form_is_forced(
    schedule_with_additional_attribs_xml_file, caplog
):
    read.read_matsim_schedule(
        schedule_with_additional_attribs_xml_file, "epsg:27700", force_long_form_attributes=True
    )
    assert caplog.records[0].levelname == "WARNING"
    assert (
        "Schedule-level additional attributes are always read into short form"
        in caplog.records[0].message
    )


def test_reading_additional_attributes_into_short_form_with_missing_class_defaults_to_string(
    xml_elem_with_missing_class, caplog
):
    t = matsim_reader._read_additional_attrib_to_short_form(elem=xml_elem_with_missing_class)
    assert isinstance(t, str)
    assert caplog.records[0].levelname == "WARNING"
    assert "does not have a Java class declared." in caplog.records[0].message


def test_reading_additional_attributes_into_long_form_with_missing_class_defaults_to_string(
    xml_elem_with_missing_class, caplog
):
    d = matsim_reader._read_additional_attrib_to_long_form(elem=xml_elem_with_missing_class)
    assert isinstance(d["text"], str)
    assert d["class"] == "java.lang.String"
    assert caplog.records[0].levelname == "WARNING"
    assert "does not have a Java class declared." in caplog.records[0].message


def test_reading_pt2matsim_vehicles(assert_semantically_equal):
    vehicles, vehicle_types = matsim_reader.read_vehicles(pt2matsim_vehicles_file)

    assert_semantically_equal(vehicles, {"veh_0_bus": {"type": "bus"}})
    assert_semantically_equal(
        vehicle_types,
        {
            "bus": {
                "capacity": {"seats": {"persons": "71"}, "standingRoom": {"persons": "1"}},
                "length": {"meter": "18.0"},
                "width": {"meter": "2.5"},
                "accessTime": {"secondsPerPerson": "0.5"},
                "egressTime": {"secondsPerPerson": "0.5"},
                "doorOperation": {"mode": "serial"},
                "passengerCarEquivalents": {"pce": "2.8"},
            }
        },
    )


def test_uses_node_elevation_data_when_present_in_network_file(assert_semantically_equal, tmpdir):
    nodes_with_elevations = {
        "1": {
            "id": "1",
            "x": 114.161432,
            "y": 22.279784,
            "z": 25.0,
            "lon": 114.161432,
            "lat": 22.279784,
            "s2_id": 3748121220106005759,
        },
        "2": {
            "id": "2",
            "x": 114.159648,
            "y": 22.278037,
            "z": 53.0,
            "lon": 114.159648,
            "lat": 22.278037,
            "s2_id": 3748121226099361651,
        },
    }
    links = {
        "0": {
            "id": "0",
            "from": "1",
            "to": "2",
            "freespeed": 4.166666666666667,
            "capacity": 600.0,
            "permlanes": 1.0,
            "oneway": "1",
            "modes": {"car"},
            "s2_from": 3748121220106005759,
            "s2_to": 3748121226099361651,
            "attributes": {
                "osm:way:access": "permissive",
                "osm:way:highway": "unclassified",
                "osm:way:id": 26997928564.0,
                "osm:way:name": "Elevation Lane",
            },
            "length": 52.765151087870265,
        }
    }
    network_file_path = make_network_with_elevations_xml_file(
        nodes_with_elevations, links, "{}/small-network-with-elevations.xml".format(tmpdir)
    )

    n = read.read_matsim(path_to_network=network_file_path, epsg="epsg:4326")

    assert_semantically_equal(dict(n.nodes()), nodes_with_elevations)
    assert_semantically_equal(dict(n.links()), links)


###########################################################
# helper functions
###########################################################


def make_network_with_elevations_xml_file(nodes_with_elevations_dict, link_dict, network_file_path):
    network_xml_string = make_network_with_elevations_xml_string(
        nodes_with_elevations_dict, link_dict
    )
    with open(network_file_path, "w") as network_file:
        network_file.write(network_xml_string)
    assert os.path.exists(network_file_path)
    return network_file_path


def make_network_with_elevations_xml_string(nodes_with_elevations_dict, link_dict):
    network_xml = """
    <network>
        <attributes>
            <attribute name="simplified" class="java.lang.String">False</attribute>
            <attribute name="crs" class="java.lang.String">epsg:4326</attribute>
        </attributes>

        <nodes>
    """
    for node_id, node_values in nodes_with_elevations_dict.items():
        network_xml += '<node id="{}" x="{}" y="{}" z="{}"/> '.format(
            node_id, node_values["x"], node_values["y"], node_values["z"]
        )
    network_xml += " </nodes> "
    network_xml += (
        ' <links capperiod="01:00:00" effectivecellsize="7.5" effectivelanewidth="3.75"> '
    )
    for link_id, link_value in link_dict.items():
        network_xml += (
            '<link id="{}" from="{}" to="{}" freespeed="{}" capacity="{}" permlanes="{}" oneway="{}" '
            'modes="{}" length="{}">'.format(
                link_id,
                link_value["from"],
                link_value["to"],
                link_value["freespeed"],
                link_value["capacity"],
                link_value["permlanes"],
                link_value["oneway"],
                ",".join(list(link_value["modes"])),
                link_value["length"],
            )
        )
        network_xml += " <attributes> "
        for attr_name, attr_value in link_value["attributes"].items():
            network_xml += '<attribute name="{}" class="{}">{}</attribute> '.format(
                attr_name, java_dtypes.python_to_java_dtype(type(attr_value)), attr_value
            )
        network_xml += " </attributes> </link>"
    network_xml += " </links> </network>"
    return network_xml
