import networkx as nx
import math


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


def get_link_attribute_validation_toolbox():
    return {
        'zero': zero_value,
        'negative': negative_value,
        'infinite': infinity_value,
        'fractional': fractional_value
    }


def zero_value(value):
    return value in {0, '0', '0.0'}


def negative_value(value):
    if isinstance(value, str):
        return '-' in value
    return value < 0


def infinity_value(value):
    if isinstance(value, str):
        return value in ['inf', '-inf']
    return math.isinf(value)


def fractional_value(value):
    if isinstance(value, str):
        return ('0.' in value) and (value != '0.0')
    return 1 > value > 0
