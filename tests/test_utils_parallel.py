from genet.utils import parallel
from tests.fixtures import assert_semantically_equal


def test_split_list_returns_the_one_list_it_was_given_when_there_is_one_process():
    list_to_be_partitioned = list(range(50))
    patitioned_list = parallel.split_list(list_to_be_partitioned, processes=1)

    assert patitioned_list == [list_to_be_partitioned]


def test_split_list_returns_the_one_list_by_default():
    list_to_be_partitioned = list(range(50))
    patitioned_list = parallel.split_list(list_to_be_partitioned)

    assert patitioned_list == [list_to_be_partitioned]


def test_split_list_returns_correctly_partitioned_lists():
    list_to_be_partitioned = list(range(10))
    patitioned_list = parallel.split_list(list_to_be_partitioned, processes=3)

    assert patitioned_list == [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9]]


def test_combine_list():
    combined_list = parallel.combine_list([[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]])
    assert combined_list == list(range(10))


def test_split_dict_returns_list_with_one_dict_with_one_process():
    dict_to_be_partitioned = dict(zip(range(50), [str(2*i) for i in range(50)]))
    patitioned_dict = parallel.split_dict(dict_to_be_partitioned, processes=1)

    assert patitioned_dict == [dict_to_be_partitioned]


def test_split_dict_returns_correctly_partitioned_lists():
    dict_to_be_partitioned = dict(zip(range(10), [str(2*i) for i in range(10)]))
    patitioned_dict = parallel.split_dict(dict_to_be_partitioned, processes=3)

    assert patitioned_dict == [{0:'0', 1:'2', 2:'4', 3:'6'}, {4:'8', 5:'10', 6:'12', 7:'14'}, {8:'16', 9:'18'}]


def test_combine_dict():
    combined_list = parallel.combine_dict([{0:'0', 1:'2', 2:'4'}, {3:'6', 4:'8', 5:'10'}, {6:'12', 7:'14', 8:'16'}, {9:'18'}])
    assert_semantically_equal(combined_list, dict(zip(range(10), [str(2*i) for i in range(10)])))


def dict_to_list_function(dictionary, arg_1=1):
    return [i*arg_1 for i in list(dictionary.keys())]


def test_multiprocess_wrap_function_processing_dict_data():
    input = dict(zip(range(200), ['a']*200))

    output = parallel.multiprocess_wrap(data=input, split=parallel.split_dict, apply=dict_to_list_function,
                                        combine=parallel.combine_list, processes=1)
    assert output == list(range(200))


def test_multiprocess_wrap_function_processing_dict_data_with_kwargs():
    input = dict(zip(range(200), ['a']*200))

    output = parallel.multiprocess_wrap(data=input, split=parallel.split_dict, apply=dict_to_list_function,
                                        combine=parallel.combine_list, processes=1, arg_1=2)
    assert output == list(range(0, 400, 2))


def test_multiprocess_wrapping_with_processes_param():
    input = dict(zip(range(200), ['a']*200))

    output = parallel.multiprocess_wrap(data=input, split=parallel.split_dict, apply=dict_to_list_function,
                                        combine=parallel.combine_list, processes=2)
    assert output == list(range(0, 200))


def custom_simple_split_method(l):
    return [{i:v} for i, v in l.items()]


def test_multiprocess_wrapping_with_custom_simple_split_method():
    # i.e. doesnt rely on number of processes
    input = dict(zip(range(10), ['a']*10))

    output = parallel.multiprocess_wrap(data=input, split=custom_simple_split_method, apply=dict_to_list_function,
                                        combine=parallel.combine_list, processes=2)
    assert output == list(range(10))