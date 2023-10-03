import logging
import os
import shutil
from pathlib import Path
from typing import Union


def ensure_dir(direc):
    if not os.path.exists(direc):
        try:
            os.makedirs(direc)
        except PermissionError as e:
            logging.warning(e)


def setify(value: Union[str, list, set]):
    if isinstance(value, (str, int, float)):
        return {value}
    elif isinstance(value, (list, set)):
        return set(value)
    elif value is None:
        return set()
    else:
        raise NotImplementedError(f"Value: {value} cannot be setified")


def listify(value: Union[str, list, set]):
    if isinstance(value, str):
        return [value]
    elif isinstance(value, (list, set)):
        return list(value)
    elif value is None:
        return []


def is_yml(path: Union[Path, str]):
    return Path(path).suffix.lower() in [".yml", ".yaml"]


def is_geojson(path: Union[Path, str]):
    return Path(path).suffix.lower() == ".geojson"


def is_csv(path: Union[Path, str]):
    return Path(path).suffix.lower() == ".csv"


def is_json(path: Union[Path, str]):
    return Path(path).suffix.lower() == ".json"


def is_zip(path: Union[Path, str]):
    return Path(path).suffix.lower() == ".zip"


def zip_folder(folder_path):
    shutil.make_archive(folder_path, "zip", folder_path)
