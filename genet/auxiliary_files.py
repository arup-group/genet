import pandas as pd
import json
import os
from copy import deepcopy
import genet.utils.persistence as persistence
import genet.utils.dict_support as dict_support


class AuxiliaryFile:
    """
    Represents an auxiliary file of JSON or CSV format, links/attaches itself to the Network or Schedule object.
    Does not require a specific schema
    """

    def __init__(self, path_to_file: str):
        self.path_to_file = path_to_file
        self.filename = os.path.basename(path_to_file)
        self.data = self.read_file()
        self.attachments = []
        self.map = {}

    def read_file(self):
        if persistence.is_csv(self.path_to_file):
            return self._read_csv()
        elif persistence.is_json(self.path_to_file):
            return self._read_json()
        else:
            raise NotImplementedError(f'File {self.path_to_file} is not currently supported as an auxiliary file.')

    def _read_csv(self):
        return pd.read_csv(self.path_to_file)

    def _read_json(self):
        with open(self.path_to_file) as json_file:
            return json.load(json_file)

    def attach(self, indicies: set):
        if isinstance(self.data, dict):
            self.attachments += dict_support.find_nested_paths_to_value(self.data, indicies)
        if isinstance(self.data, pd.DataFrame):
            for col in self.data.columns:
                if set(self.data[col]) & indicies:
                    self.attachments.append(col)

    def is_attached(self):
        return self.attachments

    def build_identity_map(self):
        ids = set()
        for attachment in self.attachments:
            attachment_data = dict_support.get_nested_value(self.data, attachment)
            if isinstance(attachment_data, (list, set)):
                ids |= set(attachment_data)
            else:
                ids.add(attachment_data)
        self.map = dict(zip(ids, ids))

    def has_updates(self):
        return any([k != v for k, v in self.map.items()])

    def update(self):
        if self.has_updates():
            for attachment in self.attachments:
                attachment_data = dict_support.get_nested_value(self.data, attachment)
                if isinstance(attachment_data, (list, set)):
                    value = attachment_data.__class__(map(self.map.get, attachment_data))
                else:
                    value = self.map[attachment_data]
                self.data = dict_support.set_nested_value(
                    self.data, dict_support.nest_at_leaf(deepcopy(attachment), value))
            self.build_identity_map()

    def write_to_file(self, output_dir):
        self.update()
