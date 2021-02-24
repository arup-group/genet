import pytest
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


def test_merging_dicts_with_lists_with_overlapping_values_returns_list_with_unique_values():
    d = dict_support.merge_complex_dictionaries({'1': ['2'], '2': []}, {'3': ['1'], '1': ['2']})

    assert_semantically_equal(d, {'1': ['2'], '2': [], '3': ['1']})


def test_merging_dicts_with_lists_when_one_dict_is_empty():
    d = dict_support.merge_complex_dictionaries({'1': [''], '2': []}, {})

    assert_semantically_equal(d, {'1': [''], '2': []})
