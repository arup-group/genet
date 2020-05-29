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
