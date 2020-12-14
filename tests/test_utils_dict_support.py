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
