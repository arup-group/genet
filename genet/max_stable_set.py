import itertools
import pandas as pd
import networkx as nx
import genet.outputs_handler.geojson as gngeojson
import genet.utils.graph_operations as graph_operations


def exists(coeff_attrib):
    return True


class MaxStableSet:
    def __init__(self, **kwargs):
        self.problem_graph = self.build(**kwargs)

    def build(self, pt_graph, network_spatial_tree, modes, distance_threshold=30, step_size=10):
        """

        :param pt_graph:
        :param network_spatial_tree:
        :param modes:
        :param distance_threshold:
        :param step_size:
        :return:
        """
        gdf_pt_stops, gdf_pt_edges = gngeojson.generate_geodataframes(pt_graph)
        gdf_pt_stops = network_spatial_tree.closest_links(
            gdf_points=gdf_pt_stops, distance_radius=step_size, modes=modes)
        # todo increase distance by step size until all stops have closest links or reached threshold

        # build the problem graph
        # build up the nodes, edges and shortest path lengths (to use as weight later on)
        gdf_pt_stops['problem_nodes'] = gdf_pt_stops['id'] + '.link:' + gdf_pt_stops['link_id']
        gdf_pt_edges = gdf_pt_edges.merge(
            gdf_pt_stops.rename(columns={'link_id': 'link_id_u', 'problem_nodes': 'problem_nodes_u'}),
            left_on='u', right_on='id')
        gdf_pt_edges = gdf_pt_edges.merge(
            gdf_pt_stops.rename(columns={'link_id': 'link_id_v', 'problem_nodes': 'problem_nodes_v'}),
            left_on='v', right_on='id')
        gdf_pt_edges = network_spatial_tree.shortest_path_lengths(
            df_pt_edges=gdf_pt_edges,
            modes=modes,
            from_col='link_id_u',
            to_col='link_id_v',
            weight='length'
        )

        # build the problem graph
        problem_graph = nx.DiGraph()
        problem_nodes = gdf_pt_stops.set_index('problem_nodes').T.to_dict()
        problem_graph.add_nodes_from(problem_nodes)
        path_length_coeff = gdf_pt_edges[gdf_pt_edges['path_lengths'].notna()].groupby('problem_nodes_u').mean()
        path_length_coeff = path_length_coeff.rename(columns={'path_lengths': 'path_lengths_u'}).merge(
            gdf_pt_edges[gdf_pt_edges['path_lengths'].notna()].rename(
                columns={'path_lengths': 'path_lengths_v'}).groupby('problem_nodes_v').mean(),
            how='outer',
            left_index=True,
            right_index=True
        )
        path_length_coeff = (
                1 / path_length_coeff[['path_lengths_u', 'path_lengths_v']].mean(axis=1, skipna=True)).to_dict()
        nx.set_node_attributes(problem_graph, problem_nodes)
        nx.set_node_attributes(problem_graph, path_length_coeff, 'coeff')

        problem_edges = gdf_pt_edges[gdf_pt_edges['path_lengths'].isna()]
        problem_graph.add_edges_from(zip(problem_edges['problem_nodes_u'], problem_edges['problem_nodes_v']))
        # connect all catchment pools
        [problem_graph.add_edges_from(itertools.combinations(group['problem_nodes'], 2)) for name, group in
         gdf_pt_stops.groupby('id')]

        nodes_without_paths = set(problem_graph.nodes()) - set(
            graph_operations.extract_on_attributes(problem_graph.nodes(data=True),
                                                   conditions={'coeff': exists}))
        problem_graph.remove_nodes_from(nodes_without_paths)
        return problem_graph
