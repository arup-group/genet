from genet.input import osmnx_customised
from tests.fixtures import assert_semantically_equal


def test_return_edges_handles_regular_non_oneway_paths(full_fat_default_config):
    paths = {
        0: {
            "osmid": 0,
            "nodes": [0, 1],
            "highway": "unclassified",
            "modes": ["bike", "car", "walk"],
        }
    }

    edges = osmnx_customised.return_edges(
        paths, config=full_fat_default_config, bidirectional=False
    )
    assert len(edges) == 2
    assert (0, 1) in [edge for edge, attribs in edges]
    assert (1, 0) in [edge for edge, attribs in edges]
    for edge, attribs in edges:
        assert_semantically_equal(
            attribs, {"modes": ["bike", "car", "walk"], "osmid": 0, "highway": "unclassified"}
        )


def test_return_edges_handles_oneway_paths(full_fat_default_config):
    paths = {
        0: {
            "osmid": 0,
            "nodes": [0, 1],
            "highway": "unclassified",
            "modes": ["bike", "car", "walk"],
            "oneway": "yes",
        }
    }

    edges = osmnx_customised.return_edges(
        paths, config=full_fat_default_config, bidirectional=False
    )
    assert len(edges) == 1
    assert (0, 1) in [edge for edge, attribs in edges]
    for edge, attribs in edges:
        assert_semantically_equal(
            attribs, {"modes": ["bike", "car", "walk"], "osmid": 0, "highway": "unclassified"}
        )


def test_return_edges_handles_reversed_oneway_paths(full_fat_default_config):
    paths = {
        0: {
            "osmid": 0,
            "nodes": [0, 1],
            "highway": "unclassified",
            "modes": ["bike", "car", "walk"],
            "oneway": "reverse",
        }
    }

    edges = osmnx_customised.return_edges(
        paths, config=full_fat_default_config, bidirectional=False
    )
    assert len(edges) == 1
    assert (1, 0) in [edge for edge, attribs in edges]
    for edge, attribs in edges:
        assert_semantically_equal(
            attribs, {"modes": ["bike", "car", "walk"], "osmid": 0, "highway": "unclassified"}
        )


def test_return_edges_handles_roundabouts_as_oneway(full_fat_default_config):
    paths = {
        0: {
            "osmid": 0,
            "nodes": [0, 1],
            "highway": "unclassified",
            "modes": ["bike", "car", "walk"],
            "junction": "roundabout",
        }
    }

    edges = osmnx_customised.return_edges(
        paths, config=full_fat_default_config, bidirectional=False
    )
    assert len(edges) == 1
    assert (0, 1) in [edge for edge, attribs in edges]
    for edge, attribs in edges:
        assert_semantically_equal(
            attribs,
            {
                "modes": ["bike", "car", "walk"],
                "osmid": 0,
                "highway": "unclassified",
                "junction": "roundabout",
            },
        )
