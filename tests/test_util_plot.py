import os
from genet.utils import plot
from tests.fixtures import network_object_from_test_data


def test_plot_graph_gets_saved_to_the_specified_directory(tmpdir, network_object_from_test_data):
    filename = 'filename'
    expected_plot_path = os.path.join(tmpdir, filename+'.png')
    assert not os.path.exists(expected_plot_path)

    n = network_object_from_test_data
    plot.plot_graph(n.graph, filename, show=False, save=True, output_dir=tmpdir)

    assert os.path.exists(expected_plot_path)


def test_plot_graph_routes_gets_saved_to_the_specified_directory(tmpdir, network_object_from_test_data):
    filename = 'filename'
    expected_plot_path = os.path.join(tmpdir, filename+'.png')
    assert not os.path.exists(expected_plot_path)

    n = network_object_from_test_data
    plot.plot_graph_routes(n.graph, [], filename, show=False, save=True, output_dir=tmpdir)

    assert os.path.exists(expected_plot_path)


def test_plot_non_routed_schedule_graph_gets_saved_to_the_specified_directory(tmpdir, network_object_from_test_data):
    filename = 'filename'
    expected_plot_path = os.path.join(tmpdir, filename+'.png')
    assert not os.path.exists(expected_plot_path)

    n = network_object_from_test_data
    plot.plot_non_routed_schedule_graph(n.graph, filename, show=False, save=True, output_dir=tmpdir)

    assert os.path.exists(expected_plot_path)
