import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QPushButton, 
                           QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
                           QComboBox, QColorDialog, QLineEdit, QMessageBox, QSlider,
                           QGroupBox, QCheckBox, QFrame)
from PyQt5.QtGui import QColor, QPalette, QFont, QKeySequence
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QEvent
import time
import colorsys
import threading

from keyboard_controller import KeyboardController
from config_manager import ConfigManager
from shortcut_manager import ShortcutManager

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
        
        # Keyboard monitoring variables
        self.shortcut_monitor_active = False
        self.currently_pressed_keys = set()
        self.highlighted_keys = []
        self.original_key_colors = {}
        self.highlight_color = QColor(255, 165, 0)  # Orange highlight color
        
        # Setup auto-reload before calling load_config
        self.auto_reload = True
        self.reload_timer = QTimer()
        self.reload_timer.timeout.connect(self.send_config)
        
        self.setupUI()
        
        # Load default configuration
        self.load_config()
        
        # Install event filter to catch key events
        QApplication.instance().installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """Filter keyboard events for shortcut highlighting"""
        if not self.shortcut_monitor_active:
            return super().eventFilter(obj, event)
            
        if event.type() == QEvent.KeyPress:
            key = event.key()
            if key in QT_KEY_MAP:
                key_name = QT_KEY_MAP[key]
                self.currently_pressed_keys.add(key_name)
                self.update_key_highlights()
                
        elif event.type() == QEvent.KeyRelease:
            key = event.key()
            if key in QT_KEY_MAP:
                key_name = QT_KEY_MAP[key]
                if key_name in self.currently_pressed_keys:
                    self.currently_pressed_keys.remove(key_name)
                
                # If no keys are pressed anymore, restore original colors
                if not self.currently_pressed_keys:
                    self.restore_highlighted_keys()
        
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
        
        # Side-by-side layout for keyboard and controls
        keyboard_controls_layout = QHBoxLayout()
        
        # Keyboard layout goes on the left
        keyboard_container = QVBoxLayout()
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
        
        # Auto reload toggle
        self.auto_reload_btn = QPushButton("Auto-Reload: ON")
        self.auto_reload_btn.setCheckable(True)
        self.auto_reload_btn.setChecked(True)
        self.auto_reload_btn.clicked.connect(self.toggle_auto_reload)
        keyboard_container.addWidget(self.auto_reload_btn)
        
        keyboard_controls_layout.addLayout(keyboard_container, 3)  # 3:1 ratio
        
        # Control panel on the right
        controls_panel = QVBoxLayout()
        
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
        
        # Rainbow preset
        rainbow_btn = QPushButton("Rainbow Effect")
        rainbow_btn.clicked.connect(self.set_rainbow_colors)
        presets_layout.addWidget(rainbow_btn)
        
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
        
        self.highlight_color_display = ColorDisplay(self.highlight_color)
        self.highlight_color_display.clicked.connect(self.choose_highlight_color)
        highlight_color_layout.addWidget(self.highlight_color_display)
        
        shortcut_layout.addLayout(highlight_color_layout)
        
        # Manage shortcuts button
        manage_shortcuts_btn = QPushButton("Manage Shortcuts")
        manage_shortcuts_btn.clicked.connect(self.manage_shortcuts)
        shortcut_layout.addWidget(manage_shortcuts_btn)
        
        # Add shortcut group to layout
        shortcut_group.setLayout(shortcut_layout)
        controls_panel.addWidget(shortcut_group)
        
        # Add stretch to push controls to the top
        controls_panel.addStretch()
        
        keyboard_controls_layout.addLayout(controls_panel, 1)  # 3:1 ratio
        
        main_layout.addLayout(keyboard_controls_layout)
        
        # Status bar
        self.statusBar().showMessage("Disconnected")
        
        self.setCentralWidget(central_widget)
    
    def key_clicked(self, key):
        """Handle when a key is clicked - either select it or apply the current color"""
        if self.selection_mode:
            # In selection mode, toggle the key's selection state
            if key in self.selected_keys:
                self.selected_keys.remove(key)
                key.setSelected(False)
            else:
                self.selected_keys.append(key)
                key.setSelected(True)
        else:
            # In normal mode, apply the current color to the clicked key
            key.setKeyColor(self.current_color)
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
    
    def region_intensity_changed(self):
        """Handle changes to the region-specific intensity slider"""
        value = self.region_intensity_slider.value()
        self.region_intensity_label.setText(f"{value}%")
        
        # Apply the intensity to selected keys
        if not self.selected_keys:
            return
        
        # Re-apply the current colors with the new intensity
        self.set_region_color()
    
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
            if self.keyboard.connect():
                self.connect_button.setText("Disconnect")
                self.statusBar().showMessage("Connected to keyboard")
                self.send_config()  # Apply config immediately on connect
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
        
        # Apply the new intensity if auto-reload is enabled
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
            # Update the combo box
            current_configs = self.config_manager.get_config_list()
            self.config_combo.clear()
            self.config_combo.addItems(current_configs)
            self.config_combo.setCurrentText(config_name)
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
        """Set all function keys to a specific color"""
        # Function key labels
        function_keys = ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"]
        
        # Find the function keys by label and set their color
        for key in self.keys:
            if key.key_name in function_keys:
                key.setKeyColor(QColor(*color))
        
        if self.auto_reload and self.keyboard.connected:
            self.send_config()
    
    def set_rainbow_colors(self):
        """Create a rainbow effect across all keys"""
        # Create a rainbow gradient
        num_keys = len(self.keys)
        for i, key in enumerate(self.keys):
            # Create a color based on position in keyboard
            hue = i / num_keys
            r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            key.setKeyColor(QColor(int(r * 255), int(g * 255), int(b * 255)))
        
        if self.auto_reload and self.keyboard.connected:
            self.send_config()
    
    def start_shortcut_monitor(self):
        """Start monitoring keyboard for shortcuts"""
        if self.shortcut_monitor_active:
            return
            
        self.shortcut_monitor_active = True
        self.statusBar().showMessage("Shortcut monitoring activated")
    
    def stop_shortcut_monitor(self):
        """Stop monitoring keyboard for shortcuts"""
        self.shortcut_monitor_active = False
        self.statusBar().showMessage("Shortcut monitoring deactivated")
        
        # Restore any highlighted keys to their original colors
        self.restore_highlighted_keys()
    
    def update_key_highlights(self):
        """Update key highlighting based on currently pressed keys"""
        if not self.currently_pressed_keys:
            return
            
        # Convert set to list for the shortcut manager
        pressed_list = list(self.currently_pressed_keys)
        
        # Get keys to highlight from shortcut manager
        keys_to_highlight = self.shortcut_manager.get_keys_to_highlight(pressed_list)
        
        # Restore previously highlighted keys
        self.restore_highlighted_keys()
        
        # Highlight new keys
        self.highlighted_keys = []
        for key in self.keys:
            # Check if key name matches (case-insensitive)
            if key.key_name.lower() in [k.lower() for k in keys_to_highlight]:
                # Save original color before highlighting
                self.original_key_colors[key] = QColor(key.color)
                
                # Apply highlight color
                key.setKeyColor(self.highlight_color)
                self.highlighted_keys.append(key)
        
        # Update UI immediately
        QApplication.processEvents()
        
        # If auto-reload is on, send the updated colors to the keyboard
        if self.auto_reload and self.keyboard.connected:
            self.send_config()
    
    def restore_highlighted_keys(self):
        """Restore original colors to highlighted keys"""
        for key in self.highlighted_keys:
            if key in self.original_key_colors:
                key.setKeyColor(self.original_key_colors[key])
        
        self.highlighted_keys = []
        self.original_key_colors = {}
        
        # Update UI immediately
        QApplication.processEvents()
        
        # If auto-reload is on, send the updated colors to the keyboard
        if self.auto_reload and self.keyboard.connected:
            self.send_config()

    def toggle_shortcut_monitor(self):
        """Toggle shortcut monitoring on/off"""
        if self.shortcut_toggle.isChecked():
            self.shortcut_toggle.setText("Stop Shortcut Monitor")
            self.start_shortcut_monitor()
        else:
            self.shortcut_toggle.setText("Start Shortcut Monitor")
            self.stop_shortcut_monitor()

    def choose_highlight_color(self):
        """Choose a custom color for highlighting shortcuts"""
        color = QColorDialog.getColor(self.highlight_color, self, "Select Highlight Color")
        if color.isValid():
            self.highlight_color = color
            self.highlight_color_display.setColor(color)

    def manage_shortcuts(self):
        """Open a dialog to manage keyboard shortcuts"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Manage Keyboard Shortcuts")
        dialog.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(dialog)
        
        # Create table to display shortcuts
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Shortcut Name", "Keys"])
        
        # Add shortcuts to table
        shortcuts = self.shortcut_manager.active_shortcuts
        table.setRowCount(len(shortcuts))
        
        for i, (name, keys) in enumerate(shortcuts.items()):
            name_item = QTableWidgetItem(name)
            keys_item = QTableWidgetItem("+".join(keys))
            
            table.setItem(i, 0, name_item)
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
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.exec_()

    def add_edit_shortcut(self, table, edit=False):
        """Add a new shortcut or edit existing one"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Shortcut" if not edit else "Edit Shortcut")
        
        layout = QVBoxLayout(dialog)
        
        # Name field
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Shortcut Name:"))
        name_input = QLineEdit()
        name_layout.addWidget(name_input)
        layout.addLayout(name_layout)
        
        # Keys field
        keys_layout = QHBoxLayout()
        keys_layout.addWidget(QLabel("Keys (separated by +):"))
        keys_input = QLineEdit()
        keys_layout.addWidget(keys_input)
        layout.addLayout(keys_layout)
        
        # Help text
        layout.addWidget(QLabel("Example: Ctrl+C or Ctrl+Shift+V"))
        
        # If editing, populate fields with selected shortcut
        if edit:
            selected_row = table.currentRow()
            if selected_row >= 0:
                name = table.item(selected_row, 0).text()
                keys = table.item(selected_row, 1).text()
                
                name_input.setText(name)
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
            name_input.text(), 
            keys_input.text(), 
            table,
            dialog
        ))
        
        dialog.exec_()

    def save_shortcut(self, name, keys_text, table, dialog):
        """Save the shortcut to the manager and update table"""
        if not name or not keys_text:
            QMessageBox.warning(self, "Error", "Name and keys cannot be empty.")
            return
        
        # Split the keys text into individual keys
        key_list = [k.strip() for k in keys_text.split("+")]
        
        # Save to manager
        self.shortcut_manager.add_shortcut(name, key_list)
        
        # Refresh table
        shortcuts = self.shortcut_manager.active_shortcuts
        table.setRowCount(len(shortcuts))
        
        for i, (s_name, s_keys) in enumerate(shortcuts.items()):
            name_item = QTableWidgetItem(s_name)
            keys_item = QTableWidgetItem("+".join(s_keys))
            
            table.setItem(i, 0, name_item)
            table.setItem(i, 1, keys_item)
        
        # Close dialog
        dialog.accept()

    def remove_shortcut(self, table):
        """Remove the selected shortcut"""
        selected_row = table.currentRow()
        if selected_row >= 0:
            name = table.item(selected_row, 0).text()
            
            # Confirm deletion
            confirm = QMessageBox.question(
                self, "Confirm Deletion", 
                f"Are you sure you want to delete the shortcut '{name}'?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if confirm == QMessageBox.Yes:
                # Remove from manager
                self.shortcut_manager.remove_shortcut(name)
                
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
            
            for i, (name, keys) in enumerate(shortcuts.items()):
                name_item = QTableWidgetItem(name)
                keys_item = QTableWidgetItem("+".join(keys))
                
                table.setItem(i, 0, name_item)
                table.setItem(i, 1, keys_item)

    def closeEvent(self, event):
        """Clean up resources when closing the application"""
        # Stop shortcut monitor if active
        if self.shortcut_monitor_active:
            self.stop_shortcut_monitor()
        
        # Disconnect from keyboard if connected
        if self.keyboard.connected:
            self.keyboard.disconnect()
        
        event.accept() 