"""Настройки (config.json) и состояние модов (state.json)."""

import contextlib
import copy
import json
import os
import threading

from . import paths

CONFIG_DEFAULTS = {
    "setup_done": False,
    "steam_root": "",
    "dota_path": "",
    "language": "russian",
    "steam_account": "",
    "pak_number": 66,
    "filter_adult": True,
    "filter_anime": False,
    "auto_refresh": True,
    "restart_steam": True,
    "tweaks": {},
    "sources": {"minify": True, "community": True},
    "launch_opts": {},
    "theme": "violet",
    "theme_vars": {},
    "ui": {"card_style": "classic", "sidebar": "left", "glow": True, "anim": True},
}

STATE_DEFAULTS = {
    "enabled": {},
    "order": [],
    "catalog_refreshed": 0,
    "patch": {},
}


def read_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


class JsonStore:
    def __init__(self, path, defaults):
        self.path = path
        self.lock = threading.RLock()
        self._data = copy.deepcopy(defaults)
        loaded = read_json(path, {})
        if isinstance(loaded, dict):
            for key, value in loaded.items():
                if isinstance(self._data.get(key), dict) and isinstance(value, dict) and key == "ui":
                    self._data[key].update(value)
                else:
                    self._data[key] = value

    def get(self, key, default=None):
        with self.lock:
            return copy.deepcopy(self._data.get(key, default))

    def snapshot(self):
        with self.lock:
            return copy.deepcopy(self._data)

    def update(self, values):
        with self.lock:
            self._data.update(copy.deepcopy(values))
            self.save()

    def set(self, key, value):
        self.update({key: value})

    @contextlib.contextmanager
    def edit(self):
        """Изменение вложенных данных с сохранением в конце блока."""
        with self.lock:
            yield self._data
            self.save()

    def save(self):
        with self.lock:
            write_json(self.path, self._data)


paths.ensure()
config = JsonStore(paths.CONFIG_FILE, CONFIG_DEFAULTS)
state = JsonStore(paths.STATE_FILE, STATE_DEFAULTS)
