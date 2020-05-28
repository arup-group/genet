from numpy import nan
import ast
from pandas.testing import assert_frame_equal
from tests.fixtures import *
from genet.modify import ChangeLog


def compare_change_log_events(event, target):
    assert event['change_event'] == target['change_event']
    assert event['object_type'] == target['object_type']
    assert event['old_id'] == target['old_id']
    assert event['new_id'] == target['new_id']
    for k, v in event['old_attributes'].items():
        assert k in target['old_attributes']
        if v is not None and target['old_attributes'][k] is not None:
            assert_semantically_equal(ast.literal_eval(v), ast.literal_eval(target['old_attributes'][k]))
    for k, v in event['new_attributes'].items():
        assert k in target['new_attributes']
        if v is not None and target['new_attributes'][k] is not None:
            assert_semantically_equal(ast.literal_eval(v), ast.literal_eval(target['new_attributes'][k]))
    assert 'timestamp' in event


def test_change_log_records_adding_objects():
    log = ChangeLog()
    log.add('link', '1234', {'attrib': 'hey'})

    target = {'change_event': {0: 'add'},
              'object_type': {0: 'link'},
              'old_id': {0: None},
              'new_id': {0: '1234'},
              'old_attributes': {0: None},
              'new_attributes': {0: "{'attrib': 'hey'}"}}

    compare_change_log_events(log.log.to_dict(), target)


def test_change_log_records_modifying_objects():
    log = ChangeLog()
    log.modify('link', '1234', {'attrib': 'old'}, '1234', {'attrib': 'new'})

    target = {'change_event': {0: 'modify'},
              'object_type': {0: 'link'},
              'old_id': {0: '1234'},
              'new_id': {0: '1234'},
              'old_attributes': {0: "{'attrib': 'old'}"},
              'new_attributes': {0: "{'attrib': 'new'}"}}

    compare_change_log_events(log.log.to_dict(), target)


def test_change_log_records_removing_objects():
    log = ChangeLog()
    log.remove('link', '1234', {'attrib': 'hey'})

    target = {'change_event': {0: 'remove'},
              'object_type': {0: 'link'},
              'old_id': {0: '1234'},
              'new_id': {0: None},
             'old_attributes': {0: "{'attrib': 'hey'}"},
              'new_attributes': {0: None}}

    compare_change_log_events(log.log.to_dict(), target)
