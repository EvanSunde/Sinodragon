import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QPushButton, 
                           QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
                           QComboBox, QColorDialog, QLineEdit, QMessageBox, QSlider)
from PyQt5.QtGui import QColor, QPalette, QFont
from PyQt5.QtCore import Qt, QTimer
import time
import colorsys

from keyboard_controller import KeyboardController
from config_manager import ConfigManager

class KeyButton(QPushButton):
    def __init__(self, key_name, index, parent=None):
        super().__init__(key_name, parent)
        self.key_name = key_name
        self.index = index
        self.color = QColor(0, 255, 0)  # Default color: green
        self.setFixedSize(60, 60)
        self.updateStyle()
        
    def setKeyColor(self, color):
        """Set the button color"""
        self.color = color
        self.updateStyle()
    
    def updateStyle(self):
        """Update the button style to reflect the current color"""
        r, g, b = self.color.red(), self.color.green(), self.color.blue()
        text_color = "#000000" if (r + g + b) > 380 else "#FFFFFF"
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: rgb({r}, {g}, {b});
                color: {text_color};
                border: 1px solid #222222;
                border-radius: 5px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: rgb({min(r+20, 255)}, {min(g+20, 255)}, {min(b+20, 255)});
                border: 2px solid #CCCCCC;
            }}
        """)

class KeyboardConfigApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.keyboard = KeyboardController()
        self.config_manager = ConfigManager()
        self.keys = []
        
        # Setup auto-reload before calling load_config
        self.auto_reload = True
        self.reload_timer = QTimer()
        self.reload_timer.timeout.connect(self.send_config)
        
        self.setupUI()
        
        # Load default configuration
        self.load_config()
        
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
        
        # Keyboard layout
        keyboard_layout = QGridLayout()
        keyboard_layout.setSpacing(5)
        
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
                    key.clicked.connect(lambda checked, k=key: self.change_key_color(k))
                    keyboard_layout.addWidget(key, row, col)
                    self.keys.append(key)
                    key_index += 1
                else:
                    # Empty placeholder for NAN keys
                    placeholder = QWidget()
                    placeholder.setFixedSize(60, 60)
                    keyboard_layout.addWidget(placeholder, row, col)
        
        # Quick color selection
        color_panel = QHBoxLayout()
        standard_colors = [
            (255, 0, 0), (0, 255, 0), (0, 0, 255),  # Red, Green, Blue
            (255, 255, 0), (0, 255, 255), (255, 0, 255),  # Yellow, Cyan, Magenta
            (255, 255, 255), (0, 0, 0), (128, 128, 128)  # White, Black, Gray
        ]
        
        for r, g, b in standard_colors:
            color_btn = QPushButton()
            color_btn.setFixedSize(40, 40)
            color_btn.setStyleSheet(f"background-color: rgb({r}, {g}, {b}); border: 1px solid black;")
            color_btn.clicked.connect(lambda checked, color=(r, g, b): self.set_all_keys_color(color))
            color_panel.addWidget(color_btn)
        
        # Add custom color button
        custom_color_btn = QPushButton("Custom")
        custom_color_btn.clicked.connect(self.choose_custom_color)
        color_panel.addWidget(custom_color_btn)
        
        # Auto reload toggle
        self.auto_reload_btn = QPushButton("Auto-Reload: ON")
        self.auto_reload_btn.setCheckable(True)
        self.auto_reload_btn.setChecked(True)
        self.auto_reload_btn.clicked.connect(self.toggle_auto_reload)
        color_panel.addWidget(self.auto_reload_btn)
        
        # After the color panel setup, add an intensity slider
        intensity_panel = QHBoxLayout()
        intensity_panel.addWidget(QLabel("Brightness:"))
        
        self.intensity_slider = QSlider(Qt.Horizontal)
        self.intensity_slider.setMinimum(0)
        self.intensity_slider.setMaximum(100)
        self.intensity_slider.setValue(100)  # Default to full brightness
        self.intensity_slider.setTickPosition(QSlider.TicksBelow)
        self.intensity_slider.setTickInterval(10)
        self.intensity_slider.valueChanged.connect(self.intensity_changed)
        intensity_panel.addWidget(self.intensity_slider)
        
        # Intensity value label
        self.intensity_label = QLabel("100%")
        intensity_panel.addWidget(self.intensity_label)
        
        # Add this panel to the main layout
        main_layout.addLayout(intensity_panel)
        
        # Add Function Keys button
        function_keys_btn = QPushButton("Function Keys")
        function_keys_btn.clicked.connect(lambda: self.set_function_key_colors((255, 128, 0))) # Orange color
        color_panel.addWidget(function_keys_btn)
        
        # Add Rainbow button
        rainbow_btn = QPushButton("Rainbow")
        rainbow_btn.clicked.connect(self.set_rainbow_colors)
        color_panel.addWidget(rainbow_btn)
        
        main_layout.addLayout(keyboard_layout)
        main_layout.addLayout(color_panel)
        
        # Status bar
        self.statusBar().showMessage("Disconnected")
        
        self.setCentralWidget(central_widget)
    
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
    
    def change_key_color(self, key):
        color = QColorDialog.getColor(key.color, self, "Select Key Color")
        if color.isValid():
            key.setKeyColor(color)
            if self.auto_reload and self.keyboard.connected:
                self.send_config()
    
    def choose_custom_color(self):
        color = QColorDialog.getColor(Qt.white, self, "Select Color for All Keys")
        if color.isValid():
            self.set_all_keys_color((color.red(), color.green(), color.blue()))
    
    def set_all_keys_color(self, color):
        r, g, b = color
        for key in self.keys:
            key.setKeyColor(QColor(r, g, b))
        
        if self.auto_reload and self.keyboard.connected:
            self.send_config()
    
    def intensity_changed(self):
        """Handle changes to the intensity slider"""
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
            
            # Visual feedback animation
            for key in self.keys:
                original_style = key.styleSheet()
                key.setStyleSheet(original_style + "border: 2px solid white;")
                QApplication.processEvents()  # Update UI
            
            # Reset styles after animation
            time.sleep(0.2)
            for key in self.keys:
                key.updateStyle()
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
        # Save original status
        original_status = self.statusBar().currentMessage()
        
        # Flash status message
        self.statusBar().showMessage("Applying configuration...")
        
        # Flash key borders
        for key in self.keys:
            original_style = key.styleSheet()
            key.setStyleSheet(original_style + "border: 2px solid white;")
            QApplication.processEvents()  # Update UI immediately
        
        # Reset after brief pause
        time.sleep(0.2)
        for key in self.keys:
            key.updateStyle()
        
        # Restore status with success message
        self.statusBar().showMessage(f"{original_status} - Configuration applied")
    
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