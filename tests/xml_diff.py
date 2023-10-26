import json
from collections import OrderedDict

import dictdiffer
import xmltodict


def deep_sort(obj):
    if isinstance(obj, dict):
        obj = OrderedDict(sorted(obj.items()))
        for k, v in obj.items():
            if isinstance(v, dict) or isinstance(v, list):
                obj[k] = deep_sort(v)

    if isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, dict) or isinstance(v, list):
                obj[i] = deep_sort(v)
        obj = sorted(obj, key=lambda x: json.dumps(x))

    return obj


def xml_diffs(xml_file_1, xml_file_2):
    dict_1 = deep_sort(xmltodict.parse(open(xml_file_1).read()))
    dict_2 = deep_sort(xmltodict.parse(open(xml_file_2).read()))

    return list(dictdiffer.diff(dict_1, dict_2, tolerance=0.001))


def parse_string_list(str):
    return str.split(",")


def is_list_string(str):
    return "," in str


def filter_diffs(diff_list, filter_func):
    removals = []
    for diff in diff_list:
        diff_type, node_location, diff_detail = diff
        if diff_type != "change":
            continue
        if filter_func(diff_detail[0], diff_detail[1]):
            removals.append(diff)
    return [diff for diff in diff_list if diff not in removals]


def is_list_ordering_difference(diff_element_1, diff_element_2):
    if is_list_string(diff_element_1) and is_list_string(diff_element_2):
        # are these two lists semantically equal, but ordered differently?
        first_list = parse_string_list(diff_element_1)
        second_list = parse_string_list(diff_element_2)
        if sorted(first_list) == sorted(second_list):
            return True
    return False


def is_permissible_numerical_difference(diff_element_1, diff_element_2, tolerance=0.0001):
    try:
        first_num = float(diff_element_1)
        second_num = float(diff_element_2)
    except ValueError:
        # you ain't no number, bruv!
        return False
    ordered_numbers = sorted([first_num, second_num])
    numerical_difference = ordered_numbers[1] - ordered_numbers[0]
    tolerance_value = ordered_numbers[0] * tolerance
    if numerical_difference <= tolerance_value:
        print(
            "Numerical difference of {} between {} and {} - ignoring because smaller than {} tolerance".format(
                numerical_difference, first_num, second_num, tolerance_value
            )
        )
        return True
    return False


def assert_semantically_equal(file_1_path, file_2_path):
    diffs = xml_diffs(file_1_path, file_2_path)
    if len(diffs) != 0:
        diffs = filter_diffs(diffs, is_list_ordering_difference)
    if len(diffs) != 0:
        diffs = filter_diffs(diffs, is_permissible_numerical_difference)
    if len(diffs) == 0:
        print("{} and {} are semantically equal".format(file_1_path, file_2_path))
        return True
    else:
        from pprint import PrettyPrinter

        PrettyPrinter().pprint(diffs)
        raise AssertionError(
            "{} and {} are NOT semantically equal".format(file_1_path, file_2_path)
        )
