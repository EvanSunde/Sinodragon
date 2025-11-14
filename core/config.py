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

    # Import/Export helpers
    def import_file(self, src_path: str, name: Optional[str] = None) -> Optional[str]:
        """Import a config JSON file from an arbitrary path into the configs dir.
        Returns the resulting config name on success.
        """
        try:
            if not os.path.exists(src_path):
                return None
            with open(src_path, 'r') as f:
                data = json.load(f)
            # Basic validation
            colors = data.get('colors')
            if not isinstance(colors, list):
                return None
            cfg_name = name or os.path.splitext(os.path.basename(src_path))[0]
            # Write normalized file
            out = {
                'name': cfg_name,
                'intensity': float(data.get('intensity', 1.0)),
                'colors': colors,
            }
            dst = os.path.join(self.configs_dir, f"{cfg_name}.json")
            with open(dst, 'w') as f:
                json.dump(out, f, indent=2)
            return cfg_name
        except Exception:
            return None

    def export_file(self, name: str, dest_path: str) -> bool:
        """Export a named config to a chosen destination path."""
        try:
            cfg = self.load(name)
            if not cfg:
                return False
            with open(dest_path, 'w') as f:
                json.dump(cfg, f, indent=2)
            return True
        except Exception:
            return False


