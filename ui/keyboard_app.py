import sys
import threading
import colorsys
import os
from PyQt5.QtWidgets import (QMainWindow, QApplication, QMessageBox, QInputDialog, QColorDialog,
                            QSystemTrayIcon, QGridLayout, QPushButton)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, QTimer, QEvent

from keyboard_controller import KeyboardController
from config_manager import ConfigManager
from shortcut_manager import ShortcutManager
from shortcut_lighting import ShortcutLighting
from features.text_display import TextDisplayFeature
from features.effects import EffectsFeature
from features.system_monitor import SystemMonitorFeature

from ui.custom_events import CustomKeyEvent
from ui.key_button import KeyButton 
from ui.system_tray import SystemTrayManager
from input.keyboard_monitor import KeyboardMonitor
from ui.color_display import ColorDisplay

# Import the UI setup function
from ui.setup_ui import setup_ui

class KeyboardConfigApp(QMainWindow):
    """Main application for keyboard LED configuration"""
    
    def __init__(self):
        """Initialize the main application"""
        super().__init__()
        
        # Initialize controllers and managers
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
        self.reload_timer.setSingleShot(True)  # Important! Only trigger once
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
        
        # Create text display and effects features
        self.text_display = TextDisplayFeature(self)
        self.effects = EffectsFeature(self)
        
        # Add system monitoring feature
        self.system_monitor = SystemMonitorFeature(self)
        
        # Create keyboard monitor for global shortcuts
        self.keyboard_monitor = KeyboardMonitor(self)
        
        # Setup UI
        setup_ui(self)
        
        # Setup system tray
        self.system_tray = SystemTrayManager(self)
        
        # Load default configuration (this will also record base_colors)
        self.load_config()
        
        # Auto-connect to keyboard if enabled
        self.auto_connect = True
        # Use timer for delayed startup to allow UI to finish loading
        QTimer.singleShot(1000, self.safe_auto_connect)
        
        # Install event filter to catch key events
        QApplication.instance().installEventFilter(self)
    
    # Create keyboard methods
    def create_keyboard(self, layout):
        """Create the keyboard layout using button widgets"""
        # Keyboard layout definition
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
        
        # Keep track of key indices
        key_index = 0
        
        # Check if custom layout is saved
        custom_layout = self.shortcut_manager.load_keyboard_layout()
        if custom_layout:
            layout_def = custom_layout
        
        # Add buttons to the grid layout for each key in the keyboard
        for col, column in enumerate(layout_def):
            for row, key_name in enumerate(column):
                if key_name != "NAN":  # Skip empty slots
                    key_button = KeyButton(key_name, key_index, self)
                    key_button.clicked.connect(lambda checked, kb=key_button: self.handle_key_click(kb))
                    layout.addWidget(key_button, row, col)
                    self.keys.append(key_button)
                    key_index += 1
        
        # Save the keyboard layout to the shortcut manager
        self.save_keyboard_layout()
        
        # Enable keyboard layout
        return True

    def save_keyboard_layout(self):
        """Save the keyboard layout to the shortcut manager"""
        # Rebuild layout from current keys
        layout_matrix = []
        for i in range(16):  # 16 columns
            column = []
            for j in range(6):  # 6 rows
                found = False
                for key in self.keys:
                    # Check if this key's widget is at this grid position
                    grid_pos = self.find_grid_position(key)
                    if grid_pos and grid_pos[0] == j and grid_pos[1] == i:
                        column.append(key.key_name)
                        found = True
                        break
                if not found:
                    column.append("NAN")  # Empty slot
            layout_matrix.append(column)
        
        # Save the layout
        self.shortcut_manager.save_keyboard_layout(layout_matrix)

    def find_grid_position(self, widget):
        """Find the grid position of a widget"""
        # Find the grid layout index of a widget
        parent = widget.parentWidget()
        if parent:
            for item in parent.children():
                if item == widget:
                    index = parent.layout().indexOf(item)
                    if index != -1:
                        return parent.layout().getItemPosition(index)[:2]
        return None
        
    # Configuration and connection methods
    def load_config(self, config_name=None):
        """Load a configuration"""
        # Avoid recursive loading by checking if we're already loading this config
        if hasattr(self, '_currently_loading') and self._currently_loading == config_name:
            return
        
        # Set flag to prevent recursion
        self._currently_loading = config_name
        
        try:
            # Get the list of available configurations
            configs = self.config_manager.get_config_list()
            
            # Update the combo box without triggering signals
            if hasattr(self, 'config_combo'):
                self.config_combo.blockSignals(True)
                current_index = self.config_combo.currentIndex()
                self.config_combo.clear()
                self.config_combo.addItems(configs)
                
                # If a specific config was requested, select it
                if config_name and config_name in configs:
                    self.config_combo.setCurrentText(config_name)
                elif current_index >= 0 and current_index < len(configs):
                    # Otherwise restore previous selection if valid
                    self.config_combo.setCurrentIndex(current_index)
                elif configs:
                    # Default to first config if available
                    self.config_combo.setCurrentIndex(0)
                self.config_combo.blockSignals(False)
            
            # Load the selected configuration
            if config_name:
                selected_config = config_name
            elif hasattr(self, 'config_combo') and self.config_combo.currentText():
                selected_config = self.config_combo.currentText()
            else:
                selected_config = None
            
            if selected_config:
                config = self.config_manager.load_config(selected_config)
                
                # Apply the configuration to the UI
                if config and "colors" in config and len(config["colors"]) == len(self.keys):
                    for i, key in enumerate(self.keys):
                        r, g, b = config["colors"][i]
                        key.setKeyColor(QColor(r, g, b))
                    
                    self.statusBar().showMessage(f"Loaded configuration: {selected_config}")
                    
                    # ─── record "base" colors for master/region sliders ───
                    # so slider always works off the original config, not last tinted color
                    self.base_colors = {
                        key.index: QColor(key.color)
                        for key in self.keys
                    }
                    
                    # Send to keyboard if connected and auto-reload is on
                    if self.auto_reload and self.keyboard.connected:
                        if not self.reload_timer.isActive():
                            self.reload_timer.start(200)
            
            return config
        
        finally:
            # Clear the loading flag
            self._currently_loading = None
    
    def send_config(self):
        """Send the current configuration to the keyboard"""
        if not self.keyboard.connected:
            self.statusBar().showMessage("Not connected to keyboard")
            return
        
        try:
            # Extract colors from keyboard for current config
            config_colors = []
            for key in self.keys:
                c = key.color
                config_colors.append((c.red(), c.green(), c.blue()))
            
            # Update config manager
            self.config_manager.current_config["colors"] = config_colors
            
            # Try to find the right method for sending colors
            # Include send_led_config (used by ShortcutLighting), then fall back
            color_methods = [
                'send_led_config',      # actual method called in shortcut_lighting.py
                'set_colors',
                'send_colors',
                'update_colors',
                'set_all_colors',
                'apply_colors',
                'send_color_config',
                'set_leds',
                'update_leds',
            ]
            
            # Find the first method that exists
            method_found = False
            for method_name in color_methods:
                if hasattr(self.keyboard, method_name):
                    method = getattr(self.keyboard, method_name)
                    success = method(config_colors)
                    method_found = True
                    self.statusBar().showMessage(f"Configuration sent to keyboard using {method_name}")
                    break
            
            if not method_found:
                # Last resort: print available methods and fail gracefully
                available_methods = [m for m in dir(self.keyboard) if not m.startswith('_') and callable(getattr(self.keyboard, m))]
                print(f"Available methods in KeyboardController: {available_methods}")
                self.statusBar().showMessage("Error: No compatible method found to send colors to keyboard")
                return False
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.statusBar().showMessage(f"Error: {str(e)}")
            return False
        
        return True
    
    def show_save_dialog(self):
        """Show dialog to save the current configuration"""
        # Get configuration name
        name, ok = QInputDialog.getText(self, "Save Configuration", "Configuration Name:")
        if ok and name:
            # Extract current colors from keyboard
            config_colors = []
            for key in self.keys:
                c = key.color
                config_colors.append((c.red(), c.green(), c.blue()))
            
            # Save configuration
            success = self.config_manager.save_config(name, config_colors)
            if success:
                # reload & apply immediately
                self.load_config(name)
                if self.auto_reload and self.keyboard.connected:
                    self.send_config()
                self.statusBar().showMessage(f"Configuration '{name}' saved")
            else:
                QMessageBox.critical(self, "Save Error", f"Could not save '{name}'")
    
    # Event handling methods        
    def eventFilter(self, obj, event):
        """Filter events for keyboard shortcut handling"""
        if event.type() == QEvent.KeyPress:
            key_event = event
            key_code = key_event.key()
            
            # Only process keyboard events if a keyboard widget has focus
            from utils.key_mappings import QT_KEY_MAP
            if key_code in QT_KEY_MAP:
                key_name = QT_KEY_MAP[key_code]
                self.shortcut_lighting.handle_key_press(key_name)
        
        elif event.type() == QEvent.KeyRelease:
            key_event = event
            key_code = key_event.key()
            
            # Only process keyboard events if a keyboard widget has focus
            from utils.key_mappings import QT_KEY_MAP
            if key_code in QT_KEY_MAP:
                key_name = QT_KEY_MAP[key_code]
                self.shortcut_lighting.handle_key_release(key_name)
        
        return False  # Continue normal event processing
    
    def event(self, event):
        """Handle custom key events from Wayland/evdev monitoring"""
        if event.type() == CustomKeyEvent.KeyPress:
            self.shortcut_lighting.handle_key_press(event.key_name)
            return True
        elif event.type() == CustomKeyEvent.KeyRelease:
            self.shortcut_lighting.handle_key_release(event.key_name)
            return True
        return super().event(event)
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Check if system tray is available and visible
        if (hasattr(self, 'system_tray') and self.system_tray and 
                hasattr(self.system_tray, 'tray_icon') and 
                self.system_tray.tray_icon and 
                self.system_tray.tray_icon.isVisible()):
            # Hide window instead of closing and show notification
            event.ignore()
            self.hide()
            
            try:
                self.system_tray.tray_icon.showMessage(
                    "Application Minimized",
                    "The application is still running in the system tray.",
                    QSystemTrayIcon.Information,
                    2000
                )
            except Exception as e:
                print(f"Error showing tray notification: {e}")
        else:
            # Actually close the application
            self.stop_all_timers()
            event.accept()
        
    def stop_all_timers(self):
        """Stop all timers to prevent errors on application close"""
        if hasattr(self, 'reload_timer') and self.reload_timer:
            self.reload_timer.stop()
        if hasattr(self, 'intensity_timer') and self.intensity_timer:
            self.intensity_timer.stop()
        
        # Stop system monitor
        if hasattr(self, 'system_monitor'):
            self.system_monitor.stop_monitoring()
        
        # Stop keyboard monitor
        if hasattr(self, 'keyboard_monitor'):
            self.keyboard_monitor.stop_global_shortcut_monitor()
    
    # Selection and UI methods
    def handle_key_click(self, key_button):
        """Handle a key button click"""
        if self.selection_mode:
            # Toggle selection
            if key_button in self.selected_keys:
                self.selected_keys.remove(key_button)
                key_button.setSelected(False)
            else:
                self.selected_keys.append(key_button)
                key_button.setSelected(True)
        else:
            # Apply current color
            key_button.setKeyColor(self.current_color)
            
            # Update keyboard if auto-reload is on
            if self.auto_reload and self.keyboard.connected:
                # Use timer to debounce rapid changes
                self.reload_timer.start(200)
    
    def toggle_selection_mode(self, enabled):
        """Toggle selection mode"""
        self.selection_mode = enabled
        
        # Clear selection when disabling selection mode
        if not enabled:
            for key in self.selected_keys:
                key.setSelected(False)
            self.selected_keys = []
        
        self.statusBar().showMessage("Selection mode " + ("enabled" if enabled else "disabled"))
    
    def apply_color_to_selection(self):
        """Apply the current color to all selected keys"""
        if not self.selected_keys:
            self.statusBar().showMessage("No keys selected")
            return
        
        # Apply color to each selected key
        for key in self.selected_keys:
            key.setKeyColor(self.current_color)
        
        # Update keyboard if auto-reload is on
        if self.auto_reload and self.keyboard.connected:
            self.reload_timer.start(200)
            
        self.statusBar().showMessage(f"Applied color to {len(self.selected_keys)} keys")
    
    def select_color(self, color):
        """Set the current working color"""
        self.current_color = color
        self.color_display.updateColor(color)
        
        # Update RGB sliders
        self.red_slider.setValue(color.red())
        self.green_slider.setValue(color.green())
        self.blue_slider.setValue(color.blue())
    
    def show_color_dialog(self):
        """Show color picker dialog"""
        color = QColorDialog.getColor(self.current_color, self)
        if color.isValid():
            self.select_color(color)
    
    def color_sliders_changed(self):
        """Update color from RGB sliders"""
        r = self.red_slider.value()
        g = self.green_slider.value()
        b = self.blue_slider.value()
        self.select_color(QColor(r, g, b))
    
    # Color and intensity methods
    def rgb_to_hsv(self, r, g, b):
        """Convert RGB [0-255] to HSV [0-1]"""
        return colorsys.rgb_to_hsv(r/255, g/255, b/255)
    
    def hsv_to_rgb(self, h, s, v):
        """Convert HSV [0-1] to RGB [0-255]"""
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return [int(r*255), int(g*255), int(b*255)]
        
    def intensity_changed(self, value):
        """Handle master intensity slider change"""
        # Update label
        self.intensity_label.setText(f"{value}%")
        
        # Calculate intensity multiplier
        intensity = value / 100.0
        
        # For each key, adjust brightness relative to the recorded base color
        for key in self.keys:
            base = self.base_colors.get(key.index, key.color)
            h, s, v = self.rgb_to_hsv(base.red(), base.green(), base.blue())
            new_rgb = self.hsv_to_rgb(h, s, v * intensity)
            key.setKeyColor(QColor(*new_rgb))
        
        # Debounce send
        self.intensity_timer.start(200)
    
    def apply_intensity(self):
        """Apply the intensity changes to the keyboard"""
        if self.auto_reload and self.keyboard.connected:
            self.send_config()
    
    def region_intensity_changed(self, value):
        """Handle region intensity slider change"""
        # Update label
        self.region_intensity_label.setText(f"{value}%")
        
        # Calculate intensity multiplier
        intensity = value / 100.0
        
        if not self.selected_keys:
            self.statusBar().showMessage("No keys selected for region intensity")
            return
            
        for key in self.selected_keys:
            base = self.base_colors.get(key.index, key.color)
            h, s, v = self.rgb_to_hsv(base.red(), base.green(), base.blue())
            new_rgb = self.hsv_to_rgb(h, s, v * intensity)
            key.setKeyColor(QColor(*new_rgb))
        
        if self.auto_reload and self.keyboard.connected:
            self.reload_timer.start(200)
    
    # Connection methods
    def toggle_connection(self):
        """Toggle the connection to the keyboard"""
        try:
            if not self.keyboard.connected:
                if self.connect_to_keyboard():
                    self.connect_button.setText("Disconnect")
                    self.status_label.setText("● Connected")
                    self.status_label.setStyleSheet("color: #4cd964; font-weight: bold;")
                    self.statusBar().showMessage("Successfully connected to keyboard")
            else:
                self.keyboard.disconnect()
                self.connect_button.setText("Connect")
                self.status_label.setText("◯ Disconnected")
                self.status_label.setStyleSheet("color: #ff6b6b; font-weight: bold;")
                self.statusBar().showMessage("Disconnected from keyboard")
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.statusBar().showMessage(f"Connection error: {str(e)}")
    
    def connect_to_keyboard(self):
        """Connect to the keyboard"""
        try:
            if self.keyboard.connect():
                self.connect_button.setText("Disconnect")
                self.status_label.setText("● Connected")
                self.status_label.setStyleSheet("color: #4cd964; font-weight: bold;")
                self.statusBar().showMessage("Connected to keyboard")
                
                # Apply current configuration safely
                if hasattr(self, 'config_manager') and hasattr(self.config_manager, 'current_config'):
                    QTimer.singleShot(300, self.safe_send_config)  # Slight delay to ensure connection is ready
                
                return True
            else:
                self.statusBar().showMessage("Failed to connect to keyboard")
                return False
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.statusBar().showMessage(f"Connection error: {str(e)}")
            return False

    def safe_send_config(self):
        """Safely send configuration to keyboard with error handling"""
        try:
            self.send_config()
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.statusBar().showMessage(f"Error sending configuration: {str(e)}")
    
    def toggle_auto_reload(self, state):
        """Toggle auto-reload of configuration"""
        self.auto_reload = (state == Qt.Checked)
        
    # Effects and presets methods
    def apply_gaming_preset(self):
        """Apply gaming-focused color preset (WASD and arrow keys)"""
        # Find WASD keys
        wasd_keys = ["W", "A", "S", "D"]
        arrow_keys = ["←", "↑", "→", "↓"]
        
        # Set all keys to dark
        for key in self.keys:
            key.setKeyColor(QColor(20, 20, 20))
        
        # Highlight WASD and arrow keys
        for key in self.keys:
            if key.key_name in wasd_keys:
                key.setKeyColor(QColor(255, 0, 0))  # Red
            elif key.key_name in arrow_keys:
                key.setKeyColor(QColor(0, 0, 255))  # Blue
        
        # Send config to keyboard
        if self.auto_reload and self.keyboard.connected:
            self.send_config()
        
        self.statusBar().showMessage("Applied gaming preset")
    
    def apply_typing_preset(self):
        """Apply typing-focused color preset (highlights home row)"""
        # Find home row keys (ASDF JKL;)
        home_row = ["A", "S", "D", "F", "J", "K", "L", ";"]
        
        # Set all keys to dark blue
        for key in self.keys:
            key.setKeyColor(QColor(0, 0, 100))
        
        # Highlight home row
        for key in self.keys:
            if key.key_name in home_row:
                key.setKeyColor(QColor(0, 200, 255))  # Cyan
        
        # Send config to keyboard
        if self.auto_reload and self.keyboard.connected:
            self.send_config()
        
        self.statusBar().showMessage("Applied typing preset")
    
    # Shortcut monitoring methods
    def start_shortcut_monitoring(self):
        """Start shortcut monitoring"""
        self.shortcut_lighting.start_monitor()
        self.statusBar().showMessage("Shortcut monitoring started")
    
    def stop_shortcut_monitoring(self):
        """Stop shortcut monitoring"""
        self.shortcut_lighting.stop_monitor()
        self.statusBar().showMessage("Shortcut monitoring stopped")
    
    # System monitoring methods
    def start_system_monitoring(self):
        """Start system monitoring based on selected metric"""
        metric_map = {
            "CPU Usage": "cpu",
            "RAM Usage": "ram",
            "Battery Status": "battery",
            "All Metrics": "all"
        }
        metric = metric_map[self.monitor_combo.currentText()]
        
        # Get update interval
        interval = self.update_interval_slider.value()
        
        if self.system_monitor.start_monitoring(metric, interval):
            self.statusBar().showMessage(f"System monitoring started: {self.monitor_combo.currentText()}")
        else:
            self.statusBar().showMessage("Failed to start system monitoring")

    def stop_system_monitoring(self):
        """Stop system monitoring"""
        self.system_monitor.stop_monitoring()
        self.statusBar().showMessage("System monitoring stopped")

    def start_system_monitoring_from_tray(self, metric):
        """Start system monitoring from the system tray menu"""
        # Default to 2 second update interval
        if self.system_monitor.start_monitoring(metric, 2.0):
            self.system_tray.tray_icon.showMessage(
                "System Monitoring",
                f"Started monitoring {metric.upper()}",
                QSystemTrayIcon.Information,
                2000
            )
        else:
            self.system_tray.tray_icon.showMessage(
                "System Monitoring",
                f"Failed to start monitoring {metric.upper()}",
                QSystemTrayIcon.Warning,
                2000
            )

    # Add a new safe auto-connect method
    def safe_auto_connect(self):
        """Safely attempt to auto-connect to the keyboard"""
        if not self.auto_connect:
            return
        
        try:
            connected = self.connect_to_keyboard()
            if connected:
                self.statusBar().showMessage("Auto-connected to keyboard")
            else:
                self.statusBar().showMessage("Auto-connect: No compatible keyboard found")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.statusBar().showMessage(f"Auto-connect failed: {str(e)}")

    def toggle_selection_mode(self, state):
         """Enable or disable key-selection mode (region tool)."""
         self.selection_mode = (state == Qt.Checked)
         # if turning OFF, clear any highlighted keys
         if not self.selection_mode:
             for kb in self.selected_keys:
                 kb.setSelected(False)
             self.selected_keys.clear()
         self.statusBar().showMessage(
             f"Selection mode {'ON' if self.selection_mode else 'OFF'}"
         )

    def on_config_changed(self, idx):
         """Called when user picks a config from the combo → load + apply."""
         name = self.config_combo.currentText()
         if not name:
             return
         # Load (updates UI colors & base_colors)
         self.load_config(name)
         # Immediately send to keyboard if auto_reload
         if self.auto_reload and self.keyboard.connected:
             self.send_config()

    def overwrite_config(self):
        """Overwrite the currently selected configuration."""
        name = self.config_combo.currentText()
        if not name:
            QMessageBox.warning(self, "Save Error", "No configuration selected to overwrite")
            return
        # Gather current colors
        colors = [(k.color.red(), k.color.green(), k.color.blue()) for k in self.keys]
        # Overwrite the existing config exactly as Save As
        success = self.config_manager.save_config(name, colors)
        if success:
            # reload & apply
            self.load_config(name)
            if self.auto_reload and self.keyboard.connected:
                self.send_config()
            self.statusBar().showMessage(f"Configuration '{name}' overwritten")
        else:
            QMessageBox.critical(self, "Save Error", f"Could not overwrite '{name}'")

    def toggle_keyboard_leds(self):
        """Toggle LEDs on/off for selected keys or all keys."""
        if not hasattr(self, 'leds_off'):
            self.leds_off = {}

        # If you have a selection, only toggle those keys
        if self.selected_keys:
            for key in self.selected_keys:
                is_off = (key.color.red() == 0 and key.color.green() == 0 and key.color.blue() == 0)
                if is_off:
                    # restore saved or default
                    key.setKeyColor(self.leds_off.get(key.index, QColor(0,255,0)))
                else:
                    # turn off and save
                    self.leds_off[key.index] = QColor(key.color)
                    key.setKeyColor(QColor(0,0,0))
        else:
            # global toggle
            if self.led_toggle.isChecked():
                for key in self.keys:
                    key.setKeyColor(self.leds_off.get(key.index, QColor(0,255,0)))
            else:
                for key in self.keys:
                    if any((key.color.red(), key.color.green(), key.color.blue())):
                        self.leds_off[key.index] = QColor(key.color)
                    key.setKeyColor(QColor(0,0,0))

        if self.auto_reload and self.keyboard.connected:
            self.send_config()

    def toggle_function_keys(self, checked):
        """When the Function-Keys button is checked, highlight or restore them."""
        if checked:
            # highlight with current color
            rgb = (self.current_color.red(),
                   self.current_color.green(),
                   self.current_color.blue())
            self.effects.set_function_key_colors(rgb)
        else:
            # restore original base_colors
            if hasattr(self, 'base_colors'):
                for key in self.keys:
                    if key.key_name in self.effects.function_keys:
                        key.setKeyColor(self.base_colors.get(key.index, QColor(0,0,0)))
            if self.auto_reload and self.keyboard.connected:
                self.send_config()

    def create_color_preset(self):
        """Ask the user for a name and add the current_color as a new preset."""
        name, ok = QInputDialog.getText(self, "Create Color Preset", "Preset name:")
        if not ok or not name.strip():
            return
        # find the bottom‐preset grid by objectName
        grid = self.findChild(QGridLayout, "preset_layout")
        if not grid:
            return

        # determine next row/col
        row = grid.rowCount()
        col = grid.columnCount()
        if col >= 5:
            col = 0
            row += 1

        btn = QPushButton("")
        btn.setStyleSheet(f"""
            background-color: {self.current_color.name()};
            border-radius: 4px;
            min-height:24px; max-height:24px;
        """)
        btn.setToolTip(name)
        btn.clicked.connect(lambda _, c=self.current_color: self.select_color(c))
        grid.addWidget(btn, row, col)
        self.statusBar().showMessage(f"Preset '{name}' created", 3000)
