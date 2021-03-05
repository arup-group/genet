import pandas as pd
from numpy import ndarray
from typing import Union
import genet.utils.graph_operations as graph_operations


def set_nested_value(d: dict, value: dict):
    """
    Changes or, if not present injects, `different_value` into nested dictionary d at key `key: key_2`
    :param d: {key: {key_2: value, key_1: 1234}
    :param value: {key: {key_2: different_value}}
    :return:
    """
    if isinstance(value, dict):
        for k, v in value.items():
            if k in d:
                if isinstance(d[k], dict):
                    d[k] = set_nested_value(d[k], v)
                else:
                    d[k] = v
            else:
                d[k] = v
    else:
        d = value
    return d


def get_nested_value(d: dict, path: dict):
    """
    Retrieves value from nested dictionary
    :param d: {key: {key_2: {key_2_1: hey}, key_1: 1234}
    :param path: {key: {key_2: key_2_1}} path to take through the dictionary d
    :return: d[key][key_2][key_2_1]
    """
    if isinstance(path, dict):
        for k, v in path.items():
            if k in d:
                return get_nested_value(d[k], v)
            else:
                raise KeyError(f'Dictionary {d} does not have key {k}')
    else:
        return d[path]


def find_nested_paths_to_value(d: dict, value: Union[str, int, float, set, list]):
    def parse_node_path(node_path):
        n_path_names_reversed = list(reversed([n.name for n in node_path if n.name != 'attribute']))
        if len(n_path_names_reversed) == 1:
            return n_path_names_reversed[0]
        else:
            d = {n_path_names_reversed[1]: n_path_names_reversed[0]}
            for key in n_path_names_reversed[2:]:
                d = {key: d}
            return d

    if not isinstance(value, (list, set)):
        value = {value}
    elif not isinstance(value, set):
        value = set(value)
    paths = []
    schema = graph_operations.get_attribute_schema([('', d)], data=True)
    for node in schema.descendants:
        try:
            if node.values & value:
                paths.append(parse_node_path(node.path))
        except AttributeError:
            # that node does not have values
            pass
    return paths


def nest_at_leaf(d: dict, value):
    for k, v in d.items():
        if isinstance(v, dict):
            nest_at_leaf(v, value)
        else:
            d[k] = {v: value}
    return d


def merge_complex_dictionaries(d1, d2):
    """
    Merges two dictionaries where the values can be lists, sets or other dictionaries with the same behaviour.
    If values are not list, set or dict then d2 values prevail
    :param d1:
    :param d2:
    :return:
    """
    clashing_keys = set(d1) & set(d2)
    for key in clashing_keys:
        if isinstance(d1[key], dict) and isinstance(d2[key], dict):
            d1[key] = merge_complex_dictionaries(d1[key], d2[key])
        elif isinstance(d1[key], list) and isinstance(d2[key], list):
            d1[key] = list(set(d1[key]) | set(d2[key]))
        elif isinstance(d1[key], set) and isinstance(d2[key], set):
            d1[key] = d1[key] | d2[key]
        else:
            d1[key] = d2[key]
    for key in set(d2) - clashing_keys:
        d1[key] = d2[key]
    return d1


def combine_edge_data_lists(l1, l2):
    """
    Merges two lists where each elem is of the form (from_node, to_node, list)
    :param l1:
    :param l2:
    :return:
    """
    edges = merge_complex_dictionaries({(u, v): dat for u, v, dat in l1}, {(u, v): dat for u, v, dat in l2})
    return [(u, v, dat) for (u, v), dat in edges.items()]


def notna(value):
    nn = pd.notna(value)
    if isinstance(nn, ndarray):
        return any(nn)
    return nn
