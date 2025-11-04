import time
from typing import List, Tuple

from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox, QColorDialog, QApplication
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor

from core.config import ConfigStore
from core.lighting import LightingController
from core.hypr_ipc import HyprlandIPCClient
from core.input_monitor import EvdevInputMonitor
from core.app_profiles import AppProfilesStore, AppProfile

from ui.keyboard_layout import KeyboardLayout


class KeyboardAppV2(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sinodragon V2")

        # core services
        self.config = ConfigStore()
        self.lighting = LightingController()
        self.profiles = AppProfilesStore()

        # state
        self.keys = []
        self.current_config_name = None
        self.intensity = 1.0
        self.current_app = "Unknown"
        self.root_key = "Win"  # can be made configurable

        # UI
        central = QWidget()
        layout = QVBoxLayout(central)

        top = QHBoxLayout()
        top.addWidget(QLabel("Config:"))
        self.combo = QComboBox()
        self.combo.addItems(self.config.list_configs())
        self.combo.currentTextChanged.connect(self.load_config)
        top.addWidget(self.combo)

        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.save_config)
        top.addWidget(btn_save)

        btn_apply = QPushButton("Apply")
        btn_apply.clicked.connect(self.apply_ui_colors)
        top.addWidget(btn_apply)

        btn_profiles = QPushButton("Manage Profiles")
        btn_profiles.clicked.connect(self.open_profiles_dialog)
        top.addWidget(btn_profiles)

        btn_coding = QPushButton("Coding Preset")
        btn_coding.clicked.connect(self.apply_coding_preset)
        top.addWidget(btn_coding)

        btn_moba = QPushButton("MOBA Preset")
        btn_moba.clicked.connect(self.apply_moba_preset)
        top.addWidget(btn_moba)

        layout.addLayout(top)

        kb = KeyboardLayout(self)
        self.keys = kb.keys
        layout.addWidget(kb)

        self.setCentralWidget(central)

        # monitors
        self.hypr = HyprlandIPCClient(self._on_active_window)
        self.hypr.start()
        self.ev = EvdevInputMonitor(self._on_key_press, self._on_key_release)
        self.ev.start()

        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self._poll_backends)
        self.poll_timer.start(100)

        # load default config
        names = self.config.list_configs()
        self.load_config(names[0] if names else None)

    # config
    def load_config(self, name: str) -> None:
        cfg = self.config.load_or_default(name, total_keys=len(self.keys) or 126)
        self.current_config_name = cfg.get("name")
        colors = cfg.get("colors", [])
        self.intensity = float(cfg.get("intensity", 1.0))
        for i, key in enumerate(self.keys):
            if i < len(colors):
                r, g, b = colors[i]
                key.setKeyColor(QColor(int(r), int(g), int(b)))
        self.apply_ui_colors()

    def save_config(self) -> None:
        colors = self._current_ui_colors()
        name = self.current_config_name or "Default"
        self.config.save(name, colors, self.intensity)

    def apply_ui_colors(self) -> None:
        colors = self._current_ui_colors()
        self.lighting.apply(colors, self.intensity)

    def _current_ui_colors(self) -> List[Tuple[int, int, int]]:
        out: List[Tuple[int, int, int]] = []
        for key in self.keys:
            c = key.color
            out.append((c.red(), c.green(), c.blue()))
        return out

    # monitors polling
    def _poll_backends(self) -> None:
        self.hypr.poll(0.05)
        self.ev.poll(0.02)

    def _on_active_window(self, app_class: str) -> None:
        if not app_class:
            return
        self.current_app = app_class
        prof = self.profiles.load(app_class)
        if not prof:
            return
        self._apply_profile_default(prof)

    # evdev key tracking
    def _on_key_press(self, key_name: str) -> None:
        if key_name == self.root_key:
            prof = self.profiles.load(self.current_app)
            if prof:
                self._apply_profile_default(prof)

    def _on_key_release(self, key_name: str) -> None:
        pass

    def _apply_profile_default(self, prof: AppProfile) -> None:
        # clear
        for k in self.keys:
            k.setKeyColor(QColor(0, 0, 0))
        color = QColor(*prof.color)
        for name in prof.default_keys:
            self._highlight_key(name, color)
        self.apply_ui_colors()

    def _highlight_key(self, name: str, color: QColor) -> None:
        if not name:
            return
        target = name.strip()
        for k in self.keys:
            if hasattr(k, 'key_name') and (k.key_name == target or k.key_name.lower() == target.lower()):
                k.setKeyColor(color)
                return

    # presets
    def apply_coding_preset(self) -> None:
        dim = QColor(10, 15, 25)
        for key in self.keys:
            key.setKeyColor(dim)
        for name in ["A","S","D","F","J","K","L",";"]:
            self._highlight_key(name, QColor(0, 200, 120))
        for name in ["Bksp","Enter","Tab","Space","Home","End","PgUp","PgDn","↑","↓","←","→"]:
            self._highlight_key(name, QColor(80, 160, 255))
        for name in ["[","]","-","=","\\","'","/",".",","]:
            self._highlight_key(name, QColor(255, 180, 70))
        for name in ["Ctrl","Shift","Alt","Win"]:
            self._highlight_key(name, QColor(255, 80, 120))
        self.apply_ui_colors()

    def apply_moba_preset(self) -> None:
        for key in self.keys:
            key.setKeyColor(QColor(0, 0, 0))
        for name in ["Q","W","E","R","D","F","1","2","3","4","5","6","B","G","Space"]:
            self._highlight_key(name, QColor(255, 140, 0))
        self.apply_ui_colors()

    # profiles dialog (minimal stub)
    def open_profiles_dialog(self) -> None:
        from ui.dialogs.app_profiles_v2 import AppProfilesDialog
        dlg = AppProfilesDialog(self, self.profiles)
        dlg.exec_()


