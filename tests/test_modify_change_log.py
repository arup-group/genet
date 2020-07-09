import ast
from pandas.testing import assert_frame_equal
from pandas import DataFrame
from tests.fixtures import *
from genet.modify import ChangeLog


def test_change_log_records_adding_objects():
    log = ChangeLog()
    log.add('link', '1234', {'attrib': 'hey'})

    target = DataFrame({
        'change_event': {0: 'add'},
        'object_type': {0: 'link'},
        'old_id': {0: None},
        'new_id': {0: '1234'},
        'old_attributes': {0: None},
        'new_attributes': {0: "{'attrib': 'hey'}"},
        'diff': {0: [('add', '', [('attrib', 'hey')]), ('add', 'id', '1234')]}
    })

    cols_to_compare = ['change_event', 'object_type', 'old_id', 'new_id', 'old_attributes', 'new_attributes', 'diff']
    assert_frame_equal(log.log[cols_to_compare], target[cols_to_compare], check_dtype=False)


def test_change_log_records_adding_objects_in_bunch():
    log = ChangeLog()
    log.add_bunch('link', ['1234', '1235'], [{'attrib': 'hey'}, {'attrib': 'helloooo'}])

    target = DataFrame(
        {'timestamp': {0: '2020-07-09 09:56:05', 1: '2020-07-09 09:56:05'}, 'change_event': {0: 'add', 1: 'add'},
         'object_type': {0: 'link', 1: 'link'}, 'old_id': {0: None, 1: None}, 'new_id': {0: '1234', 1: '1235'},
         'old_attributes': {0: None, 1: None}, 'new_attributes': {0: "{'attrib': 'hey'}", 1: "{'attrib': 'helloooo'}"},
         'diff': {0: [('add', '', [('attrib', 'hey')]), ('add', 'id', '1234')],
                  1: [('add', '', [('attrib', 'helloooo')]), ('add', 'id', '1235')]}})

    cols_to_compare = ['change_event', 'object_type', 'old_id', 'new_id', 'old_attributes', 'new_attributes', 'diff']
    assert_frame_equal(log.log[cols_to_compare], target[cols_to_compare], check_dtype=False)


def test_change_log_records_modifying_objects():
    log = ChangeLog()
    log.modify('link', '1234', {'attrib': 'old'}, '1234', {'attrib': 'new'})

    target = DataFrame({
        'change_event': {0: 'modify'},
        'object_type': {0: 'link'},
        'old_id': {0: '1234'},
        'new_id': {0: '1234'},
        'old_attributes': {0: "{'attrib': 'old'}"},
        'new_attributes': {0: "{'attrib': 'new'}"},
        'diff': {0: [('change', 'attrib', ('old', 'new'))]}
    })

    cols_to_compare = ['change_event', 'object_type', 'old_id', 'new_id', 'old_attributes', 'new_attributes', 'diff']
    assert_frame_equal(log.log[cols_to_compare], target[cols_to_compare], check_dtype=False)


def test_change_log_records_removing_objects():
    log = ChangeLog()
    log.remove('link', '1234', {'attrib': 'hey'})

    target = DataFrame({
        'change_event': {0: 'remove'},
        'object_type': {0: 'link'},
        'old_id': {0: '1234'},
        'new_id': {0: None},
        'old_attributes': {0: "{'attrib': 'hey'}"},
        'new_attributes': {0: None},
        'diff': {0: [('remove', '', [('attrib', 'hey')]), ('remove', 'id', '1234')]}
    })

    cols_to_compare = ['change_event', 'object_type', 'old_id', 'new_id', 'old_attributes', 'new_attributes', 'diff']
    assert_frame_equal(log.log[cols_to_compare], target[cols_to_compare], check_dtype=False)
