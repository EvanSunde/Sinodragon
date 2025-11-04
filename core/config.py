import os
import json
from typing import List, Tuple, Optional


class ConfigStore:
    def __init__(self, app_name: str = "sinodragon"):
        home = os.path.expanduser("~")
        self.base_dir = os.path.join(home, ".config", app_name)
        os.makedirs(self.base_dir, exist_ok=True)
        self.configs_dir = os.path.join(self.base_dir, "configs")
        os.makedirs(self.configs_dir, exist_ok=True)
        self.index_path = os.path.join(self.base_dir, "configs.json")

    def list_configs(self) -> List[str]:
        files = []
        for fn in os.listdir(self.configs_dir):
            if fn.endswith(".json"):
                files.append(fn[:-5])
        return sorted(files)

    def save(self, name: str, colors: List[Tuple[int, int, int]], intensity: float = 1.0) -> bool:
        data = {
            "name": name,
            "intensity": max(0.01, min(1.0, float(intensity))),
            "colors": colors,
        }
        path = os.path.join(self.configs_dir, f"{name}.json")
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        return True

    def load(self, name: Optional[str]) -> Optional[dict]:
        if not name:
            return None
        path = os.path.join(self.configs_dir, f"{name}.json")
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            return json.load(f)

    def load_or_default(self, name: Optional[str], total_keys: int = 126) -> dict:
        cfg = self.load(name)
        if cfg:
            return cfg
        # default dim green
        colors = [(0, 40, 0) for _ in range(total_keys)]
        return {"name": name or "Default", "intensity": 1.0, "colors": colors}

    def delete(self, name: str) -> bool:
        if not name:
            return False
        path = os.path.join(self.configs_dir, f"{name}.json")
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def rename(self, old: str, new: str) -> bool:
        if not old or not new or old == new:
            return False
        op = os.path.join(self.configs_dir, f"{old}.json")
        np = os.path.join(self.configs_dir, f"{new}.json")
        if not os.path.exists(op):
            return False
        os.replace(op, np)
        return True


