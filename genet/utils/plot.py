import osmnx as ox
import os


def plot_graph(g, filename, show=True, save=False, output_dir='', e_c='#999999'):
    if output_dir:
        filepath = os.path.join(output_dir, filename + '.png')
    else:
        filepath = None
    return ox.plot_graph(
        g,
        filepath=filepath,
        node_size=2,
        edge_color=e_c,
        save=save,
        show=show)


def plot_graph_routes(g, routes, filename, show=True, save=False, output_dir=''):
    if output_dir:
        filepath = os.path.join(output_dir, filename + '.png')
    else:
        filepath = None
    if len(routes) == 1:
        return ox.plot_graph_route(
            g,
            route=routes[0],
            route_color="#F9A825",
            route_linewidth=1,
            orig_dest_size=5,
            node_size=2,
            filepath=filepath,
            save=save,
            show=show)
    else:
        return ox.plot_graph_routes(
            g,
            routes=routes,
            route_colors="#F9A825",
            route_linewidth=1,
            orig_dest_size=5,
            node_size=2,
            filepath=filepath,
            save=save,
            show=show)


def plot_non_routed_schedule_graph(g, filename, ax=None, show=True, save=False, output_dir=''):
    if output_dir:
        filepath = os.path.join(output_dir, filename + '.png')
    else:
        filepath = None
    return ox.plot_graph(
        g,
        ax=ax,
        filepath=filepath,
        node_size=1,
        edge_color='#F9A825',
        node_color='#F9A825',
        save=save,
        show=show)
