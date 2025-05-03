import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QPushButton, 
                           QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
                           QComboBox, QColorDialog, QLineEdit, QMessageBox, QSlider,
                           QGroupBox, QCheckBox, QFrame, QSplitter, QSpinBox,
                           QSystemTrayIcon, QMenu, QAction, QTableWidgetItem, QTableWidget, QDialog)
from PyQt5.QtGui import QColor, QPalette, QFont, QKeySequence
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QEvent
import time
import colorsys
import threading
from pynput import keyboard as pynput_keyboard
import os

from keyboard_controller import KeyboardController
from config_manager import ConfigManager
from shortcut_manager import ShortcutManager
from shortcut_lighting import ShortcutLighting
from features.text_display import TextDisplayFeature
from features.effects import EffectsFeature
from features.system_monitor import SystemMonitorFeature

# Define a key mapping between Qt key constants and our keyboard layout key names
QT_KEY_MAP = {
    Qt.Key_Control: "Ctrl",
    Qt.Key_Shift: "Shift",
    Qt.Key_Alt: "Alt",
    Qt.Key_Meta: "Win",
    Qt.Key_Super_L: "Win",
    Qt.Key_Super_R: "Win",
    
    # Letters
    Qt.Key_A: "A", Qt.Key_B: "B", Qt.Key_C: "C", Qt.Key_D: "D",
    Qt.Key_E: "E", Qt.Key_F: "F", Qt.Key_G: "G", Qt.Key_H: "H",
    Qt.Key_I: "I", Qt.Key_J: "J", Qt.Key_K: "K", Qt.Key_L: "L",
    Qt.Key_M: "M", Qt.Key_N: "N", Qt.Key_O: "O", Qt.Key_P: "P",
    Qt.Key_Q: "Q", Qt.Key_R: "R", Qt.Key_S: "S", Qt.Key_T: "T",
    Qt.Key_U: "U", Qt.Key_V: "V", Qt.Key_W: "W", Qt.Key_X: "X",
    Qt.Key_Y: "Y", Qt.Key_Z: "Z",
    
    # Numbers
    Qt.Key_0: "0", Qt.Key_1: "1", Qt.Key_2: "2", Qt.Key_3: "3",
    Qt.Key_4: "4", Qt.Key_5: "5", Qt.Key_6: "6", Qt.Key_7: "7",
    Qt.Key_8: "8", Qt.Key_9: "9",
    
    # Function keys
    Qt.Key_F1: "F1", Qt.Key_F2: "F2", Qt.Key_F3: "F3", Qt.Key_F4: "F4",
    Qt.Key_F5: "F5", Qt.Key_F6: "F6", Qt.Key_F7: "F7", Qt.Key_F8: "F8",
    Qt.Key_F9: "F9", Qt.Key_F10: "F10", Qt.Key_F11: "F11", Qt.Key_F12: "F12",
    
    # Other common keys
    Qt.Key_Escape: "Esc",
    Qt.Key_Tab: "Tab",
    Qt.Key_CapsLock: "Caps",
    Qt.Key_Backspace: "Bksp",
    Qt.Key_Return: "Enter",
    Qt.Key_Space: "Space",
    Qt.Key_Insert: "Ins",
    Qt.Key_Delete: "Del",
    Qt.Key_Home: "Home",
    Qt.Key_End: "End",
    Qt.Key_PageUp: "PgUp",
    Qt.Key_PageDown: "PgDn",
    Qt.Key_Left: "←",
    Qt.Key_Right: "→",
    Qt.Key_Up: "↑",
    Qt.Key_Down: "↓",
    Qt.Key_Print: "PrtSc",
    Qt.Key_ScrollLock: "ScrLk",
    Qt.Key_Pause: "Pause",
    
    # Special characters
    Qt.Key_Backslash: "\\",
    Qt.Key_BracketLeft: "[",
    Qt.Key_BracketRight: "]",
    Qt.Key_Semicolon: ";",
    Qt.Key_Apostrophe: "'",
    Qt.Key_Comma: ",",
    Qt.Key_Period: ".",
    Qt.Key_Slash: "/",
    Qt.Key_Minus: "-",
    Qt.Key_Equal: "=",
    Qt.Key_QuoteLeft: "`"
}

class CustomKeyEvent(QEvent):
    """Custom event for key presses from alternative input sources"""
    KeyPress = QEvent.Type(QEvent.registerEventType())
    KeyRelease = QEvent.Type(QEvent.registerEventType()) 
    
    def __init__(self, event_type, key_name):
        super().__init__(event_type)
        self.key_name = key_name

class KeyButton(QPushButton):
    def __init__(self, key_name, index, parent=None):
        super().__init__(key_name, parent)
        self.key_name = key_name
        self.index = index
        self.color = QColor(0, 255, 0)  # Default color: green
        self.setFixedSize(60, 60)
        self.selected = False
        self.updateStyle()
        
    def setKeyColor(self, color):
        """Set the button color"""
        self.color = color
        self.updateStyle()
    
    def setSelected(self, selected):
        """Set selection state"""
        self.selected = selected
        self.updateStyle()
    
    def updateStyle(self):
        """Update the button style to reflect the current color and selection state"""
        r, g, b = self.color.red(), self.color.green(), self.color.blue()
        text_color = "#000000" if (r + g + b) > 380 else "#FFFFFF"
        
        border = "3px solid #FFFFFF" if self.selected else "1px solid #222222"
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: rgb({r}, {g}, {b});
                color: {text_color};
                border: {border};
                border-radius: 5px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: rgb({min(r+20, 255)}, {min(g+20, 255)}, {min(b+20, 255)});
                border-width: 2px;
            }}
        """)

class ColorDisplay(QFrame):
    clicked = pyqtSignal()
    
    def __init__(self, color=Qt.green, parent=None):
        super().__init__(parent)
        self.color = QColor(color)
        self.setMinimumSize(60, 30)
        self.setFrameShape(QFrame.Box)
        self.setFrameShadow(QFrame.Sunken)
        self.updateStyle()
        
    def setColor(self, color):
        self.color = QColor(color)
        self.updateStyle()
        
    def updateStyle(self):
        self.setStyleSheet(f"background-color: rgb({self.color.red()}, {self.color.green()}, {self.color.blue()});")
    
    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

class KeyboardConfigApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.keyboard = KeyboardController()
        self.config_manager = ConfigManager()
        self.shortcut_manager = ShortcutManager()
        self.keys = []
        self.selected_keys = []
        self.current_color = QColor(0, 255, 0)  # Default working color is green
        self.selection_mode = False
        
        # Add auto-connect option, default to true
        self.auto_connect = True
        
        # Setup auto-reload before calling load_config
        self.auto_reload = True
        self.reload_timer = QTimer()
        self.reload_timer.timeout.connect(self.send_config)
        
        # Save keyboard layout on first run
        layout = self.shortcut_manager.load_keyboard_layout()
        if not layout:
            self.save_keyboard_layout()
        
        # Create the shortcut lighting manager BEFORE setting up the UI
        self.shortcut_lighting = ShortcutLighting(self)
        
        # Add a timer for debouncing slider changes
        self.intensity_timer = QTimer()
        self.intensity_timer.setSingleShot(True)
        self.intensity_timer.timeout.connect(self.apply_intensity)
        
        # Setup UI after shortcut_lighting is created
        self.setupUI()
        
        # Setup system tray
        self.setupSystemTray()
        
        # Load default configuration
        self.load_config()
        
        # Auto-connect to keyboard if enabled
        if self.auto_connect:
            QTimer.singleShot(500, self.connect_to_keyboard)
        
        # Install event filter to catch key events
        QApplication.instance().installEventFilter(self)
        
        # Create text display feature
        self.text_display = TextDisplayFeature(self)
        self.effects = EffectsFeature(self)
        
        # Create flag for daemon mode
        self.daemon_mode = False
        
        # Initialize global monitoring variables
        self.global_listener = None
        self.global_keys_pressed = set()
        self.is_monitoring_shortcuts = False
    
    def eventFilter(self, obj, event):
        """Filter keyboard events for shortcut highlighting"""
        if event.type() == QEvent.KeyPress:
            key = event.key()
            if key in QT_KEY_MAP:
                key_name = QT_KEY_MAP[key]
                self.shortcut_lighting.handle_key_press(key_name)
            
        elif event.type() == QEvent.KeyRelease:
            key = event.key()
            if key in QT_KEY_MAP:
                key_name = QT_KEY_MAP[key]
                self.shortcut_lighting.handle_key_release(key_name)
        
        return super().eventFilter(obj, event)
    
    def setupUI(self):
        self.setWindowTitle("Keyboard LED Configuration")
        self.setMinimumSize(1100, 650)
        
        # Main widget and layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # Top control panel
        control_panel = QHBoxLayout()
        
        # Config selection
        config_label = QLabel("Configuration:")
        self.config_combo = QComboBox()
        self.config_combo.addItems(self.config_manager.get_config_list())
        self.config_combo.currentTextChanged.connect(self.load_config)
        
        # Config name
        self.config_name = QLineEdit("Default Green")
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_config)
        
        # Connect button
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.toggle_connection)
        
        # Apply button
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self.send_config)
        
        # Device Info button
        device_info_button = QPushButton("Device Info")
        device_info_button.clicked.connect(self.show_device_info)
        
        # Add controls to panel
        control_panel.addWidget(config_label)
        control_panel.addWidget(self.config_combo)
        control_panel.addWidget(QLabel("Name:"))
        control_panel.addWidget(self.config_name)
        control_panel.addWidget(save_button)
        control_panel.addStretch()
        control_panel.addWidget(self.connect_button)
        control_panel.addWidget(apply_button)
        control_panel.addWidget(device_info_button)
        
        main_layout.addLayout(control_panel)
        
        # Side-by-side layout for keyboard and controls using a splitter
        keyboard_controls_layout = QHBoxLayout()
        
        # Create a splitter for keyboard and controls
        self.main_splitter = QSplitter(Qt.Horizontal)
        
        # Keyboard layout widget
        keyboard_widget = QWidget()
        keyboard_container = QVBoxLayout(keyboard_widget)
        keyboard_grid = QGridLayout()
        keyboard_grid.setSpacing(5)
        
        # Define keyboard layout
        layout_def = [
            ["Esc", "`", "Tab", "Caps", "Shift", "Ctrl"],
            ["F1", "1", "Q", "A", "Z", "Win"],
            ["F2", "2", "W", "S", "X", "Alt"],
            ["F3", "3", "E", "D", "C", "NAN"],
            ["F4", "4", "R", "F", "V", "NAN"],
            ["F5", "5", "T", "G", "B", "Space"],
            ["F6", "6", "Y", "H", "N", "NAN"],
            ["F7", "7", "U", "J", "M", "NAN"],
            ["F8", "8", "I", "K", ",", "Alt"],
            ["F9", "9", "O", "L", ".", "Fn"],
            ["F10", "0", "P", ";", "/", "Ctrl"],
            ["F11", "-", "[", "'", "NAN", "NAN"],
            ["F12", "=", "]", "NAN", "NAN", "NAN"],
            ["PrtSc", "Bksp", "\\", "Enter", "Shift", "←"],
            ["Pause", "NAN", "NAN", "NAN", "↑", "↓"],
            ["Del", "Home", "End", "PgUp", "PgDn", "→"]
        ]
        
        # Create buttons for each key
        key_index = 0
        for col, column in enumerate(layout_def):
            for row, key_name in enumerate(column):
                if key_name != "NAN":
                    key = KeyButton(key_name, key_index, self)
                    key.clicked.connect(lambda checked, k=key: self.key_clicked(k))
                    keyboard_grid.addWidget(key, row, col)
                    self.keys.append(key)
                    key_index += 1
                else:
                    # Empty placeholder for NAN keys
                    placeholder = QWidget()
                    placeholder.setFixedSize(60, 60)
                    keyboard_grid.addWidget(placeholder, row, col)
        
        keyboard_container.addLayout(keyboard_grid)
        
        # Global brightness control
        brightness_layout = QHBoxLayout()
        brightness_layout.addWidget(QLabel("Master Brightness:"))
        
        self.intensity_slider = QSlider(Qt.Horizontal)
        self.intensity_slider.setMinimum(0)
        self.intensity_slider.setMaximum(100)
        self.intensity_slider.setValue(100)  # Default to full brightness
        self.intensity_slider.setTickPosition(QSlider.TicksBelow)
        self.intensity_slider.setTickInterval(10)
        self.intensity_slider.valueChanged.connect(self.intensity_changed)
        brightness_layout.addWidget(self.intensity_slider)
        
        # Intensity value label
        self.intensity_label = QLabel("100%")
        brightness_layout.addWidget(self.intensity_label)
        
        keyboard_container.addLayout(brightness_layout)
        
        # Add the keyboard widget to the splitter
        self.main_splitter.addWidget(keyboard_widget)
        
        # Controls panel in a widget
        controls_widget = QWidget()
        controls_panel = QVBoxLayout(controls_widget)
        
        # Add auto-reload toggle to the top of controls panel
        auto_reload_group = QGroupBox("Auto-Apply")
        auto_reload_layout = QVBoxLayout()
        self.auto_reload_btn = QPushButton("Auto-Reload: ON")
        self.auto_reload_btn.setCheckable(True)
        self.auto_reload_btn.setChecked(True)
        self.auto_reload_btn.clicked.connect(self.toggle_auto_reload)
        auto_reload_layout.addWidget(self.auto_reload_btn)
        auto_reload_group.setLayout(auto_reload_layout)
        controls_panel.addWidget(auto_reload_group)
        
        # Current color selection
        color_group = QGroupBox("Current Color")
        color_layout = QVBoxLayout()
        
        # Color display - shows the currently selected color
        self.color_display = ColorDisplay(self.current_color)
        self.color_display.clicked.connect(self.choose_current_color)
        color_layout.addWidget(self.color_display)
        
        # Quick color buttons
        quick_colors_layout = QGridLayout()
        standard_colors = [
            (255, 0, 0), (0, 255, 0), (0, 0, 255),  # Red, Green, Blue
            (255, 255, 0), (0, 255, 255), (255, 0, 255),  # Yellow, Cyan, Magenta
            (255, 255, 255), (0, 0, 0), (128, 128, 128)  # White, Black, Gray
        ]
        
        row, col = 0, 0
        for r, g, b in standard_colors:
            color_btn = QPushButton()
            color_btn.setFixedSize(40, 30)
            color_btn.setStyleSheet(f"background-color: rgb({r}, {g}, {b}); border: 1px solid black;")
            color_btn.clicked.connect(lambda checked, color=(r, g, b): self.set_current_color(color))
            quick_colors_layout.addWidget(color_btn, row, col)
            col += 1
            if col > 2:  # 3 columns
                col = 0
                row += 1
        
        color_layout.addLayout(quick_colors_layout)
        
        # Custom color button
        custom_color_btn = QPushButton("Custom Color...")
        custom_color_btn.clicked.connect(self.choose_current_color)
        color_layout.addWidget(custom_color_btn)
        
        # Apply to all button
        apply_all_btn = QPushButton("Apply to All Keys")
        apply_all_btn.clicked.connect(self.apply_current_color_to_all)
        color_layout.addWidget(apply_all_btn)
        
        color_group.setLayout(color_layout)
        controls_panel.addWidget(color_group)
        
        # Selection mode group
        selection_group = QGroupBox("Region Selection")
        selection_layout = QVBoxLayout()
        
        # Toggle selection mode
        self.selection_mode_toggle = QCheckBox("Selection Mode")
        self.selection_mode_toggle.toggled.connect(self.toggle_selection_mode)
        selection_layout.addWidget(self.selection_mode_toggle)
        
        # Selection controls
        selection_controls = QVBoxLayout()
        
        # Selected region color adjustment
        selection_color_btn = QPushButton("Apply Current Color to Region")
        selection_color_btn.clicked.connect(self.set_region_color)
        selection_controls.addWidget(selection_color_btn)
        
        # Selected region brightness
        selection_brightness_layout = QHBoxLayout()
        selection_brightness_layout.addWidget(QLabel("Region Brightness:"))
        
        self.region_intensity_slider = QSlider(Qt.Horizontal)
        self.region_intensity_slider.setMinimum(0)
        self.region_intensity_slider.setMaximum(100)
        self.region_intensity_slider.setValue(100)
        self.region_intensity_slider.valueChanged.connect(self.region_intensity_changed)
        selection_brightness_layout.addWidget(self.region_intensity_slider)
        
        self.region_intensity_label = QLabel("100%")
        selection_brightness_layout.addWidget(self.region_intensity_label)
        
        selection_controls.addLayout(selection_brightness_layout)
        
        # Clear selection button
        clear_selection_btn = QPushButton("Clear Selection")
        clear_selection_btn.clicked.connect(self.clear_selection)
        selection_controls.addWidget(clear_selection_btn)
        
        selection_layout.addLayout(selection_controls)
        selection_group.setLayout(selection_layout)
        controls_panel.addWidget(selection_group)
        
        # Presets group
        presets_group = QGroupBox("Presets")
        presets_layout = QVBoxLayout()
        
        # Function key preset
        function_keys_btn = QPushButton("Highlight Function Keys")
        function_keys_btn.clicked.connect(lambda: self.set_function_key_colors((255, 128, 0)))
        presets_layout.addWidget(function_keys_btn)

        # Add a few more useful presets
        gaming_preset_btn = QPushButton("Gaming Preset (WASD)")
        gaming_preset_btn.clicked.connect(self.apply_gaming_preset)
        presets_layout.addWidget(gaming_preset_btn)

        typing_preset_btn = QPushButton("Typing Preset")
        typing_preset_btn.clicked.connect(self.apply_typing_preset)
        presets_layout.addWidget(typing_preset_btn)

        presets_group.setLayout(presets_layout)
        controls_panel.addWidget(presets_group)
        
        # After the presets group, add shortcut monitoring controls
        shortcut_group = QGroupBox("Shortcut Monitoring")
        shortcut_layout = QVBoxLayout()
        
        # Enable/disable shortcut monitoring
        self.shortcut_toggle = QPushButton("Start Shortcut Monitor")
        self.shortcut_toggle.setCheckable(True)
        self.shortcut_toggle.clicked.connect(self.toggle_shortcut_monitor)
        shortcut_layout.addWidget(self.shortcut_toggle)
        
        # Highlight color selection
        highlight_color_layout = QHBoxLayout()
        highlight_color_layout.addWidget(QLabel("Highlight Color:"))
        
        self.highlight_color_display = ColorDisplay(self.shortcut_lighting.default_highlight_color)
        self.highlight_color_display.clicked.connect(self.choose_highlight_color)
        highlight_color_layout.addWidget(self.highlight_color_display)
        
        modifier_color_btn = QPushButton("Manage Modifier Colors...")
        modifier_color_btn.clicked.connect(self.manage_modifier_colors)
        shortcut_layout.addWidget(modifier_color_btn)
        
        # In the shortcut_group section, add a checkbox for global monitoring
        self.global_shortcut_checkbox = QCheckBox("Global Monitoring (System-wide)")
        self.global_shortcut_checkbox.setToolTip("Monitor keyboard shortcuts even when application is not in focus")
        shortcut_layout.addWidget(self.global_shortcut_checkbox)
        
        # Default config selection for when shortcut keys are released
        default_config_layout = QHBoxLayout()
        default_config_layout.addWidget(QLabel("Default Config:"))
        
        self.default_shortcut_config = QComboBox()
        self.default_shortcut_config.addItems(self.config_manager.get_config_list())
        self.default_shortcut_config.setCurrentText(self.shortcut_lighting.default_config_name)
        self.default_shortcut_config.currentTextChanged.connect(self.set_default_shortcut_config)
        default_config_layout.addWidget(self.default_shortcut_config)
        
        shortcut_layout.addLayout(default_config_layout)
        
        # Manage shortcuts button
        manage_shortcuts_btn = QPushButton("Manage Shortcuts")
        manage_shortcuts_btn.clicked.connect(self.manage_shortcuts)
        shortcut_layout.addWidget(manage_shortcuts_btn)
        
        # Add shortcut group to layout
        shortcut_group.setLayout(shortcut_layout)
        controls_panel.addWidget(shortcut_group)
        
        # # System monitoring group
        # system_monitor_group = QGroupBox("System Monitoring")
        # system_monitor_layout = QVBoxLayout()

        # # Add monitoring selection dropdown
        # system_monitor_layout.addWidget(QLabel("Select Monitoring:"))
        # self.monitor_combo = QComboBox()
        # self.monitor_combo.addItems([
        #     "CPU Usage", 
        #     "RAM Usage",
        #     "Battery Status",
        #     "All Metrics"
        # ])
        # system_monitor_layout.addWidget(self.monitor_combo)

        # # Add update interval slider
        # update_interval_layout = QHBoxLayout()
        # update_interval_layout.addWidget(QLabel("Update Interval:"))
        # self.update_interval_slider = QSlider(Qt.Horizontal)
        # self.update_interval_slider.setMinimum(1)
        # self.update_interval_slider.setMaximum(10)
        # self.update_interval_slider.setValue(2)
        # self.update_interval_slider.setTickPosition(QSlider.TicksBelow)
        # self.update_interval_slider.setTickInterval(1)
        # update_interval_layout.addWidget(self.update_interval_slider)
        # self.update_interval_label = QLabel("2s")
        # self.update_interval_slider.valueChanged.connect(
        #     lambda v: self.update_interval_label.setText(f"{v}s")
        # )
        # update_interval_layout.addWidget(self.update_interval_label)
        # system_monitor_layout.addLayout(update_interval_layout)

        ## Start/stop monitoring buttons
        # monitor_buttons_layout = QHBoxLayout()

        # self.start_monitor_btn = QPushButton("Start Monitoring")
        # self.start_monitor_btn.clicked.connect(self.start_system_monitoring)
        # monitor_buttons_layout.addWidget(self.start_monitor_btn)

        # self.stop_monitor_btn = QPushButton("Stop Monitoring")
        # self.stop_monitor_btn.clicked.connect(self.stop_system_monitoring)
        # monitor_buttons_layout.addWidget(self.stop_monitor_btn)

        # system_monitor_layout.addLayout(monitor_buttons_layout)

        # # Add the group to controls panel
        # system_monitor_group.setLayout(system_monitor_layout)
        # controls_panel.addWidget(system_monitor_group)
        
        # Create a group for effects
        effects_group = QGroupBox("Effects")
        effects_layout = QVBoxLayout()
        
        # Add effect selection dropdown
        effects_layout.addWidget(QLabel("Select Effect:"))
        self.effect_combo = QComboBox()
        self.effect_combo.addItems([
            "Rainbow Colors", 
            "Wave Effect",
            "Breathing Effect", 
            "Spectrum Cycle",
            "Starlight",
            "Ripple Effect",
            "Reactive Typing",
            "Gradient Flow"
        ])
        self.effect_combo.currentIndexChanged.connect(self.update_effect_options)
        effects_layout.addWidget(self.effect_combo)

        # Add effect options container (will be populated based on selection)
        self.effect_options_container = QWidget()
        self.effect_options_layout = QVBoxLayout(self.effect_options_container)
        effects_layout.addWidget(self.effect_options_container)

        # Add color selection for effects that need it
        self.effect_color_layout = QHBoxLayout()
        self.effect_color_layout.addWidget(QLabel("Effect Color:"))
        self.effect_color_display = ColorDisplay(QColor(0, 150, 255))  # Default cyan-blue
        self.effect_color_display.clicked.connect(self.choose_effect_color)
        self.effect_color_layout.addWidget(self.effect_color_display)
        self.effect_options_layout.addLayout(self.effect_color_layout)

        # Add speed control
        self.effect_speed_layout = QHBoxLayout()
        self.effect_speed_layout.addWidget(QLabel("Speed:"))
        self.effect_speed_slider = QSlider(Qt.Horizontal)
        self.effect_speed_slider.setMinimum(1)
        self.effect_speed_slider.setMaximum(20)
        self.effect_speed_slider.setValue(10)
        self.effect_speed_slider.setTickPosition(QSlider.TicksBelow)
        self.effect_speed_slider.setTickInterval(1)
        self.effect_speed_layout.addWidget(self.effect_speed_slider)
        self.effect_options_layout.addLayout(self.effect_speed_layout)

        # Duration control for applicable effects
        self.effect_duration_layout = QHBoxLayout()
        self.effect_duration_layout.addWidget(QLabel("Duration (sec):"))
        self.effect_duration_spin = QSpinBox()
        self.effect_duration_spin.setMinimum(1)
        self.effect_duration_spin.setMaximum(60)
        self.effect_duration_spin.setValue(10)
        self.effect_duration_layout.addWidget(self.effect_duration_spin)
        self.effect_options_layout.addLayout(self.effect_duration_layout)

        # Effect control buttons
        effect_control_layout = QHBoxLayout()
        self.run_effect_btn = QPushButton("Run Effect")
        self.run_effect_btn.clicked.connect(self.run_selected_effect)
        effect_control_layout.addWidget(self.run_effect_btn)

        self.stop_effect_btn = QPushButton("Stop Effect")
        self.stop_effect_btn.clicked.connect(self.stop_effects)
        effect_control_layout.addWidget(self.stop_effect_btn)
        effects_layout.addLayout(effect_control_layout)

        effects_group.setLayout(effects_layout)
        controls_panel.addWidget(effects_group)
        
        # Initial update to show/hide relevant controls
        self.update_effect_options()
        
        # Add stretch to push controls to the top
        controls_panel.addStretch()
        
        # Add the controls widget to the splitter
        self.main_splitter.addWidget(controls_widget)
        
        # Set initial sizes (3:1 ratio)
        self.main_splitter.setSizes([750, 250])
        
        # Add the splitter to the layout
        keyboard_controls_layout.addWidget(self.main_splitter)
        
        main_layout.addLayout(keyboard_controls_layout)
        
        # Status bar
        self.statusBar().showMessage("Disconnected")
        
        self.setCentralWidget(central_widget)
    
    def key_clicked(self, key):
        """Handle when a key is clicked - either select it, toggle, or apply the current color"""
        if self.selection_mode:
            # In selection mode, toggle the key's selection state
            if key in self.selected_keys:
                self.selected_keys.remove(key)
                key.setSelected(False)
            else:
                self.selected_keys.append(key)
                key.setSelected(True)
        else:
            # In normal mode, toggle between current color and off (black)
            if key.color == QColor(0, 0, 0):
                # If key is off, apply current color
                key.setKeyColor(self.current_color)
            else:
                # If key has a color, turn it off
                key.setKeyColor(QColor(0, 0, 0))
            
            if self.auto_reload and self.keyboard.connected:
                self.send_config()
    
    def toggle_selection_mode(self, enabled):
        """Toggle between selection mode and normal color application mode"""
        self.selection_mode = enabled
        if not enabled:
            self.clear_selection()
    
    def clear_selection(self):
        """Clear all selected keys"""
        for key in self.selected_keys:
            key.setSelected(False)
        self.selected_keys = []
    
    def set_region_color(self):
        """Apply the current color to the selected region with the region's intensity"""
        if not self.selected_keys:
            QMessageBox.information(self, "No Selection", "Please select keys first (enable Selection Mode and click on keys)")
            return
        
        # Get intensity from slider (0-100)
        intensity = self.region_intensity_slider.value() / 100.0
        
        for key in self.selected_keys:
            # Create a color with the current color's RGB values adjusted by intensity
            adjusted_color = QColor(
                int(self.current_color.red() * intensity),
                int(self.current_color.green() * intensity),
                int(self.current_color.blue() * intensity)
            )
            key.setKeyColor(adjusted_color)
        
        if self.auto_reload and self.keyboard.connected:
            self.send_config()
    
    def region_intensity_changed(self, value):
        """Handle change in region intensity slider"""
        self.region_intensity_label.setText(f"{value}%")
        
        # Apply intensity to selected keys
        if self.selected_keys:
            # Calculate intensity factor
            intensity = value / 100.0
            
            # For each selected key, adjust brightness
            for key in self.selected_keys:
                original_color = key.color
                # Preserve hue and saturation but adjust value (brightness)
                h, s, v = self.rgb_to_hsv(original_color.red(), original_color.green(), original_color.blue())
                new_color = self.hsv_to_rgb(h, s, v * intensity)
                key.setKeyColor(QColor(*new_color))
            
            # Restart the timer - this will delay sending the config until the user stops changing values
            self.intensity_timer.start(200)  # 200ms delay

    def rgb_to_hsv(self, r, g, b):
        """Convert RGB to HSV color values"""
        r, g, b = r/255.0, g/255.0, b/255.0
        return colorsys.rgb_to_hsv(r, g, b)

    def hsv_to_rgb(self, h, s, v):
        """Convert HSV to RGB color values"""
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return int(r*255), int(g*255), int(b*255)
    
    def set_current_color(self, color):
        """Set the current working color"""
        r, g, b = color
        self.current_color = QColor(r, g, b)
        self.color_display.setColor(self.current_color)
    
    def choose_current_color(self):
        """Choose a custom color for the current working color"""
        color = QColorDialog.getColor(self.current_color, self, "Select Current Color")
        if color.isValid():
            self.current_color = color
            self.color_display.setColor(color)
    
    def apply_current_color_to_all(self):
        """Apply the current color to all keys"""
        for key in self.keys:
            key.setKeyColor(self.current_color)
        
        if self.auto_reload and self.keyboard.connected:
            self.send_config()
    
    def toggle_connection(self):
        if not self.keyboard.connected:
            if self.connect_to_keyboard():
                self.connect_button.setText("Disconnect")
                self.statusBar().showMessage("Connected to keyboard")
            else:
                QMessageBox.warning(self, "Connection Failed", 
                                   "Could not connect to the keyboard. Make sure it's plugged in and has the correct VID/PID.")
        else:
            self.keyboard.disconnect()
            self.connect_button.setText("Connect")
            self.statusBar().showMessage("Disconnected")
    
    def toggle_auto_reload(self):
        self.auto_reload = not self.auto_reload
        self.auto_reload_btn.setText(f"Auto-Reload: {'ON' if self.auto_reload else 'OFF'}")
        
        if self.auto_reload:
            self.reload_timer.start(500)  # Check every 500ms
        else:
            self.reload_timer.stop()
    
    def intensity_changed(self):
        """Handle changes to the master intensity slider"""
        value = self.intensity_slider.value()
        self.intensity_label.setText(f"{value}%")
        
        # Restart the timer - this will delay sending the config until the user stops changing values
        self.intensity_timer.start(200)  # 200ms delay

    def apply_intensity(self):
        """Apply the intensity change after slider movement has stopped"""
        if self.auto_reload and self.keyboard.connected:
            self.send_config()
    
    def send_config(self):
        if not self.keyboard.connected:
            self.statusBar().showMessage("Connecting to keyboard...")
            if not self.keyboard.connect():
                self.statusBar().showMessage("Failed to connect")
                return
            self.connect_button.setText("Disconnect")
        
        # Collect colors for all keys
        key_colors = []
        for key in self.keys:
            key_colors.append((key.color.red(), key.color.green(), key.color.blue()))
        
        # Get current intensity (0.0-1.0)
        intensity = self.intensity_slider.value() / 100.0
        
        self.statusBar().showMessage("Sending configuration to keyboard...")
        
        # Pass intensity to the send_led_config method
        success = self.keyboard.send_led_config(key_colors, intensity)
        if success:
            self.statusBar().showMessage("Configuration applied successfully")
            self.provide_feedback()
        else:
            self.statusBar().showMessage("Failed to apply configuration")
    
    def load_config(self, config_name=None):
        config = self.config_manager.load_config(config_name)
        self.config_name.setText(config["name"])
        
        # Apply colors to keys
        colors = config["colors"]
        for i, key in enumerate(self.keys):
            if i < len(colors):
                r, g, b = colors[i]
                key.setKeyColor(QColor(r, g, b))
        
        if self.auto_reload and self.keyboard.connected:
            self.send_config()
    
    def save_config(self):
        config_name = self.config_name.text()
        if not config_name:
            QMessageBox.warning(self, "Invalid Name", "Please enter a configuration name")
            return
        
        # Collect colors
        colors = []
        for key in self.keys:
            colors.append((key.color.red(), key.color.green(), key.color.blue()))
        
        if self.config_manager.save_config(config_name, colors):
            # Update the combo boxes
            current_configs = self.config_manager.get_config_list()
            
            # Update main config combo
            self.config_combo.clear()
            self.config_combo.addItems(current_configs)
            self.config_combo.setCurrentText(config_name)
            
            # Also update the default shortcut config combo
            current_default = self.default_shortcut_config.currentText()
            self.default_shortcut_config.clear()
            self.default_shortcut_config.addItems(current_configs)
            if current_default in current_configs:
                self.default_shortcut_config.setCurrentText(current_default)
            else:
                self.default_shortcut_config.setCurrentText(config_name)
                self.shortcut_lighting.set_default_config(config_name)
            
            self.statusBar().showMessage(f"Configuration '{config_name}' saved")
        else:
            self.statusBar().showMessage("Failed to save configuration")
    
    def provide_feedback(self):
        """Visual confirmation when sending configuration"""
        # Flash key borders
        for key in self.keys:
            if not key.selected:  # Don't overwrite selection borders
                original_style = key.styleSheet()
                key.setStyleSheet(original_style + "border-color: #AAAAAA;")
                QApplication.processEvents()  # Update UI immediately
        
        # Reset after brief pause
        time.sleep(0.1)
        for key in self.keys:
            if not key.selected:
                key.updateStyle()
    
    def show_device_info(self):
        """Show information about the connected keyboard"""
        if not self.keyboard.connected:
            QMessageBox.information(self, "Device Information", 
                                   "Not connected to any keyboard")
            return
        
        try:
            info = {}
            try:
                info["Manufacturer"] = self.keyboard.device.get_manufacturer_string()
                info["Product"] = self.keyboard.device.get_product_string()
                info["Serial"] = self.keyboard.device.get_serial_number_string()
            except:
                pass
            
            info["VID"] = f"0x{self.keyboard.vendor_id:04X}"
            info["PID"] = f"0x{self.keyboard.product_id:04X}"
            
            info_text = "\n".join([f"{key}: {value}" for key, value in info.items()])
            
            QMessageBox.information(self, "Device Information", info_text)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to get device information: {str(e)}")

    def set_function_key_colors(self, color):
        """Delegate to effects module"""
        return self.effects.set_function_key_colors(color)

    def set_rainbow_colors(self):
        """Delegate to effects module"""
        return self.effects.set_rainbow_colors()
    
    def start_shortcut_monitor(self):
        """Start monitoring keyboard for shortcuts"""
        self.shortcut_lighting.start_monitor()
    
    def stop_shortcut_monitor(self):
        """Stop monitoring keyboard for shortcuts"""
        self.shortcut_lighting.stop_monitor()
    
    def toggle_shortcut_monitor(self):
        """Toggle shortcut monitoring on/off using global monitoring only"""
        if self.shortcut_toggle.isChecked():
            self.shortcut_toggle.setText("Stop Shortcut Monitor")
            # Start global monitoring directly
            self.shortcut_lighting.start_monitor()
            self.start_global_shortcut_monitor()
            self.is_monitoring_shortcuts = True
            self.statusBar().showMessage("Global shortcut monitoring started")
        else:
            self.shortcut_toggle.setText("Start Shortcut Monitor")
            self.shortcut_lighting.stop_monitor()
            self.stop_global_shortcut_monitor()
            self.is_monitoring_shortcuts = False
            self.statusBar().showMessage("Global shortcut monitoring stopped")

    def choose_highlight_color(self):
        """Choose a custom color for highlighting shortcuts"""
        color = QColorDialog.getColor(self.shortcut_lighting.default_highlight_color, self, "Select Highlight Color")
        if color.isValid():
            self.shortcut_lighting.set_default_highlight_color(color)
            self.highlight_color_display.setColor(color)

    def manage_shortcuts(self):
        """Open a dialog to manage keyboard shortcuts"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Manage Shortcut Highlighting")
        dialog.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(dialog)
        
        # Instructions
        layout.addWidget(QLabel("Configure which keys light up when modifier keys are pressed:"))
        
        # Create table to display shortcuts
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Modifier", "Keys to Highlight"])
        
        # Add shortcuts to table
        shortcuts = self.shortcut_manager.active_shortcuts
        table.setRowCount(len(shortcuts))
        
        for i, (modifier, keys) in enumerate(shortcuts.items()):
            modifier_item = QTableWidgetItem(modifier)
            keys_item = QTableWidgetItem(" ".join(keys))
            
            table.setItem(i, 0, modifier_item)
            table.setItem(i, 1, keys_item)
        
        table.resizeColumnsToContents()
        layout.addWidget(table)
        
        # Add buttons for add/remove/edit
        button_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add New")
        add_btn.clicked.connect(lambda: self.add_edit_shortcut(table))
        button_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("Edit Selected")
        edit_btn.clicked.connect(lambda: self.add_edit_shortcut(table, edit=True))
        button_layout.addWidget(edit_btn)
        
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(lambda: self.remove_shortcut(table))
        button_layout.addWidget(remove_btn)
        
        restore_defaults_btn = QPushButton("Restore Defaults")
        restore_defaults_btn.clicked.connect(lambda: self.restore_default_shortcuts(table))
        button_layout.addWidget(restore_defaults_btn)
        
        layout.addLayout(button_layout)
        
        # Save layout button
        save_layout_btn = QPushButton("Save Keyboard Layout")
        save_layout_btn.clicked.connect(self.save_keyboard_layout)
        layout.addWidget(save_layout_btn)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.exec_()

    def add_edit_shortcut(self, table, edit=False):
        """Add a new shortcut or edit existing one"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Shortcut Highlighting" if not edit else "Edit Shortcut Highlighting")
        
        layout = QVBoxLayout(dialog)
        
        # Modifier field
        modifier_layout = QHBoxLayout()
        modifier_layout.addWidget(QLabel("Modifier Key(s):"))
        modifier_input = QLineEdit()
        modifier_layout.addWidget(modifier_input)
        layout.addLayout(modifier_layout)
        
        # Keys field
        keys_layout = QHBoxLayout()
        keys_layout.addWidget(QLabel("Keys to Highlight (separated by spaces):"))
        keys_input = QLineEdit()
        keys_layout.addWidget(keys_input)
        layout.addLayout(keys_layout)
        
        # Help text
        layout.addWidget(QLabel("Examples:\nCtrl\nCtrl+Shift\nWin"))
        layout.addWidget(QLabel("Highlight Keys Examples: A B C D E F"))
        
        # If editing, populate fields with selected shortcut
        if edit:
            selected_row = table.currentRow()
            if selected_row >= 0:
                modifier = table.item(selected_row, 0).text()
                keys = table.item(selected_row, 1).text()
                
                modifier_input.setText(modifier)
                keys_input.setText(keys)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Connect buttons
        cancel_btn.clicked.connect(dialog.reject)
        save_btn.clicked.connect(lambda: self.save_shortcut(
            modifier_input.text(), 
            keys_input.text(), 
            table,
            dialog
        ))
        
        dialog.exec_()

    def save_shortcut(self, modifier, keys_text, table, dialog):
        """Save the shortcut to the manager and update table"""
        if not modifier or not keys_text:
            QMessageBox.warning(self, "Error", "Modifier and keys cannot be empty.")
            return
        
        # Split the keys text into individual keys
        key_list = [k.strip() for k in keys_text.split()]
        
        # Save to manager
        self.shortcut_manager.add_shortcut(modifier, key_list)
        
        # Refresh table
        shortcuts = self.shortcut_manager.active_shortcuts
        table.setRowCount(len(shortcuts))
        
        for i, (mod, keys) in enumerate(shortcuts.items()):
            mod_item = QTableWidgetItem(mod)
            keys_item = QTableWidgetItem(" ".join(keys))
            
            table.setItem(i, 0, mod_item)
            table.setItem(i, 1, keys_item)
        
        # Close dialog
        dialog.accept()

    def remove_shortcut(self, table):
        """Remove the selected shortcut"""
        selected_row = table.currentRow()
        if selected_row >= 0:
            modifier = table.item(selected_row, 0).text()
            
            # Confirm deletion
            confirm = QMessageBox.question(
                self, "Confirm Deletion", 
                f"Are you sure you want to delete the shortcut '{modifier}'?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if confirm == QMessageBox.Yes:
                # Remove from manager
                self.shortcut_manager.remove_shortcut(modifier)
                
                # Remove from table
                table.removeRow(selected_row)

    def restore_default_shortcuts(self, table):
        """Restore default shortcuts"""
        confirm = QMessageBox.question(
            self, "Confirm Reset", 
            "Are you sure you want to restore default shortcuts? This will overwrite any custom shortcuts.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            # Reset shortcuts in manager
            self.shortcut_manager.active_shortcuts = self.shortcut_manager.default_shortcuts.copy()
            self.shortcut_manager.save_shortcuts()
            
            # Refresh table
            shortcuts = self.shortcut_manager.active_shortcuts
            table.setRowCount(len(shortcuts))
            
            for i, (mod, keys) in enumerate(shortcuts.items()):
                mod_item = QTableWidgetItem(mod)
                keys_item = QTableWidgetItem(" ".join(keys))
                
                table.setItem(i, 0, mod_item)
                table.setItem(i, 1, keys_item)

    def closeEvent(self, event):
        """Handle application close event"""
        # If in daemon mode, just hide the window
        if self.daemon_mode:
            event.ignore()
            self.hide()
            return
        
        # Check if should minimize to tray instead
        minimize_to_tray = True  # Could be a setting
        
        if minimize_to_tray and self.tray_icon.isVisible():
            # Hide the window instead of closing
            event.ignore()
            self.hide()
            
            # Show notification
            self.tray_icon.showMessage(
                "Running in Background",
                "The keyboard application is still running in the system tray.",
                QSystemTrayIcon.Information,
                2000
            )
        else:
            # Stop any active listeners
            self.stop_global_shortcut_monitor()
            
            # Stop shortcut monitoring
            if hasattr(self, 'shortcut_lighting'):
                self.shortcut_lighting.stop_monitor()
            
            # Disconnect from keyboard
            if self.keyboard.connected:
                self.keyboard.disconnect()
            
            # Accept the close event
            event.accept()

    def save_keyboard_layout(self):
        """Save the keyboard layout to the configuration file"""
        # Get the layout definition
        layout_matrix = [
            ["Esc", "`", "Tab", "Caps", "Shift", "Ctrl"],
            ["F1", "1", "Q", "A", "Z", "Win"],
            ["F2", "2", "W", "S", "X", "Alt"],
            ["F3", "3", "E", "D", "C", "NAN"],
            ["F4", "4", "R", "F", "V", "NAN"],
            ["F5", "5", "T", "G", "B", "Space"],
            ["F6", "6", "Y", "H", "N", "NAN"],
            ["F7", "7", "U", "J", "M", "NAN"],
            ["F8", "8", "I", "K", ",", "Alt"],
            ["F9", "9", "O", "L", ".", "Fn"],
            ["F10", "0", "P", ";", "/", "Ctrl"],
            ["F11", "-", "[", "'", "NAN", "NAN"],
            ["F12", "=", "]", "NAN", "NAN", "NAN"],
            ["PrtSc", "Bksp", "\\", "Enter", "Shift", "←"],
            ["Pause", "NAN", "NAN", "NAN", "↑", "↓"],
            ["Del", "Home", "End", "PgUp", "PgDn", "→"]
        ]
        
        # Save to configuration file
        self.shortcut_manager.save_keyboard_layout(layout_matrix)
        self.statusBar().showMessage("Keyboard layout saved to configuration")

    def manage_modifier_colors(self):
        """Open a dialog to manage modifier key colors"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Modifier Key Colors")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Choose colors for each modifier key:"))
        
        grid = QGridLayout()
        row = 0
        
        for modifier, color in self.shortcut_lighting.modifier_colors.items():
            # Label for the modifier
            grid.addWidget(QLabel(modifier + ":"), row, 0)
            
            # Color display
            color_display = ColorDisplay(color)
            grid.addWidget(color_display, row, 1)
            
            # Change button
            change_btn = QPushButton("Change...")
            change_btn.clicked.connect(lambda checked, mod=modifier, disp=color_display: self.change_modifier_color(mod, disp))
            grid.addWidget(change_btn, row, 2)
            
            row += 1
        
        layout.addLayout(grid)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.exec_()

    def change_modifier_color(self, modifier, display):
        """Change the color for a specific modifier key"""
        current_color = self.shortcut_lighting.get_modifier_color(modifier)
        new_color = QColorDialog.getColor(current_color, self, f"Select Color for {modifier}")
        
        if new_color.isValid():
            self.shortcut_lighting.set_modifier_color(modifier, new_color)
            display.setColor(new_color)

    def set_default_shortcut_config(self, config_name):
        """Set the configuration to be loaded when shortcut keys are released"""
        self.shortcut_lighting.set_default_config(config_name)

    def clear_keyboard(self):
        """Delegate to text_display module"""
        return self.text_display.clear_keyboard()

    def display_text(self, text, color=None, clear_first=True):
        """Delegate to text_display module"""
        return self.text_display.display_text(text, color, clear_first)

    def display_advanced_text(self, text, color=None, start_pos=None, clear_first=True):
        """Delegate to text_display module"""
        return self.text_display.display_advanced_text(text, color, start_pos, clear_first)

    def scroll_text(self, text, speed=0.5, color=None):
        """Delegate to text_display module"""
        return self.text_display.scroll_text(text, speed, color)

    def run_selected_effect(self):
        """Run the effect selected in the dropdown"""
        effect_name = self.effect_combo.currentText()
        speed = self.get_effect_speed()
        color = self.effect_color_display.color
        color_tuple = (color.red(), color.green(), color.blue())
        duration = self.effect_duration_spin.value()
        
        # Show status message
        self.statusBar().showMessage(f"Running {effect_name}...")
        
        # Run the appropriate effect
        if effect_name == "Rainbow Colors":
            self.run_effect_in_thread(self.effects.set_rainbow_colors)
        
        elif effect_name == "Wave Effect":
            self.run_effect_in_thread(self.effects.set_wave_effect, speed=speed)
        
        elif effect_name == "Breathing Effect":
            self.run_effect_in_thread(self.effects.breathe_effect, color=color_tuple, speed=speed, cycles=duration)
        
        elif effect_name == "Spectrum Cycle":
            self.run_effect_in_thread(self.effects.spectrum_effect, speed=speed, cycles=duration)
        
        elif effect_name == "Starlight":
            self.run_effect_in_thread(self.effects.starlight_effect, star_color=color_tuple, duration=duration)
        
        elif effect_name == "Ripple Effect":
            self.run_effect_in_thread(self.effects.ripple_effect, color=color_tuple, speed=speed)
        
        elif effect_name == "Reactive Typing":
            self.run_effect_in_thread(self.effects.reactive_effect, highlight_color=color_tuple, duration=duration)
        
        elif effect_name == "Gradient Flow":
            self.run_effect_in_thread(self.effects.gradient_effect, speed=speed, cycles=duration)

    def stop_effects(self):
        """Stop any running effects by setting a flag"""
        # A simple approach - load the current configuration to overwrite any effect
        self.statusBar().showMessage("Stopping effects...")
        
        # Need to interrupt any running effect threads
        # This is a challenge since we're using multiple threads
        # A simple approach is to just reload the current config
        self.load_config()
        self.send_config()
        
        self.statusBar().showMessage("Effects stopped, configuration reloaded")

    def run_effect_in_thread(self, effect_func, **kwargs):
        """Run an effect function in a separate thread"""
        threading.Thread(target=effect_func, kwargs=kwargs, daemon=True).start()

    def get_effect_speed(self):
        """Convert slider value to appropriate speed value (inverted)"""
        slider_value = self.effect_speed_slider.value()
        # Convert from 1-20 range to 0.01-0.2 range (inverted - higher is slower)
        return 0.21 - (slider_value / 100.0)

    def update_effect_options(self):
        """Update the options shown based on selected effect"""
        effect_name = self.effect_combo.currentText()
        
        # Default - show all options
        self.effect_color_layout.parentWidget().setVisible(True)
        self.effect_speed_layout.parentWidget().setVisible(True)
        self.effect_duration_layout.parentWidget().setVisible(True)
        
        # Hide/show options based on effect
        if effect_name == "Rainbow Colors":
            # Rainbow doesn't need color or duration
            self.effect_color_layout.parentWidget().setVisible(False) 
            self.effect_duration_layout.parentWidget().setVisible(False)
        
        elif effect_name == "Spectrum Cycle":
            # Spectrum doesn't need color or duration
            self.effect_color_layout.parentWidget().setVisible(False)
        
        elif effect_name == "Wave Effect":
            # Wave doesn't need duration
            self.effect_duration_layout.parentWidget().setVisible(False)
        
        elif effect_name == "Gradient Flow":
            # Gradient doesn't need duration
            self.effect_duration_layout.parentWidget().setVisible(False)
        
        # Update button text
        self.run_effect_btn.setText(f"Run {effect_name}")
        
        # Update status bar with hint
        self.statusBar().showMessage(f"Ready to run {effect_name}")

    def choose_effect_color(self):
        """Open a color dialog to choose the effect color"""
        color = QColorDialog.getColor(self.effect_color_display.color, self, "Choose Effect Color")
        if color.isValid():
            self.effect_color_display.setColor(color)

    def run_rainbow_effect(self):
        """Run the rainbow effect in a thread"""
        self.run_effect_in_thread(self.effects.set_rainbow_colors)

    def run_wave_effect(self):
        """Run the wave effect in a thread"""
        self.run_effect_in_thread(self.effects.set_wave_effect, speed=0.1)

    def run_breathe_effect(self):
        """Run the breathing effect in a thread"""
        self.run_effect_in_thread(self.effects.breathe_effect, cycles=3)

    def run_spectrum_effect(self):
        """Run the spectrum effect in a thread"""
        self.run_effect_in_thread(self.effects.spectrum_effect, speed=0.1)

    def run_starlight_effect(self):
        """Run the starlight effect in a thread"""
        self.run_effect_in_thread(self.effects.starlight_effect, duration=10)

    def apply_gaming_preset(self):
        """Apply a preset for gaming with WASD keys highlighted"""
        # Clear keyboard first
        self.clear_keyboard()
        
        # Highlight WASD keys in blue
        gaming_keys = ["W", "A", "S", "D", "Space", "Shift", "Ctrl"]
        for key in self.keys:
            if key.key_name in gaming_keys:
                key.setKeyColor(QColor(0, 150, 255))  # Blue
        
        # Highlight function keys in orange
        function_keys = ["F1", "F2", "F3", "F4", "F5", "F6"]
        for key in self.keys:
            if key.key_name in function_keys:
                key.setKeyColor(QColor(255, 128, 0))  # Orange
        
        self.send_config()
        self.statusBar().showMessage("Gaming preset applied")

    def apply_typing_preset(self):
        """Apply a preset for typing with home row highlighted"""
        # Clear keyboard first
        self.clear_keyboard()
        
        # Highlight home row (ASDF JKL;) in green
        home_row = ["A", "S", "D", "F", "J", "K", "L", ";"]
        for key in self.keys:
            if key.key_name in home_row:
                key.setKeyColor(QColor(0, 230, 115))  # Green
        
        # Set other keys to a subtle blue
        for key in self.keys:
            if key.key_name not in home_row and key.color == QColor(0, 0, 0):
                key.setKeyColor(QColor(20, 40, 80))  # Dark blue
        
        self.send_config()
        self.statusBar().showMessage("Typing preset applied")

    def start_global_shortcut_monitor(self):
        """Start global shortcut monitoring with Wayland compatibility"""
        if hasattr(self, 'global_listener') and self.global_listener:
            return  # Already monitoring
        
        self.global_keys_pressed = set()
        
        # Check if running on Wayland
        wayland_session = 'WAYLAND_DISPLAY' in os.environ
        
        if wayland_session:
            self.statusBar().showMessage("Wayland detected: using compatible input monitoring")
            
            try:
                # For Wayland we need a different approach
                # We'll use evdev for direct input device monitoring
                from evdev import InputDevice, categorize, ecodes, list_devices
                import threading
                
                # For evdev we need to find the keyboard device
                def setup_evdev_monitor():
                    devices = [InputDevice(path) for path in list_devices()]
                    keyboards = []
                    
                    for device in devices:
                        if "keyboard" in device.name.lower() or any(key in device.capabilities() for key in [ecodes.EV_KEY]):
                            keyboards.append(device)
                    
                    if not keyboards:
                        self.statusBar().showMessage("No keyboard devices found for monitoring")
                        return False
                    
                    # Monitor all keyboard devices
                    for keyboard in keyboards:
                        # Start a thread for each keyboard
                        thread = threading.Thread(
                            target=self.evdev_monitor_thread,
                            args=(keyboard,),
                            daemon=True
                        )
                        thread.start()
                    
                    self.statusBar().showMessage(f"Monitoring {len(keyboards)} keyboard input devices")
                    return True
                
                # Start evdev monitoring in a separate thread
                threading.Thread(target=setup_evdev_monitor, daemon=True).start()
                self.global_listener = True  # Just a flag to indicate monitoring is active
                
            except ImportError:
                self.statusBar().showMessage("Wayland support requires 'evdev' package. Using fallback method.")
                self._setup_fallback_monitor()
        else:
            # X11 or other systems: use pynput
            self._setup_fallback_monitor()

    def evdev_monitor_thread(self, device):
        """Monitor a keyboard device with evdev"""
        try:
            from evdev import categorize, ecodes
            
            # Map evdev keycodes to our key names - ONLY MODIFIER KEYS
            modifier_key_map = {
                ecodes.KEY_LEFTCTRL: "Ctrl", 
                ecodes.KEY_RIGHTCTRL: "Ctrl",
                ecodes.KEY_LEFTSHIFT: "Shift",
                ecodes.KEY_RIGHTSHIFT: "Shift",
                ecodes.KEY_LEFTALT: "Alt",
                ecodes.KEY_RIGHTALT: "Alt",
                ecodes.KEY_LEFTMETA: "Win",
                ecodes.KEY_RIGHTMETA: "Win",
            }
            
            for event in device.read_loop():
                if event.type == ecodes.EV_KEY:
                    key_event = categorize(event)
                    keycode = key_event.scancode
                    
                    # Only process modifier keys
                    if keycode in modifier_key_map:
                        key_name = modifier_key_map[keycode]
                        
                        if key_event.keystate == 1:  # Key down
                            # Process in main thread to avoid race conditions
                            QApplication.instance().postEvent(
                                self, 
                                CustomKeyEvent(CustomKeyEvent.KeyPress, key_name)
                            )
                        elif key_event.keystate == 0:  # Key up
                            QApplication.instance().postEvent(
                                self, 
                                CustomKeyEvent(CustomKeyEvent.KeyRelease, key_name)
                            )
        
        except Exception as e:
            print(f"Evdev monitor error: {e}")

    def _setup_fallback_monitor(self):
        """Setup fallback monitoring with pynput"""
        def on_press(key):
            """Handle global key press events"""
            try:
                # Filter out regular character keys
                return
            except (AttributeError, TypeError):
                # Special key handling
                key_name = str(key).replace('Key.', '')
                
                # Map pynput keys to our key names
                key_map = {
                    'ctrl': 'Ctrl',
                    'ctrl_l': 'Ctrl', 
                    'ctrl_r': 'Ctrl',
                    'shift': 'Shift',
                    'shift_l': 'Shift',
                    'shift_r': 'Shift',
                    'alt': 'Alt',
                    'alt_l': 'Alt',
                    'alt_r': 'Alt',
                    'cmd': 'Win',
                    'cmd_l': 'Win',
                    'cmd_r': 'Win'
                }
                
                # Only process modifier keys
                if key_name in key_map:
                    key_name = key_map[key_name]
                    # If this is a new key press, process it
                    if key_name not in self.global_keys_pressed:
                        self.global_keys_pressed.add(key_name)
                        # Use a thread to avoid blocking the listener
                        threading.Thread(target=self.shortcut_lighting.handle_key_press,
                                      args=(key_name,), daemon=True).start()
        
        def on_release(key):
            """Handle global key release events"""
            try:
                # Filter out regular character keys
                return
            except (AttributeError, TypeError):
                # Special key handling
                key_name = str(key).replace('Key.', '')
                
                # Map pynput keys to our key names
                key_map = {
                    'ctrl': 'Ctrl',
                    'ctrl_l': 'Ctrl', 
                    'ctrl_r': 'Ctrl',
                    'shift': 'Shift',
                    'shift_l': 'Shift',
                    'shift_r': 'Shift',
                    'alt': 'Alt',
                    'alt_l': 'Alt',
                    'alt_r': 'Alt',
                    'cmd': 'Win',
                    'cmd_l': 'Win',
                    'cmd_r': 'Win'
                }
                
                # Only process modifier keys
                if key_name in key_map:
                    key_name = key_map[key_name]
                    # Remove from pressed keys
                    if key_name in self.global_keys_pressed:
                        self.global_keys_pressed.remove(key_name)
                        # Use a thread to avoid blocking the listener
                        threading.Thread(target=self.shortcut_lighting.handle_key_release,
                                      args=(key_name,), daemon=True).start()
        
        # Start the global key listener in a separate thread
        self.global_listener = pynput_keyboard.Listener(on_press=on_press, on_release=on_release)
        self.global_listener.start()
        self.statusBar().showMessage("Global shortcut monitoring active (modifiers only)")

    def stop_global_shortcut_monitor(self):
        """Stop the global shortcut monitoring"""
        # Check if global_listener is an actual listener object and not a boolean
        if hasattr(self.global_listener, 'stop') and callable(self.global_listener.stop):
            self.global_listener.stop()
            self.global_listener = None
        else:
            # Just reset it if it's not a proper listener
            self.global_listener = None
        
        # Additional cleanup
        if hasattr(self, 'is_monitoring_shortcuts'):
            self.is_monitoring_shortcuts = False
        
        self.statusBar().showMessage("Global shortcut monitoring stopped")

    def setupSystemTray(self):
        """Setup system tray icon and menu"""
        # Create system tray icon
        self.tray_icon = QSystemTrayIcon(self)
        
        # Use app icon if available, otherwise use a default
        self.tray_icon.setIcon(QApplication.instance().windowIcon())
        # Create the tray menu
        tray_menu = QMenu()
        
        # Add show/hide action
        self.show_action = QAction("Show Window", self)
        self.show_action.triggered.connect(self.showNormal)
        tray_menu.addAction(self.show_action)
        
        # Add separator
        tray_menu.addSeparator()
        
        # Add configurations submenu
        configs_menu = QMenu("Configurations")
        tray_menu.addMenu(configs_menu)
        
        # Add configurations to submenu
        self.update_tray_configs(configs_menu)
        
        # Add refresh configs action
        refresh_action = QAction("Refresh Configurations", self)
        refresh_action.triggered.connect(lambda: self.update_tray_configs(configs_menu))
        tray_menu.addAction(refresh_action)
        
        # Add separator
        tray_menu.addSeparator()
        
        # Add shortcut monitoring toggle
        self.tray_shortcut_action = QAction("Start Shortcut Monitoring", self)
        self.tray_shortcut_action.triggered.connect(self.toggle_shortcut_monitoring_from_tray)
        tray_menu.addAction(self.tray_shortcut_action)
        
        # Add daemon mode toggle
        self.daemon_mode_action = QAction("Enter Daemon Mode", self)
        self.daemon_mode_action.triggered.connect(self.toggle_daemon_mode)
        tray_menu.addAction(self.daemon_mode_action)
        
        # Add separator
        tray_menu.addSeparator()
        
        # Add quit option
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)
        
        # Set the tray icon menu
        self.tray_icon.setContextMenu(tray_menu)
        
        # Show the tray icon
        self.tray_icon.show()
        
        # Connect signal for tray icon activation
        self.tray_icon.activated.connect(self.tray_icon_activated)

    def update_tray_configs(self, menu):
        """Update the configurations in the tray menu"""
        # Clear current items
        menu.clear()
        
        # Get config list
        configs = self.config_manager.get_config_list()
        
        # Add each config as an action
        for config_name in configs:
            action = QAction(config_name, self)
            action.triggered.connect(lambda checked, name=config_name: self.apply_tray_config(name))
            menu.addAction(action)

    def apply_tray_config(self, config_name):
        """Apply a configuration from the tray menu"""
        # Load the configuration
        self.load_config(config_name)
        
        # Ensure keyboard is connected
        if not self.keyboard.connected:
            self.connect_to_keyboard()
        
        # Send config to keyboard
        self.send_config()
        
        # Show notification
        self.tray_icon.showMessage(
            "Configuration Applied",
            f"Applied configuration: {config_name}",
            QSystemTrayIcon.Information,
            2000
        )

    def connect_to_keyboard(self):
        """Connect to the keyboard"""
        if not self.keyboard.connected:
            if self.keyboard.connect():
                self.connect_button.setText("Disconnect")
                self.statusBar().showMessage("Connected to keyboard")
                self.send_config()  # Apply config immediately on connect
                return True
            else:
                self.statusBar().showMessage("Failed to connect to keyboard")
                return False
        return True

    def tray_icon_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.DoubleClick:
            # Show/hide the window on double click
            if self.isVisible():
                self.hide()
            else:
                self.showNormal()
                self.activateWindow()

    def event(self, event):
        """Handle custom key events from Wayland/evdev monitoring"""
        if event.type() == CustomKeyEvent.KeyPress:
            self.shortcut_lighting.handle_key_press(event.key_name)
            return True
        elif event.type() == CustomKeyEvent.KeyRelease:
            self.shortcut_lighting.handle_key_release(event.key_name)
            return True
        return super().event(event)

    def toggle_shortcut_monitoring_from_tray(self):
        """Toggle shortcut monitoring from system tray"""
        if self.is_monitoring_shortcuts:
            # Stop monitoring
            self.stop_global_shortcut_monitor()
            self.is_monitoring_shortcuts = False
            self.tray_shortcut_action.setText("Start Shortcut Monitoring")
            self.tray_icon.showMessage(
                "Shortcut Monitoring",
                "Shortcut monitoring stopped",
                QSystemTrayIcon.Information,
                2000
            )
        else:
            # Start monitoring
            self.start_global_shortcut_monitor()
            self.is_monitoring_shortcuts = True
            self.tray_shortcut_action.setText("Stop Shortcut Monitoring")
            self.tray_icon.showMessage(
                "Shortcut Monitoring",
                "Shortcut monitoring started",
                QSystemTrayIcon.Information,
                2000
            )
            
            # Update GUI if it's visible
            if hasattr(self, 'shortcut_toggle') and self.isVisible():
                self.shortcut_toggle.setChecked(True)
                self.shortcut_toggle.setText("Stop Shortcut Monitor")

    def toggle_daemon_mode(self):
        """Toggle daemon mode (shortcut monitoring only)"""
        if self.daemon_mode:
            # Exit daemon mode
            self.daemon_mode = False
            self.daemon_mode_action.setText("Enter Daemon Mode")
            self.show_action.setEnabled(True)
            
            # Show notification
            self.tray_icon.showMessage(
                "Daemon Mode",
                "Exited daemon mode",
                QSystemTrayIcon.Information,
                2000
            )
        else:
            # Enter daemon mode
            self.daemon_mode = True
            self.daemon_mode_action.setText("Exit Daemon Mode")
            self.hide()  # Hide the main window
            self.show_action.setEnabled(False)  # Disable show window option
            
            # Start shortcut monitoring if not already active
            if not self.is_monitoring_shortcuts:
                self.toggle_shortcut_monitoring_from_tray()
            
            # Show notification
            self.tray_icon.showMessage(
                "Daemon Mode",
                "Entered daemon mode (shortcut monitoring only)",
                QSystemTrayIcon.Information,
                2000
            )

    def quit_application(self):
        """Quit the application entirely"""
        # Stop any active listeners
        self.stop_global_shortcut_monitor()
        
        # Stop shortcut monitoring
        if hasattr(self, 'shortcut_lighting'):
            self.shortcut_lighting.stop_monitor()
        
        # Disconnect from keyboard
        if self.keyboard.connected:
            self.keyboard.disconnect()
        
        # Exit the application
        QApplication.instance().quit() 