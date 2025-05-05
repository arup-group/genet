from pandas import Float64Dtype, Int64Dtype

from genet.utils import pandas_helpers


def test_uses_object_dtype_for_empty_dictionary():
    dtype = pandas_helpers.get_pandas_dtype({})
    assert dtype is object


def test_uses_int64_dtype_for_dictionary_with_integral_values():
    dtype = pandas_helpers.get_pandas_dtype({"number": 42})
    assert dtype is Int64Dtype.type


def test_uses_float64_dtype_for_dictionary_with_floating_point_values():
    dtype = pandas_helpers.get_pandas_dtype({"number": 42.42})
    assert dtype is Float64Dtype.type


def test_uses_object_dtype_for_dictionary_with_list_values():
    dtype = pandas_helpers.get_pandas_dtype({"numbers": [42, 101, -1]})
    assert dtype is object
