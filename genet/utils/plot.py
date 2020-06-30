import osmnx as ox
import os
import matplotlib.pyplot as plt


def plot_graph(g, filename, show=True, save=False, output_dir='', e_c='#273746'):
    if output_dir:
        ox.settings.imgs_folder = output_dir
    return ox.plot_graph(
        g,
        filename=filename,
        node_color='#273746',
        node_size=1,
        edge_linewidth=0.5,
        edge_alpha=0.5,
        edge_color=e_c,
        save=save,
        show=show)


def plot_graph_routes(g, routes, filename, show=True, save=False, output_dir=''):
    if output_dir:
        ox.settings.imgs_folder = output_dir
    return ox.plot_graph_routes(
            g,
            routes=routes,
            route_color="#EC7063",
            route_linewidth=1,
            orig_dest_size=5,
            filename=filename,
            node_color='#273746',
            node_size=1,
            edge_linewidth=0.5,
            edge_alpha=0.5,
            save=save,
            show=show)


def plot_non_routed_schedule_graph(g, filename, ax=None, show=True, save=False, output_dir=''):
    if ax is not None:
        fig = ax.figure
    else:
        fig, ax = plt.subplots(frameon=False)
    edges = ox.utils_graph.graph_to_gdfs(g, nodes=False)["geometry"]
    ax = edges.plot(ax=ax, color='#EC7063', alpha=0.7)
    if save:
        fig.savefig(os.path.join(output_dir, filename))
    if show:
        plt.show()
    return fig, ax
