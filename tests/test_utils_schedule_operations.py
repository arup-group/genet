from genet.utils import schedule_operations
from tests.fixtures import schedule_object_from_test_data, assert_semantically_equal


def test_generate_validation_report(schedule_object_from_test_data):
    correct_report = {
        'schedule_level': {'is_valid': True, 'has_valid_services': True, 'invalid_services': []},
        'service_level': {'10314': {'is_valid': True, 'has_valid_routes': True, 'invalid_routes': []}},
        'route_level': {'10314': {'VJbd8660f05fe6f744e58a66ae12bd66acbca88b98': {'is_valid_route': True}}}}
    report = schedule_operations.generate_validation_report(schedule_object_from_test_data)
    assert_semantically_equal(report, correct_report)
