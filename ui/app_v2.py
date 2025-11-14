import time
import logging
import os
from typing import List, Tuple

from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox, QColorDialog, QApplication, QSplitter, QTabWidget, QCheckBox, QSlider, QLineEdit, QSystemTrayIcon, QMenu, QAction, QFileDialog, QMessageBox
from PyQt5.QtGui import QPalette
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor

from core.config import ConfigStore
from core.lighting import LightingController
from core.hypr_ipc import HyprlandIPCClient
from core.input_monitor import EvdevInputMonitor
from core.app_profiles import AppProfilesStore, AppProfile

from ui.keyboard_layout import KeyboardLayout
from ui.color_display import ColorDisplay
from features import presets as preset_mod

logger = logging.getLogger(__name__)
_debug = os.environ.get('DEBUG', '').lower() in ('1', 'true', 'yes', 'on')
logger.setLevel(logging.INFO if _debug else logging.WARNING)


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
        self._pressed_keys = set()
        self._baseline_colors = []
        self._view_state = "baseline"  # baseline | app_default | combo
        self._last_combo_key = None
        # selection state
        self.selected_indices = set()
        self.last_clicked_index = None
        # color state
        self._current_qcolor = QColor(0, 255, 0)
        self._saved_colors = self.config.load_palette()

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
        btn_import = QPushButton("Import…")
        btn_import.clicked.connect(self.import_config_dialog)
        row2.addWidget(btn_import)
        btn_export = QPushButton("Export…")
        btn_export.clicked.connect(self.export_config_dialog)
        row2.addWidget(btn_export)
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

        # RGB sliders for current color
        row_rgb = QHBoxLayout()
        row_rgb.addWidget(QLabel("RGB:"))
        self.r_slider = QSlider(Qt.Horizontal)
        self.r_slider.setRange(0, 255)
        self.g_slider = QSlider(Qt.Horizontal)
        self.g_slider.setRange(0, 255)
        self.b_slider = QSlider(Qt.Horizontal)
        self.b_slider.setRange(0, 255)
        self.r_val_label = QLabel("0")
        self.g_val_label = QLabel("0")
        self.b_val_label = QLabel("0")
        row_rgb.addWidget(QLabel("R"))
        row_rgb.addWidget(self.r_slider)
        row_rgb.addWidget(self.r_val_label)
        row_rgb.addWidget(QLabel("G"))
        row_rgb.addWidget(self.g_slider)
        row_rgb.addWidget(self.g_val_label)
        row_rgb.addWidget(QLabel("B"))
        row_rgb.addWidget(self.b_slider)
        row_rgb.addWidget(self.b_val_label)
        cfg_layout.addLayout(row_rgb)
        # sync initial values and connect
        self._sync_rgb_sliders_to_current()
        self.r_slider.valueChanged.connect(self._on_rgb_changed)
        self.g_slider.valueChanged.connect(self._on_rgb_changed)
        self.b_slider.valueChanged.connect(self._on_rgb_changed)

        # Current color row (moved from Colors tab)
        rowc = QHBoxLayout()
        rowc.addWidget(QLabel("Current Color:"))
        self.current_color_display = ColorDisplay(self._current_qcolor)
        def _open_color_dialog():
            self.pick_current_color()
        self.current_color_display.clicked.connect(_open_color_dialog)
        rowc.addWidget(self.current_color_display)
        btn_pick = QPushButton("Pick…")
        btn_pick.clicked.connect(self.pick_current_color)
        rowc.addWidget(btn_pick)
        cfg_layout.addLayout(rowc)

        # Selection actions (moved from Colors tab)
        row_actions = QHBoxLayout()
        btn_apply_sel = QPushButton("Apply To Selection")
        btn_apply_sel.clicked.connect(self.apply_color_to_selection)
        row_actions.addWidget(btn_apply_sel)
        btn_clear_sel = QPushButton("Clear Selection")
        btn_clear_sel.clicked.connect(self.clear_selection)
        row_actions.addWidget(btn_clear_sel)
        btn_save_color = QPushButton("Save Color")
        btn_save_color.clicked.connect(self.save_current_color_to_palette)
        row_actions.addWidget(btn_save_color)
        cfg_layout.addLayout(row_actions)

        # Saved colors palette (moved from Colors tab)
        cfg_layout.addWidget(QLabel("Saved Colors:"))
        self.palette_container = QWidget()
        self.palette_layout = QHBoxLayout(self.palette_container)
        self.palette_layout.setContentsMargins(0, 0, 0, 0)
        cfg_layout.addWidget(self.palette_container)
        self._refresh_palette_ui()

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

        # System tray for daemon mode
        self._daemon_mode = False
        self._setup_tray()
        self._apply_dark_mode(True)

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
        self._save_baseline_from_ui()
        # reload palette and clear selection
        self._saved_colors = self.config.load_palette()
        self._refresh_palette_ui()
        self.clear_selection()

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
            # Blank active window -> load baseline
            self.current_app = "Unknown"
            if hasattr(self, 'current_app_label'):
                self.current_app_label.setText("Current App: Unknown")
            self._pressed_keys.clear()
            self._restore_baseline_to_ui()
            return
        logger.info(f"Active app changed: {app_class}")
        self.current_app = app_class
        if hasattr(self, 'current_app_label'):
            self.current_app_label.setText(f"Current App: {self.current_app}")
        # Clear combo state on app switch
        self._pressed_keys.clear()
        if not self.short_enabled.isChecked():
            return
        prof = self._get_cached_profile(app_class)
        if prof:
            mode = getattr(prof, 'default_mode', 'keys')
            if mode == 'none':
                # Do not change defaults; use baseline
                self._restore_baseline_to_ui()
            elif mode == 'config':
                cfg = getattr(prof, 'default_config_name', '') or ''
                if cfg:
                    self._apply_config_as_default(cfg)
                else:
                    self._restore_baseline_to_ui()
            elif getattr(prof, 'default_keys', None):
                self._apply_profile_default(prof)
            else:
                gprof = self._get_global_profile()
                if gprof and getattr(gprof, 'default_keys', None):
                    self._apply_default_keys(gprof.default_keys, QColor(*gprof.color))
                else:
                    self._restore_baseline_to_ui()
        else:
            gprof = self._get_global_profile()
            if gprof and getattr(gprof, 'default_keys', None):
                self._apply_default_keys(gprof.default_keys, QColor(*gprof.color))
            else:
                self._restore_baseline_to_ui()

    # evdev key tracking
    def _on_key_press(self, key_name: str) -> None:
        logger.info(f"Key press: {key_name}")
        # Track pressed keys
        self._pressed_keys.add(key_name)
        if not self.short_enabled.isChecked():
            return
        prof = self._get_cached_profile(self.current_app)
        if not prof:
            return
        # Root trigger: Win + Delete
        if 'Win' in self._pressed_keys and 'Delete' in self._pressed_keys:
            self._apply_profile_default(prof)
            return
        # Combo highlighting
        self._apply_combo_highlights_if_any(prof)

    def _on_key_release(self, key_name: str) -> None:
        if key_name in self._pressed_keys:
            self._pressed_keys.remove(key_name)
        if not self.short_enabled.isChecked():
            return
        prof = self._get_cached_profile(self.current_app)
        if not prof:
            return
        # If any combo still active, re-apply; else restore according to default_mode
        if 'Win' in self._pressed_keys and 'Delete' in self._pressed_keys:
            self._apply_profile_default(prof)
            return
        if self._has_active_modifiers():
            self._apply_combo_highlights_if_any(prof)
        else:
            mode = getattr(prof, 'default_mode', 'keys')
            if mode == 'none':
                self._restore_baseline_to_ui()
            elif mode == 'config':
                cfg = getattr(prof, 'default_config_name', '') or ''
                if cfg:
                    self._apply_config_as_default(cfg)
                else:
                    self._restore_baseline_to_ui()
            else:
                if self._view_state != 'app_default':
                    self._apply_profile_default(prof)
                else:
                    self.apply_ui_colors()

    def _apply_profile_default(self, prof: AppProfile) -> None:
        logger.info(f"Applying profile defaults for {prof.name}")
        if self._view_state != 'app_default':
            # clear
            for k in self.keys:
                k.setKeyColor(QColor(0, 0, 0))
            color = QColor(*prof.color)
            for name in (prof.default_keys or []):
                self._highlight_key(name, color)
            self._view_state = 'app_default'
            self._last_combo_key = None
        self.apply_ui_colors()

    def _apply_default_keys(self, keys: List[str], color: QColor) -> None:
        if self._view_state != 'app_default':
            for k in self.keys:
                k.setKeyColor(QColor(0, 0, 0))
            for name in (keys or []):
                self._highlight_key(name, color)
            self._view_state = 'app_default'
            self._last_combo_key = None
        self.apply_ui_colors()

    def _apply_config_as_default(self, config_name: str) -> None:
        cfg = self.config.load(config_name)
        if not cfg:
            self._restore_baseline_to_ui()
            return
        colors = cfg.get('colors', [])
        for i, key in enumerate(self.keys):
            if i < len(colors):
                r, g, b = colors[i]
                key.setKeyColor(QColor(int(r), int(g), int(b)))
            else:
                key.setKeyColor(QColor(0, 0, 0))
        self._view_state = 'app_default'
        self._last_combo_key = None
        self.apply_ui_colors()

    def _apply_combo_highlights_if_any(self, prof: AppProfile) -> None:
        mods = self._current_modifiers()
        if not mods:
            return
        # Build key like Ctrl+Shift etc (sorted for stable lookup)
        key = "+".join(sorted(mods))
        combos = prof.combos or {}
        keys_to_highlight = combos.get(key)
        if not keys_to_highlight:
            # Fallback to global profile combos
            gprof = self._get_global_profile()
            if gprof and (gprof.combos or {}):
                keys_to_highlight = (gprof.combos or {}).get(key)
        # Order-insensitive fallback for modifier-only keys
        if not keys_to_highlight:
            for k, v in (combos or {}).items():
                parts = [p.strip() for p in k.split('+') if p.strip()]
                if all(p in ['Ctrl', 'Shift', 'Alt', 'Win'] for p in parts):
                    if sorted(parts) == sorted(mods):
                        keys_to_highlight = v
                        break
        if not keys_to_highlight:
            gprof = self._get_global_profile()
            if gprof and (gprof.combos or {}):
                for k, v in (gprof.combos or {}).items():
                    parts = [p.strip() for p in k.split('+') if p.strip()]
                    if all(p in ['Ctrl', 'Shift', 'Alt', 'Win'] for p in parts):
                        if sorted(parts) == sorted(mods):
                            keys_to_highlight = v
                            break
        if not keys_to_highlight:
            return
        if self._view_state != 'combo' or self._last_combo_key != key:
            for k in self.keys:
                k.setKeyColor(QColor(0, 0, 0))
            color = QColor(*prof.color)
            for name in keys_to_highlight:
                self._highlight_key(name, color)
            for m in mods:
                self._highlight_key(m, QColor(255, 200, 80))
            self._view_state = 'combo'
            self._last_combo_key = key
        self.apply_ui_colors()

    def _current_modifiers(self) -> List[str]:
        mods = []
        for m in ['Ctrl', 'Shift', 'Alt', 'Win']:
            if m in self._pressed_keys:
                mods.append(m)
        return mods

    def _has_active_modifiers(self) -> bool:
        return any(m in self._pressed_keys for m in ['Ctrl', 'Shift', 'Alt', 'Win'])

    def _save_baseline_from_ui(self) -> None:
        self._baseline_colors = self._current_ui_colors()

    def _restore_baseline_to_ui(self) -> None:
        if not self._baseline_colors:
            return
        for i, key in enumerate(self.keys):
            if i < len(self._baseline_colors):
                r, g, b = self._baseline_colors[i]
                key.setKeyColor(QColor(r, g, b))
        self._view_state = 'baseline'
        self._last_combo_key = None
        self.apply_ui_colors()

    def _get_global_profile(self) -> AppProfile:
        if not hasattr(self, '_global_profile_cache'):
            self._global_profile_cache = None
        if self._global_profile_cache is None:
            self._global_profile_cache = self.profiles.load('global')
        return self._global_profile_cache


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

    # Additional presets
    def apply_ocean_preset(self) -> None:
        logger.info("Preset: ocean")
        n = len(self.keys)
        for i, key in enumerate(self.keys):
            h = 0.55 + 0.1 * (i / max(1, n))
            r, g, b = _hsv_to_rgb(h % 1.0, 0.7, 1.0)
            key.setKeyColor(QColor(r, g, b))
        self.apply_ui_colors()

    def apply_sunset_preset(self) -> None:
        logger.info("Preset: sunset")
        n = len(self.keys)
        for i, key in enumerate(self.keys):
            h = 0.03 + 0.1 * (i / max(1, n))
            r, g, b = _hsv_to_rgb(h % 1.0, 0.9, 1.0)
            key.setKeyColor(QColor(r, g, b))
        self.apply_ui_colors()

    def apply_matrix_preset(self) -> None:
        logger.info("Preset: matrix")
        for key in self.keys:
            key.setKeyColor(QColor(0, 20, 0))
        cols = [k for k in self.keys if hasattr(k, 'key_name')]
        for i, key in enumerate(cols):
            if i % 3 == 0:
                key.setKeyColor(QColor(0, 255, 70))
        self.apply_ui_colors()

    def apply_fire_preset(self) -> None:
        logger.info("Preset: fire")
        n = len(self.keys)
        for i, key in enumerate(self.keys):
            h = 0.02 + 0.05 * (i % 10) / 10.0
            r, g, b = _hsv_to_rgb(h, 1.0, 1.0)
            key.setKeyColor(QColor(r, g, b))
        self.apply_ui_colors()

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
            if hasattr(self, 'current_color_display'):
                self.current_color_display.setColor(c)
            # sync sliders
            if hasattr(self, 'r_slider'):
                self._sync_rgb_sliders_to_current()

    def handle_key_click(self, key) -> None:
        # KeyboardLayout expects this method on parent
        try:
            idx = getattr(key, 'index', None)
            if idx is None:
                return
            mods = QApplication.keyboardModifiers()
            shift = bool(mods & Qt.ShiftModifier)
            ctrl = bool(mods & Qt.ControlModifier)

            if shift and self.last_clicked_index is not None:
                a = min(self.last_clicked_index, idx)
                b = max(self.last_clicked_index, idx)
                if not ctrl:
                    self.selected_indices = set(range(a, b + 1))
                else:
                    # union the range with current selection
                    self.selected_indices.update(range(a, b + 1))
            elif ctrl:
                if idx in self.selected_indices:
                    self.selected_indices.remove(idx)
                else:
                    self.selected_indices.add(idx)
                self.last_clicked_index = idx
            else:
                self.selected_indices = {idx}
                self.last_clicked_index = idx

            self._update_selection_visuals()

            # Preserve previous behavior: clicking paints the clicked key with current color
            c = getattr(self, '_current_qcolor', QColor(0, 255, 0))
            if hasattr(key, 'setKeyColor'):
                key.setKeyColor(c)
                self.apply_ui_colors()
        except Exception:
            pass

    def clear_selection(self) -> None:
        self.selected_indices = set()
        self.last_clicked_index = None
        self._update_selection_visuals()

    def _update_selection_visuals(self) -> None:
        for k in self.keys:
            try:
                k.setSelected(getattr(k, 'index', -1) in self.selected_indices)
            except Exception:
                pass

    def apply_color_to_selection(self) -> None:
        if not self.selected_indices:
            return
        c = getattr(self, '_current_qcolor', QColor(0, 255, 0))
        for k in self.keys:
            idx = getattr(k, 'index', None)
            if idx in self.selected_indices and hasattr(k, 'setKeyColor'):
                k.setKeyColor(c)
        self.apply_ui_colors()

    def save_current_color_to_palette(self) -> None:
        c = getattr(self, '_current_qcolor', QColor(0, 255, 0))
        rgb = (int(c.red()), int(c.green()), int(c.blue()))
        if rgb not in self._saved_colors:
            self._saved_colors.append(rgb)
            # keep palette reasonably small
            if len(self._saved_colors) > 24:
                self._saved_colors = self._saved_colors[-24:]
            self.config.save_palette(self._saved_colors)
            self._refresh_palette_ui()

    def _refresh_palette_ui(self) -> None:
        if not hasattr(self, 'palette_layout') or self.palette_layout is None:
            return
        # clear existing widgets
        while self.palette_layout.count():
            item = self.palette_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
        # add each saved color as a small swatch
        for (r, g, b) in (self._saved_colors or []):
            swatch = ColorDisplay(QColor(int(r), int(g), int(b)))
            def _make_setter(color_tuple):
                def _on_click():
                    self._set_current_color_from_palette(color_tuple)
                return _on_click
            swatch.clicked.connect(_make_setter((int(r), int(g), int(b))))
            self.palette_layout.addWidget(swatch)

    def _set_current_color_from_palette(self, rgb: Tuple[int, int, int]) -> None:
        self._current_qcolor = QColor(int(rgb[0]), int(rgb[1]), int(rgb[2]))
        if hasattr(self, 'current_color_display'):
            self.current_color_display.setColor(self._current_qcolor)
        if hasattr(self, 'r_slider'):
            self._sync_rgb_sliders_to_current()

    def _on_rgb_changed(self) -> None:
        try:
            r = int(self.r_slider.value())
            g = int(self.g_slider.value())
            b = int(self.b_slider.value())
            self._current_qcolor = QColor(r, g, b)
            if hasattr(self, 'current_color_display'):
                self.current_color_display.setColor(self._current_qcolor)
            self._update_rgb_value_labels(r, g, b)
        except Exception:
            pass

    def _sync_rgb_sliders_to_current(self) -> None:
        c = getattr(self, '_current_qcolor', QColor(0, 255, 0))
        if hasattr(self, 'r_slider'):
            self.r_slider.setValue(int(c.red()))
            self.g_slider.setValue(int(c.green()))
            self.b_slider.setValue(int(c.blue()))
        self._update_rgb_value_labels(int(c.red()), int(c.green()), int(c.blue()))

    def _update_rgb_value_labels(self, r: int, g: int, b: int) -> None:
        if hasattr(self, 'r_val_label'):
            self.r_val_label.setText(str(int(r)))
        if hasattr(self, 'g_val_label'):
            self.g_val_label.setText(str(int(g)))
        if hasattr(self, 'b_val_label'):
            self.b_val_label.setText(str(int(b)))

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

    # Tray / Daemon Mode
    def _setup_tray(self) -> None:
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.windowIcon())
        menu = QMenu()
        act_show = QAction("Show Window", self)
        act_show.triggered.connect(self.showNormal)
        menu.addAction(act_show)

        act_toggle_profiles = QAction("Toggle App Profiles", self)
        def _toggle_profiles():
            if hasattr(self, 'short_enabled'):
                self.short_enabled.setChecked(not self.short_enabled.isChecked())
        act_toggle_profiles.triggered.connect(_toggle_profiles)
        menu.addAction(act_toggle_profiles)

        # Dark mode toggle
        self._dark_mode = True
        self._dark_action = QAction("Enable Dark Mode", self)
        def _toggle_dark():
            self._dark_mode = not self._dark_mode
            self._apply_dark_mode(self._dark_mode)
            self._dark_action.setText("Disable Dark Mode" if self._dark_mode else "Enable Dark Mode")
        self._dark_action.triggered.connect(_toggle_dark)
        menu.addAction(self._dark_action)

        # Config submenu
        self._configs_menu = QMenu("Configs", self)
        menu.addMenu(self._configs_menu)
        self._populate_configs_menu()
        # Import/Export from tray
        act_import = QAction("Import Config…", self)
        act_import.triggered.connect(self.import_config_dialog)
        self._configs_menu.addAction(act_import)
        act_export = QAction("Export Current…", self)
        act_export.triggered.connect(self.export_config_dialog)
        self._configs_menu.addAction(act_export)

        # Presets submenu
        presets_menu = QMenu("Presets", self)
        for title, handler in [
            ("Coding", self.apply_coding_preset),
            ("Gaming", self.apply_gaming_preset),
            ("Movie", self.apply_movie_preset),
            ("Rainbow", self.apply_rainbow_preset),
            ("Stars", self.apply_stars_preset),
            ("Ocean", lambda: preset_mod.apply_ocean(self)),
            ("Sunset", lambda: preset_mod.apply_sunset(self)),
            ("Matrix", lambda: preset_mod.apply_matrix(self)),
            ("Fire", lambda: preset_mod.apply_fire(self)),
            ("Firefox", lambda: preset_mod.apply_firefox_preset(self)),
            ("Dolphin", lambda: preset_mod.apply_dolphin_preset(self)),
            ("VS Code", lambda: preset_mod.apply_vscode_preset(self)),
        ]:
            act = QAction(title, self)
            act.triggered.connect(handler)
            presets_menu.addAction(act)
        menu.addMenu(presets_menu)

        self._daemon_action = QAction("Enter Daemon Mode", self)
        self._daemon_action.triggered.connect(self.toggle_daemon_mode)
        menu.addAction(self._daemon_action)

        menu.addSeparator()
        # Manage profiles from tray
        act_profiles = QAction("Manage Profiles...", self)
        act_profiles.triggered.connect(self.open_profiles_dialog)
        menu.addAction(act_profiles)

        act_quit = QAction("Quit", self)
        act_quit.triggered.connect(self._quit)
        menu.addAction(act_quit)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _populate_configs_menu(self) -> None:
        if not hasattr(self, '_configs_menu') or self._configs_menu is None:
            return
        self._configs_menu.clear()
        for name in self.config.list_configs():
            act = QAction(name, self)
            def _make_loader(n):
                return lambda: self.load_config(n)
            act.triggered.connect(_make_loader(name))
            self._configs_menu.addAction(act)

    # Import/Export handlers
    def import_config_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import Config", "", "Config JSON (*.json)")
        if not path:
            return
        result = self.config.import_file(path)
        if result:
            self.combo.clear()
            self.combo.addItems(self.config.list_configs())
            self.combo.setCurrentText(result)
            self.load_config(result)
            self._populate_configs_menu()
        else:
            QMessageBox.warning(self, "Import Failed", "Could not import the selected config file.")

    def export_config_dialog(self) -> None:
        name = self.combo.currentText()
        if not name:
            QMessageBox.information(self, "No Config", "Please select a config to export.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Config", f"{name}.json", "Config JSON (*.json)")
        if not path:
            return
        ok = self.config.export_file(name, path)
        if not ok:
            QMessageBox.warning(self, "Export Failed", "Could not export the config.")

    def toggle_daemon_mode(self) -> None:
        self._daemon_mode = not self._daemon_mode
        if self._daemon_mode:
            self.hide()
            self._daemon_action.setText("Exit Daemon Mode")
            if self.tray_icon:
                self.tray_icon.showMessage("Sinodragon", "Running in background.")
        else:
            self.showNormal()
            self._daemon_action.setText("Enter Daemon Mode")

    def _on_tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.showNormal()

    def _quit(self) -> None:
        QApplication.instance().quit()

    def _apply_dark_mode(self, enabled: bool) -> None:
        app = QApplication.instance()
        if not app:
            return
        if not enabled:
            app.setPalette(QPalette())
            return
        p = QPalette()
        p.setColor(QPalette.Window, QColor(53, 53, 53))
        p.setColor(QPalette.WindowText, QColor(220, 220, 220))
        p.setColor(QPalette.Base, QColor(35, 35, 35))
        p.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        p.setColor(QPalette.ToolTipBase, QColor(220, 220, 220))
        p.setColor(QPalette.ToolTipText, QColor(220, 220, 220))
        p.setColor(QPalette.Text, QColor(220, 220, 220))
        p.setColor(QPalette.Button, QColor(53, 53, 53))
        p.setColor(QPalette.ButtonText, QColor(220, 220, 220))
        p.setColor(QPalette.BrightText, QColor(255, 0, 0))
        p.setColor(QPalette.Highlight, QColor(42, 130, 218))
        p.setColor(QPalette.HighlightedText, QColor(0, 0, 0))
        app.setPalette(p)

def _hsv_to_rgb(h: float, s: float, v: float) -> Tuple[int, int, int]:
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return int(r * 255), int(g * 255), int(b * 255)


