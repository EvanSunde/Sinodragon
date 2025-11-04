import os
import json
from typing import Dict, List, Tuple, Optional
from PyQt5.QtGui import QColor


class AppProfile:
    def __init__(self, name: str, color: Tuple[int, int, int], default_keys: List[str], combos: Dict[str, List[str]]):
        self.name = name
        self.color = color
        self.default_keys = default_keys
        self.combos = combos  # e.g., {"Ctrl": ["S","F"], "Ctrl+Shift": ["N"]}

    def to_dict(self) -> dict:
        return {
            "color": list(self.color),
            "default_keys": self.default_keys,
            "combos": self.combos,
        }

    @staticmethod
    def from_dict(name: str, data: dict) -> 'AppProfile':
        color = tuple(data.get("color", (255, 165, 0)))
        default_keys = data.get("default_keys", [])
        combos = data.get("combos", {})
        return AppProfile(name, (int(color[0]), int(color[1]), int(color[2])), default_keys, combos)


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

    def load_all(self) -> Dict[str, AppProfile]:
        out: Dict[str, AppProfile] = {}
        for app in self.list_apps():
            p = self.load(app)
            if p:
                out[app] = p
        return out


