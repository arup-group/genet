import logging
import multiprocessing as mp


def partition_list(_list, k=100):
    """
    Partitions list into list of subsets of l
    :param _list: any list
    :param k: batch size (number of items from the list)
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


def multiprocess_wrap_function_processing_dict_data(function, dict_data, processes=1, **kwargs):
    """
    Split up dict_data into batches and process in parallel using function(batch, kwargs),
    where kwargs is a dictionary of arguments
    :param function:
    :param dict_data:
    :param processes:
    :param kwargs:
    :return:
    """
    keys = list(dict_data.keys())
    keys_partitioned = partition_list(keys)

    pool = mp.Pool(processes=processes)

    results = [pool.apply_async(function, args=({key: dict_data[key] for key in keys_bunch}, kwargs)) for keys_bunch in
               keys_partitioned]
    output = [p.get() for p in results]

    return_list = []

    for res in output:
        return_list.extend(res)
    return return_list
