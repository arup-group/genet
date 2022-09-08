import networkx as nx
import math
from dataclasses import dataclass, fields


def validate_attribute_data(attributes, necessary_attributes):
    missing_attribs = set(necessary_attributes) - set(attributes)
    if missing_attribs:
        raise AttributeError(f'Attributes: {missing_attribs} missing from data: {attributes}')


def find_problem_nodes(G):
    problem_nodes = {}
    problem_nodes['dead_ends'] = []
    problem_nodes['unreachable_node'] = []
    for node in G.nodes:
        if (G.in_degree(node) == 0):
            problem_nodes['unreachable_node'].append(node)
        if (G.out_degree(node) == 0):
            problem_nodes['dead_ends'].append(node)
    return problem_nodes


def find_connected_subgraphs(G):
    return [(list(c), len(c)) for c in sorted(nx.strongly_connected_components(G), key=len, reverse=True)]


def describe_graph_connectivity(G):
    """
    Computes dead ends and unreachable nodes in G. Computes strongly connected components of G
    :param G:
    :return:
    """
    dict_to_return = {}
    # find dead ends or unreachable nodes
    dict_to_return['problem_nodes'] = find_problem_nodes(G)
    # find number of connected subgraphs
    dict_to_return['number_of_connected_subgraphs'] = len(find_connected_subgraphs(G))
    return dict_to_return


def evaluate_condition_for_floatable(value, condition):
    try:
        value = float(value)
        return condition(value)
    except ValueError:
        return False


def zero_value(value):
    return value == 0.0


def negative_value(value):
    return value < 0.0


def infinity_value(value):
    return math.isinf(value)


def fractional_value(value):
    return 1.0 > value > 0.0


@dataclass()
class Condition:
    condition: callable

    def evaluate(self, value):
        return evaluate_condition_for_floatable(value, self.condition)


@dataclass()
class ConditionsToolbox:
    zero: Condition = Condition(zero_value)
    negative: Condition = Condition(negative_value)
    infinite: Condition = Condition(infinity_value)
    fractional: Condition = Condition(fractional_value)

    def condition_names(self) -> list:
        return [field.name for field in fields(self)]

    def get_condition_evaluator(self, condition: str) -> callable:
        if condition in self.__dict__:
            return self.__dict__[condition].evaluate
        else:
            raise NotImplementedError(f'Condition {condition} is not defined.')
