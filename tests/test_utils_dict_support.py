import pytest
from copy import deepcopy
from pandas import DataFrame
import genet.utils.dict_support as dict_support
from tests.fixtures import assert_semantically_equal


def test_set_nested_value_overwrites_current_value():
    d = {'attributes': {'some_osm_tag': 'hello'}}
    value = {'attributes': {'some_osm_tag': 'bye'}}
    return_d = dict_support.set_nested_value(d, value)

    assert return_d == {'attributes': {'some_osm_tag': 'bye'}}


def test_set_nested_value_adds_new_key_val_pair():
    d = {'attributes': {'some_osm_tag': 'hello'}}
    value = {'attributes': {'some_tag': 'bye'}}
    return_d = dict_support.set_nested_value(d, value)

    assert return_d == {'attributes': {'some_osm_tag': 'hello', 'some_tag': 'bye'}}


def test_set_nested_value_creates_new_nest_in_place_of_single_value():
    d = {'attributes': 1}
    value = {'attributes': {'some_tag': 'bye'}}
    return_d = dict_support.set_nested_value(d, value)

    assert return_d == {'attributes': {'some_tag': 'bye'}}


def test_getting_nested_value_from_dictionary():
    d = {'1': {'2': {'3': {'4': 'hey'}}}}
    path = {'1': {'2': {'3': '4'}}}
    assert dict_support.get_nested_value(d, path) == 'hey'


def test_get_nested_value_throws_error_if_passed_incorrect_path():
    d = {'1': {'2': {'3': {'4': 'hey'}}}}
    path = {'1': {'2': {'3': '5'}}}
    with pytest.raises(KeyError) as e:
        dict_support.get_nested_value(d, path)
    assert '5' in str(e.value)


def test_finding_nested_path_on_condition():
    d = {'1': {'2': {'3': {'4': 'hey'}, '5': '6'}, '7': '8'}, '9': '10'}
    value = 'hey'
    assert dict_support.find_nested_paths_to_value(d, value) == [{'1': {'2': {'3': '4'}}}]


def test_finding_nested_path_on_condition_with_list():
    d = {'1': {'2': {'3': {'4': ['hey']}, '5': '6'}, '7': '8'}, '9': '10'}
    value = 'hey'
    assert dict_support.find_nested_paths_to_value(d, value) == [{'1': {'2': {'3': '4'}}}]


def test_finding_nested_path_on_set_condition_with_list():
    d = {'1': {'2': {'3': {'4': ['hey']}, '5': '6'}, '7': '8'}, '9': '10'}
    value = {'hey'}
    assert dict_support.find_nested_paths_to_value(d, value) == [{'1': {'2': {'3': '4'}}}]


def test_finding_multiple_nested_paths_on_condition():
    d = {'1': {'2': {'3': {'4': ['hey']}, '5': '6'}, '7': 'hey'}, '9': '10', '11': 'heyo'}
    value = {'hey', 'heyo'}
    assert dict_support.find_nested_paths_to_value(d, value) == [{'1': {'2': {'3': '4'}}}, {'1': '7'}, '11']


def test_nesting_at_leaf_with_some_value():
    d = {'1': {'2': {'3': {'4': 'hey'}}}}
    _d = dict_support.nest_at_leaf(d, 'some')
    assert d == {'1': {'2': {'3': {'4': {'hey': 'some'}}}}}
    assert _d == {'1': {'2': {'3': {'4': {'hey': 'some'}}}}}


def test_merging_simple_dictionaries():
    return_d = dict_support.merge_complex_dictionaries(
        {'a': 1, 'b': 3},
        {'b': 5, 'c': 8}
    )
    assert return_d == {'a': 1, 'b': 5, 'c': 8}


def test_merging_dictionaries_with_lists():
    return_d = dict_support.merge_complex_dictionaries(
        {'a': 1, 'b': [3, 6], 'c': [1]},
        {'b': [5], 'c': [8, 90]}
    )
    assert_semantically_equal(return_d, {'a': 1, 'b': [3, 6, 5], 'c': [1, 8, 90]})


def test_preserves_duplicates_in_input_list_when_merging_dictionaries():
    return_d = dict_support.merge_complex_dictionaries(
        {'b': [6, 6]},
        {'b': [5]}
    )
    assert_semantically_equal(return_d, {'b': [6, 6, 5]})


def test_preserves_resulting_duplicates_in_lists_when_merging_dictionaries():
    return_d = dict_support.merge_complex_dictionaries(
        {'b': [6]},
        {'b': [5, 6]}
    )
    assert_semantically_equal(return_d, {'b': [6, 5, 6]})


def test_preserves_lists_order_when_merging_dictionaries():
    return_d = dict_support.merge_complex_dictionaries(
        {'b': [1, 2]},
        {'b': [3, 4]}
    )
    assert_semantically_equal(return_d, {'b': [1, 2, 3, 4]})


def test_combines_sets_with_or_operator_when_merging_dictionaries():
    return_d = dict_support.merge_complex_dictionaries(
        {'b': {1, 2}},
        {'b': {2, 3}}
    )
    assert_semantically_equal(return_d, {'b': {1, 2, 3}})


def test_does_not_mutate_parameters_when_merging_complex_dictionaries():
    A = {
        'a': {1, 2},
        'b': [6, 6],
        'c': {
            'a': {1, 2},
            'b': [6, 6]
        },
        'd': 'hey'
    }
    B = {
        'a': {2, 3},
        'b': [5],
        'c': {
            'a': {2, 3},
            'b': [5]
        },
        'd': 'yo'
    }
    A_before = deepcopy(A)
    B_before = deepcopy(B)

    dict_support.merge_complex_dictionaries(A, B)

    assert_semantically_equal(A, A_before)
    assert_semantically_equal(B, B_before)


def test_merging_nested_dictionaries():
    return_d = dict_support.merge_complex_dictionaries(
        {'a': 1, 'b': {3: 5}, 'c': {1: 4}},
        {'b': {5: 3}, 'c': {8: 90}}
    )
    assert_semantically_equal(return_d, {'a': 1, 'b': {3: 5, 5: 3}, 'c': {1: 4, 8: 90}})


def test_merging_dictionaries_with_nested_lists():
    return_d = dict_support.merge_complex_dictionaries(
        {'a': 1, 'b': {'a': [3, 6]}, 'c': {'b': [1]}},
        {'b': {'a': [5]}, 'c': {'b': [8, 90]}}
    )
    assert_semantically_equal(return_d, {'a': 1, 'b': {'a': [3, 6, 5]}, 'c': {'b': [8, 90, 1]}})


def test_merging_dictionaries_with_nested_sets():
    return_d = dict_support.merge_complex_dictionaries(
        {'a': 1, 'b': {'a': {3, 6}}, 'c': {'b': {1}}},
        {'b': {'a': {5}}, 'c': {'b': {8, 90}}}
    )
    assert_semantically_equal(return_d, {'a': 1, 'b': {'a': {3, 6, 5}}, 'c': {'b': {8, 90, 1}}})


def test_merging_dicts_with_lists():
    d = dict_support.merge_complex_dictionaries({'1': [''], '2': []}, {'3': ['1'], '1': ['2']})

    assert_semantically_equal(d, {'1': ['', '2'], '2': [], '3': ['1']})


def test_merging_dicts_with_lists_when_one_dict_is_empty():
    d = dict_support.merge_complex_dictionaries({'1': [''], '2': []}, {})

    assert_semantically_equal(d, {'1': [''], '2': []})


def test_simple_dict_to_string():
    assert dict_support.dict_to_string({'simple': 'nest'}) == 'simple::nest'


def test_deeper_dict_to_string():
    assert dict_support.dict_to_string({'deeper': {'nested': 'dict'}}) == 'deeper::nested::dict'


def test_dataframe_to_dict_returns_dictionary_ignoring_nan_values():
    df = DataFrame(
        {
            'id' : [1,2,3],
            'value': ['6', float('nan'), 5]
        }
    )
    assert_semantically_equal(
        dict_support.dataframe_to_dict(df.T),
        {0: {'id': 1, 'value': '6'}, 1: {'id': 2}, 2: {'id': 3, 'value': 5}}
    )
