"""
Application-specific shortcut highlighting.
Highlights keyboard shortcuts based on the active application window.
"""

import os
import json
import threading
import subprocess
import time
import logging
from pathlib import Path
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QListWidget, QComboBox, QLineEdit,
                            QTableWidget, QTableWidgetItem, QHeaderView,
                            QCheckBox, QMessageBox, QColorDialog, QFrame,
                            QSplitter, QWidget, QGroupBox)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, pyqtSignal, QTimer

logger = logging.getLogger(__name__)

class ColorDisplay(QFrame):
    clicked = pyqtSignal()
    
    def __init__(self, color=Qt.green, parent=None):
        super().__init__(parent)
        self.color = QColor(color)
        self.setMinimumSize(40, 20)
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

class AppShortcutFeature:
    def __init__(self, keyboard_app):
        """
        Initialize the application-specific shortcut feature.
        
        Args:
            keyboard_app: The main keyboard application instance
        """
        self.app = keyboard_app
        self.keys = keyboard_app.keys
        self.keyboard = keyboard_app.keyboard
        self.shortcut_manager = keyboard_app.shortcut_manager
        
        # Get the config directory
        self.config_dir = self.shortcut_manager.config_dir
        self.app_shortcuts_dir = os.path.join(self.config_dir, "app_shortcuts")
        
        # Ensure app shortcuts directory exists
        os.makedirs(self.app_shortcuts_dir, exist_ok=True)
        
        # State tracking
        self.monitoring = False
        self.monitor_thread = None
        self.current_app = None
        self.app_shortcuts = {}
        self.app_colors = {}
        self.default_color = QColor(255, 165, 0)  # Orange by default
        
        # Store the default state for efficient restoration
        self.default_state = []  # Will store RGB tuples for each key
        
        # CRITICAL FIX: Add our own key tracking
        self._currently_pressed_keys = set()
        
        # Load any existing app shortcuts
        self.load_app_shortcuts()
        
    def load_app_shortcuts(self):
        """Load all application shortcuts from the config directory"""
        self.app_shortcuts = {}
        self.app_colors = {}
        
        try:
            # Load the app colors file if it exists
            app_colors_path = os.path.join(self.app_shortcuts_dir, "app_colors.json")
            if os.path.exists(app_colors_path):
                with open(app_colors_path, 'r') as f:
                    color_data = json.load(f)
                    for app_name, color_value in color_data.items():
                        self.app_colors[app_name] = QColor(*color_value)
            
            # Load individual app shortcut files
            for filename in os.listdir(self.app_shortcuts_dir):
                if filename.endswith('.json') and filename != "app_colors.json":
                    app_name = filename.replace('.json', '')
                    file_path = os.path.join(self.app_shortcuts_dir, filename)
                    
                    with open(file_path, 'r') as f:
                        shortcuts = json.load(f)
                        self.app_shortcuts[app_name] = shortcuts
                        
            logger.info(f"Loaded shortcuts for {len(self.app_shortcuts)} applications")
            
        except Exception as e:
            logger.error(f"Error loading application shortcuts: {e}")
    
    def save_app_shortcuts(self, app_name, shortcut_data):
        """
        Save shortcuts for a specific application
        
        Args:
            app_name: Name of the application
            shortcut_data: Dictionary with modifiers as keys and lists of keys as values
                           e.g., {"Ctrl": ["W", "A", "S", "D"], "Ctrl+Shift": ["N", "P"]}
        """
        try:
            # Save the shortcuts structure directly
            file_path = os.path.join(self.app_shortcuts_dir, f"{app_name}.json")
            with open(file_path, 'w') as f:
                json.dump(shortcut_data, f, indent=2)
            
            # Update in-memory cache
            self.app_shortcuts[app_name] = shortcut_data
            
            logger.info(f"Saved shortcuts for {app_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving application shortcuts for {app_name}: {e}")
            return False
    
    def save_app_colors(self):
        """Save application highlight colors"""
        try:
            file_path = os.path.join(self.app_shortcuts_dir, "app_colors.json")
            
            # Convert QColors to RGB tuples for JSON serialization
            color_data = {}
            for app_name, color in self.app_colors.items():
                color_data[app_name] = (color.red(), color.green(), color.blue())
            
            with open(file_path, 'w') as f:
                json.dump(color_data, f, indent=2)
            
            logger.info(f"Saved application colors")
            return True
            
        except Exception as e:
            logger.error(f"Error saving application colors: {e}")
            return False
    
    def get_active_window_name(self):
        """Get the class name of the active window using appropriate window manager command"""
        try:
            # Check if Hyprland is running (Wayland)
            if os.environ.get('HYPRLAND_INSTANCE_SIGNATURE'):
                cmd = "hyprctl activewindow | grep class | awk '{print $2}'"
                result = subprocess.check_output(cmd, shell=True, text=True).strip()
                return result
                
            # Check for X11 window managers
            elif os.environ.get('DISPLAY'):
                cmd = "xprop -id $(xprop -root _NET_ACTIVE_WINDOW | cut -d ' ' -f 5) | grep WM_CLASS | awk '{print $4}' | tr -d '\"'"
                result = subprocess.check_output(cmd, shell=True, text=True).strip()
                return result
                
            # Check for other Wayland compositors (GNOME, etc.)
            elif os.environ.get('WAYLAND_DISPLAY'):
                # This is a simplified approach - in practice more logic might be needed
                # Would need additional logic specific to other Wayland compositors
                return "Unknown"
                
            else:
                return "Unknown"
                
        except Exception as e:
            logger.error(f"Error getting active window: {e}")
            return "Unknown"
    
    def start_monitoring(self):
        """Start monitoring for application changes"""
        if self.monitoring:
            return
            
        self.monitoring = True
        
        # Start monitor thread
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.monitor_thread.start()
        
        logger.info("Application shortcut monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring for application changes"""
        self.monitoring = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)
            
        logger.info("Application shortcut monitoring stopped")
        
        # Restore default keyboard appearance
        self.app.shortcut_lighting.restore_key_colors()
    
    def _monitoring_loop(self):
        """Background thread to monitor active application and update shortcuts"""
        last_check_time = 0
        
        while self.monitoring:
            try:
                # Only check for app changes every 1 second to reduce CPU usage
                current_time = time.time()
                if current_time - last_check_time < 1.0:
                    time.sleep(0.1)
                    continue
                    
                last_check_time = current_time
                    
                # Get current active application
                app_name = self.get_active_window_name()
                
                # If application changed, update shortcuts
                if app_name != self.current_app:
                    self.current_app = app_name
                    logger.info(f"Active application changed to: {app_name}")
                    
                    # IMPORTANT: Don't use QTimer here - directly apply the shortcuts
                    # This ensures immediate update when application changes
                    self.apply_app_shortcuts(app_name)
                    
            except Exception as e:
                logger.error(f"Error in app monitoring loop: {e}")
                time.sleep(1.0)  # Prevent rapid error looping
    
    def apply_app_shortcuts(self, app_name):
        """Apply application-specific shortcuts to the keyboard"""
        try:
            # If we don't have specific shortcuts for this app, use defaults
            if app_name not in self.app_shortcuts:
                # Just display the application name on the keyboard for visual feedback
                logger.info(f"No shortcuts defined for {app_name}, using default behavior")
                
                # Restore to default configuration and save this as our default state
                self.app.shortcut_lighting.restore_key_colors()
                self.save_default_state()
                return
                
            # We have specific shortcuts for this app - apply them
            logger.info(f"Applying shortcuts for {app_name}")
            self._apply_app_specific_shortcuts(app_name)
        except Exception as e:
            logger.error(f"Error applying shortcuts for {app_name}: {e}")
            # In case of error, try to restore to default state
            try:
                self.restore_default_state()
            except:
                pass
    
    def _safely_display_app_name(self, app_name):
        """Safely display app name with proper error handling"""
        try:
            # Only run if monitoring is still active
            if not self.monitoring:
                return
            
            # Clear keyboard with error handling
            try:
                self.app.clear_keyboard()
            except Exception as e:
                logger.error(f"Error clearing keyboard: {e}")
                return
            
            # Display app name for a brief moment
            try:
                short_name = app_name[:8] if app_name else "Unknown"
                self.app.text_display.display_text(short_name, clear_first=True)
                
                # After a brief delay, restore to default config
                QTimer.singleShot(1000, self.app.shortcut_lighting.restore_key_colors)
            except Exception as e:
                logger.error(f"Error displaying app name: {e}")
                # Try to restore default state
                QTimer.singleShot(0, self.app.shortcut_lighting.restore_key_colors)
        except Exception as e:
            logger.error(f"Unexpected error in _safely_display_app_name: {e}")
    
    def _apply_app_specific_shortcuts(self, app_name):
        """Apply shortcuts specific to an application with proper error handling"""
        try:
            # Clear keyboard first
            self.app.clear_keyboard()
            
            # Get app-specific color or use default
            highlight_color = self.app_colors.get(app_name, self.default_color)
            
            # Get the shortcuts for this app
            shortcuts = self.app_shortcuts[app_name]
            
            # Check if we should apply default keys highlighting
            if "default_keys" in shortcuts and shortcuts["default_keys"]:
                logger.info(f"Highlighting default keys for {app_name}: {shortcuts['default_keys']}")
                for key_name in shortcuts["default_keys"]:
                    self._highlight_key(key_name, highlight_color)
            else:
                logger.info(f"No default keys found for {app_name}")
            
            # CRITICAL FIX: Create a list of RGB tuples for all keys
            color_list = []
            for key in self.app.keys:
                # Fix: Access the color attribute directly instead of calling keyColor()
                color = key.color
                color_list.append((color.red(), color.green(), color.blue()))
            
            # Send the color list directly to the keyboard controller
            if self.app.keyboard.connected:
                logger.info(f"Sending highlighted configuration to keyboard")
                # Use the direct send_led_config method instead of app.send_config()
                self.app.keyboard.send_led_config(color_list)
            else:
                logger.warning("Keyboard not connected, can't update LEDs")
        except Exception as e:
            logger.error(f"Error highlighting keys for {app_name}: {e}", exc_info=True)
            # Try to restore default state
            self.app.shortcut_lighting.restore_key_colors()
    
    def _highlight_key(self, key_name, color):
        """Highlight a specific key with the given color"""
        for key in self.app.keys:
            if key.key_name.lower() == key_name.lower():
                logger.debug(f"Highlighting key {key_name} with color {color.name()}")
                key.setKeyColor(color)
                break
    
    def show_app_shortcut_manager(self):
        """Show the application shortcut manager dialog"""
        dialog = AppShortcutManagerDialog(self.app, self)
        dialog.exec_()

    def handle_key_press(self, key_name):
        """Handle a key press event when app-specific shortcut monitoring is active"""
        if not self.monitoring or not self.current_app:
            logger.info(f"App shortcuts not monitoring or no current app")
            return False  # Return False to allow global handling
        
        if self.current_app not in self.app_shortcuts:
            logger.info(f"No shortcuts defined for current app: {self.current_app}")
            return False  # Return False to allow global handling
        
        try:
            # Get the list of currently pressed modifier keys from the global shortcut system
            pressed_modifiers = list(self.app.shortcut_lighting.currently_pressed_keys)
            logger.info(f"App shortcuts handling key press: {key_name}")
            logger.info(f"Currently pressed keys from global system: {pressed_modifiers}")
            
            # Filter to keep only actual modifiers (case-insensitive)
            real_modifiers = []
            for mod in pressed_modifiers:
                if mod.lower() in ["ctrl", "shift", "alt", "win", "fn"]:
                    # Use the canonical case for consistency
                    if mod.lower() == "ctrl": real_modifiers.append("Ctrl")
                    elif mod.lower() == "shift": real_modifiers.append("Shift")
                    elif mod.lower() == "alt": real_modifiers.append("Alt")
                    elif mod.lower() == "win": real_modifiers.append("Win")
                    elif mod.lower() == "fn": real_modifiers.append("Fn")
            
            # Sort modifiers for consistent lookup
            if real_modifiers:
                # Create lookup key based on sorted modifiers
                modifiers_key = "+".join(sorted(real_modifiers))
                logger.info(f"Looking for shortcuts with modifier key: {modifiers_key}")
                
                # Check if we have this modifier combination for the current app
                shortcuts = self.app_shortcuts[self.current_app]
                
                # Try exact match first
                if modifiers_key in shortcuts:
                    # We found an app-specific shortcut for this modifier combo!
                    logger.info(f"Found shortcuts for {modifiers_key} in {self.current_app}")
                    self._highlight_app_shortcut_keys(modifiers_key, shortcuts[modifiers_key])
                    return True  # Handled by app-specific shortcuts
                
                # Try case-insensitive match
                for shortcut_key in shortcuts:
                    if shortcut_key.lower() == modifiers_key.lower() and shortcut_key != "default_keys":
                        logger.info(f"Found shortcuts for {shortcut_key} in {self.current_app} (case-insensitive match)")
                        self._highlight_app_shortcut_keys(shortcut_key, shortcuts[shortcut_key])
                        return True
            
            # If we get here, no modifier-specific shortcuts were found
            # Check if we should apply default keys
            if "default_keys" in self.app_shortcuts[self.current_app]:
                # If modifiers are pressed but we don't have specific shortcuts for them,
                # still highlight the default keys
                logger.info(f"No specific shortcuts for modifiers, using default keys")
                self._highlight_app_shortcut_keys("default", self.app_shortcuts[self.current_app]["default_keys"])
                return True
            
            logger.debug(f"No modifier shortcuts found for {key_name} in {self.current_app}")
            return False  # Let global shortcuts handle it
        except Exception as e:
            logger.error(f"Error handling key press: {e}", exc_info=True)
            return False  # On error, fall back to global shortcuts

    def _highlight_app_shortcut_keys(self, modifier_key, keys_to_highlight):
        """Highlight specific keys for an application shortcut"""
        try:
            # Clear keyboard first
            self.app.clear_keyboard()
            
            # Get app-specific color
            highlight_color = self.app_colors.get(self.current_app, self.default_color)
            
            # Highlight modifier keys if this isn't the default keySet
            if modifier_key != "default":
                modifiers = modifier_key.split("+")
                for modifier in modifiers:
                    # Normalize modifier name
                    if modifier.lower() == "ctrl": mod_name = "Ctrl"
                    elif modifier.lower() == "shift": mod_name = "Shift"
                    elif modifier.lower() == "alt": mod_name = "Alt"
                    elif modifier.lower() == "win": mod_name = "Win"
                    elif modifier.lower() == "fn": mod_name = "Fn"
                    else: mod_name = modifier
                    
                    # Get the color for this modifier
                    mod_color = self.app.shortcut_lighting.get_modifier_color(mod_name)
                    logger.info(f"Highlighting modifier key {mod_name} with color {mod_color.name()}")
                    self._highlight_key(mod_name, mod_color)
            
            # Highlight the specified keys
            for key in keys_to_highlight:
                logger.info(f"Highlighting key {key} with color {highlight_color.name()}")
                self._highlight_key(key, highlight_color)
            
            # CRITICAL FIX: Create a list of RGB tuples for all keys
            color_list = []
            for key in self.app.keys:
                # Fix: Access the color attribute directly instead of calling keyColor()
                color = key.color
                color_list.append((color.red(), color.green(), color.blue()))
            
            # Send the color list directly to the keyboard controller
            if self.app.keyboard.connected:
                # Use the direct send_led_config method instead of app.send_config()
                self.app.keyboard.send_led_config(color_list)
                logger.info(f"Sent app-specific shortcut highlights to keyboard for modifier {modifier_key}")
            else:
                logger.warning("Keyboard not connected, can't update LEDs")
        except Exception as e:
            logger.error(f"Error highlighting app shortcut keys: {e}", exc_info=True)

    def highlight_default_keys(self):
        """Immediately highlight the default keys for the current application"""
        if not self.monitoring or not self.current_app:
            return
        
        if self.current_app not in self.app_shortcuts:
            return
        
        # Get the shortcuts for this app
        shortcuts = self.app_shortcuts[self.current_app]
        
        # Check if we have default keys
        if "default_keys" in shortcuts and shortcuts["default_keys"]:
            logger.info(f"Highlighting default keys for {self.current_app}")
            
            # Clear the keyboard first
            self.app.clear_keyboard()
            
            # Get app-specific color
            highlight_color = self.app_colors.get(self.current_app, self.default_color)
            
            # Highlight all default keys
            for key_name in shortcuts["default_keys"]:
                self._highlight_key(key_name, highlight_color)
            
            # Convert to color list and send directly to keyboard
            color_list = []
            for key in self.app.keys:
                # Fix: Access the color attribute directly instead of calling keyColor()
                color = key.color
                color_list.append((color.red(), color.green(), color.blue()))
            
            # Send the color list directly to the keyboard controller
            if self.app.keyboard.connected:
                self.app.keyboard.send_led_config(color_list)
                logger.info(f"Sent default key highlights to keyboard for {self.current_app}")

    def _track_key_press(self, key_name):
        """Track a key press in our own system"""
        self._currently_pressed_keys.add(key_name)
        logger.debug(f"App shortcuts tracking key press: {key_name}")

    def handle_key_release(self, key_name):
        """Handle a key release event"""
        try:
            # Check if any modifiers are still pressed in the global system
            pressed_modifiers = list(self.app.shortcut_lighting.currently_pressed_keys)
            real_modifiers = [mod for mod in pressed_modifiers if mod.lower() in ["ctrl", "shift", "alt", "win", "fn"]]
            
            # If no modifiers are pressed, restore default keys for current app
            if not real_modifiers and self.current_app and self.current_app in self.app_shortcuts:
                # Check if we have default keys
                if "default_keys" in self.app_shortcuts[self.current_app]:
                    logger.info(f"All modifier keys released, restoring default keys for {self.current_app}")
                    self._highlight_app_shortcut_keys("default", self.app_shortcuts[self.current_app]["default_keys"])
                    return True
                else:
                    # No default keys, restore to saved default state
                    self.restore_default_state()
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Error handling key release: {e}", exc_info=True)
            return False

    def save_default_state(self):
        """Save the current keyboard state as the default state"""
        self.default_state = []
        for key in self.app.keys:
            color = key.color
            self.default_state.append((color.red(), color.green(), color.blue()))
        logger.debug("Saved default keyboard state")

    def restore_default_state(self):
        """Restore the keyboard to the saved default state"""
        if not self.default_state:
            # If no default state is saved, use the app's restore method
            logger.debug("No default state saved, using global restore")
            self.app.shortcut_lighting.restore_key_colors()
            return
        
        # Apply the saved default state directly
        if self.app.keyboard.connected:
            self.app.keyboard.send_led_config(self.default_state)
            logger.debug("Restored keyboard to default state")

class AppShortcutManagerDialog(QDialog):
    def __init__(self, keyboard_app, feature):
        super().__init__(keyboard_app)
        self.app = keyboard_app
        self.feature = feature
        self.setWindowTitle("Application Shortcut Manager")
        self.setMinimumSize(800, 600)
        
        # Main layout
        layout = QVBoxLayout(self)
        
        # Split view with app list on left, details on right
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side - App list
        app_list_widget = QWidget()
        app_list_layout = QVBoxLayout(app_list_widget)
        
        app_list_layout.addWidget(QLabel("Applications:"))
        
        self.app_list = QListWidget()
        self.app_list.currentItemChanged.connect(self.app_selected)
        app_list_layout.addWidget(self.app_list)
        
        # Buttons for app management
        app_buttons_layout = QHBoxLayout()
        
        add_app_btn = QPushButton("New App")
        add_app_btn.clicked.connect(self.add_new_app)
        app_buttons_layout.addWidget(add_app_btn)
        
        remove_app_btn = QPushButton("Remove App")
        remove_app_btn.clicked.connect(self.remove_app)
        app_buttons_layout.addWidget(remove_app_btn)
        
        app_list_layout.addLayout(app_buttons_layout)
        
        # Right side - App details
        app_details_widget = QWidget()
        app_details_layout = QVBoxLayout(app_details_widget)
        
        # App name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Application Name:"))
        
        self.app_name_edit = QLineEdit()
        name_layout.addWidget(self.app_name_edit)
        
        app_details_layout.addLayout(name_layout)
        
        # App highlight color
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Highlight Color:"))
        
        self.app_color_display = ColorDisplay(self.feature.default_color)
        self.app_color_display.clicked.connect(self.choose_app_color)
        color_layout.addWidget(self.app_color_display)
        
        app_details_layout.addLayout(color_layout)
        
        # Default keys to highlight (when no modifiers are pressed)
        default_keys_layout = QVBoxLayout()
        default_keys_layout.addWidget(QLabel("Default Keys (highlighted when app is active):"))
        
        self.default_keys_edit = QLineEdit()
        self.default_keys_edit.setPlaceholderText("e.g., W,A,S,D (comma-separated)")
        default_keys_layout.addWidget(self.default_keys_edit)
        
        app_details_layout.addLayout(default_keys_layout)
        
        # Modifier shortcut sections
        app_details_layout.addWidget(QLabel("Modifier Shortcuts:"))
        
        # Create tables for common modifier combinations
        self.modifier_tables = {}
        
        # Ctrl keys
        ctrl_group = QGroupBox("Ctrl Keys")
        ctrl_layout = QVBoxLayout(ctrl_group)
        self.ctrl_keys_edit = QLineEdit()
        self.ctrl_keys_edit.setPlaceholderText("e.g., C,V,X,Z (comma-separated)")
        ctrl_layout.addWidget(self.ctrl_keys_edit)
        app_details_layout.addWidget(ctrl_group)
        
        # Shift keys
        shift_group = QGroupBox("Shift Keys")
        shift_layout = QVBoxLayout(shift_group)
        self.shift_keys_edit = QLineEdit()
        self.shift_keys_edit.setPlaceholderText("e.g., Tab,1,2,3 (comma-separated)")
        shift_layout.addWidget(self.shift_keys_edit)
        app_details_layout.addWidget(shift_group)
        
        # Alt keys
        alt_group = QGroupBox("Alt Keys")
        alt_layout = QVBoxLayout(alt_group)
        self.alt_keys_edit = QLineEdit()
        self.alt_keys_edit.setPlaceholderText("e.g., Tab,F4 (comma-separated)")
        alt_layout.addWidget(self.alt_keys_edit)
        app_details_layout.addWidget(alt_group)
        
        # Ctrl+Shift keys
        ctrl_shift_group = QGroupBox("Ctrl+Shift Keys")
        ctrl_shift_layout = QVBoxLayout(ctrl_shift_group)
        self.ctrl_shift_keys_edit = QLineEdit()
        self.ctrl_shift_keys_edit.setPlaceholderText("e.g., N,T (comma-separated)")
        ctrl_shift_layout.addWidget(self.ctrl_shift_keys_edit)
        app_details_layout.addWidget(ctrl_shift_group)
        
        # Ctrl+Alt keys
        ctrl_alt_group = QGroupBox("Ctrl+Alt Keys")
        ctrl_alt_layout = QVBoxLayout(ctrl_alt_group)
        self.ctrl_alt_keys_edit = QLineEdit()
        self.ctrl_alt_keys_edit.setPlaceholderText("e.g., T,D (comma-separated)")
        ctrl_alt_layout.addWidget(self.ctrl_alt_keys_edit)
        app_details_layout.addWidget(ctrl_alt_group)
        
        # Save button
        save_btn = QPushButton("Save Application")
        save_btn.clicked.connect(self.save_current_app)
        app_details_layout.addWidget(save_btn)
        
        # Add widgets to splitter
        splitter.addWidget(app_list_widget)
        splitter.addWidget(app_details_widget)
        
        # Set splitter sizes (40% left, 60% right)
        splitter.setSizes([300, 500])
        
        # Add splitter to main layout
        layout.addWidget(splitter)
        
        # Load the list of applications
        self.load_app_list()
    
    def load_app_list(self):
        """Load the list of applications with shortcuts"""
        self.app_list.clear()
        
        # Add each app to the list
        for app_name in sorted(self.feature.app_shortcuts.keys()):
            self.app_list.addItem(app_name)
    
    def app_selected(self, current, previous):
        """Handle application selection"""
        if not current:
            return
            
        app_name = current.text()
        self.app_name_edit.setText(app_name)
        
        # Clear all shortcut fields
        self.default_keys_edit.clear()
        self.ctrl_keys_edit.clear()
        self.shift_keys_edit.clear()
        self.alt_keys_edit.clear()
        self.ctrl_shift_keys_edit.clear()
        self.ctrl_alt_keys_edit.clear()
        
        # Set color if available
        if app_name in self.feature.app_colors:
            self.app_color_display.setColor(self.feature.app_colors[app_name])
        else:
            self.app_color_display.setColor(self.feature.default_color)
        
        # Load app shortcuts
        self.load_app_shortcuts(app_name)
    
    def load_app_shortcuts(self, app_name):
        """Load shortcuts for the selected application"""
        if app_name not in self.feature.app_shortcuts:
            return
        
        shortcuts = self.feature.app_shortcuts[app_name]
        
        # Load default keys
        if "default_keys" in shortcuts:
            self.default_keys_edit.setText(",".join(shortcuts["default_keys"]))
        
        # Load modifier keys
        if "Ctrl" in shortcuts:
            self.ctrl_keys_edit.setText(",".join(shortcuts["Ctrl"]))
            
        if "Shift" in shortcuts:
            self.shift_keys_edit.setText(",".join(shortcuts["Shift"]))
            
        if "Alt" in shortcuts:
            self.alt_keys_edit.setText(",".join(shortcuts["Alt"]))
            
        if "Ctrl+Shift" in shortcuts:
            self.ctrl_shift_keys_edit.setText(",".join(shortcuts["Ctrl+Shift"]))
            
        if "Ctrl+Alt" in shortcuts:
            self.ctrl_alt_keys_edit.setText(",".join(shortcuts["Ctrl+Alt"]))
    
    def save_current_app(self):
        """Save the current application configuration"""
        app_name = self.app_name_edit.text().strip()
        if not app_name:
            QMessageBox.warning(self, "Empty Name", "Please enter an application name")
            return
        
        # Collect all shortcuts
        shortcuts = {}
        
        # Get default keys
        default_keys_text = self.default_keys_edit.text().strip()
        if default_keys_text:
            shortcuts["default_keys"] = [k.strip() for k in default_keys_text.split(",")]
        
        # Get modifier key combinations
        ctrl_keys_text = self.ctrl_keys_edit.text().strip()
        if ctrl_keys_text:
            shortcuts["Ctrl"] = [k.strip() for k in ctrl_keys_text.split(",")]
            
        shift_keys_text = self.shift_keys_edit.text().strip()
        if shift_keys_text:
            shortcuts["Shift"] = [k.strip() for k in shift_keys_text.split(",")]
            
        alt_keys_text = self.alt_keys_edit.text().strip()
        if alt_keys_text:
            shortcuts["Alt"] = [k.strip() for k in alt_keys_text.split(",")]
            
        ctrl_shift_keys_text = self.ctrl_shift_keys_edit.text().strip()
        if ctrl_shift_keys_text:
            shortcuts["Ctrl+Shift"] = [k.strip() for k in ctrl_shift_keys_text.split(",")]
            
        ctrl_alt_keys_text = self.ctrl_alt_keys_edit.text().strip()
        if ctrl_alt_keys_text:
            shortcuts["Ctrl+Alt"] = [k.strip() for k in ctrl_alt_keys_text.split(",")]
        
        # Save shortcuts
        self.feature.save_app_shortcuts(app_name, shortcuts)
        
        # Save color
        self.feature.app_colors[app_name] = self.app_color_display.color
        self.feature.save_app_colors()
        
        # Refresh list
        self.load_app_list()
        
        # Select the saved app
        for i in range(self.app_list.count()):
            if self.app_list.item(i).text() == app_name:
                self.app_list.setCurrentRow(i)
                break
        
        QMessageBox.information(self, "Saved", f"Shortcuts for '{app_name}' have been saved")
    
    def choose_app_color(self):
        """Choose a highlight color for the application"""
        color = QColorDialog.getColor(self.app_color_display.color, self, "Select Highlight Color")
        if color.isValid():
            self.app_color_display.setColor(color)

    def add_new_app(self):
        """Add a new application"""
        self.app_name_edit.clear()
        self.app_color_display.setColor(self.feature.default_color)
        self.default_keys_edit.clear()
        self.ctrl_keys_edit.clear()
        self.shift_keys_edit.clear()
        self.alt_keys_edit.clear()
        self.ctrl_shift_keys_edit.clear()
        self.ctrl_alt_keys_edit.clear()
    
    def remove_app(self):
        """Remove the selected application"""
        current_item = self.app_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select an application to remove")
            return
            
        app_name = current_item.text()
        
        # Confirm deletion
        confirm = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete the shortcuts for '{app_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            # Remove from memory
            if app_name in self.feature.app_shortcuts:
                del self.feature.app_shortcuts[app_name]
            
            if app_name in self.feature.app_colors:
                del self.feature.app_colors[app_name]
                
            # Remove file from disk
            try:
                file_path = os.path.join(self.feature.app_shortcuts_dir, f"{app_name}.json")
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.error(f"Error removing app shortcut file: {e}")
            
            # Save colors
            self.feature.save_app_colors()
            
            # Refresh list
            self.load_app_list()


class ShortcutEditorDialog(QDialog):
    def __init__(self, parent, shortcut="", description=""):
        super().__init__(parent)
        self.setWindowTitle("Edit Shortcut")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Shortcut input
        shortcut_layout = QHBoxLayout()
        shortcut_layout.addWidget(QLabel("Shortcut:"))
        
        self.shortcut_edit = QLineEdit(shortcut)
        shortcut_layout.addWidget(self.shortcut_edit)
        
        layout.addLayout(shortcut_layout)
        
        # Description input
        description_layout = QHBoxLayout()
        description_layout.addWidget(QLabel("Description:"))
        
        self.description_edit = QLineEdit(description)
        description_layout.addWidget(self.description_edit)
        
        layout.addLayout(description_layout)
        
        # Help text
        layout.addWidget(QLabel("Format examples: Ctrl+C, Alt+Tab, Ctrl+Shift+N"))
        
        # Buttons
        button_layout = QHBoxLayout()
        
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.accept)
        button_layout.addWidget(save_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout) 