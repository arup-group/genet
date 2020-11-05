import dictdiffer


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


def merge_complex_dictionaries(d1, d2):
    """
    Merges two dictionaries with where the values can be lists, sets or other dictionaries with the same behaviour.
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
