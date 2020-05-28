import pandas as pd
from datetime import datetime


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
                     'new_attributes'])

    def add(self, object_type: str, object_id: str, object_attributes: dict):
        self.log = self.log.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'change_event': 'add',
            'object_type': object_type,
            'old_id': pd.NA,
            'new_id': object_id,
            'old_attributes': pd.NA,
            'new_attributes': str(object_attributes)
        }, ignore_index=True)

    def modify(self, object_type: str, old_id: str, old_attributes: dict, new_id: str,
               new_attributes: dict):
        self.log = self.log.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'change_event': 'modify',
            'object_type': object_type,
            'old_id': old_id,
            'new_id': new_id,
            'old_attributes': str(old_attributes),
            'new_attributes': str(new_attributes)
        }, ignore_index=True)

    def remove(self, object_type: str, object_id: str, object_attributes: dict):
        self.log = self.log.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'change_event': 'remove',
            'object_type': object_type,
            'old_id': object_id,
            'new_id': pd.NA,
            'old_attributes': str(object_attributes),
            'new_attributes': pd.NA
        }, ignore_index=True)

    def export(self, path):
        self.log.write_csv(path)
