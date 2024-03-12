import logging
import multiprocessing as mp
from math import ceil
from typing import Callable, Union, overload


def split_list(_list: list, processes: int = 1) -> list[list]:
    """Partitions list into list of subsets of _list.

    Args:
        _list (list): Input list
        processes (int, optional): Number of processes to split data across. Defaults to 1.

    Returns:
        list: List of lists
    """
    k = ceil(len(_list) / processes)
    if len(_list) <= k:
        return [_list]
    else:
        n = int(len(_list) // k)
        l_partitioned = [_list[(k * i) : (k * (i + 1))] for i in range(n)]
        leftovers = _list[(k * n) :]
        if leftovers:
            l_partitioned.append(leftovers)
        logging.info("{} or {} batches of size {} ish".format(n, n + 1, k))
        return l_partitioned


def combine_list(list_list: list[list]) -> list:
    """Flattens list of lists into a single list.

    Args:
        list_list (list[list]): list of lists to flatten.

    Returns:
        list: Flattened list.
    """
    return_list = []
    for res in list_list:
        return_list.extend(res)
    return return_list


def split_dict(_dict: dict, processes: int = 1) -> list[dict]:
    """Partitions dict into list of subset dicts of _dict

    Args:
        _dict (dict): Input dictionary to split.
        processes (int, optional): _description. Defaults to 1.

    Returns:
        list[dict]: List of dictionaries.
    """
    k = ceil(len(_dict) / processes)
    if len(_dict) <= k:
        return [_dict]
    else:
        keys = list(_dict.keys())
        keys_partitioned = split_list(keys, processes=processes)
        return [{key: _dict[key] for key in keys_bunch} for keys_bunch in keys_partitioned]


def combine_dict(list_dict: list[dict]) -> dict:
    """Flattens list of dicts into a single dict.

    Args:
        list_dict (list[dict]): list of dicts to flatten.

    Returns:
        dict: Flattened dict.
    """
    return_dict = {}
    for res in list_dict:
        return_dict = {**return_dict, **res}
    return return_dict


@overload
def multiprocess_wrap(
    data: dict, split: Callable, apply: Callable, combine: Callable, processes: int = 1, **kwargs
) -> dict:
    "Dict in -> dict out"


@overload
def multiprocess_wrap(
    data: list, split: Callable, apply: Callable, combine: Callable, processes: int = 1, **kwargs
) -> list:
    "List in -> list out"


def multiprocess_wrap(
    data: Union[dict, list],
    split: Callable,
    apply: Callable,
    combine: Callable,
    processes: int = 1,
    **kwargs,
) -> Union[dict, list]:
    """Batch process data using a `split-apply-combine` approach.

    Results of all parallel processes are consolidated using the given `combine` function.

    Args:
        data (Union[dict, list]): Data the `apply` function expects, which will be partitioned by `split` function if the number of parallel `processes` > 1.
        split (Callable):
            Function which partitions `data` into list of batches of same type as `data` to be processed in parallel.
            `processes` argument must be greater than 1 if you want data to be split.
        apply (Callable): Function that expects `data` or a subset of it (if `data` has been split).
        combine (Callable):
            Function which expects a list of the returns of function `apply` and combines it back into what `apply` would have returned if it had been run in a single process.
        processes (int, optional): Max number of processes to use for computations. Defaults to 1.

    Keyword Args: will be passed to the `apply` function.

    Returns:
        Union[dict, list]: output of the `apply` (+ optionally `combine`) function.
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
