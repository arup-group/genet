from pathlib import Path

import pytest
from genet import Network, cli


@pytest.fixture()
def network(tmpdir):
    output_dir = Path(tmpdir) / "network"
    n = Network("epsg:27700")
    n.add_nodes({"n1": {"x": 1, "y": 1}, "n2": {"x": 2, "y": 2}})
    n.add_link(
        "link_n1_n2",
        "n1",
        "n2",
        attribs={"modes": {"car", "bike", "bus"}, "permlanes": 1, "freespeed": 1, "capacity": 1},
    )
    n.write_to_matsim(output_dir)
    return {"network": n, "link_id": "link_n1_n2", "path": output_dir / "network.xml"}


@pytest.fixture()
def sub_network(tmpdir):
    output_dir = Path(tmpdir) / "sub_network"
    n = Network("epsg:27700")
    n.add_nodes({"n1": {"x": 1, "y": 1}, "n2": {"x": 2, "y": 2}})
    n.add_link(
        "link_n1_n2",
        "n1",
        "n2",
        attribs={
            "modes": {"car", "bike", "bus"},
            "permlanes": 1,
            "freespeed": 1,
            "capacity": 1,
            "attributes": {"unique_data": "yes"},
        },
    )
    n.write_to_matsim(output_dir)
    return {
        "network": n,
        "bike_link_id": "link_n1_n2",
        "expected_bike_link_id": "bike---link_n1_n2",
        "expected_link_id_mapping": {"link_n1_n2": "bike---link_n1_n2"},
        "path": output_dir / "network.xml",
    }


def test_retains_original_link_strips_bike_mode(tmpdir, network, sub_network):
    link_id = sub_network["bike_link_id"]
    assert "bike" in network["network"].link(link_id)["modes"]

    output_network = cli._replace_modal_subgraph(
        path_to_network=network["path"],
        projection="epsg:27700",
        output_dir=tmpdir,
        path_to_subgraph=sub_network["path"],
        modes="bike",
        increase_capacity=True,
    )

    assert output_network.has_link(link_id), f"Link {link_id} is missing from the output network"
    assert (
        "bike" not in output_network.link(link_id)["modes"]
    ), f"Mode `bike` was not removed from link: {link_id}"


def test_adds_new_links_from_sub_network_just_for_bike(tmpdir, network, sub_network):
    output_network = cli._replace_modal_subgraph(
        path_to_network=network["path"],
        projection="epsg:27700",
        output_dir=tmpdir,
        path_to_subgraph=sub_network["path"],
        modes="bike",
        increase_capacity=True,
    )

    expected_new_link_id = sub_network["expected_bike_link_id"]
    assert output_network.has_link(
        expected_new_link_id
    ), f"Link {expected_new_link_id} is missing from the output network"
    assert output_network.link(expected_new_link_id)["modes"] == {
        "bike"
    }, f"Link {expected_new_link_id} did not have the correct modes set"


def test_retains_link_data_from_subgraph_network(tmpdir, network, sub_network):
    original_link_data = sub_network["network"].link(sub_network["bike_link_id"])

    output_network = cli._replace_modal_subgraph(
        path_to_network=network["path"],
        projection="epsg:27700",
        output_dir=tmpdir,
        path_to_subgraph=sub_network["path"],
        modes="bike",
        increase_capacity=True,
    )

    output_data = output_network.link(sub_network["expected_bike_link_id"])
    keys_to_ignore = {"from", "s2_from", "to", "s2_to", "id", "modes", "capacity"}
    assert {k: v for k, v in output_data.items() if k not in keys_to_ignore} == {
        k: v for k, v in original_link_data.items() if k not in keys_to_ignore
    }, "Data for the added link does not match the original data of the link"


def test_increases_capacity_for_added_links_only(tmpdir, network, sub_network):
    original_net_capacity = {
        link_id: data["capacity"] for link_id, data in network["network"].links()
    }

    output_network = cli._replace_modal_subgraph(
        path_to_network=network["path"],
        projection="epsg:27700",
        output_dir=tmpdir,
        path_to_subgraph=sub_network["path"],
        modes="bike",
        increase_capacity=True,
    )

    expected_new_link_id = sub_network["expected_bike_link_id"]
    assert output_network.has_link(
        expected_new_link_id
    ), f"Link {expected_new_link_id} is missing from the output network"
    assert (
        output_network.link(expected_new_link_id)["capacity"] == 9999
    ), f"Link {expected_new_link_id} did not have capacity increased"

    link_id = network["link_id"]
    assert output_network.has_link(link_id), f"Link {link_id} is missing from the output network"
    assert (
        output_network.link(link_id)["capacity"] == original_net_capacity[link_id]
    ), f"Link {link_id} did not retain th original capacity value"


def test_does_not_increase_capacity_if_not_requested(tmpdir, network, sub_network):
    original_subnet_capacity = {
        link_id: data["capacity"] for link_id, data in sub_network["network"].links()
    }

    output_network = cli._replace_modal_subgraph(
        path_to_network=network["path"],
        projection="epsg:27700",
        output_dir=tmpdir,
        path_to_subgraph=sub_network["path"],
        modes="bike",
        increase_capacity=False,
    )

    for link_id, old_capacity in original_subnet_capacity.items():
        expected_new_link_id = sub_network["expected_link_id_mapping"][link_id]
        assert output_network.has_link(
            expected_new_link_id
        ), f"Link {expected_new_link_id} is missing from the output network"
        assert (
            output_network.link(expected_new_link_id)["capacity"] == old_capacity
        ), f"Link {expected_new_link_id} did not retain th original capacity value"


def test_adds_nodes_only_once_with_multiple_subgraphs(tmpdir, network, sub_network):
    original_net_no_nodes = len(list(network["network"].nodes()))
    original_subnet_no_nodes = len(list(sub_network["network"].nodes()))

    output_network = cli._replace_modal_subgraph(
        path_to_network=network["path"],
        projection="epsg:27700",
        output_dir=tmpdir,
        path_to_subgraph=sub_network["path"],
        modes="bike,bus",
        increase_capacity=False,
    )

    assert (
        len(list(output_network.nodes())) == original_net_no_nodes + original_subnet_no_nodes
    ), "Number of nodes in the output network is not consistent with the input networks"


def test_adds_links_shared_in_subgraph_network_separately(tmpdir, network, sub_network):
    original_net_no_links = len(list(network["network"].links()))
    original_subnet_no_links = len(list(sub_network["network"].links()))

    output_network = cli._replace_modal_subgraph(
        path_to_network=network["path"],
        projection="epsg:27700",
        output_dir=tmpdir,
        path_to_subgraph=sub_network["path"],
        modes="bike,bus",
        increase_capacity=False,
    )

    assert len(list(output_network.links())) == original_net_no_links + (
        2 * original_subnet_no_links
    ), (
        "Number of links in the output network is not consistent with the input network plus separation of links "
        "in the subgraph network"
    )
