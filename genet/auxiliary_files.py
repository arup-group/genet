import pandas as pd
import json
import os
import ast
import logging
from copy import deepcopy
import genet.utils.persistence as persistence
import genet.utils.dict_support as dict_support


class AuxiliaryFile:
    """
    Represents an auxiliary file of JSON or CSV format, can be 'attached' to a Network or Schedule object by sharing
    their IDs through the `attach` method.
    Does not require the file to follow a specific schema, it will search for an overlap in indices and record the path
    to that data within the file in the `attachments` attribute. It works under a few assumptions though:
        - for CSV: table with single level indexing. The IDs can be nested in lists.
        - for JSON: any level of nestedness is allowed, the IDs can live singularly or within lists.
    In both cases, the IDs of interest need to be stored as values and no other data using the same values is stored
    in the file.
    Can handle only one type of indices. So a file has to correspond to one set of indices, no mixing allowed.
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
        df = pd.read_csv(self.path_to_file)
        for col in df.columns:
            try:
                df[col] = df[col].apply(lambda x: ast.literal_eval(x))
            except ValueError:
                pass
        return df

    def _read_json(self):
        with open(self.path_to_file) as json_file:
            return json.load(json_file)

    def attach(self, indices: set):
        if isinstance(self.data, dict):
            self.attachments += dict_support.find_nested_paths_to_value(self.data, indices)
        if isinstance(self.data, pd.DataFrame):
            for col in self.data.columns:
                if all([isinstance(x, (list, set)) for x in self.data[col]]):
                    if set(self.data[col].sum()) & indices:
                        self.attachments.append(col)
                elif set(self.data[col]) & indices:
                    self.attachments.append(col)
        self.build_identity_map()

    def is_attached(self):
        return self.attachments

    def build_identity_map(self):
        ids = set()
        if isinstance(self.data, dict):
            for attachment in self.attachments:
                attachment_data = dict_support.get_nested_value(self.data, attachment)
                if isinstance(attachment_data, (list, set)):
                    ids |= set(attachment_data)
                else:
                    ids.add(attachment_data)
        else:
            for attachment in self.attachments:
                if all([isinstance(x, (list, set)) for x in self.data[attachment]]):
                    ids |= set(self.data[attachment].sum())
                else:
                    ids |= set(self.data[attachment])
        self.map = dict(zip(ids, ids))

    def apply_map(self, id_map):
        self.map = {**self.map, **id_map}

    def has_updates(self):
        return any([k != v for k, v in self.map.items()])

    def update(self):
        if self.has_updates():
            if isinstance(self.data, dict):
                for attachment in self.attachments:
                    attachment_data = dict_support.get_nested_value(self.data, attachment)
                    if isinstance(attachment_data, (list, set)):
                        value = attachment_data.__class__(map(self.map.get, attachment_data))
                    else:
                        value = self.map[attachment_data]
                    self.data = dict_support.set_nested_value(
                        self.data, dict_support.nest_at_leaf(deepcopy(attachment), value))
            else:
                for attachment in self.attachments:
                    if all([isinstance(x, (list, set)) for x in self.data[attachment]]):
                        self.data[attachment] = self.data[attachment].apply(
                            lambda x: x.__class__([self.map[i] for i in x]))
                    else:
                        self.data[attachment] = self.data[attachment].replace(self.map)
            self.build_identity_map()

    def write_to_file(self, output_dir):
        self.update()
        persistence.ensure_dir(output_dir)
        logging.info(f'Saving auxiliary file {self.filename} in {output_dir}')
        if persistence.is_csv(self.filename):
            return self._write_csv(output_dir)
        elif persistence.is_json(self.filename):
            return self._write_json(output_dir)
        else:
            raise NotImplementedError(f'File {self.filename} is not currently supported as an auxiliary file.')

    def _write_csv(self, output_dir):
        self.data.to_csv(os.path.join(output_dir, self.filename))

    def _write_json(self, output_dir):
        with open(os.path.join(output_dir, self.filename), 'w') as outfile:
            json.dump(self.data, outfile)
