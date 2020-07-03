from genet.validate import schedule_validation
from tests.fixtures import correct_schedule, test_schedule, assert_semantically_equal


def test_generate_validation_report_with_correct_schedule(correct_schedule):
    correct_report = {
        'schedule_level': {'is_valid_schedule': True, 'invalid_stages': [], 'has_valid_services': True,
                           'invalid_services': []}, 'service_level': {
            'service': {'is_valid_service': True, 'invalid_stages': [], 'has_valid_routes': True,
                        'invalid_routes': []}}, 'route_level': {
            'service': {'1': {'is_valid_route': True, 'invalid_stages': []},
                        '2': {'is_valid_route': True, 'invalid_stages': []}}}}
    report = schedule_validation.generate_validation_report(correct_schedule)
    assert_semantically_equal(report, correct_report)


def test_generate_validation_report_with_incorrect_schedule(test_schedule):
    correct_report = {
        'schedule_level': {'is_valid_schedule': False,
                           'invalid_stages': ['has_valid_services', 'has_uniquely_indexed_services'],
                           'has_valid_services': False, 'invalid_services': ['service']}, 'service_level': {
            'service': {'is_valid_service': False,
                        'invalid_stages': ['has_valid_routes', 'has_uniquely_indexed_routes'],
                        'has_valid_routes': False, 'invalid_routes': [0, 1]}}, 'route_level': {'service': [
            {'is_valid_route': False,
             'invalid_stages': ['has_correctly_ordered_route', 'has_valid_offsets', 'has_self_loops']},
            {'is_valid_route': False,
             'invalid_stages': ['has_correctly_ordered_route', 'has_valid_offsets', 'has_self_loops']}]}}
    report = schedule_validation.generate_validation_report(test_schedule)
    assert_semantically_equal(report, correct_report)
