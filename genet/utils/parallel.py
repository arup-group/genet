import logging
import multiprocessing as mp
from math import ceil


def split_list(_list, processes=1):
    """
    Split type function. Partitions list into list of subsets of _list
    :param _list: any list
    :param processes: number of processes to split data across, takes precedence over k to split data evenly over
    exactly the number of processes being used but is optional
    :return: list of lists
    """
    k = ceil(len(_list) / processes)
    if len(_list) <= k:
        return [_list]
    else:
        n = int(len(_list) // k)
        l_partitioned = [_list[(k * i):(k * (i + 1))] for i in range(n)]
        leftovers = _list[(k * n):]
        if leftovers:
            l_partitioned.append(leftovers)
        logging.info('{} or {} batches of size {} ish'.format(n, n + 1, k))
        return l_partitioned


def combine_list(list_list):
    """
    Combine type function. Combines list of lists into a single list
    :param list_list: list of lists
    :return: single list
    """
    return_list = []
    for res in list_list:
        return_list.extend(res)
    return return_list


def split_dict(_dict, processes=1):
    """
    Split type function. Partitions dict into list of subset dicts of _dict
    :param _dict: any dict
    :param processes: number of processes to split data across, takes precedence over k to split data evenly over
    exactly the number of processes being used but is optional
    :return: list of dicts
    """
    k = ceil(len(_dict) / processes)
    if len(_dict) <= k:
        return [_dict]
    else:
        keys = list(_dict.keys())
        keys_partitioned = split_list(keys, processes=processes)
        return [{key: _dict[key] for key in keys_bunch} for keys_bunch in keys_partitioned]


def combine_dict(list_dict):
    """
    Combine type function. Combines list of dicts into a single dict. Assumes keys don't clash
    :param list_dict: list of lists
    :return: single list
    """
    return_dict = {}
    for res in list_dict:
        return_dict = {**return_dict, **res}
    return return_dict


def multiprocess_wrap(data, split, apply, combine, processes=1, **kwargs):
    """
    Split up data into batches using `split` function and process in parallel using `apply(data, kwargs)` function,
    kwargs is a dictionary of arguments. Results of all parallel processes are consolidated using the given `combine`
    function.
    :param data: data the function expects, which should be partitioned by split function to be processed in parallel
    :param split: function which partitions `data` into list of bunches of same type as `data` to be processed in
    parallel. Include `processes` variable in this function if you want to use this variable for splitting data
    :param apply: function that expects `data`, process to be applied to `data` in parallel
    :param combine: function which expects a list of the returns of function `apply` and combines it back into
    what `apply` would have returned if it had been ran in a single process
    :param processes: max number of processes to use for computations
    :param kwargs: that need to be passed to the function `apply` which remain constant across all data
    :return: output of the combine function
    """
    if processes == 1:
        return apply(data, **kwargs)
    try:
        data_partitioned = split(data, processes=processes)
    except TypeError:
        data_partitioned = split(data)

    pool = mp.Pool(processes=processes)

    results = [pool.apply_async(apply, (data_bunch,), kwargs) for data_bunch in data_partitioned]

    output = [p.get() for p in results]

    return combine(output)
