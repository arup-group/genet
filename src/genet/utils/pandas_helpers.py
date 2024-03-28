import pandas as pd
from numpy import ndarray


def notna(value):
    nn = pd.notna(value)
    if isinstance(nn, ndarray):
        return any(nn)
    return nn


def get_pandas_dtype(dict):
    pandas_dtype = object
    if dict:
        first_value = list(dict.values())[0]
        python_type = type(first_value)
        if python_type is int:
            pandas_dtype = pd.Int64Dtype.type
        if python_type is float:
            pandas_dtype = pd.Float64Dtype.type
    return pandas_dtype
