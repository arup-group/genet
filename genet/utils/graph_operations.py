from typing import Union, Dict, Callable, Iterable
from anytree import Node, RenderTree
import pandas as pd
import logging
from copy import deepcopy
from pyproj import Proj, Transformer
from genet.utils import spatial


class Filter():
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
            ],
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
    Returns all data stored under key in attribute dictionaries for interators yielding (index, attribute_dictionary),
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
    spatially.
    :param left: genet.core.Network
    :param right: genet.core.Network that needs to be updated to match left network
    :return: updated right
    """
    # right will change projection to left's if not the same
    # only the nodes hold spatial information and only the ones that dont exist in
    # left will need to be reprojected, we will use nx.compose to combine the graphs and the
    # left.graph will impose it's data on right.graph
    # find spatially overlapping nodes by extracting all of the s2_ids from right
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
    # combine spatial info on nodes in left and right into a dataframe
    s2_id_df = pd.DataFrame(s2_ids_right).reset_index().merge(
        pd.DataFrame(s2_ids_left).reset_index(), on='s2_id', how='outer')

    # update the data dict of those nodes which overlap
    [right.apply_attributes_to_node(s2_id_df.loc[idx, 'right'], left.node(s2_id_df.loc[idx, 'left']))
     for idx in s2_id_df.dropna().index]
    # change x,y coordinates for right nodes if the projections dont match
    if left.epsg != right.epsg:
        logging.info('Adding two Networks with different projections may require less strict spatial matching.'
                     'Please check where your networks overlap for duplication of nodes and edges.')
        transformer = Transformer.from_proj(Proj(init=right.epsg), Proj(init=left.epsg))
        # re-project the rest of right's nodes if do not match
        for idx in s2_id_df[s2_id_df['left'].isna()].index:
            node_attribs = deepcopy(right.node(s2_id_df.loc[idx, 'right']))
            node_attribs['x'], node_attribs['y'] = spatial.change_proj(
                node_attribs['x'], node_attribs['y'], transformer)
            right.apply_attributes_to_node(s2_id_df.loc[idx, 'right'], node_attribs)

    # check uniqueness of the node indices that are left in right
    clashing_right_node_ids = \
        set(s2_id_df[s2_id_df['left'].isna()]['right']) & set(s2_id_df['left'].dropna())
    if clashing_right_node_ids:
        # generate the index in left, otherwise the method could return one that is only unique in right
        [right.reindex_node(node, left.generate_index_for_node()) for node in clashing_right_node_ids]

    # finally change node ids for overlapping nodes
    # TODO check that a new index is not being generated if an index exists in reight but hasnt been overwritten yet
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
    def sort_and_hash(l):
        l.sort()
        return '_'.join(l)

    def extract_multindex(l, g):
        return g.link_id_mapping[l]['multi_edge_idx']

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

    # first resolve clashing link ids for links in right which don't exist in left
    clashing_right_link_ids = \
        set(df[df['left'].isna()]['link_id_right']) & set(df['link_id_left'].dropna())
    if clashing_right_link_ids:
        # generate the index in left, otherwise the method could return one that is only unique in right
        [right.reindex_link(link, left.generate_index_for_edge()) for link in clashing_right_link_ids]

    # TODO Impose link id and multi index if from left on right
    # TODO check that a new index is not being generated if an index exists in right but hasn't been overwritten yet

    logging.info('Finished consolidating link indexing between the two graphs')

    return right