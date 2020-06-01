from typing import Union, Dict, Callable


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

    :param how : {'all', 'any'}, default 'any'
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
            how='any'):
        self.conditions = conditions
        self.how = how

    def satisfies_conditions(self, data_dict):
        if isinstance(self.conditions, list):
            conditions_satisfied = []
            for condition in self.conditions:
                conditions_satisfied.append(self.evaluate_condition(condition, data_dict))
            if self.how == 'any':
                return any(conditions_satisfied)
            elif self.how == 'all':
                return all(conditions_satisfied)
            else:
                raise RuntimeError('You need to specify the \'how\' attribute to be either \'any\' or \'all\'.')
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


def extract_links_on_edge_attributes(network, conditions: Union[list, dict], how='any'):
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

    :param how: {'all', 'any'}, default 'any'
    How to subset the graph if more than one condition is specified in values_to_subset_on

    * all: means all conditions need to be met
    * any: means at least one condition needs to be met
    :return: list of link ids of the input network
    """
    filter = Filter(conditions, how)

    link_ids_to_return = []
    for link_id, link_attribs in network.links():
        a = filter.satisfies_conditions(link_attribs)
        if a:
            link_ids_to_return.append(link_id)

    return link_ids_to_return


def extract_nodes_on_node_attributes(network, conditions: Union[list, dict], how='any'):
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

    :param how: {'all', 'any'}, default 'any'
    How to subset the graph if more than one condition is specified in values_to_subset_on

    * all: means all conditions need to be met
    * any: means at least one condition needs to be met
    :return: list of node ids of the input network
    """
    filter = Filter(conditions, how)

    node_ids_to_return = []
    for node_id, node_attribs in network.nodes():
        a = filter.satisfies_conditions(node_attribs)
        if a:
            node_ids_to_return.append(node_id)

    return node_ids_to_return
