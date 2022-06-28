import pytest
from genet.utils.java_dtypes import *


def test_mapping_java_array_to_python_type():
    assert java_to_python_dtype('java.lang.Array') == list


def test_mapping_java_bool_to_python_type():
    assert java_to_python_dtype('java.lang.Boolean') == bool


def test_mapping_java_double_to_python_type():
    assert java_to_python_dtype('java.lang.Double') == float


def test_mapping_java_long_to_python_type():
    assert java_to_python_dtype('java.lang.Long') == float


def test_mapping_java_float_to_python_type():
    assert java_to_python_dtype('java.lang.Float') == float


def test_mapping_java_integer_to_python_type():
    assert java_to_python_dtype('java.lang.Integer') == int


def test_mapping_java_byte_to_python_type():
    assert java_to_python_dtype('java.lang.Byte') == int


def test_mapping_java_short_to_python_type():
    assert java_to_python_dtype('java.lang.Short') == int


def test_mapping_java_char_to_python_type():
    assert java_to_python_dtype('java.lang.Char') == str


def test_mapping_java_string_to_python_type():
    assert java_to_python_dtype('java.lang.String') == str


def test_unknown_java_type_raises_exception():
    with pytest.raises(NotImplementedError) as error_info:
        java_to_python_dtype('java.lang.UnknownType')
    assert "java.lang.UnknownType is not understood" in str(error_info.value)


def test_mapping_list_to_java_lang_string():
    assert python_to_java_dtype(list) == 'java.lang.Array'


def test_mapping_set_to_java_lang_string():
    assert python_to_java_dtype(set) == 'java.lang.Array'


def test_mapping_bool_to_java_lang_string():
    assert python_to_java_dtype(bool) == 'java.lang.Boolean'


def test_mapping_float_to_java_lang_string():
    assert python_to_java_dtype(float) == 'java.lang.Float'


def test_mapping_int_to_java_lang_string():
    assert python_to_java_dtype(int) == 'java.lang.Integer'


def test_mapping_str_to_java_lang_string():
    assert python_to_java_dtype(str) == 'java.lang.String'


def test_unknown_python_type_raises_exception():
    with pytest.raises(NotImplementedError) as error_info:
        python_to_java_dtype('lol')
    assert "lol is not recognised" in str(error_info.value)
