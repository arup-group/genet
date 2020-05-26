from pandas import NA
from genet.modify import ChangeLog


def compare_change_log_events(event, target):
    assert event['change_event'] == target['change_event']
    assert event['object_type'] == target['object_type']
    assert event['old_id'] == target['old_id']
    assert event['new_id'] == target['new_id']
    assert event['old_attributes'] == target['old_attributes']
    assert event['new_attributes'] == target['new_attributes']
    assert 'timestamp' in event


def test_change_log_records_adding_objects():
    log = ChangeLog()
    log.add('link', '1234', {'attrib': 'hey'})

    target = {'change_event': {0: 'add'},
              'object_type': {0: 'link'},
              'old_id': {0: NA},
              'new_id': {0: '1234'},
              'old_attributes': {0: NA},
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
              'new_id': {0: NA},
             'old_attributes': {0: "{'attrib': 'hey'}"},
              'new_attributes': {0: NA}}

    compare_change_log_events(log.log.to_dict(), target)
