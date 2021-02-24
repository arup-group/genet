import pandas as pd
import json
import os
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
        # todo use self.attachments locations to build a dictionary of all indices in data mapping to themselves
        pass

    def update(self):
        # todo use map to update all index mentions under self.attachments locations
        # todo build identity map again
        pass

    def write_to_file(self, output_dir):
        pass
