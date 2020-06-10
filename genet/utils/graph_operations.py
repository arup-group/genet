from typing import Union, Dict, Callable, Iterable
from anytree import Node, RenderTree
import networkx as nx


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


def describe_graph_connectivity(G):
    """
    Computes dead ends and unreachable nodes in G. Computes strongly connected components of G
    :param G:
    :return:
    """
    dict_to_return = {}
    # find dead ends or unreachable nodes
    dict_to_return['problem_nodes'] = {}
    dict_to_return['problem_nodes']['dead_ends'] = []
    dict_to_return['problem_nodes']['unreachable_node'] = []
    for node in G.nodes:
        if (G.in_degree(node) == 0):
            dict_to_return['problem_nodes']['unreachable_node'].append(node)
        if (G.out_degree(node) == 0):
            dict_to_return['problem_nodes']['dead_ends'].append(node)

    # find connected subgraphs
    connected_subgraphs = list(nx.strongly_connected_components(G))
    dict_to_return['number_of_connected_subgraphs'] = len(connected_subgraphs)
    dict_to_return['connected_subgraphs'] = \
        [(list(c), len(c)) for c in sorted(nx.strongly_connected_components(G), key=len, reverse=True)]
    return dict_to_return
