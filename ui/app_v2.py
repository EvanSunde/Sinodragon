import time
import logging
from typing import List, Tuple

from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox, QColorDialog, QApplication, QSplitter, QTabWidget, QCheckBox, QSlider, QLineEdit
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor

from core.config import ConfigStore
from core.lighting import LightingController
from core.hypr_ipc import HyprlandIPCClient
from core.input_monitor import EvdevInputMonitor
from core.app_profiles import AppProfilesStore, AppProfile

from ui.keyboard_layout import KeyboardLayout

logger = logging.getLogger(__name__)


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

        splitter = QSplitter(Qt.Horizontal)

        # Left: Keyboard
        kb = KeyboardLayout(self)
        self.keys = kb.keys
        splitter.addWidget(kb)

        # Right: Tabbed control panel
        right = QWidget()
        right_layout = QVBoxLayout(right)
        tabs = QTabWidget()

        # Tab 1: Config
        tab_cfg = QWidget()
        cfg_layout = QVBoxLayout(tab_cfg)
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Config:"))
        self.combo = QComboBox()
        self.combo.addItems(self.config.list_configs())
        self.combo.currentTextChanged.connect(self.load_config)
        row1.addWidget(self.combo)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Config name")
        row1.addWidget(self.name_edit)
        cfg_layout.addLayout(row1)

        row2 = QHBoxLayout()
        btn_new = QPushButton("New")
        btn_new.clicked.connect(self.new_config)
        row2.addWidget(btn_new)
        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.save_config)
        row2.addWidget(btn_save)
        btn_rename = QPushButton("Rename")
        btn_rename.clicked.connect(self.rename_config)
        row2.addWidget(btn_rename)
        btn_delete = QPushButton("Delete")
        btn_delete.clicked.connect(self.delete_config)
        row2.addWidget(btn_delete)
        btn_apply = QPushButton("Apply")
        btn_apply.clicked.connect(self.apply_ui_colors)
        row2.addWidget(btn_apply)
        cfg_layout.addLayout(row2)

        # Color picker and intensity
        row3 = QHBoxLayout()
        self.color_btn = QPushButton("Pick Color")
        self.color_btn.clicked.connect(self.pick_current_color)
        row3.addWidget(self.color_btn)
        row3.addWidget(QLabel("Intensity:"))
        self.intensity_slider = QSlider(Qt.Horizontal)
        self.intensity_slider.setRange(5, 100)
        self.intensity_slider.setValue(100)
        self.intensity_slider.valueChanged.connect(self.on_intensity_changed)
        row3.addWidget(self.intensity_slider)
        cfg_layout.addLayout(row3)

        tabs.addTab(tab_cfg, "Config")

        # Tab 2: Presets
        tab_presets = QWidget()
        p_layout = QVBoxLayout(tab_presets)
        btn_coding = QPushButton("Coding Preset")
        btn_coding.clicked.connect(self.apply_coding_preset)
        p_layout.addWidget(btn_coding)
        btn_moba = QPushButton("MOBA Preset")
        btn_moba.clicked.connect(self.apply_moba_preset)
        p_layout.addWidget(btn_moba)
        btn_movie = QPushButton("Movie Preset")
        btn_movie.clicked.connect(self.apply_movie_preset)
        p_layout.addWidget(btn_movie)
        btn_gaming = QPushButton("Gaming Preset")
        btn_gaming.clicked.connect(self.apply_gaming_preset)
        p_layout.addWidget(btn_gaming)
        btn_rainbow = QPushButton("Rainbow Preset")
        btn_rainbow.clicked.connect(self.apply_rainbow_preset)
        p_layout.addWidget(btn_rainbow)
        btn_stars = QPushButton("Stars Preset (animated)")
        btn_stars.clicked.connect(self.apply_stars_preset)
        p_layout.addWidget(btn_stars)
        tabs.addTab(tab_presets, "Presets")

        # Tab 3: Shortcuts
        tab_short = QWidget()
        s_layout = QVBoxLayout(tab_short)
        self.short_enabled = QCheckBox("Enable App Profiles")
        self.short_enabled.setChecked(True)
        s_layout.addWidget(self.short_enabled)
        self.current_app_label = QLabel("Current App: Unknown")
        s_layout.addWidget(self.current_app_label)
        s_layout.addWidget(QLabel("Root Key triggers default keys (Win by default)."))
        row_short = QHBoxLayout()
        btn_manage_profiles = QPushButton("Manage Profiles")
        btn_manage_profiles.clicked.connect(self.open_profiles_dialog)
        row_short.addWidget(btn_manage_profiles)
        btn_new_for_app = QPushButton("New Profile for Current App")
        btn_new_for_app.clicked.connect(self.create_profile_for_current_app)
        row_short.addWidget(btn_new_for_app)
        s_layout.addLayout(row_short)
        tabs.addTab(tab_short, "Shortcuts")

        right_layout.addWidget(tabs)
        splitter.addWidget(right)
        splitter.setSizes([900, 300])

        layout.addWidget(splitter)

        self.setCentralWidget(central)

        # monitors
        self.hypr = HyprlandIPCClient(self._on_active_window)
        self.hypr.start()
        self.ev = EvdevInputMonitor(self._on_key_press, self._on_key_release)
        self.ev.start()

        # Current app will update on first IPC event (no hyprctl)

        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self._poll_backends)
        self.poll_timer.start(50)

        # load default config
        names = self.config.list_configs()
        self.load_config(names[0] if names else None)

    # config
    def load_config(self, name: str) -> None:
        logger.info(f"Loading config: {name}")
        cfg = self.config.load_or_default(name, total_keys=len(self.keys) or 126)
        self.current_config_name = cfg.get("name")
        colors = cfg.get("colors", [])
        self.intensity = float(cfg.get("intensity", 1.0))
        self.intensity_slider.setValue(int(self.intensity * 100))
        self.name_edit.setText(self.current_config_name or "")
        for i, key in enumerate(self.keys):
            if i < len(colors):
                r, g, b = colors[i]
                key.setKeyColor(QColor(int(r), int(g), int(b)))
        self.apply_ui_colors()

    def save_config(self) -> None:
        colors = self._current_ui_colors()
        name = self.name_edit.text().strip() or self.current_config_name or "Default"
        self.config.save(name, colors, self.intensity)
        # refresh list
        items = self.config.list_configs()
        self.combo.clear()
        self.combo.addItems(items)
        self.combo.setCurrentText(name)
        logger.info(f"Saved config: {name}")

    def new_config(self) -> None:
        self.current_config_name = "New"
        self.name_edit.setText(self.current_config_name)
        for key in self.keys:
            key.setKeyColor(QColor(0, 0, 0))
        self.apply_ui_colors()

    def rename_config(self) -> None:
        old = self.current_config_name
        new = self.name_edit.text().strip()
        if old and new and old != new:
            if self.config.rename(old, new):
                items = self.config.list_configs()
                self.combo.clear()
                self.combo.addItems(items)
                self.combo.setCurrentText(new)
                self.current_config_name = new
                logger.info(f"Renamed config {old} -> {new}")

    def delete_config(self) -> None:
        name = self.combo.currentText()
        if name and self.config.delete(name):
            items = self.config.list_configs()
            self.combo.clear()
            self.combo.addItems(items)
            self.name_edit.clear()
            logger.info(f"Deleted config: {name}")

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
        self.hypr.poll(0.0)
        self.ev.poll(0.0)

    def _on_active_window(self, app_class: str) -> None:
        if not app_class:
            return
        logger.info(f"Active app changed: {app_class}")
        self.current_app = app_class
        if hasattr(self, 'current_app_label'):
            self.current_app_label.setText(f"Current App: {self.current_app}")
        if not self.short_enabled.isChecked():
            return
        prof = self._get_cached_profile(app_class)
        if prof:
            self._apply_profile_default(prof)

    # evdev key tracking
    def _on_key_press(self, key_name: str) -> None:
        logger.info(f"Key press: {key_name}")
        if key_name == self.root_key and self.short_enabled.isChecked():
            prof = self._get_cached_profile(self.current_app)
            if prof:
                self._apply_profile_default(prof)

    def _on_key_release(self, key_name: str) -> None:
        pass

    def _apply_profile_default(self, prof: AppProfile) -> None:
        logger.info(f"Applying profile defaults for {prof.name}")
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
        logger.info("Preset: coding")
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
        logger.info("Preset: moba")
        for key in self.keys:
            key.setKeyColor(QColor(0, 0, 0))
        for name in ["Q","W","E","R","D","F","1","2","3","4","5","6","B","G","Space"]:
            self._highlight_key(name, QColor(255, 140, 0))
        self.apply_ui_colors()

    def apply_movie_preset(self) -> None:
        logger.info("Preset: movie")
        base = QColor(0, 0, 10)
        for key in self.keys:
            key.setKeyColor(base)
        for name in ["Space","↑","↓","←","→","Home","End","PgUp","PgDn"]:
            self._highlight_key(name, QColor(30, 180, 255))
        for name in ["F2","F3","F7","F8","F9","F10"]:
            self._highlight_key(name, QColor(120, 240, 160))
        self.apply_ui_colors()

    def apply_gaming_preset(self) -> None:
        logger.info("Preset: gaming")
        for key in self.keys:
            key.setKeyColor(QColor(0, 0, 0))
        for name in ["W","A","S","D","Space","Shift","Ctrl"]:
            self._highlight_key(name, QColor(0, 150, 255))
        for name in ["F1","F2","F3","F4","F5","F6"]:
            self._highlight_key(name, QColor(255, 128, 0))
        self.apply_ui_colors()

    def apply_rainbow_preset(self) -> None:
        logger.info("Preset: rainbow")
        n = len(self.keys)
        if n == 0:
            return
        for i, key in enumerate(self.keys):
            h = i / max(1, n)
            r, g, b = _hsv_to_rgb(h, 1.0, 1.0)
            key.setKeyColor(QColor(r, g, b))
        self.apply_ui_colors()

    def apply_stars_preset(self) -> None:
        logger.info("Preset: stars")
        # simple twinkle animation for a short duration, non-blocking
        for key in self.keys:
            key.setKeyColor(QColor(0, 0, 20))
        self._stars_ticks = 0
        if not hasattr(self, '_anim_timer'):
            self._anim_timer = QTimer()
            self._anim_timer.timeout.connect(self._stars_step)
        self._anim_timer.start(150)

    def _stars_step(self) -> None:
        import random
        self._stars_ticks += 1
        # dim base
        for key in self.keys:
            c = key.color
            key.setKeyColor(QColor(max(0, c.red() - 10), max(0, c.green() - 10), max(0, c.blue() - 10)))
        # new stars
        stars = min(10, max(3, len(self.keys) // 20))
        for key in random.sample(self.keys, stars):
            br = 0.5 + random.random() * 0.5
            key.setKeyColor(QColor(int(255 * br), int(255 * br), int(255 * br)))
        self.apply_ui_colors()
        if self._stars_ticks >= 40:  # ~6s
            self._anim_timer.stop()

    # profile cache (LRU size 5)
    def _get_cached_profile(self, app: str) -> AppProfile:
        try:
            from collections import OrderedDict
        except Exception:
            return self.profiles.load(app)
        if not hasattr(self, '_profile_cache'):
            self._profile_cache = OrderedDict()
        cache = self._profile_cache
        if app in cache:
            prof = cache.pop(app)
            cache[app] = prof
            return prof
        prof = self.profiles.load(app)
        if prof:
            cache[app] = prof
            if len(cache) > 5:
                cache.popitem(last=False)
        return prof

    # key clicking + color management
    def pick_current_color(self) -> None:
        c = QColorDialog.getColor(getattr(self, '_current_qcolor', QColor(0, 255, 0)), self, "Select Color")
        if c.isValid():
            self._current_qcolor = c

    def handle_key_click(self, key) -> None:
        # KeyboardLayout expects this method on parent
        c = getattr(self, '_current_qcolor', QColor(0, 255, 0))
        if hasattr(key, 'setKeyColor'):
            key.setKeyColor(c)
            # live apply
            self.apply_ui_colors()

    def on_intensity_changed(self, value: int) -> None:
        self.intensity = max(0.05, min(1.0, value / 100.0))
        self.apply_ui_colors()

    # profiles dialog (minimal stub)
    def open_profiles_dialog(self) -> None:
        from ui.dialogs.app_profiles_v2 import AppProfilesDialog
        dlg = AppProfilesDialog(self, self.profiles)
        dlg.exec_()

    def create_profile_for_current_app(self) -> None:
        from ui.dialogs.app_profiles_v2 import AppProfilesDialog
        dlg = AppProfilesDialog(self, self.profiles)
        # prefill with current app name for convenience
        try:
            if hasattr(dlg, 'name_edit'):
                dlg.name_edit.setText(self.current_app or "")
        except Exception:
            pass
        dlg.exec_()


