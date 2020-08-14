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


def test_merging_dicts_with_lists():
    d = dict_support.merge_dicts_with_lists({'1': [''], '2': []}, {'3': ['1'], '1': ['2']})

    assert_semantically_equal(d, {'1': ['', '2'], '2': [], '3': ['1']})


def test_merging_dicts_with_lists_with_overlapping_values_returns_list_with_unique_values():
    d = dict_support.merge_dicts_with_lists({'1': ['2'], '2': []}, {'3': ['1'], '1': ['2']})

    assert_semantically_equal(d, {'1': ['2'], '2': [], '3': ['1']})


def test_merging_dicts_with_lists_when_one_dict_is_empty():
    d = dict_support.merge_dicts_with_lists({'1': [''], '2': []}, {})

    assert_semantically_equal(d, {'1': [''], '2': []})
