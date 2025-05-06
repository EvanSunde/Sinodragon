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

class AppShortcutConfigManager:
    """Manages configuration for application-specific shortcuts"""
    
    def __init__(self, config_dir):
        """Initialize the configuration manager"""
        self.config_dir = config_dir
        self.app_shortcuts_dir = os.path.join(self.config_dir, "app_shortcuts")
        
        # Ensure app shortcuts directory exists
        os.makedirs(self.app_shortcuts_dir, exist_ok=True)
        
        # Default configuration
        self.app_shortcuts = {}
        self.app_colors = {}
        self.default_color = QColor(255, 165, 0)  # Orange by default
        
        # Load existing configuration
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

class AppShortcutFeature:
    def __init__(self, config_manager, keyboard, shortcut_lighting):
        """Initialize with configuration and keyboard"""
        super().__init__()
        self.config_manager = config_manager
        self.keyboard = keyboard
        self.shortcut_lighting = shortcut_lighting
        self.monitoring = False
        self.monitor_thread = None
        self.current_app = "Unknown"
        
        # For tracking keys and default state
        self.default_state = []  # Will store RGB tuples for each key
        self.disable_global_shortcuts = False
        self._currently_pressed_keys = set()
        
        # Performance optimization
        self._app_cache = {}  # Cache app-specific shortcut data for faster access
        self._last_window_check = 0
        self._window_check_interval = 0.5  # Check every 0.5 seconds at most
        
        # Hyprland-specific components
        self.is_hyprland = os.environ.get('HYPRLAND_INSTANCE_SIGNATURE') is not None
        self.hyprland_ipc = None
        
        # Signal connections - ensure we're handling possible compatibility issues
        try:
            # Connect to signals if they exist
            if hasattr(self.shortcut_lighting, 'key_pressed'):
                self.shortcut_lighting.key_pressed.connect(self.on_key_press)
                logger.info("Connected to key_pressed signal")
            
            if hasattr(self.shortcut_lighting, 'key_released'):
                self.shortcut_lighting.key_released.connect(self.on_key_release)
                logger.info("Connected to key_released signal")
        except Exception as e:
            logger.error(f"Error connecting to shortcut lighting signals: {e}")
            # We'll fall back to direct method calls if signals aren't available
            logger.info("Will use direct method calls for key event handling")
        
        logger.info("App shortcut feature initialized")
        
        # Initialize cache for better performance
        self._initialize_cache()
        
    @property
    def default_color(self):
        """Get the default highlight color from the config manager"""
        return self.config_manager.default_color
    
    @property
    def app_colors(self):
        """Get the app colors dictionary from the config manager"""
        return self.config_manager.app_colors
        
    @property
    def app_shortcuts(self):
        """Get the app shortcuts dictionary from the config manager"""
        return self.config_manager.app_shortcuts
    
    @property
    def app_shortcuts_dir(self):
        """Get the app shortcuts directory from the config manager"""
        return self.config_manager.app_shortcuts_dir
    
    def _initialize_cache(self):
        """Initialize caches for better performance"""
        # Cache frequently accessed keys to reduce lookups
        self._app_cache = {}
        
        # Pre-cache existing app configurations
        for app_name, shortcuts in self.config_manager.app_shortcuts.items():
            self._app_cache[app_name] = {
                'shortcuts': shortcuts,
                'color': self.config_manager.app_colors.get(app_name, self.config_manager.default_color),
                'has_default_keys': 'default_keys' in shortcuts and shortcuts['default_keys']
            }
        
        logger.info(f"Initialized cache for {len(self._app_cache)} applications")
    
    def _update_app_cache(self, app_name):
        """Update the cache for a specific app"""
        if app_name not in self.config_manager.app_shortcuts:
            if app_name in self._app_cache:
                del self._app_cache[app_name]
            return
            
        shortcuts = self.config_manager.app_shortcuts[app_name]
        self._app_cache[app_name] = {
            'shortcuts': shortcuts,
            'color': self.config_manager.app_colors.get(app_name, self.config_manager.default_color),
            'has_default_keys': 'default_keys' in shortcuts and shortcuts['default_keys']
        }
    
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
        
        # Enable app-specific shortcuts
        self.disable_global_shortcuts = True
        
        logger.info("Application shortcut monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring for application changes"""
        self.monitoring = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)
            
        # Re-enable global shortcuts
        self.disable_global_shortcuts = False
        
        logger.info("Application shortcut monitoring stopped")
        
        # Restore default keyboard appearance
        self.shortcut_lighting.restore_key_colors()
    
    def _monitoring_loop(self):
        """Background thread to monitor active application and update shortcuts"""
        last_check_time = 0
        
        while self.monitoring:
            try:
                # Only check for app changes periodically to reduce CPU usage
                current_time = time.time()
                if current_time - last_check_time < self._window_check_interval:
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
            # Update app cache if needed
            if app_name not in self._app_cache:
                if app_name in self.config_manager.app_shortcuts:
                    self._update_app_cache(app_name)
                else:
                    # Just display the application name on the keyboard for visual feedback
                    logger.info(f"No shortcuts defined for {app_name}, using default behavior")
                    
                    # Restore to default configuration and save this as our default state
                    self.shortcut_lighting.restore_key_colors()
                    self.save_default_state()
                    return
            
            # Get from cache for better performance
            cache_entry = self._app_cache[app_name]
            shortcuts = cache_entry['shortcuts']
            has_default_keys = cache_entry['has_default_keys']
            
            # Check if this app has any useful settings
            if not has_default_keys and not any(k for k in shortcuts.keys() if k != "default_keys"):
                # App exists but has no useful shortcuts defined - use global defaults
                logger.info(f"App {app_name} has no useful shortcuts, using global defaults")
                self.shortcut_lighting.restore_key_colors()
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
            except Exception as inner_e:
                logger.error(f"Error restoring default state: {inner_e}")
                # Last resort fallback
                self.shortcut_lighting.restore_key_colors()
    
    def _safely_display_app_name(self, app_name):
        """Safely display app name with proper error handling"""
        try:
            # Only run if monitoring is still active
            if not self.monitoring:
                return
            
            # Clear keyboard with error handling
            try:
                self.keyboard.clear_keyboard()
            except Exception as e:
                logger.error(f"Error clearing keyboard: {e}")
                return
            
            # Display app name for a brief moment
            try:
                short_name = app_name[:8] if app_name else "Unknown"
                self.keyboard.text_display.display_text(short_name, clear_first=True)
                
                # After a brief delay, restore to default config
                QTimer.singleShot(1000, self.shortcut_lighting.restore_key_colors)
            except Exception as e:
                logger.error(f"Error displaying app name: {e}")
                # Try to restore default state
                QTimer.singleShot(0, self.shortcut_lighting.restore_key_colors)
        except Exception as e:
            logger.error(f"Unexpected error in _safely_display_app_name: {e}")
    
    def _apply_app_specific_shortcuts(self, app_name):
        """Apply shortcuts specific to an application with proper error handling"""
        try:
            # Clear keyboard first
            self.keyboard.clear_keyboard()
            
            # Get app-specific color or use default
            highlight_color = self._app_cache[app_name]['color']
            
            # Get the shortcuts for this app
            shortcuts = self._app_cache[app_name]['shortcuts']
            
            # Check if we should apply default keys highlighting
            if "default_keys" in shortcuts and shortcuts["default_keys"]:
                logger.info(f"Highlighting default keys for {app_name}: {shortcuts['default_keys']}")
                for key_name in shortcuts["default_keys"]:
                    self._highlight_key(key_name, highlight_color)
            else:
                logger.info(f"No default keys found for {app_name}")
            
            # CRITICAL FIX: Create a list of RGB tuples for all keys
            color_list = []
            for key in self.keyboard.keys:
                # Fix: Access the color attribute directly instead of calling keyColor()
                color = key.color
                color_list.append((color.red(), color.green(), color.blue()))
            
            # Send the color list directly to the keyboard controller
            if self.keyboard.keyboard.connected:
                logger.info(f"Sending highlighted configuration to keyboard")
                # Use the direct send_led_config method instead of app.send_config()
                self.keyboard.keyboard.send_led_config(color_list)
            else:
                logger.warning("Keyboard not connected, can't update LEDs")
        except Exception as e:
            logger.error(f"Error highlighting keys for {app_name}: {e}", exc_info=True)
            # Try to restore default state
            self.shortcut_lighting.restore_key_colors()
    
    def _highlight_key(self, key_name, color):
        """
        Highlight a specific key with the given color
        
        Args:
            key_name: Name of the key to highlight
            color: QColor to use for highlighting
            
        Returns:
            bool: True if key was found and highlighted, False otherwise
        """
        if not key_name or not isinstance(key_name, str):
            logger.warning(f"Invalid key name: {key_name}")
            return False
            
        # Normalize key name for comparison
        normalized_key = key_name.strip().lower()
        if not normalized_key:
            return False
            
        # Search for matching key
        for key in self.keyboard.keys:
            if key.key_name.lower() == normalized_key:
                logger.debug(f"Highlighting key {key_name} with color {color.name()}")
                key.setKeyColor(color)
                return True
                
        logger.debug(f"Key not found: {key_name}")
        return False
    
    def show_app_shortcut_manager(self):
        """Show the application shortcut manager dialog"""
        dialog = AppShortcutManagerDialog(self.keyboard, self)
        dialog.exec_()

    def handle_key_press(self, key_name):
        """Handle a key press event when app-specific shortcut monitoring is active"""
        if not self.monitoring or not self.current_app:
            logger.info(f"App shortcuts not monitoring or no current app")
            return False  # Return False to allow global handling
        
        if self.current_app not in self._app_cache:
            logger.info(f"No shortcuts defined for current app: {self.current_app}")
            return False  # Return False to allow global handling
        
        try:
            # Add this key to our own tracking
            self._currently_pressed_keys.add(key_name)
            
            # Get the list of currently pressed modifier keys from the global shortcut system
            pressed_modifiers = list(self.shortcut_lighting.currently_pressed_keys)
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
                shortcuts = self._app_cache[self.current_app]['shortcuts']
                
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
            if "default_keys" in self._app_cache[self.current_app]['shortcuts']:
                # Save the keyboard state first if needed - only on the first modifier press
                if not self.default_state:
                    self.save_default_state()
                    
                # If modifiers are pressed but we don't have specific shortcuts for them,
                # still highlight the default keys
                logger.info(f"No specific shortcuts for modifiers, using default keys")
                self._highlight_app_shortcut_keys("default", self._app_cache[self.current_app]['shortcuts']["default_keys"])
                return True
            
            logger.debug(f"No shortcuts found for {key_name} in {self.current_app}")
            return False  # Let global shortcuts handle it
        except Exception as e:
            logger.error(f"Error handling key press: {e}", exc_info=True)
            return False  # On error, fall back to global shortcuts

    def _highlight_app_shortcut_keys(self, modifier_key, keys_to_highlight):
        """Highlight specific keys for an application shortcut"""
        try:
            # Validate input
            if not keys_to_highlight or not isinstance(keys_to_highlight, list):
                logger.warning(f"Empty or invalid keys_to_highlight: {keys_to_highlight}")
                # Fall back to global defaults if keys list is empty or invalid
                self.shortcut_lighting.restore_key_colors()
                return
                
            # Clear keyboard first
            self.keyboard.clear_keyboard()
            
            # Get app-specific color
            highlight_color = self._app_cache[self.current_app]['color']
            
            # Convert any string keys to string and strip whitespace
            keys_to_highlight = [str(k).strip() for k in keys_to_highlight if k]
            
            # If we still have no valid keys, fall back to global defaults
            if not keys_to_highlight:
                logger.warning(f"No valid keys to highlight for {modifier_key} in {self.current_app}")
                self.shortcut_lighting.restore_key_colors()
                return
                
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
                    mod_color = self.shortcut_lighting.get_modifier_color(mod_name)
                    logger.info(f"Highlighting modifier key {mod_name} with color {mod_color.name()}")
                    self._highlight_key(mod_name, mod_color)
            
            # Highlight the specified keys
            keys_highlighted = 0
            for key in keys_to_highlight:
                if key and isinstance(key, str):
                    logger.info(f"Highlighting key {key} with color {highlight_color.name()}")
                    if self._highlight_key(key, highlight_color):
                        keys_highlighted += 1
            
            logger.info(f"Successfully highlighted {keys_highlighted} out of {len(keys_to_highlight)} keys")
            
            # CRITICAL FIX: Create a list of RGB tuples for all keys
            color_list = []
            for key in self.keyboard.keys:
                # Fix: Access the color attribute directly instead of calling keyColor()
                color = key.color
                color_list.append((color.red(), color.green(), color.blue()))
            
            # Send the color list directly to the keyboard controller
            if self.keyboard.keyboard.connected:
                # Use the direct send_led_config method instead of app.send_config()
                self.keyboard.keyboard.send_led_config(color_list)
                logger.info(f"Sent app-specific shortcut highlights to keyboard for modifier {modifier_key}")
            else:
                logger.warning("Keyboard not connected, can't update LEDs")
                
        except Exception as e:
            logger.error(f"Error highlighting app shortcut keys: {e}", exc_info=True)
            # Fall back to global defaults in case of error
            self.shortcut_lighting.restore_key_colors()

    def highlight_default_keys(self):
        """Highlight default keys for current app"""
        try:
            if not self.monitoring or not self.current_app:
                logger.info("Not monitoring or no current app, skipping default key highlighting")
                return False
                
            if self.current_app not in self._app_cache:
                logger.info(f"No shortcuts defined for {self.current_app}, loading global default config")
                # Fall back to global default configuration
                self.shortcut_lighting.restore_key_colors()
                return False
            
            # Save current keyboard state as default first if not saved already
            if not self.default_state:
                logger.info("Saving current keyboard state as default")
                self.save_default_state()
                
            # Check if app has valid default keys
            shortcuts = self._app_cache[self.current_app]['shortcuts']
            has_default_keys = self._app_cache[self.current_app]['has_default_keys']
            
            if has_default_keys:
                # Apply app-specific default keys
                logger.info(f"Highlighting default keys for {self.current_app}")
                self._highlight_app_shortcut_keys("default", shortcuts["default_keys"])
                return True
            else:
                # No default keys defined for this app - fall back to global default
                logger.info(f"No default keys for {self.current_app}, loading global default config")
                self.shortcut_lighting.restore_key_colors()
                return False
                
        except Exception as e:
            logger.error(f"Error highlighting default keys: {e}", exc_info=True)
            # Always fall back to global defaults in case of error
            self.shortcut_lighting.restore_key_colors()
            return False

    def _track_key_press(self, key_name):
        """Track a key press in our own system"""
        self._currently_pressed_keys.add(key_name)
        logger.debug(f"App shortcuts tracking key press: {key_name}")

    def handle_key_release(self, key_name):
        """Handle a key release event"""
        try:
            # Remove key from our own tracking
            if key_name in self._currently_pressed_keys:
                self._currently_pressed_keys.remove(key_name)
                
            # Check if any modifiers are still pressed in the global system
            pressed_modifiers = list(self.shortcut_lighting.currently_pressed_keys)
            real_modifiers = [mod for mod in pressed_modifiers if mod.lower() in ["ctrl", "shift", "alt", "win", "fn"]]
            
            # Only restore defaults if no modifiers are pressed
            if not real_modifiers:
                if self.current_app and self.current_app in self._app_cache:
                    shortcuts = self._app_cache[self.current_app]['shortcuts']
                    has_default_keys = self._app_cache[self.current_app]['has_default_keys']
                    
                    if has_default_keys:
                        # App has default keys - restore them
                        logger.info(f"All modifier keys released, restoring default keys for {self.current_app}")
                        self._highlight_app_shortcut_keys("default", shortcuts["default_keys"])
                        return True
                    else:
                        # No default keys for this app - restore to global default or saved state
                        logger.info(f"All modifier keys released, no default keys for {self.current_app}")
                        if self.default_state and len(self.default_state) > 0:
                            # Restore to saved default state if available
                            logger.info("Restoring to saved default state")
                            self.restore_default_state()
                        else:
                            # Fall back to global default
                            logger.info("Restoring to global default config")
                            self.shortcut_lighting.restore_key_colors()
                        return True
                else:
                    # No app-specific shortcuts - restore global defaults
                    logger.info("All modifier keys released, restoring to global default")
                    self.shortcut_lighting.restore_key_colors()
                    return True
            
            # If modifiers are still pressed, let the system handle it
            return False
            
        except Exception as e:
            logger.error(f"Error handling key release: {e}", exc_info=True)
            # In case of error, restore to global defaults
            self.shortcut_lighting.restore_key_colors()
            return False

    def save_default_state(self):
        """Save the current keyboard state as the default state"""
        self.default_state = []
        for key in self.keyboard.keys:
            color = key.color
            self.default_state.append((color.red(), color.green(), color.blue()))
        logger.debug("Saved default keyboard state")

    def restore_default_state(self):
        """Restore the keyboard to the saved default state"""
        try:
            if not self.default_state or len(self.default_state) == 0:
                # If no default state is saved, use the app's restore method
                logger.debug("No default state saved, using global restore")
                self.shortcut_lighting.restore_key_colors()
                return
            
            # Clear the keyboard first to avoid visual artifacts
            self.keyboard.clear_keyboard()
            
            # Apply the saved default state directly
            logger.debug("Applying saved default state to keys")
            
            # Apply default state to the keys in the UI
            for i, key in enumerate(self.keyboard.keys):
                if i < len(self.default_state):
                    r, g, b = self.default_state[i]
                    key.setKeyColor(QColor(r, g, b))
            
            # Send to keyboard
            if self.keyboard.keyboard.connected:
                self.keyboard.keyboard.send_led_config(self.default_state)
                logger.debug("Restored keyboard to default state")
        except Exception as e:
            logger.error(f"Error restoring default state: {e}", exc_info=True)
            # Fall back to global restore
            self.shortcut_lighting.restore_key_colors()

    def should_disable_global_shortcuts(self, key_name=None):
        """
        Check if global shortcuts should be disabled for the current app
        
        Args:
            key_name: Optional key name to check (for meta/super key exception)
            
        Returns:
            True if global shortcuts should be disabled, False otherwise
        """
        # Always allow meta/super key shortcuts
        if key_name and key_name.lower() in ["win", "meta", "super"]:
            return False
        
        # If we're not monitoring or don't have a current app, don't disable global shortcuts
        if not self.monitoring or not self.current_app:
            return False
        
        # If we don't have shortcuts for this app, don't disable global shortcuts
        if self.current_app not in self._app_cache:
            return False
        
        # If we have app-specific shortcuts, disable global shortcuts
        return self.disable_global_shortcuts

    def on_key_press(self, key_name):
        """Handle key press signal from shortcut lighting system"""
        return self.handle_key_press(key_name)
    
    def on_key_release(self, key_name):
        """Handle key release signal from shortcut lighting system"""
        return self.handle_key_release(key_name)

    def save_app_shortcuts(self, app_name, shortcut_data):
        """
        Save shortcuts for a specific application by delegating to config manager
        
        Args:
            app_name: Name of the application
            shortcut_data: Dictionary with modifiers as keys and lists of keys as values
        """
        result = self.config_manager.save_app_shortcuts(app_name, shortcut_data)
        
        # Update the cache
        if result and app_name in self.config_manager.app_shortcuts:
            self._update_app_cache(app_name)
            
        return result
    
    def save_app_colors(self):
        """Save application highlight colors by delegating to config manager"""
        return self.config_manager.save_app_colors()

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
                logger.info(f"Removed app shortcut file for {app_name}")
            except Exception as e:
                logger.error(f"Error removing app shortcut file: {e}")
            
            # Save colors
            self.feature.save_app_colors()
            
            # Refresh list
            self.load_app_list()
            
            QMessageBox.information(self, "Removed", f"Shortcuts for '{app_name}' have been removed")


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

class HyprlandIPC:
    def __init__(self, callback):
        """
        Initialize Hyprland IPC client
        
        Args:
            callback: Function to call when active window changes
        """
        self.callback = callback
        self.socket_path = None
        self.socket = None
        self.running = False
        self.thread = None
        self.last_window = "Unknown"
        
        # Memory optimization - use system buffer size
        self.buffer_size = 4096
        
        # Get socket path from environment
        instance_signature = os.environ.get('HYPRLAND_INSTANCE_SIGNATURE')
        if instance_signature:
            self.socket_path = f"/tmp/hypr/{instance_signature}/.socket2.sock"
        
    def start(self):
        """Start monitoring Hyprland events"""
        if not self.socket_path:
            logger.error("Hyprland socket path not available")
            return False
            
        self.running = True
        self.thread = threading.Thread(target=self._event_loop, daemon=True)
        self.thread.start()
        return True
    
    def stop(self):
        """Stop monitoring Hyprland events"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
    
    def _event_loop(self):
        """Event loop listening for Hyprland window change events"""
        import socket
        reconnect_delay = 1.0  # Initial reconnect delay
        
        while self.running:
            try:
                # Create and connect socket
                self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.socket.connect(self.socket_path)
                self.socket.settimeout(1.0)  # Add timeout to prevent blocking
                
                logger.info("Connected to Hyprland socket")
                reconnect_delay = 1.0  # Reset delay after successful connection
                
                # Process events
                buffer = ""
                while self.running:
                    try:
                        data = self.socket.recv(self.buffer_size).decode('utf-8')
                        if not data:
                            break
                            
                        buffer += data
                        
                        # Process complete lines
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            
                            # Only process active window events
                            if line.startswith("activewindow>>"):
                                self._handle_window_event(line)
                    except socket.timeout:
                        # Just a timeout, continue to allow checking if we're still supposed to run
                        continue
                    except (socket.error, ConnectionRefusedError) as e:
                        logger.error(f"Socket error during receive: {e}")
                        break
                
                # If we reach here, the socket was closed
                logger.warning("Hyprland socket closed, reconnecting...")
                time.sleep(reconnect_delay)
                
            except (socket.error, ConnectionRefusedError) as e:
                logger.error(f"Socket error: {e}, retrying in {reconnect_delay} seconds")
                time.sleep(reconnect_delay)
                # Exponential backoff with a maximum delay of 30 seconds
                reconnect_delay = min(30.0, reconnect_delay * 1.5)
                
            finally:
                # Ensure socket is closed before reconnect attempt
                if self.socket:
                    try:
                        self.socket.close()
                    except:
                        pass
                    self.socket = None
    
    def _handle_window_event(self, event_line):
        """Process window change events"""
        try:
            # Parse the active window info
            parts = event_line.split('>>', 1)[1].strip()
            
            # Skip empty events
            if not parts or parts == ",":
                return
                
            # Extract class name
            app_class = parts.split(',')[0]
            
            # Skip if same as last window to avoid redundant processing
            if app_class == self.last_window:
                return
                
            self.last_window = app_class
            
            # Only call back if we have a valid class
            if app_class and app_class != "":
                self.callback(app_class)
                
        except Exception as e:
            logger.error(f"Error handling window event: {e}")
    
    def get_active_window(self):
        """Get current active window using hyprctl command"""
        try:
            import json
            import subprocess
            
            # Try JSON output first (more reliable parsing)
            try:
                # Use -j for JSON output
                output = subprocess.check_output(["hyprctl", "-j", "activewindow"], text=True)
                data = json.loads(output)
                
                if "class" in data:
                    return data["class"]
            except (json.JSONDecodeError, subprocess.CalledProcessError):
                # Fallback to grep if JSON fails
                cmd = "hyprctl activewindow | grep class | awk '{print $2}'"
                try:
                    result = subprocess.check_output(cmd, shell=True, text=True).strip()
                    return result
                except subprocess.CalledProcessError:
                    pass
        except Exception as e:
            logger.error(f"Error getting active window: {e}")
            
        return "Unknown" 