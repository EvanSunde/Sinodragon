import os
import json
from typing import Dict, List, Tuple, Optional
from PyQt5.QtGui import QColor


class AppProfile:
    def __init__(self, name: str, color: Tuple[int, int, int], default_keys: List[str], combos: Dict[str, List[str]], default_mode: str = "keys", default_config_name: str = ""):
        self.name = name
        self.color = color
        self.default_keys = default_keys
        self.combos = combos  # e.g., {"Ctrl": ["S","F"], "Ctrl+Shift": ["N"]}
        # default_mode: "keys" (use default_keys), "none" (do not change), "config" (use baseline/config)
        self.default_mode = default_mode
        # when default_mode == "config", the config name to use
        self.default_config_name = default_config_name

    def to_dict(self) -> dict:
        return {
            "color": list(self.color),
            "default_keys": self.default_keys,
            "combos": self.combos,
            "default_mode": self.default_mode,
            "default_config_name": self.default_config_name,
        }

    @staticmethod
    def from_dict(name: str, data: dict) -> 'AppProfile':
        color = tuple(data.get("color", (255, 165, 0)))
        default_keys = data.get("default_keys", [])
        combos = data.get("combos", {})
        default_mode = data.get("default_mode", "keys")
        default_config_name = data.get("default_config_name", "")
        return AppProfile(name, (int(color[0]), int(color[1]), int(color[2])), default_keys, combos, default_mode, default_config_name)


class AppProfilesStore:
    def __init__(self, app_name: str = "sinodragon"):
        home = os.path.expanduser("~")
        self.base_dir = os.path.join(home, ".config", app_name, "app_profiles")
        os.makedirs(self.base_dir, exist_ok=True)

    def path_for(self, app: str) -> str:
        return os.path.join(self.base_dir, f"{app}.json")

    def list_apps(self) -> List[str]:
        apps = []
        for fn in os.listdir(self.base_dir):
            if fn.endswith('.json'):
                apps.append(fn[:-5])
        return sorted(apps)

    def load(self, app: str) -> Optional[AppProfile]:
        path = self.path_for(app)
        if not os.path.exists(path):
            return None
        with open(path, 'r') as f:
            data = json.load(f)
        return AppProfile.from_dict(app, data)

    def save(self, profile: AppProfile) -> bool:
        path = self.path_for(profile.name)
        with open(path, 'w') as f:
            json.dump(profile.to_dict(), f, indent=2)
        return True

    def delete(self, app: str) -> bool:
        path = self.path_for(app)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def rename(self, old: str, new: str) -> bool:
        if not old or not new or old == new:
            return False
        op = self.path_for(old)
        np = self.path_for(new)
        if not os.path.exists(op):
            return False
        os.replace(op, np)
        return True

    def load_all(self) -> Dict[str, AppProfile]:
        out: Dict[str, AppProfile] = {}
        for app in self.list_apps():
            p = self.load(app)
            if p:
                out[app] = p
        return out


