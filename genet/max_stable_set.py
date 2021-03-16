from pyomo.environ import *  # noqa: F403
import itertools
import logging
import networkx as nx
import genet.outputs_handler.geojson as gngeojson
import genet.utils.graph_operations as graph_operations
import matplotlib.pyplot as plt


def exists(coeff_attrib):
    return True


class MaxStableSet:
    def __init__(self, pt_graph, network_spatial_tree, modes, distance_threshold=30, step_size=10):
        self.modes = modes
        self.distance_threshold = distance_threshold
        self.step_size = step_size
        self.network_spatial_tree = network_spatial_tree
        self.pt_graph = pt_graph
        self.stops, self.pt_edges = gngeojson.generate_geodataframes(pt_graph)
        self.edges = self.pt_edges[['u', 'v', 'geometry']].copy()
        self.nodes = self.find_closest_links()
        self.problem_graph = self.generate_problem_graph()
        self.solution = None
        self.artificial_stops = {}

    def find_closest_links(self):
        # increase distance by step size until all stops have closest links or reached threshold
        distance = self.step_size
        nodes = self.cast_catchment(df_stops=self.stops[['id', 'geometry']].copy(), distance=distance)
        nodes['catchment'] = distance
        stops = set(self.stops['id'])
        while (set(nodes.index) != stops) and (distance < self.distance_threshold):
            distance += self.step_size
            _df = self.cast_catchment(
                df_stops=self.stops[self.stops['id'].isin(stops - set(nodes.index))][['id', 'geometry']].copy(),
                distance=distance)
            _df['catchment'] = distance
            nodes = nodes.append(_df)
        return nodes

    def cast_catchment(self, df_stops, distance):
        return self.network_spatial_tree.closest_links(
            gdf_points=df_stops,
            distance_radius=distance,
            modes=self.modes).dropna()

    def all_stops_have_nearest_links(self):
        return not bool(self.stops_missing_nearest_links())

    def stops_missing_nearest_links(self):
        return set(self.stops['id']) - {stop for problem_node, stop in self.problem_graph.nodes(data='id')}

    def generate_problem_graph(self):
        # build the problem graph
        # build up the nodes, edges and shortest path lengths (will be used to compute weight coefficient later on)
        self.nodes['problem_nodes'] = self.nodes['id'] + '.link:' + self.nodes['link_id']
        self.edges = self.edges.merge(
            self.nodes[['id', 'link_id', 'problem_nodes']].rename(
                columns={'link_id': 'link_id_u', 'problem_nodes': 'problem_nodes_u'}),
            left_on='u', right_on='id')
        self.edges = self.edges.merge(
            self.nodes[['id', 'link_id', 'problem_nodes']].rename(
                columns={'link_id': 'link_id_v', 'problem_nodes': 'problem_nodes_v'}),
            left_on='v', right_on='id')
        self.edges = self.network_spatial_tree.shortest_path_lengths(
            df_pt_edges=self.edges,
            modes=self.modes,
            from_col='link_id_u',
            to_col='link_id_v',
            weight='length'
        )

        # build the problem graph
        problem_graph = nx.DiGraph()
        problem_nodes = self.nodes.set_index('problem_nodes').T.to_dict()
        problem_graph.add_nodes_from(problem_nodes)
        path_length_coeff = self.edges[self.edges['path_lengths'].notna()].groupby('problem_nodes_u').mean()
        path_length_coeff = path_length_coeff.rename(columns={'path_lengths': 'path_lengths_u'}).merge(
            self.edges[self.edges['path_lengths'].notna()].rename(
                columns={'path_lengths': 'path_lengths_v'}).groupby('problem_nodes_v').mean(),
            how='outer',
            left_index=True,
            right_index=True
        )
        path_length_coeff = (
                1 / path_length_coeff[['path_lengths_u', 'path_lengths_v']].mean(axis=1, skipna=True)).to_dict()
        nx.set_node_attributes(problem_graph, problem_nodes)
        nx.set_node_attributes(problem_graph, path_length_coeff, 'coeff')

        problem_edges = self.edges[self.edges['path_lengths'].isna()]
        problem_graph.add_edges_from(zip(problem_edges['problem_nodes_u'], problem_edges['problem_nodes_v']))
        # connect all catchment pools
        [problem_graph.add_edges_from(itertools.combinations(group['problem_nodes'], 2)) for name, group in
         self.nodes.groupby('id')]

        nodes_without_paths = set(problem_graph.nodes()) - set(
            graph_operations.extract_on_attributes(problem_graph.nodes(data=True),
                                                   conditions={'coeff': exists}))
        problem_graph.remove_nodes_from(nodes_without_paths)
        return problem_graph

    def in_out_degree(self, node):
        _out = self.problem_graph.out_degree(node)
        _in = self.problem_graph.in_degree(node)
        try:
            return _out + _in
        except TypeError:
            if not isinstance(_out, int):
                _out = 0
            if not isinstance(_in, int):
                _in = 0
            return _in + _out

    def has_a_completely_connected_catchment(self):
        stop_id_groups = self.nodes.groupby('id')
        for u, v in self.pt_graph.edges():
            node_degrees = [self.in_out_degree(n) for n in stop_id_groups.get_group(u)['problem_nodes']]
            node_degrees = node_degrees + [self.in_out_degree(n) for n in stop_id_groups.get_group(v)['problem_nodes']]
            total_nodes = len(stop_id_groups.get_group(u)) + len(stop_id_groups.get_group(v))
            if all([node_degree >= total_nodes - 1 for node_degree in node_degrees]):
                logging.warning(
                    f'Two stops: {u} and {v} are completely connected, suggesting that one or more stops has found no '
                    f'viable network links within the specified threshold')
                return True
        return False

    def is_viable(self):
        # all stops have closest links to snap to (catchments)
        # and the catchments are not all completely connected to one another
        return self.all_stops_have_nearest_links() and (not self.has_a_completely_connected_catchment())

    def is_partially_viable(self):
        # just the catchments are not all completely connected to one another
        return not self.has_a_completely_connected_catchment()

    def plot(self):
        minx, miny, maxx, maxy = self.nodes.geometry.total_bounds

        fig, ax = plt.subplots(figsize=(8, 8))
        self.network_spatial_tree.links.plot(ax=ax, color='#BFBFBF', alpha=0.8)
        self.network_spatial_tree.links[self.network_spatial_tree.links['link_id'].isin(self.nodes['link_id'])].plot(
            ax=ax, color='#FFD710')
        self.nodes.plot(ax=ax, color='#F9CACA', alpha=0.7)
        self.stops.plot(ax=ax, marker='x', color='#F76363')

        ax.set_xlim(minx - 0.001, maxx + 0.001)
        ax.set_ylim(miny - 0.001, maxy + 0.001)
        ax.set_title('Stops, their catchments and underlying network for the Max Stable Set Problem')
        return fig, ax

    def plot_routes(self):
        minx, miny, maxx, maxy = self.nodes.geometry.total_bounds

        fig, ax = plt.subplots(figsize=(8, 8))
        self.network_spatial_tree.links.plot(ax=ax, color='#BFBFBF', alpha=0.8)
        self.network_spatial_tree.links[self.network_spatial_tree.links['link_id'].isin(
            [item for sublist in self.pt_edges['shortest_path'] for item in sublist])].plot(ax=ax, color='#E5AF00')
        self.nodes.plot(ax=ax, color='#F9CACA', alpha=0.7)
        self.stops.plot(ax=ax, marker='x', color='#F76363')

        ax.set_xlim(minx - 0.001, maxx + 0.001)
        ax.set_ylim(miny - 0.001, maxy + 0.001)
        ax.set_title('Stops, their catchments, the underlying network and route')
        return fig, ax

    def solve(self, solver='glpk'):
        # --------------------------------------------------------
        # Model
        # --------------------------------------------------------

        model = ConcreteModel()  # noqa: F405

        # --------------------------------------------------------
        # Sets/Params
        # --------------------------------------------------------

        # nodes and edge sets
        # nodes: network's graph nodes that are closest to stops
        # edges: connections between nodes if they are in the same
        #    selection pool or there is no path between them
        vertices = set(self.problem_graph.nodes)
        edges = set(self.problem_graph.edges)

        model.vertices = Set(initialize=vertices)  # noqa: F405

        def spatial_proximity_coefficient_init(model, i):
            attribs = self.problem_graph.nodes[i]
            # todo normalise
            return attribs['coeff']

        model.c = Param(model.vertices, initialize=spatial_proximity_coefficient_init)  # noqa: F405

        # --------------------------------------------------------
        # Variables
        # --------------------------------------------------------

        model.x = Var(vertices, within=Binary)  # noqa: F405

        # --------------------------------------------------------
        # Constraints
        # --------------------------------------------------------

        model.edge_adjacency = ConstraintList()  # noqa: F405
        for u, v in edges:
            model.edge_adjacency.add(model.x[u] + model.x[v] <= 1)

        # --------------------------------------------------------
        # Objective
        # --------------------------------------------------------

        def total_nodes_rule(model):
            return sum(model.c[i] * model.x[i] for i in model.vertices)

        model.total_nodes = Objective(rule=total_nodes_rule, sense=maximize)  # noqa: F405

        # --------------------------------------------------------
        # Solver
        # --------------------------------------------------------

        logging.info('Passing problem to solver')
        _solver = SolverFactory(solver)  # noqa: F405
        _solver.solve(model)

        # --------------------------------------------------------
        # Solution parse
        # --------------------------------------------------------

        selected = [str(v).strip('x[]') for v in model.component_data_objects(Var) if  # noqa: F405
                    float(v.value) == 1.0]
        # solution maps Stop IDs to Link IDs
        self.solution = {self.problem_graph.nodes[node]['id']: node.split(':')[-1] for node in selected}
        self.artificial_stops = {
            node: {
                **self.pt_graph.nodes[self.problem_graph.nodes[node]['id']],
                **{'linkRefId': node.split(':')[-1],
                   'stop_id': self.problem_graph.nodes[node]['id']}}
            for node in selected}

    def unsolved_stops(self):
        return set(self.stops['id']) - set(self.solution.keys())

    def all_stops_solved(self):
        return not bool(self.unsolved_stops())

    def route_edges(self):
        self.pt_edges['linkRefId_u'] = self.pt_edges['u'].map(self.solution)
        self.pt_edges['linkRefId_v'] = self.pt_edges['v'].map(self.solution)
        self.pt_edges = self.network_spatial_tree.shortest_paths(
            df_pt_edges=self.pt_edges,
            modes=self.modes,
            from_col='linkRefId_u',
            to_col='linkRefId_v',
            weight='length'
        )
