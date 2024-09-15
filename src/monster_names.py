import json


class MonsterNames:
    def __init__(self, data):
        if not isinstance(data, dict):
            raise TypeError('data must be of type dict')
        self.MONSTER_NAMES_DICT = data
        self.INV_MONSTER_NAMES_DICT = {v: k for k, v in self.MONSTER_NAMES_DICT.items()}

    @classmethod
    def from_json(cls, file_path):
        """Initialize the instance from a JSON file."""
        with open(file_path, "r") as json_file:
            data = json.load(json_file)
        return cls(data)