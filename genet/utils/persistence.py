import os
import logging


def ensure_dir(direc):
    if not os.path.exists(direc):
        try:
            os.makedirs(direc)
        except PermissionError as e:
            logging.warning(e)


def is_zip(path):
    return path.lower().endswith(".zip")


def set_nested_value(d: dict, value: dict):
    """
    Changes or, if not present injects, `different_value` into nested dictionary d at key `key: key_2`
    :param d: {key: {key_2: value, key_1: 1234}
    :param value: {key: {key_2: different_value}}
    :return:
    """
    if isinstance(value, dict):
        for k, v in value.items():
            if k in d:
                if isinstance(d[k], dict):
                    d[k] = set_nested_value(d[k], v)
                else:
                    d[k] = v
            else:
                d[k] = v
    else:
        d = value
    return d
