import networkx as nx


def validate_link_data(link_attributes):
    assert 'id' in link_attributes
    assert 'from' in link_attributes
    assert 'to' in link_attributes
    assert 'length' in link_attributes
    assert 'freespeed' in link_attributes
    assert 'capacity' in link_attributes
    assert 'permlanes' in link_attributes
    assert 'oneway' in link_attributes
    assert 'modes' in link_attributes


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