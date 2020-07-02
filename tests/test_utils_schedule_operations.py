from genet.utils import schedule_operations
from tests.fixtures import correct_schedule, test_schedule, assert_semantically_equal


def test_generate_validation_report_with_correct_schedule(correct_schedule):
    correct_report = {
        'schedule_level': {'is_valid_schedule': True, 'has_valid_services': True, 'invalid_services': []},
        'service_level': {'service': {'is_valid_service': True, 'has_valid_routes': True, 'invalid_routes': []}},
        'route_level': {'service': {'1': {'is_valid_route': True}, '2': {'is_valid_route': True}}}}
    report = schedule_operations.generate_validation_report(correct_schedule)
    assert_semantically_equal(report, correct_report)


def test_generate_validation_report_with_incorrect_schedule(test_schedule):
    correct_report = {
        'schedule_level': {'is_valid_schedule': False, 'has_valid_services': False, 'invalid_services': ['service']},
        'service_level': {'service': {'is_valid_service': False, 'has_valid_routes': False, 'invalid_routes': [0, 1]}},
        'route_level': {'service': [{'is_valid_route': False}, {'is_valid_route': False}]}}
    report = schedule_operations.generate_validation_report(test_schedule)
    assert_semantically_equal(report, correct_report)
