from genet.utils import parallel
from tests.fixtures import assert_semantically_equal


def test_split_list_returns_the_one_list_it_was_given_when_batch_size_is_bigger_than_the_size_of_the_list():
    list_to_be_partitioned = list(range(50))
    patitioned_list = parallel.split_list(list_to_be_partitioned, k=100)

    assert patitioned_list == [list_to_be_partitioned]


def test_split_list_returns_correctly_partitioned_lists():
    list_to_be_partitioned = list(range(10))
    patitioned_list = parallel.split_list(list_to_be_partitioned, k=3)

    assert patitioned_list == [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]]


def test_combine_list():
    combined_list = parallel.combine_list([[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]])
    assert combined_list == list(range(10))


def test_split_dict_returns_list_with_one_dict_it_was_given_when_batch_size_is_bigger_than_the_size_of_the_list():
    dict_to_be_partitioned = dict(zip(range(50), [str(2*i) for i in range(50)]))
    patitioned_list = parallel.split_dict(dict_to_be_partitioned, k=100)

    assert patitioned_list == [dict_to_be_partitioned]


def test_split_dict_returns_correctly_partitioned_lists():
    dict_to_be_partitioned = dict(zip(range(10), [str(2*i) for i in range(10)]))
    combined_list = parallel.split_dict(dict_to_be_partitioned, k=3)

    assert combined_list == [{0:'0', 1:'2', 2:'4'}, {3:'6', 4:'8', 5:'10'}, {6:'12', 7:'14', 8:'16'}, {9:'18'}]


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
