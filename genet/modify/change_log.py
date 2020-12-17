import pandas as pd
import dictdiffer
from datetime import datetime
from typing import Union, List


class ChangeLog:
    """
    Records changes in genet.core.Network into a pandas.DataFrame

    Change Events:
    • Add :
    • Modify :
    • Remove :
    """

    def __init__(self):
        self.log = pd.DataFrame(
            columns=['timestamp', 'change_event', 'object_type', 'old_id', 'new_id', 'old_attributes',
                     'new_attributes', 'diff'])

    def add(self, object_type: str, object_id: Union[int, str], object_attributes: dict):
        self.log = self.log.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'change_event': 'add',
            'object_type': object_type,
            'old_id': None,
            'new_id': object_id,
            'old_attributes': None,
            'new_attributes': str(object_attributes),
            'diff': self.generate_diff(None, object_id, None, object_attributes)
        }, ignore_index=True)

    def add_bunch(self, object_type: str, id_bunch: List[Union[int, str]], attributes_bunch: List[dict]):
        """
        :param object_type:
        :param id_bunch: same len as attributes_bunch
        :param attributes_bunch: same len as id_bunch
        :return:
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.log = self.log.append(pd.DataFrame({
            'timestamp': [timestamp]*len(id_bunch),
            'change_event': ['add']*len(id_bunch),
            'object_type': [object_type]*len(id_bunch),
            'old_id': None,
            'new_id': id_bunch,
            'old_attributes': None,
            'new_attributes': [str(d) for d in attributes_bunch],
            'diff': [self.generate_diff(None, _id, None, attrib) for _id, attrib in zip(id_bunch, attributes_bunch)]
        }), ignore_index=True)

    def modify(self, object_type: str, old_id: Union[int, str], old_attributes: dict, new_id: Union[int, str],
               new_attributes: dict):
        self.log = self.log.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'change_event': 'modify',
            'object_type': object_type,
            'old_id': old_id,
            'new_id': new_id,
            'old_attributes': str(old_attributes),
            'new_attributes': str(new_attributes),
            'diff': self.generate_diff(old_id, new_id, old_attributes, new_attributes)
        }, ignore_index=True)

    def modify_bunch(self, object_type: str, old_id_bunch: List[Union[int, str]], old_attributes: List[dict],
                     new_id_bunch: List[Union[int, str]], new_attributes: List[dict]):
        """
        :param object_type:
        :param old_id_bunch: same len as attributes_bunch
        :param old_attributes: same len as attributes_bunch
        :param new_id_bunch: same len as id_bunch
        :param new_attributes: same len as id_bunch
        :return:
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.log = self.log.append(pd.DataFrame({
            'timestamp': [timestamp]*len(old_id_bunch),
            'change_event': ['modify']*len(old_id_bunch),
            'object_type': [object_type]*len(old_id_bunch),
            'old_id': old_id_bunch,
            'new_id': new_id_bunch,
            'old_attributes': [str(d) for d in old_attributes],
            'new_attributes': [str(d) for d in new_attributes],
            'diff': [self.generate_diff(old_id, new_id, old_attrib, new_attrib)
                     for old_id, new_id, old_attrib, new_attrib in
                     zip(old_id_bunch, new_id_bunch, old_attributes, new_attributes)]
        }), ignore_index=True)

    def simplify_bunch(self, old_ids_list_bunch, new_id_bunch, indexed_paths_to_simplify, links_to_add):
        """ Series of ordered lists of indecies and attributes to log simplification of links, data prior to
        simplification and the nodes simplified
        :param old_ids_list_bunch: same len as attributes_bunch
        :param old_attributes: same len as attributes_bunch
        :param new_id_bunch: same len as id_bunch
        :param new_attributes: same len as id_bunch
        :param path_diff: lists of nodes deleted in order e.g. is path_before = [A, B, C, D] and path_after = [A, D]
        path_diff = [B, C], list of those for all links
        :return:
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.log = self.log.append(pd.DataFrame({
            'timestamp': [timestamp] * len(new_id_bunch),
            'change_event': ['simplify'] * len(new_id_bunch),
            'object_type': ['links'] * len(new_id_bunch),
            'old_id': old_ids_list_bunch,
            'new_id': new_id_bunch,
            'old_attributes': [str(indexed_paths_to_simplify[_id]['link_data']) for _id in new_id_bunch],
            'new_attributes': [str(links_to_add[_id]) for _id in new_id_bunch],
            'diff': [str(indexed_paths_to_simplify[_id]['nodes_to_remove']) for _id in new_id_bunch]
        }), ignore_index=True)

    def remove(self, object_type: str, object_id: Union[int, str], object_attributes: dict):
        self.log = self.log.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'change_event': 'remove',
            'object_type': object_type,
            'old_id': object_id,
            'new_id': None,
            'old_attributes': str(object_attributes),
            'new_attributes': None,
            'diff': self.generate_diff(object_id, None, object_attributes, None)
        }, ignore_index=True)

    def remove_bunch(self, object_type: str, id_bunch: List[Union[int, str]], attributes_bunch: List[dict]):
        """
        :param object_type:
        :param id_bunch: same len as attributes_bunch
        :param attributes_bunch: same len as id_bunch
        :return:
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.log = self.log.append(pd.DataFrame({
            'timestamp': [timestamp]*len(id_bunch),
            'change_event': ['remove']*len(id_bunch),
            'object_type': [object_type]*len(id_bunch),
            'old_id': id_bunch,
            'new_id': None,
            'old_attributes': [str(d) for d in attributes_bunch],
            'new_attributes': None,
            'diff': [self.generate_diff(_id, None, attrib, None) for _id, attrib in zip(id_bunch, attributes_bunch)]
        }), ignore_index=True)

    def generate_diff(self, old_id, new_id, old_attributes_dict, new_attributes_dict):
        if old_attributes_dict is None:
            old_attributes_dict = {}
        if new_attributes_dict is None:
            new_attributes_dict = {}

        diff = list(dictdiffer.diff(old_attributes_dict, new_attributes_dict))
        if old_id != new_id:
            if old_id is None:
                diff.append(('add', 'id', new_id))
            elif new_id is None:
                diff.append(('remove', 'id', old_id))
            else:
                diff.append(('change', 'id', (old_id, new_id)))
        return diff

    def export(self, path):
        self.log.to_csv(path)
