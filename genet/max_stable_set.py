import itertools
import logging
from copy import deepcopy

import matplotlib.pyplot as plt
import networkx as nx
from pyomo.environ import *  # noqa: F403
import pandas as pd

import genet.output.geojson as gngeojson
import genet.utils.dict_support as dict_support
import genet.utils.graph_operations as graph_operations
from genet.exceptions import InvalidMaxStableSetProblem


def has_attrib(attrib_value):
    # used with a method to extract graph elements with a specific attribute key regardless of the value, if the key
    # exists, this function evaluates to True.
    return True


class MaxStableSet:
    def __init__(self, pt_graph, network_spatial_tree, modes, distance_threshold=30, step_size=10):
        self.service_modes = modes
        self.distance_threshold = distance_threshold
        self.step_size = step_size
        self.network_spatial_tree = network_spatial_tree
        self.pt_graph = pt_graph
        _gdf = gngeojson.generate_geodataframes(pt_graph)
        self.stops, self.pt_edges = _gdf['nodes'].to_crs('epsg:4326'), _gdf['links'].to_crs('epsg:4326')
        self.edges = self.pt_edges.loc[:, ['u', 'v', 'geometry']].copy()
        self.nodes = self.find_closest_links()
        if self.nodes.empty or len(set(self.nodes['id'])) == 1:
            logging.info('The problem did not find closest links for enough stops. If partial solution is allowed,'
                         'the stops will not be snapped and the routes will be entirely artificial.')
            self.is_partial = True
            self.problem_graph = nx.DiGraph()
        else:
            self.is_partial = False
            self.problem_graph = self.generate_problem_graph()
        if not self.is_viable():
            self.is_partial = self.is_partially_viable()
            if self.is_partial:
                logging.warning('This Maximum Stable Set Problem is partially viable.')
            else:
                raise InvalidMaxStableSetProblem('This Maximum Stable Set Problem has at least one completely connected'
                                                 'catchment and cannot proceed to the solver.')

        self.solution = {}
        self.artificial_stops = {}
        self.artificial_links = {}
        self.unsolved_stops = set()

    def find_closest_links(self):
        # increase distance by step size until all stops have closest links or reached threshold
        distance = self.step_size
        nodes = self.cast_catchment(df_stops=self.stops.loc[:, ['id', 'geometry']].copy(), distance=distance)
        nodes['catchment'] = distance
        stops = set(self.stops['id'])
        while (set(nodes.index) != stops) and (distance < self.distance_threshold):
            distance += self.step_size
            _df = self.cast_catchment(
                df_stops=self.stops.loc[self.stops['id'].isin(stops - set(nodes.index)), ['id', 'geometry']].copy(),
                distance=distance)
            _df['catchment'] = distance
            nodes = pd.concat([nodes, _df])
        return nodes[~nodes['link_id'].str.match("artificial")]

    def cast_catchment(self, df_stops, distance):
        return self.network_spatial_tree.closest_links(
            gdf_points=df_stops,
            distance_radius=distance).dropna()

    def all_stops_have_nearest_links(self):
        return not bool(self.stops_missing_nearest_links())

    def stops_missing_nearest_links(self):
        return set(self.stops['id']) - {stop for problem_node, stop in self.problem_graph.nodes(data='id')}

    def generate_problem_graph(self):
        # build the problem graph
        # build up the nodes, edges and shortest path lengths (will be used to compute weight coefficient later on)
        self.nodes.loc[:, 'problem_nodes'] = self.nodes.loc[:, 'id'] + '.link:' + self.nodes.loc[:, 'link_id']
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
            from_col='link_id_u',
            to_col='link_id_v',
            weight='length'
        )

        # build the problem graph
        problem_graph = nx.DiGraph()
        problem_nodes = self.nodes.set_index('problem_nodes').T.to_dict()
        problem_graph.add_nodes_from(problem_nodes)
        path_length_components = pd.concat(
            [
                self.edges["path_lengths"]
                .dropna()
                .groupby(self.edges[f"problem_nodes_{component}"])
                .mean()
                .to_frame(f"path_lengths_{component}")
                for component in ["u", "v"]
            ],
            axis=1,
        )
        path_length_coeff = (1 / path_length_components.mean(axis=1, skipna=True)).to_dict()
        nx.set_node_attributes(problem_graph, problem_nodes)
        nx.set_node_attributes(problem_graph, path_length_coeff, 'coeff')

        problem_edges = self.edges.loc[self.edges['path_lengths'].isna(), :]
        problem_graph.add_edges_from(zip(problem_edges['problem_nodes_u'], problem_edges['problem_nodes_v']))
        # connect all catchment pools
        [problem_graph.add_edges_from(itertools.combinations(group['problem_nodes'], 2)) for name, group in
         self.nodes.groupby('id')]

        nodes_without_paths = set(problem_graph.nodes()) - set(
            graph_operations.extract_on_attributes(problem_graph.nodes(data=True),
                                                   conditions={'coeff': has_attrib}))
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
            u_group = None
            v_group = None
            if u in stop_id_groups.groups:
                u_group = stop_id_groups.get_group(u)
            if v in stop_id_groups.groups:
                v_group = stop_id_groups.get_group(v)
            if (u_group is not None) and (v_group is not None):
                node_degrees = [self.in_out_degree(n) for n in u_group['problem_nodes']]
                node_degrees += [self.in_out_degree(n) for n in v_group['problem_nodes']]
                total_nodes = len(u_group) + len(v_group)
                if all([node_degree >= total_nodes - 1 for node_degree in node_degrees]):
                    logging.warning(
                        f'Two stops: {u} and {v} are completely connected, suggesting that one or more stops has '
                        f'found no viable network links within the specified threshold')
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

        ax.set_xlim(minx - 0.003, maxx + 0.003)
        ax.set_ylim(miny - 0.003, maxy + 0.003)
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

        ax.set_xlim(minx - 0.003, maxx + 0.003)
        ax.set_ylim(miny - 0.003, maxy + 0.003)
        ax.set_title('Stops, their catchments, the underlying network and route')
        return fig, ax

    def solve(self, solver='cbc'):
        if nx.is_empty(self.problem_graph):
            logging.info('Empty problem graph passed to the solver. No stops will find a solution.')
            self.unsolved_stops = set(self.stops['id'])
        else:
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

            selected = [str(v).strip("x[\\']") for v in model.component_data_objects(Var) if  # noqa: F405
                        v.value is not None and float(v.value) == 1.0]
            # solution maps Stop IDs to Link IDs
            self.solution = {self.problem_graph.nodes[node]['id']: self.problem_graph.nodes[node]['link_id'] for
                             node in selected}
            self.artificial_stops = {
                node: {
                    **self.pt_graph.nodes[self.problem_graph.nodes[node]['id']],
                    **{'linkRefId': self.problem_graph.nodes[node]['link_id'],
                       'stop_id': self.problem_graph.nodes[node]['id'],
                       'id': node}
                }
                for node in selected}
            self.unsolved_stops = set(self.stops['id']) - set(self.solution.keys())

    def all_stops_solved(self):
        return not bool(self.unsolved_stops)

    def stops_to_artificial_stops_map(self):
        return {**{s: s for s in self.unsolved_stops},
                **{data['stop_id']: a_s for a_s, data in self.artificial_stops.items()}}

    def route_edges(self):
        self.pt_edges['linkRefId_u'] = self.pt_edges['u'].map(self.solution)
        self.pt_edges['linkRefId_v'] = self.pt_edges['v'].map(self.solution)
        pt_edges = self.network_spatial_tree.shortest_paths(
            df_pt_edges=self.pt_edges.loc[self.pt_edges.notna().all(axis=1), ('linkRefId_u', 'linkRefId_v')],
            from_col='linkRefId_u',
            to_col='linkRefId_v',
            weight='length'
        )
        self.pt_edges = self.pt_edges.merge(
            pt_edges,
            left_on=['linkRefId_u', 'linkRefId_v'], right_on=['linkRefId_u', 'linkRefId_v'],
            how='left'
        )
        return self.pt_edges

    def _generate_artificial_link(self, from_node, to_node):
        link_id = f'artificial_link===from:{from_node}===to:{to_node}'
        self.artificial_links[link_id] = {
            'from': from_node,
            'to': to_node,
            'modes': self.service_modes
        }
        return link_id

    def _access_link_data(self, link_id):
        try:
            link_data = self.network_spatial_tree.links.loc[link_id, :].to_dict()
        except KeyError:
            # that link must be artificial
            if 'artificial_link' in link_id:
                link_data = self.artificial_links[link_id]
            else:
                raise RuntimeError(f'A stop has snapped to an identified link {link_data}')
        return link_data

    def _generate_artificial_path(self, from_link, to_link):
        return [from_link, self._generate_artificial_link(self._access_link_data(from_link)['to'],
                                                          self._access_link_data(to_link)['from']), to_link]

    def fill_in_solution_artificially(self):
        # generate unsnapped stops
        self.solution = {**self.solution, **{s: self._generate_artificial_link(s, s) for s in self.unsolved_stops}}
        self.artificial_stops = {
            **self.artificial_stops,
            **{f'{s}.link:{self._generate_artificial_link(s,s)}': {
                **self.pt_graph.nodes[s],
                **{'linkRefId': self._generate_artificial_link(s, s), 'stop_id': s,
                   'id': f'{s}.link:{self._generate_artificial_link(s,s)}'}} for s in self.unsolved_stops}}

        # fill in the blanks with generated stop-links and
        if 'shortest_path' in self.pt_edges.columns:
            missing_linkref_u_mask = self.pt_edges['linkRefId_u'].isna()
            self.pt_edges.loc[missing_linkref_u_mask, 'linkRefId_u'] = self.pt_edges.loc[
                missing_linkref_u_mask, 'u'].map(self.solution)
            missing_linkref_v_mask = self.pt_edges['linkRefId_v'].isna()
            self.pt_edges.loc[missing_linkref_v_mask, 'linkRefId_v'] = self.pt_edges.loc[
                missing_linkref_v_mask, 'v'].map(self.solution)
            missing_shortest_path_mask = self.pt_edges['shortest_path'].isna()
            self.pt_edges.loc[missing_shortest_path_mask, 'shortest_path'] = self.pt_edges.loc[
                missing_shortest_path_mask].apply(
                lambda x: self._generate_artificial_path(from_link=x['linkRefId_u'], to_link=x['linkRefId_v']), axis=1)
        else:
            logging.warning('Solution is being artificially filled in before the edges were routed. If your problem is'
                            'partial, this will result in gaps in routed paths.')

    def routed_path(self, ordered_stops):
        """
        :param ordered_stops: list of stops in the route (not artificial/snapped stops)
        :return:
        """
        path = []
        for u, v in zip(ordered_stops[:-1], ordered_stops[1:]):
            pairwise_path = \
                self.pt_edges.loc[(self.pt_edges['u'] == u) & (self.pt_edges['v'] == v), 'shortest_path'].tolist()[0]
            if path:
                if path[-1] == pairwise_path[0]:
                    path += pairwise_path[1:]
                else:
                    path += pairwise_path
            else:
                path.extend(pairwise_path)
        return path

    def to_changeset(self, routes_df):
        return ChangeSet(self, routes_df)


class ChangeSet:
    """
    Record of network and schedule changes needed for a solved max stable set
    """

    def __init__(self, max_stable_set, df_route_data):
        self.routes = set(df_route_data.index)
        self.services = {max_stable_set.pt_graph.graph['route_to_service_map'][r_id] for r_id in self.routes}
        self.other_routes_in_service = {r_id for s_id in self.services for r_id in
                                        max_stable_set.pt_graph.graph['service_to_route_map'][s_id]} - self.routes

        self.new_links = self.new_network_links(max_stable_set)
        self.new_nodes = self.new_network_nodes(max_stable_set)
        self.df_route_data = self.update_df_route_data(df_route_data, max_stable_set)
        self.additional_links_modes = self.generate_additional_links_modes(max_stable_set)
        self.new_stops = self.schedule_stops(max_stable_set)
        self.new_pt_edges = self.schedule_edges(max_stable_set)

    def new_network_links(self, max_stable_set):
        # generate data needed for the network to add artificial links following a partially viable max stable set
        return max_stable_set.artificial_links

    def new_network_nodes(self, max_stable_set):
        # generate data needed for the network to add artificial nodes following a partially viable max stable set
        return {s: {k: v for k, v in max_stable_set.pt_graph.nodes[s].items() if
                    k not in ['routes', 'services', 'additional_attributes', 'epsg']} for s in
                max_stable_set.unsolved_stops}

    def update_df_route_data(self, df_route_data, max_stable_set):
        # update stops and generate routed paths
        df_route_data.loc[:, 'route'] = df_route_data.loc[:, 'ordered_stops'].apply(
            lambda x: max_stable_set.routed_path(x))
        _map = max_stable_set.stops_to_artificial_stops_map()
        df_route_data.loc[:, 'ordered_stops'] = df_route_data.loc[:, 'ordered_stops'].map(
            lambda x: [_map[stop] for stop in x])
        return df_route_data

    def generate_additional_links_modes(self, max_stable_set):
        link_ids = {link_id for route_list in self.df_route_data['route'].values for link_id in route_list}
        links = max_stable_set.network_spatial_tree.links.copy()
        links = links.loc[links['link_id'].isin(link_ids), ['link_id', 'modes']]
        links['modes'] = links['modes'].apply(lambda x: set(x) | max_stable_set.service_modes)
        return links.set_index('link_id').T.to_dict()

    def schedule_stops(self, max_stable_set):
        # generate data needed for the network to add artificial stops and
        new_stops = deepcopy(max_stable_set.artificial_stops)
        for stop, data in new_stops.items():
            data['routes'] = self.routes
            data['services'] = self.services
        return new_stops

    def schedule_edges(self, max_stable_set):
        map = max_stable_set.stops_to_artificial_stops_map()
        new_pt_edges = [
            (map[u], map[v], {'routes': data['routes'] & self.routes, 'services': data['services'] & self.services}) for
            u, v, data in list(max_stable_set.pt_graph.edges(data=True))]
        return new_pt_edges

    def __add__(self, other):
        # combine two changesets
        self.new_links = {**self.new_links, **other.new_links}
        self.new_nodes = {**self.new_nodes, **other.new_nodes}
        self.df_route_data = pd.concat([self.df_route_data, other.df_route_data])
        self.additional_links_modes = dict_support.merge_complex_dictionaries(
            self.additional_links_modes, other.additional_links_modes)
        self.new_stops = dict_support.merge_complex_dictionaries(self.new_stops, other.new_stops)
        self.new_pt_edges = dict_support.combine_edge_data_lists(self.new_pt_edges, other.new_pt_edges)
        return self
