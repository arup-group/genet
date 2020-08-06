import networkx as nx
import pandas as pd
import uuid
import logging
import os
from copy import deepcopy
from typing import Union, List
from pyproj import Transformer
import genet.inputs_handler.matsim_reader as matsim_reader
import genet.inputs_handler.osm_reader as osm_reader
import genet.outputs_handler.matsim_xml_writer as matsim_xml_writer
import genet.outputs_handler.geojson as geojson
import genet.modify.change_log as change_log
import genet.utils.spatial as spatial
import genet.utils.persistence as persistence
import genet.utils.graph_operations as graph_operations
import genet.validate.network_validation as network_validation
import genet.utils.plot as plot
import genet.schedule_elements as schedule_elements

logging.basicConfig(format='%(asctime)s - %(message)s', level=logging.INFO)


class Network:
    def __init__(self, epsg):
        self.epsg = epsg
        self.transformer = Transformer.from_crs(epsg, 'epsg:4326')
        self.graph = nx.MultiDiGraph(name='Network graph', crs={'init': self.epsg})
        self.schedule = schedule_elements.Schedule(epsg)
        self.change_log = change_log.ChangeLog()
        self.spatial_tree = spatial.SpatialTree()
        # link_id_mapping maps between (usually string literal) index per edge to the from and to nodes that are
        # connected by the edge
        self.link_id_mapping = {}

    def __repr__(self):
        return "<{} instance at {}: with \ngraph: {} and \nschedule {}".format(
            self.__class__.__name__,
            id(self),
            nx.info(self.graph),
            self.schedule.info()
        )

    def __str__(self):
        return self.info()

    def add(self, other):
        """
        This is deliberately not a magic function to discourage `new_network = network_1 + network_2` (and memory
        goes out the window)
        :param other:
        :return:
        """
        # consolidate coordinate systems
        if other.epsg != self.epsg:
            logging.info('Attempting to merge two networks in different coordinate systems. '
                         'Reprojecting from {} to {}'.format(other.epsg, self.epsg))
            other.reproject(other.epsg)
        # consolidate node ids
        other = graph_operations.consolidate_node_indices(self, other)
        # consolidate link ids
        other = graph_operations.consolidate_link_indices(self, other)

        # finally, once the node and link ids have been sorted, combine the graphs
        # nx.compose(left, right) overwrites data in left with data in right under matching ids
        self.graph = nx.compose(other.graph, self.graph)
        # finally, combine link_id_mappings
        self.link_id_mapping = {**other.link_id_mapping, **self.link_id_mapping}

        # combine schedules
        self.schedule.add(other.schedule)

        # merge change_log DataFrames
        self.change_log.log = self.change_log.log.append(other.change_log.log)
        self.change_log.log = self.change_log.log.sort_values(by='timestamp').reset_index(drop=True)

    def print(self):
        print(self.info())

    def info(self):
        return "Graph info: {} \nSchedule info: {}".format(
            nx.info(self.graph),
            self.schedule.info()
        )

    def plot(self, show=True, save=False, output_dir=''):
        """
        Plots the network graph and schedule
        :param show: whether to display the plot
        :param save: whether to save the plot
        :param output_dir: output directory for the image
        :return:
        """
        return plot.plot_graph_routes(self.graph, self.schedule_routes_nodes(), 'network_route_graph', show=show,
                                      save=save, output_dir=output_dir)

    def plot_graph(self, show=True, save=False, output_dir=''):
        """
        Plots the network graph only
        :param show: whether to display the plot
        :param save: whether to save the plot
        :param output_dir: output directory for the image
        :return:
        """
        return plot.plot_graph(self.graph, 'network_graph', show=show, save=save, output_dir=output_dir)

    def plot_schedule(self, show=True, save=False, output_dir=''):
        """
        Plots original stop connections in the network's schedule over the network graph
        :param show: whether to display the plot
        :param save: whether to save the plot
        :param output_dir: output directory for the image
        :return:
        """
        fig, ax = self.plot_graph(show=False)
        return plot.plot_non_routed_schedule_graph(
            nx.MultiDiGraph(self.schedule.graph()),
            'network_schedule.png',
            ax=ax,
            show=show,
            save=save,
            output_dir=output_dir
        )

    def reproject(self, new_epsg):
        """
        Changes projection of the network to new_epsg
        :param new_epsg: 'epsg:1234'
        :return:
        """
        old_to_new_transformer = Transformer.from_crs(self.epsg, new_epsg)
        for node_id, node_attribs in self.nodes():
            x, y = spatial.change_proj(node_attribs['x'], node_attribs['y'], old_to_new_transformer)
            reprojected_node_attribs = {'x': x, 'y': y}
            self.apply_attributes_to_node(node_id, reprojected_node_attribs, silent=True)
        if self.schedule:
            self.schedule.reproject(new_epsg)
        self.initiate_crs_transformer(new_epsg)

    def initiate_crs_transformer(self, epsg):
        self.epsg = epsg
        if epsg != 'epsg:4326':
            self.transformer = Transformer.from_crs(epsg, 'epsg:4326')
        else:
            self.transformer = None

    def node_attribute_summary(self, data=False):
        """
        Is expensive. Parses through data stored on nodes and gives a summary tree of the data stored on the nodes.
        If data is True, shows also up to 5 unique values stored under such keys.
        :param data: bool, False by default
        :return:
        """
        root = graph_operations.get_attribute_schema(self.nodes(), data=data)
        graph_operations.render_tree(root, data)

    def node_attribute_data_under_key(self, key):
        """
        Generates a pandas.Series object index by node ids, with data stored on the nodes under `key`
        :param key: either a string e.g. 'x', or if accessing nested information, a dictionary
            e.g. {'attributes': {'osm:way:name': 'text'}}
        :return: pandas.Series
        """
        return pd.Series(graph_operations.get_attribute_data_under_key(self.nodes(), key))

    def node_attribute_data_under_keys(self, keys: list, index_name=None):
        """
        Generates a pandas.DataFrame object index by link ids, with data stored on the nodes under `key`
        :param keys: list of either a string e.g. 'x', or if accessing nested information, a dictionary
            e.g. {'attributes': {'osm:way:name': 'text'}}
        :param index_name: optional, gives the index_name to dataframes index
        :return: pandas.DataFrame
        """
        df = None
        for key in keys:
            if isinstance(key, dict):
                # consolidate nestedness to get a name for the column
                name = str(key)
                name = name.replace('{', '').replace('}', '').replace("'", '').replace(' ', ':')
            else:
                name = key

            col_series = self.node_attribute_data_under_key(key)
            col_series.name = name

            if df is not None:
                df = df.merge(pd.DataFrame(col_series), left_index=True, right_index=True, how='outer')
            else:
                df = pd.DataFrame(col_series)
        if index_name:
            df.index = df.index.set_names([index_name])
        return df

    def link_attribute_summary(self, data=False):
        """
        Is expensive. Parses through data stored on links and gives a summary tree of the data stored on the links.
        If data is True, shows also up to 5 unique values stored under such keys.
        :param data: bool, False by default
        :return:
        """
        root = graph_operations.get_attribute_schema(self.links(), data=data)
        graph_operations.render_tree(root, data)

    def link_attribute_data_under_key(self, key: Union[str, dict]):
        """
        Generates a pandas.Series object index by link ids, with data stored on the links under `key`
        :param key: either a string e.g. 'modes', or if accessing nested information, a dictionary
            e.g. {'attributes': {'osm:way:name': 'text'}}
        :return: pandas.Series
        """
        return pd.Series(graph_operations.get_attribute_data_under_key(self.links(), key))

    def link_attribute_data_under_keys(self, keys: list, index_name=None):
        """
        Generates a pandas.DataFrame object index by link ids, with data stored on the links under `key`
        :param keys: list of either a string e.g. 'modes', or if accessing nested information, a dictionary
            e.g. {'attributes': {'osm:way:name': 'text'}}
        :param index_name: optional, gives the index_name to dataframes index
        :return: pandas.DataFrame
        """
        df = None
        for key in keys:
            if isinstance(key, dict):
                # consolidate nestedness to get a name for the column
                name = str(key)
                name = name.replace('{', '').replace('}', '').replace("'", '').replace(' ', ':')
            else:
                name = key

            col_series = self.link_attribute_data_under_key(key)
            col_series.name = name

            if df is not None:
                df = df.merge(pd.DataFrame(col_series), left_index=True, right_index=True, how='outer')
            else:
                df = pd.DataFrame(col_series)
        if index_name:
            df.index = df.index.set_names([index_name])
        return df

    def add_node(self, node: Union[str, int], attribs: dict = None, silent: bool = False):
        """
        Adds a node.
        :param node:
        :param attribs: should include spatial information x,y in epsg cosistent with the network or lat lon in
        epsg:4326
        :param silent: whether to mute stdout logging messages, useful for big batches
        :return:
        """
        if attribs is not None:
            self.graph.add_node(node, **attribs)
        else:
            self.graph.add_node(node)
        self.change_log.add(object_type='node', object_id=node, object_attributes=attribs)
        if not silent:
            logging.info('Added Node with index `{}` and data={}'.format(node, attribs))
        return node

    def add_edge(self, u: Union[str, int], v: Union[str, int], multi_edge_idx: int = None, attribs: dict = None,
                 silent: bool = False):
        """
        Adds an edge between u and v. If an edge between u and v already exists, adds an additional one. Generates
        link id. If you already have a link id, use the method to add_link.
        :param u: node in the graph
        :param v: node in the graph
        :param multi_edge_idx: you can specify which multi index to use if there are other edges between u and v.
        Will generate new index if already used.
        :param attribs:
        :param silent: whether to mute stdout logging messages, useful for big batches
        :return:
        """
        link_id = self.generate_index_for_edge(silent=silent)
        self.add_link(link_id, u, v, multi_edge_idx, attribs, silent)
        if not silent:
            logging.info('Added edge from `{}` to `{}` with link_id `{}`'.format(u, v, link_id))
        return link_id

    def add_link(self, link_id: Union[str, int], u: Union[str, int], v: Union[str, int], multi_edge_idx: int = None,
                 attribs: dict = None, silent: bool = False):
        """
        Adds an link between u and v with id link_id, if available. If a link between u and v already exists,
        adds an additional one.
        :param link_id:
        :param u: node in the graph
        :param v: node in the graph
        :param multi_edge_idx: you can specify which multi index to use if there are other edges between u and v.
        Will generate new index if already used.
        :param attribs:
        :param silent: whether to mute stdout logging messages, useful for big batches
        :return:
        """
        if link_id in self.link_id_mapping:
            new_link_id = self.generate_index_for_edge(silent=silent)
            logging.warning('This link_id=`{}` already exists. Generated a new unique_index: `{}`'.format(
                link_id, new_link_id))
            link_id = new_link_id

        if multi_edge_idx is None:
            multi_edge_idx = self.graph.new_edge_key(u, v)
        if self.graph.has_edge(u, v, multi_edge_idx):
            old_idx = multi_edge_idx
            multi_edge_idx = self.graph.new_edge_key(u, v)
            logging.warning('Changing passed multi_edge_idx: `{}` as there already exists an edge stored under that '
                            'index. New multi_edge_idx: `{}`'.format(old_idx, multi_edge_idx))
        if not isinstance(multi_edge_idx, int):
            raise RuntimeError('Multi index key needs to be an integer')

        self.link_id_mapping[link_id] = {'from': u, 'to': v, 'multi_edge_idx': multi_edge_idx}
        compulsory_attribs = {'from': u, 'to': v, 'id': link_id}
        if attribs is None:
            attribs = compulsory_attribs
        else:
            attribs = {**attribs, **compulsory_attribs}
        self.graph.add_edge(u, v, key=multi_edge_idx, **attribs)
        self.change_log.add(object_type='link', object_id=link_id, object_attributes=attribs)
        if not silent:
            logging.info('Added Link with index {}, from node:{} to node:{}, under multi-index:{}, and data={}'.format(
                link_id, u, v, multi_edge_idx, attribs))
        return link_id

    def reindex_node(self, node_id, new_node_id, silent: bool = False):
        # check if new id is already occupied
        if self.node_id_exists(new_node_id):
            new_node_id = self.generate_index_for_node()
        # extract link ids which will be affected byt the node relabel and change the from anf to attributes
        from_links = graph_operations.extract_links_on_edge_attributes(self, conditions={'from': node_id})
        self.apply_attributes_to_links({link: {'from': new_node_id} for link in from_links})
        to_links = graph_operations.extract_links_on_edge_attributes(self, conditions={'to': node_id})
        self.apply_attributes_to_links({link: {'to': new_node_id} for link in to_links})
        # update link_id_mapping
        for k in from_links:
            self.link_id_mapping[k]['from'] = new_node_id
        for k in to_links:
            self.link_id_mapping[k]['to'] = new_node_id

        new_attribs = deepcopy(self.node(node_id))
        new_attribs['id'] = new_node_id
        self.change_log.modify(object_type='node', old_id=node_id, new_id=new_node_id,
                               old_attributes=self.node(node_id), new_attributes=new_attribs)
        self.apply_attributes_to_node(node_id, new_attribs)
        self.graph = nx.relabel_nodes(self.graph, {node_id: new_node_id})
        if not silent:
            logging.info('Changed Node index from {} to {}'.format(node_id, new_node_id))

    def reindex_link(self, link_id, new_link_id, silent: bool = False):
        # check if new id is already occupied
        if self.link_id_exists(new_link_id):
            new_link_id = self.generate_index_for_edge()
        new_attribs = deepcopy(self.link(link_id))
        new_attribs['id'] = new_link_id
        self.change_log.modify(object_type='link', old_id=link_id, new_id=new_link_id,
                               old_attributes=self.link(link_id), new_attributes=new_attribs)
        self.apply_attributes_to_link(link_id, new_attribs)
        self.link_id_mapping[new_link_id] = self.link_id_mapping[link_id]
        del self.link_id_mapping[link_id]
        if not silent:
            logging.info('Changed Link index from {} to {}'.format(link_id, new_link_id))

    def subgraph_on_link_conditions(self, conditions):
        """
        Gives a subgraph of network.graph based on matching conditions defined in conditions
        :param conditions as describen in graph_operations.extract_links_on_edge_attributes
        :return:
        """
        links = graph_operations.extract_links_on_edge_attributes(self, conditions)
        edges_for_sub = [
            (self.link_id_mapping[link]['from'],
             self.link_id_mapping[link]['to'],
             self.link_id_mapping[link]['multi_edge_idx'])
            for link in links]
        return nx.MultiDiGraph(nx.edge_subgraph(self.graph, edges_for_sub))

    def modal_subgraph(self, modes: Union[str, list]):
        if isinstance(modes, str):
            modes = {modes}
        else:
            modes = set(modes)

        def modal_condition(modes_list):
            return set(modes_list) & modes

        return self.subgraph_on_link_conditions(conditions={'modes': modal_condition})

    def find_shortest_path(self, from_node, to_node, modes: Union[str, list] = None, subgraph: nx.MultiDiGraph = None,
                           return_nodes=False):
        """
        Finds shortest path between from and to nodes in the graph. If modes specified, finds shortest path in the
        modal subgraph (using links which have given modes stored under 'modes' key in link attributes). If computing
        a large number of routes on the same modal subgraph, it is best to find the subgraph using the `modal_subgraph`
        method and pass it under subgraph to avoid re-computing the subgraph every time.
        :param from_node: node id in the graph
        :param to_node: node id in the graph
        :param modes: string e.g. 'car' or list ['car', 'bike']
        :param subgraph: nx.MultiDiGraph, preferably the result of `modal_subgraph`
        :param return_nodes: If True, returns list of node ids defining a route (reminder: there can be more than one
        link between two nodes, by default this method will return a list of link ids that results in shortest journey)
        :return: list of link ids defining a route
        """
        if subgraph is not None:
            g = subgraph
        elif modes:
            g = self.modal_subgraph(modes)
        else:
            g = self.graph
        route = nx.shortest_path(g, source=from_node, target=to_node, weight='length')

        if return_nodes:
            return route
        else:
            return [graph_operations.find_shortest_path_link(dict(g[u][v]), modes=modes)
                    for u, v in zip(route[:-1], route[1:])]

    def apply_attributes_to_node(self, node_id, new_attributes, silent: bool = False):
        """
        Adds, or changes if already present, the attributes in new_attributes. Doesn't replace the dictionary
        stored at the node currently so no data is lost, unless it is being overwritten.
        :param node_id: node id to perform the change to
        :param new_attributes: dictionary of data to add/replace if present
        :param silent: whether to mute stdout logging messages, useful for big batches
        :return:
        """
        old_attributes = deepcopy(self.node(node_id))

        # check if change is to nested part of node data
        if any(isinstance(v, dict) for v in new_attributes.values()):
            new_attributes = persistence.set_nested_value(old_attributes, new_attributes)
        else:
            new_attributes = {**old_attributes, **new_attributes}

        self.change_log.modify(
            object_type='node',
            old_id=node_id,
            new_id=node_id,
            old_attributes=self.node(node_id),
            new_attributes=new_attributes)
        nx.set_node_attributes(self.graph, {node_id: new_attributes})
        if not silent:
            logging.info('Changed Node attributes under index: {}'.format(node_id))

    def apply_attributes_to_nodes(self, new_attributes: dict, silent: bool = False):
        """
        Adds, or changes if already present, the attributes in new_attributes. Doesn't replace the dictionary
        stored at the node currently so no data is lost, unless it is being overwritten.
        :param new_attributes: keys are node ids and values are dictionaries of data to add/replace if present
        :param silent: whether to mute stdout logging messages, useful for big batches
        :return:
        """
        [self.apply_attributes_to_node(node, new_attribs, silent) for node, new_attribs in new_attributes.items()]

    def apply_function_to_nodes(self, function, location: str, silent: bool = False):
        """
        Applies function to node attributes dictionary
        :param function: function of node attributes dictionary returning a value that should be stored
        under `location`
        :param location: where to save the results: string defining the key in the nodes attributes dictionary
        :param silent: whether to mute stdout logging messages, useful for big batches
        :return:
        """
        new_node_attribs = {}
        for node, node_attribs in self.nodes():
            try:
                new_node_attribs[node] = {location: function(node_attribs)}
            except KeyError:
                # Not all nodes/edges are required to have all the same attributes stored. Fail silently and only apply
                # to relevant nodes/edges
                pass
        self.apply_attributes_to_nodes(new_node_attribs, silent=silent)

    def apply_attributes_to_edge(self, u, v, new_attributes, conditions=None, how=any, silent: bool = False):
        """
        Applies attributes to edges (which optionally match certain criteria)
        :param u: from node
        :param v: to node
        :param new_attributes: attributes data to be applied
        :param conditions: graph_operations.Filter conditions
        :param how: graph_operations.Filter how
        :param silent:
        :return:
        """
        filter = graph_operations.Filter(conditions=conditions, how=how)

        for multi_idx, edge_atrribs in self.edge(u, v).items():
            if filter.satisfies_conditions(edge_atrribs):
                old_attributes = deepcopy(edge_atrribs)

                # check if change is to nested part of node data
                if any(isinstance(v, dict) for v in new_attributes.values()):
                    new_attribs = persistence.set_nested_value(old_attributes, new_attributes)
                else:
                    new_attribs = {**old_attributes, **new_attributes}

                edge = '({}, {}, {})'.format(u, v, multi_idx)

                self.change_log.modify(
                    object_type='edge',
                    old_id=edge,
                    new_id=edge,
                    old_attributes=edge_atrribs,
                    new_attributes=new_attribs)

                nx.set_edge_attributes(self.graph, {(u, v, multi_idx): new_attribs})
                if not silent:
                    logging.info('Changed Link attributes under index: {}'.format(edge))

    def apply_attributes_to_edges(self, new_attributes: dict, conditions=None, how=any, silent: bool = False):
        """
        Applies new attributes for edges (optionally satisfying certain criteria)
        :param new_attributes: dictionary where keys are two tuples (u, v) where u is the from node and v is the to
        node. The value at the key are the new attributes to be applied to links on edge (u,v)
        :param conditions: graph_operations.Filter conditions
        :param how: graph_operations.Filter how
        :param silent:
        :return:
        """
        [self.apply_attributes_to_edge(u, v, new_attribs, conditions, how, silent)
         for (u, v), new_attribs in new_attributes.items()]

    def apply_attributes_to_link(self, link_id, new_attributes, silent: bool = False):
        """
        Adds, or changes if already present, the attributes in new_attributes. Doesn't replace the dictionary
        stored at the link currently so no data is lost, unless it is being overwritten.
        :param link_id: link id to perform the change to
        :param new_attributes: dictionary of data to add/replace if present
        :param silent: whether to mute stdout logging messages, useful for big batches
        :return:
        """
        u, v = self.link_id_mapping[link_id]['from'], self.link_id_mapping[link_id]['to']
        multi_idx = self.link_id_mapping[link_id]['multi_edge_idx']
        old_attributes = deepcopy(self.link(link_id))

        # check if change is to nested part of node data
        if any(isinstance(v, dict) for v in new_attributes.values()):
            new_attributes = persistence.set_nested_value(old_attributes, new_attributes)
        else:
            new_attributes = {**old_attributes, **new_attributes}

        self.change_log.modify(
            object_type='link',
            old_id=link_id,
            new_id=link_id,
            old_attributes=self.link(link_id),
            new_attributes=new_attributes)

        nx.set_edge_attributes(self.graph, {(u, v, multi_idx): new_attributes})
        if not silent:
            logging.info('Changed Link attributes under index: {}'.format(link_id))

    def apply_attributes_to_links(self, new_attributes: dict, silent: bool = False):
        """
        Adds, or changes if already present, the attributes in new_attributes. Doesn't replace the dictionary
        stored at the link currently so no data is lost, unless it is being overwritten.
        :param new_attributes: keys are link ids and values are dictionaries of data to add/replace if present
        :param silent: whether to mute stdout logging messages, useful for big batches
        :return:
        """
        [self.apply_attributes_to_link(link, new_attribs, silent) for link, new_attribs in new_attributes.items()]

    def apply_function_to_links(self, function, location: str, silent: bool = False):
        """
        Applies function to node attributes dictionary
        :param function: function of node attributes dictionary returning a value that should be stored
        under `location`
        :param location: where to save the results: string defining the key in the nodes attributes dictionary
        :param silent: whether to mute stdout logging messages, useful for big batches
        :return:
        """
        new_link_attribs = {}
        for link_id, link_attribs in self.links():
            try:
                new_link_attribs[link_id] = {location: function(link_attribs)}
            except KeyError:
                # Not all nodes/edges are required to have all the same attributes stored. Fail silently and only apply
                # to relevant nodes/edges
                pass
        number_of_links_not_affected = len(self.link_id_mapping) - len(new_link_attribs)
        if number_of_links_not_affected != 0:
            logging.info(f'{number_of_links_not_affected} out of {len(self.link_id_mapping)} links have not been '
                         f'affected by the function. Links affected: {list(new_link_attribs.keys())}')
        self.apply_attributes_to_links(new_link_attribs, silent=silent)

    def remove_node(self, node_id, silent: bool = False):
        """
        Removes the node n and all adjacent edges
        :param node_id:
        :param silent: whether to mute stdout logging messages, useful for big batches
        :return:
        """
        self.change_log.remove(object_type='node', object_id=node_id, object_attributes=self.node(node_id))
        self.graph.remove_node(node_id)
        if not silent:
            logging.info('Removed Node under index: {}'.format(node_id))

    def remove_nodes(self, nodes, silent: bool = False):
        """
        Removes several nodes and all adjacent edges
        :param nodes:
        :param silent: whether to mute stdout logging messages, useful for big batches
        :return:
        """
        [self.remove_node(node, silent) for node in nodes]

    def remove_link(self, link_id, silent: bool = False):
        """
        Removes the multi edge pertaining to link given
        :param link_id:
        :param silent: whether to mute stdout logging messages, useful for big batches
        :return:
        """
        self.change_log.remove(object_type='link', object_id=link_id, object_attributes=self.link(link_id))
        u, v = self.link_id_mapping[link_id]['from'], self.link_id_mapping[link_id]['to']
        multi_idx = self.link_id_mapping[link_id]['multi_edge_idx']
        self.graph.remove_edge(u, v, multi_idx)
        del self.link_id_mapping[link_id]
        if not silent:
            logging.info('Removed Link under index: {}'.format(link_id))

    def remove_links(self, links, silent: bool = False):
        """
        Removes the multi edges pertaining to links given
        :param links:
        :param silent: whether to mute stdout logging messages, useful for big batches
        :return:
        """
        [self.remove_link(link, silent) for link in links]

    def number_of_multi_edges(self, u, v):
        """
        number of multi edges on edge from u to v
        :param u: from node
        :param v: to node
        :return:
        """
        if self.graph.has_edge(u, v):
            return len(self.graph.edges(u, v))
        else:
            return 0

    def nodes(self):
        """
        :return:  Iterator through each node and its attrib (two-tuple)
        """
        for id, attrib in self.graph.nodes(data=True):
            yield id, attrib

    def node(self, node_id):
        """
        :return:  attribs of the 'node_id'
        """
        return self.graph.nodes[node_id]

    def edges(self):
        """
        :return: Iterator through each edge's from, to nodes and its attrib (three-tuple)
        """
        for u, v in self.graph.edges():
            yield u, v, self.edge(u, v)

    def edge(self, u, v):
        """
        :param u: from node of self.graph
        :param v: to node of self.graph
        :return:  attribs of the edge from u to  v
        """
        return dict(self.graph[u][v])

    def links(self):
        """
        :return: Iterator through each link id its attrib (two-tuple)
        """
        for link_id in self.link_id_mapping.keys():
            yield link_id, self.link(link_id)

    def link(self, link_id):
        """
        :param link_id:
        :return:
        """
        u, v = self.link_id_mapping[link_id]['from'], self.link_id_mapping[link_id]['to']
        multi_idx = self.link_id_mapping[link_id]['multi_edge_idx']
        return dict(self.graph[u][v][multi_idx])

    def services(self):
        """
        Iterator returning services
        :return:
        """
        for id, service in self.schedule.services.items():
            yield service

    def schedule_routes(self):
        """
        Iterator returning service_id and a route within that service
        :return:
        """
        for service_id, route in self.schedule.routes():
            yield service_id, route

    def schedule_routes_nodes(self):
        routes = []
        for service_id, _route in self.schedule_routes():
            if _route.route:
                route_nodes = graph_operations.convert_list_of_link_ids_to_network_nodes(self, _route.route)
                if len(route_nodes) != 1:
                    logging.warning('The route: {} within service {}, is disconnected. Consists of {} chunks.'
                                    ''.format(_route.id, service_id, len(route_nodes)))
                    routes.extend(route_nodes)
                else:
                    routes.append(route_nodes[0])
        return routes

    def schedule_routes_links(self):
        routes = []
        for service_id, _route in self.schedule_routes():
            if _route.route:
                routes.append(_route.route)
        return routes

    def node_id_exists(self, node_id):
        if node_id in [i for i, attribs in self.nodes()]:
            logging.warning('This node_id={} already exists.'.format(node_id))
            return True
        return False

    def has_node(self, node_id):
        return self.graph.has_node(node_id)

    def has_nodes(self, node_id: list):
        return all([self.has_node(node_id) for node_id in node_id])

    def has_edge(self, u, v):
        return self.graph.has_edge(u, v)

    def has_link(self, link_id: str):
        if link_id in self.link_id_mapping:
            link_edge = self.link_id_mapping[link_id]
            u, v, multi_idx = link_edge['from'], link_edge['to'], link_edge['multi_edge_idx']
            if self.graph.has_edge(u, v, multi_idx):
                return True
            else:
                logging.info('Link with id {} is declared in the network with from_node: {}, to_node: {} and '
                             'multi_index: {} but this edge is not in the graph.'.format(link_id, u, v, multi_idx))
                return False
        else:
            logging.info('Link with id {} is not in the network.'.format(link_id))
            return False

    def has_links(self, link_ids: list, conditions: Union[list, dict] = None):
        """
        Whether the Network contains the links given in the link_ids list. If attribs is specified, checks whether the
        Network contains the links specified and those links match the attributes in the attribs dict.
        :param link_ids: list of link ids e.g. ['1', '102']
        :param conditions: confer graph_operations.Filter conditions
        :return:
        """
        has_all_links = all([self.has_link(link_id) for link_id in link_ids])
        if not conditions:
            return has_all_links
        elif has_all_links:
            filter = graph_operations.Filter(conditions, how=any)
            links_satisfy = [link_id for link_id in link_ids if filter.satisfies_conditions(self.link(link_id))]
            return set(links_satisfy) == set(link_ids)
        else:
            return False

    def has_valid_link_chain(self, link_ids: List[str]):
        for prev_link_id, next_link_id in zip(link_ids[:-1], link_ids[1:]):
            prev_link_id_to_node = self.link_id_mapping[prev_link_id]['to']
            next_link_id_from_node = self.link_id_mapping[next_link_id]['from']
            if prev_link_id_to_node != next_link_id_from_node:
                logging.info('Links {} and {} are not connected'.format(prev_link_id, next_link_id))
                return False
        if not link_ids:
            logging.info('Links chain is empty')
            return False
        return True

    def route_distance(self, link_ids):
        if self.has_valid_link_chain(link_ids):
            distance = 0
            for link_id in link_ids:
                link_attribs = self.link(link_id)
                if 'length' in link_attribs:
                    distance += link_attribs['length']
                else:
                    length = spatial.distance_between_s2cellids(link_attribs['from'], link_attribs['to'])
                    link_attribs['length'] = length
                    distance += length
            return distance
        else:
            logging.warning('This route is invalid: {}'.format(link_ids))
            return 0

    def generate_index_for_node(self, avoid_keys: Union[list, set] = None, silent: bool = False):
        existing_keys = set([i for i, attribs in self.nodes()])
        if avoid_keys:
            existing_keys = existing_keys | set(avoid_keys)
        try:
            id = max([int(i) for i in existing_keys]) + 1
        except ValueError:
            id = len(existing_keys) + 1
        if (id in existing_keys) or (str(id) in existing_keys):
            id = uuid.uuid4()
        if not silent:
            logging.info('Generated node id {}.'.format(id))
        return str(id)

    def link_id_exists(self, link_id):
        if link_id in self.link_id_mapping:
            logging.warning('This link_id={} already exists.'.format(link_id))
            return True
        return False

    def generate_index_for_edge(self, avoid_keys: Union[list, set] = None, silent: bool = False):
        existing_keys = set(self.link_id_mapping.keys())
        if avoid_keys:
            existing_keys = existing_keys | set(avoid_keys)
        try:
            id = max([int(i) for i in existing_keys]) + 1
        except ValueError:
            id = len(existing_keys) + 1
        if (id in existing_keys) or (str(id) in existing_keys):
            id = uuid.uuid4()
        if not silent:
            logging.info('Generated link id {}.'.format(id))
        return str(id)

    def index_graph_edges(self):
        logging.warning('This method clears the existing link_id indexing')
        self.link_id_mapping = {}
        i = 0
        for u, v, multi_edge_idx in self.graph.edges:
            self.link_id_mapping[str(i)] = {'from': u, 'to': v, 'multi_edge_idx': multi_edge_idx}
            i += 1

    def has_schedule_with_valid_network_routes(self):
        if all([route.has_network_route() for service_id, route in self.schedule_routes()]):
            return all([self.is_valid_network_route(route) for service_id, route in self.schedule_routes()])
        return False

    def calculate_route_to_crow_fly_ratio(self, route: schedule_elements.Route):
        route_dist = self.route_distance(route.route)
        crowfly_dist = route.crowfly_distance()
        if crowfly_dist:
            return route_dist / crowfly_dist
        else:
            return 'Division by zero'

    def is_valid_network_route(self, route: schedule_elements.Route):
        def modal_condition(modes_list):
            return set(modes_list) & {route.mode}

        if self.has_links(route.route):
            valid_link_chain = self.has_valid_link_chain(route.route)
            links_have_correct_modes = self.has_links(route.route, {'modes': modal_condition})
            if not links_have_correct_modes:
                logging.info('Some link ids in Route: {} don\'t accept the route\'s mode: {}'.format(
                    route.id, route.mode))
            return valid_link_chain and links_have_correct_modes
        logging.info('Not all link ids in Route: {} are in the graph.'.format(route.id))
        return False

    def invalid_network_routes(self):
        return [(service_id, route.id) for service_id, route in self.schedule.routes() if not route.has_network_route()
                or not self.is_valid_network_route(route)]

    def generate_validation_report(self, link_length_threshold=1000):
        """
        Generates a dictionary with keys: 'graph', 'schedule' and 'routing' describing validity of the Network's
        underlying graph, the schedule services and then the intersection of the two which is the routing of schedule
        services onto the graph.
        :param link_length_threshold: in meters defaults to 1000, i.e. 1km
        :return:
        """
        logging.info('Checking validity of the Network')
        logging.info('Checking validity of the Network graph')
        report = {}
        # decribe network connectivity
        modes = ['car', 'walk', 'bike']
        report['graph'] = {'graph_connectivity': {}}
        for mode in modes:
            logging.info('Checking network connectivity for mode: {}'.format(mode))
            # subgraph for the mode to be tested
            G_mode = self.modal_subgraph(mode)
            # calculate how many connected subgraphs there are
            report['graph']['graph_connectivity'][mode] = network_validation.describe_graph_connectivity(G_mode)

        def links_over_threshold_length(value):
            return value >= link_length_threshold
        report['graph']['links_over_1km_length'] = graph_operations.extract_links_on_edge_attributes(
            self,
            conditions={'length': links_over_threshold_length}
        )

        report['schedule'] = self.schedule.generate_validation_report()

        route_to_crow_fly_ratio = {}
        for service_id, route in self.schedule_routes():
            if 'not_has_uniquely_indexed_routes' in report['schedule']['service_level'][service_id]['invalid_stages']:
                if service_id in route_to_crow_fly_ratio:
                    route_id = len(route_to_crow_fly_ratio[service_id])
                else:
                    route_id = 0
            else:
                route_id = route.id
            if service_id in route_to_crow_fly_ratio:
                route_to_crow_fly_ratio[service_id][route_id] = self.calculate_route_to_crow_fly_ratio(route)
            else:
                route_to_crow_fly_ratio[service_id] = {route_id: self.calculate_route_to_crow_fly_ratio(route)}

        report['routing'] = {
            'services_have_routes_in_the_graph': self.has_schedule_with_valid_network_routes(),
            'service_routes_with_invalid_network_route': self.invalid_network_routes(),
            'route_to_crow_fly_ratio': route_to_crow_fly_ratio
        }
        return report

    def read_osm(self, osm_file_path, osm_read_config, num_processes: int = 1):
        input_to_output_transformer = Transformer.from_crs('epsg:4326', self.epsg)

        config = osm_reader.Config(osm_read_config)
        nodes, edges = osm_reader.generate_osm_graph_edges_from_file(
            osm_file_path, config, num_processes)
        for node_id, attribs in nodes.items():
            x, y = spatial.change_proj(attribs['x'], attribs['y'], input_to_output_transformer)
            self.add_node(str(node_id), {
                'id': str(node_id),
                'x': x,
                'y': y,
                'lat': attribs['x'],
                'lon': attribs['y'],
                's2_id': attribs['s2id']
            }, silent=True)

        for edge, attribs in edges:
            u, v = str(edge[0]), str(edge[1])
            link_attributes = osm_reader.find_matsim_link_values(attribs, config)
            link_attributes['oneway'] = '1'
            link_attributes['modes'] = attribs['modes']
            link_attributes['from'] = self.node(u)['id']
            link_attributes['to'] = self.node(v)['id']
            link_attributes['s2_from'] = self.node(u)['s2_id']
            link_attributes['s2_to'] = self.node(v)['s2_id']
            link_attributes['length'] = attribs['length']

            # the rest of the keys are osm attributes
            link_attributes['attributes'] = {}
            for key, val in attribs.items():
                if key not in link_attributes:
                    link_attributes['attributes']['osm:way:{}'.format(key)] = {
                            'name': 'osm:way:{}'.format(key),
                            'class': 'java.lang.String',
                            'text': str(val),
                        }

            self.add_edge(u, v, attribs=link_attributes, silent=True)

        logging.info('Deleting isolated nodes which have no edges.')
        self.remove_nodes(list(nx.isolates(self.graph)), silent=True)

    def read_matsim_network(self, path):
        self.graph, self.link_id_mapping, duplicated_nodes, duplicated_links = \
            matsim_reader.read_network(path, self.transformer)
        self.graph.graph['name'] = 'Network graph'
        self.graph.graph['crs'] = {'init': self.epsg}

        for node_id, duplicated_node_attribs in duplicated_nodes.items():
            for duplicated_node_attrib in duplicated_node_attribs:
                self.change_log.remove(
                    object_type='node',
                    object_id=node_id,
                    object_attributes=duplicated_node_attrib
                )
        for link_id, reindexed_duplicated_links in duplicated_links.items():
            for duplicated_link in reindexed_duplicated_links:
                self.change_log.modify(
                    object_type='link',
                    old_id=link_id,
                    old_attributes=self.link(duplicated_link),
                    new_id=duplicated_link,
                    new_attributes=self.link(duplicated_link)
                )

    def read_matsim_schedule(self, path):
        self.schedule.read_matsim_schedule(path)

    def write_to_matsim(self, output_dir):
        persistence.ensure_dir(output_dir)
        matsim_xml_writer.write_matsim_network(output_dir, self)
        if self.schedule:
            self.schedule.write_to_matsim(output_dir)
        self.change_log.export(os.path.join(output_dir, 'change_log.csv'))
        geojson.save_nodes_and_links_geojson(self.graph, output_dir)
