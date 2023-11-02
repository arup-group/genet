from genet.modify import graph


def test_reproj(assert_semantically_equal):
    nodes = graph.reproj(
        {"node": {"x": 528704.1425925883, "y": 182068.78193707118}}, "epsg:27700", "epsg:4326"
    )
    assert_semantically_equal(nodes, {"node": {"x": -0.14625948709424305, "y": 51.52287873323954}})
