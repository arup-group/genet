import logging
import multiprocessing as mp


def split_list(_list, k=3000):
    """
    Split type function. Partitions list into list of subsets of _list
    :param _list: any list
    :param k: batch size
    :return: list of lists
    """
    if len(_list) <= k:
        return [_list]
    else:
        n = len(_list) // k
        l_partitioned = [_list[(k * i):(k * (i + 1))] for i in range(n)]
        # leftovers
        l_partitioned.append(_list[(k * n):])
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


def split_dict(_dict, k=3000):
    """
    Split type function. Partitions dict into list of subset dicts of _dict
    :param _dict: any dict
    :param k: batch size
    :return: list of dicts
    """
    if len(_dict) <= k:
        return [_dict]
    else:
        keys = list(_dict.keys())
        keys_partitioned = split_list(keys, k=k)
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


def multiprocess_wrap(data, split, apply, combine, processes=1, shared_object=None, **kwargs):
    """
    Split up data into batches using `split` function and process in parallel using `apply(data, kwargs)` function,
    kwargs is a dictionary of arguments. Results of all parallel processes are consolidated using the given `combine`
    function.
    :param data: data the function expects, which should be partitioned by split function to be processed in parallel
    :param split: function which partitions `data` into list of bunches of same type as `data` to be processed in
    parallel
    :param apply: function that expects `data`, process to be applied to `data` in parallel
    :param combine: function which expects a list of the returns of function `apply` and combines it back into
    what `apply` would have returned if it had been ran in a single process
    :param processes: max number of processes to use for computations
    :param shared_object: key in the kwargs under which the object should not be copied across processes
    :param kwargs: that need to be passed to the function `apply` which remain constant across all data
    :return: output of the combine function
    """
    data_partitioned = split(data)

    pool = mp.Pool(processes=processes)

    if shared_object is not None:
        mgr = mp.Manager()
        ns = mgr.Namespace()
        ns.g = kwargs[shared_object]
        kwargs[shared_object] = ns

    results = [pool.apply_async(apply, (data_bunch,), kwargs) for data_bunch in data_partitioned]

    output = [p.get() for p in results]

    return combine(output)
