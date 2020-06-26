from genet.utils import parallel


def test_partition_list_returns_the_one_list_it_was_given_when_batch_size_is_bigger_than_the_size_of_the_list():
    list_to_be_partitioned = list(range(50))
    patitioned_list = parallel.partition_list(list_to_be_partitioned, k=100)

    assert patitioned_list == [list_to_be_partitioned]


def test_partition_list_returns_correctly_partitioned_lists():
    list_to_be_partitioned = list(range(10))
    patitioned_list = parallel.partition_list(list_to_be_partitioned, k=3)

    assert patitioned_list == [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]]


def dict_to_list_function(dictionary, arg_1=1):
    return [i*arg_1 for i in list(dictionary.keys())]


def test_multiprocess_wrap_function_processing_dict_data():
    input = dict(zip(range(200), ['a']*200))

    output = parallel.multiprocess_wrap_function_processing_dict_data(dict_to_list_function, input, processes=1)
    assert output == list(range(200))


def test_multiprocess_wrap_function_processing_dict_data_with_kwargs():
    input = dict(zip(range(200), ['a']*200))

    output = parallel.multiprocess_wrap_function_processing_dict_data(dict_to_list_function, input, processes=1, arg_1=2)
    assert output == list(range(0, 400, 2))
