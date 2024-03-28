import pytest
from genet.validate.network import (
    Condition,
    FloatCondition,
    fractional_value,
    infinity_value,
    negative_value,
    none_condition,
    zero_value,
)


@pytest.mark.parametrize(
    ["value", "condition", "expected_result"],
    [
        ("0.00", zero_value, True),
        ("0.0", zero_value, True),
        ("zero", zero_value, False),
        ("-1", negative_value, True),
        ("non-negative", negative_value, False),
        ("-inf", infinity_value, True),
        ("inf", infinity_value, True),
        ("infinity", infinity_value, True),
        ("0.01", fractional_value, True),
        ("0.00", fractional_value, False),
    ],
)
def test_string_cases_for_float_conditions(value, condition, expected_result):
    assert FloatCondition(condition).evaluate(value) == expected_result


@pytest.mark.parametrize(
    ["value", "condition", "expected_result"],
    [("None", none_condition, True), (None, none_condition, True)],
)
def test_cases_for_none_conditions(value, condition, expected_result):
    assert Condition(condition).evaluate(value) == expected_result
