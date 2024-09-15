import os
from pathlib import Path

class _Globals:
    def __init__(self):
        self.DEBUG_MODE = 0
        self.SESSION_ID = '0'
        self.DEBUG_PATH = os.path.join(Path(__file__).resolve().parents[1], 'DEBUG', self.SESSION_ID)
        Path(self.DEBUG_PATH).mkdir(parents = True, exist_ok = True)

    def update_debug(self, mode):
        self.DEBUG_MODE = mode

    def update_session_id(self, id):
        self.SESSION_ID = id
        self.DEBUG_PATH = os.path.join(Path(__file__).resolve().parents[1], 'DEBUG', self.SESSION_ID)
        Path(self.DEBUG_PATH).mkdir(parents = True, exist_ok = True)

    def get_debug_path(self):
        Path(self.DEBUG_PATH).mkdir(parents = True, exist_ok = True)
        return self.DEBUG_PATH


globals = _Globals()