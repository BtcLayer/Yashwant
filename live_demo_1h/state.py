import json
import os
from typing import Any, Dict


class JSONState:
    def __init__(self, path: str):
        self.path = path
        self._state: Dict[str, Any] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self._state = json.load(f)
            except (OSError, json.JSONDecodeError):
                self._state = {}

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2)
        except OSError:
            pass

    def get(self, key: str, default=None):
        return self._state.get(key, default)

    def set(self, key: str, value: Any):
        self._state[key] = value
        self.save()
