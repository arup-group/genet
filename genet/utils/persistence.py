import os
import logging
import shutil


def ensure_dir(direc):
    if not os.path.exists(direc):
        try:
            os.makedirs(direc)
        except PermissionError as e:
            logging.warning(e)


def is_zip(path):
    return path.lower().endswith(".zip")


def zip_folder(folder_path):
    shutil.make_archive(folder_path, 'zip', folder_path)
