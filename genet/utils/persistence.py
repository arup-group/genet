import os
import logging
import shutil


def ensure_dir(direc):
    if not os.path.exists(direc):
        try:
            os.makedirs(direc)
        except PermissionError as e:
            logging.warning(e)


def is_yml(path):
    if isinstance(path, str):
        return path.lower().endswith(".yml") or path.lower().endswith(".yaml")
    return False


def is_geojson(path):
    return path.lower().endswith(".geojson")


def is_csv(path):
    return path.lower().endswith(".csv")


def is_json(path):
    return path.lower().endswith(".json")


def is_zip(path):
    return path.lower().endswith(".zip")


def zip_folder(folder_path):
    shutil.make_archive(folder_path, 'zip', folder_path)
