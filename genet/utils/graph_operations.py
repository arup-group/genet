from typing import Union, Dict, Callable, Iterable
from anytree import Node, RenderTree
import pandas as pd
import logging
from itertools import count, filterfalse


class Filter:
    """
    Helps filtering on specified attributes

    Parameters
    ----------
    :param conditions
    Dictionary of (or list of such dictionaries)
    key = edge attribute key
    value = either another key, if the edge data is nested or the target condition for what the value should be. That
     is:
    - single value, string, int, float, where the edge_data[key] == value
    - list of single values as above, where edge_data[key] in list(value1, value2)
    - for int or float values, two-tuple bound (lower_bound, upper_bound) where
      lower_bound <= edge_data[key] <= upper_bound
    - function that returns a boolean given the value e.g.

    def below_exclusive_upper_bound(value):
        return value < 100

    :param how : {all, any}, default any
    The level of rigour used to match conditions

    * all: means all conditions need to be met
    * any: means at least one condition needs to be met
    """

    def __init__(
            self,
            conditions: Union[
                list,
                Dict[str, Union[dict, Union[str, int, float], list, Callable[[str, int, float], bool]]]
            ] = None,
            how=any):
        self.conditions = conditions
        self.how = how

    def satisfies_conditions(self, data_dict):
        if isinstance(self.conditions, list):
            conditions_satisfied = []
            for condition in self.conditions:
                conditions_satisfied.append(self.evaluate_condition(condition, data_dict))
            return self.how(conditions_satisfied)
        elif isinstance(self.conditions, dict):
            return self.evaluate_condition(self.conditions, data_dict)
        elif self.conditions is None:
            return True

    def evaluate_condition(self, condition, data_dict):
        satisfies = False
        for key, val in condition.items():
            if key in data_dict:
                if isinstance(val, dict):
                    # keep going
                    satisfies = self.evaluate_condition(val, data_dict[key])
                elif isinstance(val, (int, float, str)):
                    # value is that value
                    satisfies = data_dict[key] == val
                elif isinstance(val, list):
                    # value is one of the items in the list
                    satisfies = data_dict[key] in val
                elif isinstance(val, tuple):
                    # value is within the bound
                    assert len(val) == 2, 'Tuple defining the bound has to be a two-tuple: (lower_bound, upper_bound)'
                    satisfies = data_dict[key] >= val[0] and data_dict[key] <= val[1]
                elif callable(val):
                    # value is a function of data_dict[key] that returns a bool
                    satisfies = val(data_dict[key])
        return satisfies


def extract_links_on_edge_attributes(network, conditions: Union[list, dict], how=any):
    """
    Extracts graph links based on values of attributes saved on the edges. Fails silently,
    assumes not all edges have those attributes.
    :param network: genet.core.Network object
    :param conditions: {'attribute_key': 'target_value'} or nested
    {'attribute_key': {'another_key': {'yet_another_key': 'target_value'}}}, where 'target_value' could be

    - single value, string, int, float, where the edge_data[key] == value
    - list of single values as above, where edge_data[key] in list(value1, value2)
    - for int or float values, two-tuple bound (lower_bound, upper_bound) where
      lower_bound <= edge_data[key] <= upper_bound
    - function that returns a boolean given the value e.g.

    def below_exclusive_upper_bound(value):
        return value < 100

    :param how: {all, any}, default any
    How to subset the graph if more than one condition is specified in values_to_subset_on

    * all: means all conditions need to be met
    * any: means at least one condition needs to be met
    :return: list of link ids of the input network
    """
    filter = Filter(conditions, how)
    return [link_id for link_id, link_attribs in network.links() if filter.satisfies_conditions(link_attribs)]


def extract_nodes_on_node_attributes(network, conditions: Union[list, dict], how=any):
    """
    Extracts graph nodes based on values of attributes saved on the nodes. Fails silently,
    assumes not all nodes have all of the attributes.
    :param network: genet.core.Network object
    :param conditions: {'attribute_key': 'target_value'} or nested
    {'attribute_key': {'another_key': {'yet_another_key': 'target_value'}}}, where 'target_value' could be

    - single value, string, int, float, where the node_data[key] == value
    - list of single values as above, where node_data[key] in list(value1, value2)
    - for int or float values, two-tuple bound (lower_bound, upper_bound) where
      lower_bound <= node_data[key] <= upper_bound
    - function that returns a boolean given the value e.g.

    def below_exclusive_upper_bound(value):
        return value < 100

    :param how: {all, any}, default any
    How to subset the graph if more than one condition is specified in values_to_subset_on

    * all: means all conditions need to be met
    * any: means at least one condition needs to be met
    :return: list of node ids of the input network
    """
    filter = Filter(conditions, how)
    return [node_id for node_id, node_attribs in network.nodes() if filter.satisfies_conditions(node_attribs)]


def get_attribute_schema(iterator, data=False):
    def get_identical_twin_if_exists(parent, name_of_node_to_be):
        for child in parent.children:
            if name_of_node_to_be == child.name:
                return child
        return None

    def append_to_tree(d: dict, parent):
        for k, v in d.items():
            twin = get_identical_twin_if_exists(parent, k)
            if isinstance(v, dict):
                if not twin:
                    twin = Node(k, parent=parent)
                append_to_tree(v, twin)
            elif not twin:
                if data:
                    if isinstance(v, list):
                        values = set(v)
                    else:
                        values = {v}
                    Node(k, parent=parent, values=values)
                else:
                    Node(k, parent=parent)
            elif data:
                node = get_identical_twin_if_exists(parent, k)
                if isinstance(v, list):
                    values = set(v)
                else:
                    values = {v}
                node.values = node.values | values

    root = Node('attribute')

    for _id, _attribs in iterator:
        append_to_tree(_attribs, root)

    return root


def render_tree(root, data=False):
    for pre, fill, node in RenderTree(root):
        if hasattr(node, 'values') and data:
            print("%s%s: %s" % (pre, node.name, list(node.values)[:5]))
        else:
            print("%s%s" % (pre, node.name))


def get_attribute_data_under_key(iterator: Iterable, key: Union[str, dict]):
    """
    Returns all data stored under key in attribute dictionaries for iterators yielding (index, attribute_dictionary),
    inherits index from the iterator.
    :param iterator: list or iterator yielding (index, attribute_dictionary)
    :param key: either a string e.g. 'modes', or if accessing nested information, a dictionary
        e.g. {'attributes': {'osm:way:name': 'text'}}
    :return: dictionary where keys are indicies and values are data stored under the key
    """

    def get_the_data(attributes, key):
        if isinstance(key, dict):
            for k, v in key.items():
                if k in attributes:
                    if isinstance(v, dict):
                        get_the_data(attributes[k], v)
                    else:
                        data[_id] = attributes[k][v]
        else:
            if key in attributes:
                data[_id] = attributes[key]

    data = {}

    for _id, _attribs in iterator:
        get_the_data(_attribs, key)

    return data


def consolidate_node_indices(left, right):
    """
    Changes the node indexing in right to match left spatially and resolves clashing node ids if they don't match
    spatially. The two networks need to be in matching coordinate systems.
    :param left: genet.core.Network
    :param right: genet.core.Network that needs to be updated to match left network
    :return: updated right
    """
    # find spatially overlapping nodes by extracting all of the s2 spatial ids from right
    s2_ids_right = right.node_attribute_data_under_key('s2_id')
    if len(s2_ids_right) != len(s2_ids_right.unique()):
        raise RuntimeError('There is more than one node in one place in the network you are trying to add')
    s2_ids_right.name = 's2_id'
    s2_ids_right.index = s2_ids_right.index.set_names(['right'])
    s2_ids_left = left.node_attribute_data_under_key('s2_id')
    # do the same for left
    if len(s2_ids_left) != len(s2_ids_left.unique()):
        raise RuntimeError('There is more than one node in one place in the network you are trying to add')
    s2_ids_left.name = 's2_id'
    s2_ids_left.index = s2_ids_left.index.set_names(['left'])
    # combine spatial info on nodes in left and right into a dataframe, join on s2 ids
    s2_id_df = pd.DataFrame(s2_ids_right).reset_index().merge(
        pd.DataFrame(s2_ids_left).reset_index(), on='s2_id', how='outer')

    # check uniqueness of the node indices that are left in right
    clashing_right_node_ids = \
        set(s2_id_df[s2_id_df['left'].isna()]['right']) & set(s2_id_df['left'].dropna())
    if clashing_right_node_ids:
        # generate the index avoiding indices from left, that way they're unique across both graphs
        [right.reindex_node(node, right.generate_index_for_node([i for i, a in left.nodes()])) for node in
         clashing_right_node_ids]

    # finally change node ids for overlapping nodes
    # TODO check that a new index is not being generated if an index exists in right but hasnt been overwritten yet
    [right.reindex_node(s2_id_df.loc[idx, 'right'], s2_id_df.loc[idx, 'left'])
     for idx in s2_id_df.dropna()[s2_id_df['right'] != s2_id_df['left']].index]
    logging.info('Finished consolidating node indexing between the two graphs')
    return right


def consolidate_link_indices(left, right):
    """
    Changes the link indexing in right to match left on modes stored on the links and resolves clashing link ids if
    they don't match. This method assumes that the node ids of left vs right have already been consolidated (see
    the method above with consolidates node ids)
    :param left: genet.core.Network
    :param right: genet.core.Network that needs to be updated to match left network
    :return: updated right
    """

    def sort_and_hash(modes_list):
        modes_list.sort()
        return '_'.join(modes_list)

    def extract_multindex(link_id, graph):
        return graph.link_id_mapping[link_id]['multi_edge_idx']

    def get_edges_with_clashing_ids(group):
        if ((group.dropna()['link_id_right'] != group.dropna()['link_id_left']) | (
                group.dropna()['multi_idx_right'] != group.dropna()['multi_idx_left'])).any():
            return group
        elif group.dropna().empty:
            clashing_multi_idx = set(group['multi_idx_right'].dropna()) & set(group['multi_idx_left'].dropna())
            if clashing_multi_idx:
                return group

    def append_data_to_overlapping_links_data(row):
        if not row.empty:
            overlapping_links_data[row['link_id_left']] = right.link(row['link_id_right'])

    def append_data_to_unique_clashing_links_data(row):
        if not row.empty:
            unique_clashing_links_data[row['link_id_right']] = right.link(row['link_id_right'])

    # Now consolidate link ids, we do a similar dataframe join as for nodes but on edge data and nodes the edges
    # connect instead of spatial
    left_df = left.link_attribute_data_under_keys(['modes', 'from', 'to', 'id'], index_name='left')
    # extract multi index and hash modes
    left_df['multi_idx'] = left_df['id'].apply(lambda x: extract_multindex(x, left))
    left_df['modes'] = left_df['modes'].apply(lambda x: sort_and_hash(x))
    left_df = left_df.rename(columns={'id': 'link_id'})
    right_df = right.link_attribute_data_under_keys(['modes', 'from', 'to', 'id'], index_name='right')
    # extract multi index and hash modes
    right_df['multi_idx'] = right_df['id'].apply(lambda x: extract_multindex(x, right))
    right_df['modes'] = right_df['modes'].apply(lambda x: sort_and_hash(x))
    right_df = right_df.rename(columns={'id': 'link_id'})

    df = left_df.reset_index().merge(right_df.reset_index(), on=['modes', 'from', 'to'], how='outer',
                                     suffixes=('_left', '_right'))

    # In the dataframe above we have combined to compare edges which have the same from and to nodes and the same modes
    # on the edge. Remember these graphs have multi edges, there could be more than one edge between two nodes.
    # There are a few different scenarios here, if edges have found a match on mode, and nodes
    # - link ids match and multi indices match
    # - link ids match but the multi indices dont match
    # - link ids dont match but multi indices do match
    # - neither link ids or multi indices match, but the edge is the same in terms of mode and from/to nodes
    # Similarly, there are a few scenarios if the edges didn't find a match
    # - remaining (unmatched) link ids for edges in right are unique, don't clash with left,
    # they will remain as they are
    # - link ids clash with left

    # remove all edges that match and clash, we will re-add them later
    # this includes multiedges of edges that may have matched only one multiedge or no multi edges at all, i.e. the
    # graphs that multi edges that are completely separate but clash in the multi index
    # ---this is to consolidate the multindices across left and right
    clashing_overlapping_edges = df.groupby(['from', 'to']).apply(get_edges_with_clashing_ids).reset_index(drop=True)
    # store the edge data from right
    overlapping_links_data = {}
    unique_clashing_links_data = {}
    if not clashing_overlapping_edges.empty:
        clashing_overlapping_edges[clashing_overlapping_edges['link_id_right'].notna() & clashing_overlapping_edges[
            'link_id_left'].notna()].apply(
            lambda row: append_data_to_overlapping_links_data(row), axis=1)
        clashing_overlapping_edges[clashing_overlapping_edges['link_id_right'].notna() & clashing_overlapping_edges[
            'link_id_left'].isna()].apply(
            lambda row: append_data_to_unique_clashing_links_data(row), axis=1)

        right.remove_links(set(clashing_overlapping_edges['link_id_right'].dropna()), silent=True)

    # resolve clashing link ids for links in right which don't exist in left
    clashing_right_link_ids = set(df[df['left'].isna()]['link_id_right']) & set(df['link_id_left'].dropna())
    # some link ids could have been picked up before and deleted, only consider the ones which don't overlap
    clashing_right_link_ids = set(right.link_id_mapping.keys()) & clashing_right_link_ids
    if clashing_right_link_ids:
        # generate the index avoiding indices from left, that way they're unique across both graphs
        [right.reindex_link(link, right.generate_index_for_edge(set(left.link_id_mapping.keys()))) for link in
         clashing_right_link_ids]

    # Impose link id and multi index if from left on right, basically add the links we deleted from right but using
    # left's indexing, keep the data from right using the dictionaries where we saved them
    for left_link_id, data in overlapping_links_data.items():
        u, v = left.link_id_mapping[left_link_id]['from'], left.link_id_mapping[left_link_id]['to']
        multi_idx = left.link_id_mapping[left_link_id]['multi_edge_idx']
        right.add_link(left_link_id, u, v, multi_idx, data, silent=True)

    for right_link_id, data in unique_clashing_links_data.items():
        u, v = data['from'], data['to']
        # generate unique multi index, unique in both left and right
        right_multi_idx = set()
        if right.graph.has_edge(u, v):
            right_multi_idx = set(right.graph[u][v].keys())
        left_multi_idx = set()
        if left.graph.has_edge(u, v):
            left_multi_idx = set(left.graph[u][v].keys())
        existing_multi_edge_ids = right_multi_idx | left_multi_idx
        multi_idx = next(filterfalse(set(existing_multi_edge_ids).__contains__, count(1)))
        if right_link_id in set(left.link_id_mapping.keys()) | set(right.link_id_mapping.keys()):
            right_link_id = right.generate_index_for_edge(set(left.link_id_mapping.keys()))
        right.add_link(right_link_id, u, v, multi_idx, data, silent=True)

    logging.info('Finished consolidating link indexing between the two graphs')
    return right


def convert_list_of_link_ids_to_network_nodes(network, link_ids: list):
    """
    Extracts nodes corresponding to link ids in the order of given link_ids list. Useful for extracting network routes.
    :param network:
    :param link_ids:
    :return:
    """
    paths = []
    connected_path = []
    for link_id in link_ids:
        x, y = network.link_id_mapping[link_id]['from'], network.link_id_mapping[link_id]['to']
        if not connected_path:
            connected_path = [x, y]
        elif connected_path[-1] != x:
            paths.append(connected_path)
            connected_path = [x, y]
        else:
            connected_path.append(y)
    paths.append(connected_path)
    return paths


def find_shortest_path_link(link_attribute_dictionary, modes=None):
    """
    Finds link that is deemed quickest if freespeed present. Relies on (link) id being stored on edge data (default
    if using genet Network's `add_link` or `add_edge` methods or reading data using genet's Network methods.)
    Throws a `RuntimeError` if a link id is not found.
    :param link_attribute_dictionary: {multi_index_id: {'length': 10}}
    :param modes: optional, if passed and there are more than one possible edge that has the same length and speed,
    will also check if there is a link with modes that match exactly with `modes`.
    :return:
    """
    selected_link = None
    if len(link_attribute_dictionary) > 1:
        # check if any link is better than the other
        if modes:
            for multi_idx, attribs in link_attribute_dictionary.items():
                if 'modes' in attribs:
                    if isinstance(modes, str):
                        modes = [modes]
                    if set(attribs['modes']) == set(modes):
                        selected_link = attribs['id']
        if selected_link is None:
            current_freespeed = None
            for multi_idx, attribs in link_attribute_dictionary.items():
                if 'freespeed' in attribs:
                    if current_freespeed is None:
                        current_freespeed = attribs['freespeed']
                        selected_link = attribs['id']
                    elif attribs['freespeed'] > current_freespeed:
                        current_freespeed = attribs['freespeed']
                        selected_link = attribs['id']
    else:
        selected_link = link_attribute_dictionary[list(link_attribute_dictionary.keys())[0]]['id']
    if selected_link is None:
        raise RuntimeError('Failed to find suitable link_id for shortest path')
    else:
        return selected_link
