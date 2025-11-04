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
                            QSplitter, QWidget, QGroupBox, QTabWidget, QInputDialog,
                            QAbstractItemView)
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
        """
        Highlight specific keys for an application shortcut
        
        Args:
            modifier_key: String representing the modifier keys (e.g., "Ctrl", "Shift", "Ctrl+Alt")
            keys_to_highlight: List of key names to highlight
        """
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
            
            # Check if there are disabled keys for this app
            shortcuts = self._app_cache[self.current_app]['shortcuts']
            disabled_keys = []
            if "disabled_keys" in shortcuts and shortcuts["disabled_keys"]:
                disabled_keys = [k.lower() for k in shortcuts["disabled_keys"]]
                logger.info(f"Found disabled keys for {self.current_app}: {disabled_keys}")
            
            # Filter out disabled keys
            if disabled_keys:
                original_count = len(keys_to_highlight)
                keys_to_highlight = [k for k in keys_to_highlight if k.lower() not in disabled_keys]
                if len(keys_to_highlight) < original_count:
                    logger.info(f"Filtered out {original_count - len(keys_to_highlight)} disabled keys")
            
            # If we still have no valid keys, fall back to global defaults
            if not keys_to_highlight:
                logger.warning(f"No valid keys to highlight for {modifier_key} in {self.current_app}")
                self.shortcut_lighting.restore_key_colors()
                return
            
            # Track how many keys we're highlighting
            keys_highlighted = 0
            
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
                    
                    # Skip disabled modifier keys
                    if mod_name.lower() in disabled_keys:
                        logger.info(f"Skipping disabled modifier key: {mod_name}")
                        continue
                    
                    # Get the color for this modifier
                    mod_color = self.shortcut_lighting.get_modifier_color(mod_name)
                    logger.info(f"Highlighting modifier key {mod_name} with color {mod_color.name()}")
                    if self._highlight_key(mod_name, mod_color):
                        keys_highlighted += 1
            
            # Highlight the specified keys
            for key in keys_to_highlight:
                if key and isinstance(key, str):
                    logger.info(f"Highlighting key {key} with color {highlight_color.name()}")
                    if self._highlight_key(key, highlight_color):
                        keys_highlighted += 1
            
            logger.info(f"Successfully highlighted {keys_highlighted} out of {len(keys_to_highlight)} keys")
            
            # IMPORTANT: Use a safe approach to send LEDs
            # Create a list of RGB tuples for all keys
            color_list = []
            for key in self.keyboard.keys:
                # Fix: Access the color attribute directly instead of calling keyColor()
                color = key.color
                color_list.append((color.red(), color.green(), color.blue()))
            
            # Ensure each color value is a valid integer in range 0-255
            safe_colors = []
            for r, g, b in color_list:
                safe_colors.append((
                    max(0, min(255, int(r))),
                    max(0, min(255, int(g))),
                    max(0, min(255, int(b)))
                ))
            
            # Send the color list directly to the keyboard controller with proper exception handling
            if self.keyboard.keyboard.connected:
                try:
                    # Use the direct send_led_config method instead of app.send_config()
                    logger.info(f"Sending app-specific shortcut highlights to keyboard for modifier {modifier_key}")
                    self.keyboard.keyboard.send_led_config(safe_colors)
                except Exception as e:
                    logger.error(f"Error sending LED config: {e}")
                    # Don't attempt to restore immediately - just log the error
            else:
                logger.warning("Keyboard not connected, can't update LEDs")
                
        except Exception as e:
            logger.error(f"Error highlighting app shortcut keys: {e}", exc_info=True)
            # Fall back to global defaults in case of error, with a slight delay
            # to avoid potential packet conflicts
            QTimer.singleShot(100, self.shortcut_lighting.restore_key_colors)

    def highlight_default_keys(self):
        """Highlight default keys for current app"""
        try:
            # Check if we're monitoring and have a current app
            if not self.monitoring or not self.current_app:
                logger.info("Not monitoring or no current app, skipping default key highlighting")
                return False
                
            # Check if we have shortcuts for this app
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
                    
                    # Make sure we're still monitoring
                    if not self.monitoring:
                        return False
                    
                    # Use a slightly longer delay to let key handling complete
                    # and avoid packet conflicts
                    delay = 0.1  # 100ms delay
                    
                    if has_default_keys:
                        # App has default keys - restore them
                        logger.info(f"All modifier keys released, restoring default keys for {self.current_app}")
                        # Use a timer instead of a thread
                        QTimer.singleShot(int(delay * 1000), 
                            lambda: self._highlight_app_shortcut_keys("default", shortcuts["default_keys"]))
                        return True
                    else:
                        # No default keys for this app - restore to global default or saved state
                        logger.info(f"All modifier keys released, no default keys for {self.current_app}")
                        if self.default_state and len(self.default_state) > 0:
                            # Restore to saved default state if available
                            logger.info("Restoring to saved default state")
                            QTimer.singleShot(int(delay * 1000), self.restore_default_state)
                        else:
                            # Fall back to global default
                            logger.info("Restoring to global default config")
                            QTimer.singleShot(int(delay * 1000), self.shortcut_lighting.restore_key_colors)
                        return True
                else:
                    # No app-specific shortcuts - restore global defaults
                    logger.info("All modifier keys released, restoring to global default")
                    # Use a slightly longer delay
                    QTimer.singleShot(100, self.shortcut_lighting.restore_key_colors)
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
        self.feature = feature
        self.keyboard_app = keyboard_app
        
        self.setWindowTitle("Application Shortcuts Manager")
        self.setMinimumSize(800, 500)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # App selection
        app_selection_layout = QHBoxLayout()
        app_selection_layout.addWidget(QLabel("Application:"))
        
        self.app_selector = QComboBox()
        self.app_selector.addItems(self.feature.app_shortcuts.keys())
        self.app_selector.currentTextChanged.connect(self.load_app_shortcuts)
        app_selection_layout.addWidget(self.app_selector, 1)
        
        # App name edit
        app_selection_layout.addWidget(QLabel("Name:"))
        self.app_name_edit = QLineEdit()
        app_selection_layout.addWidget(self.app_name_edit, 1)
        
        main_layout.addLayout(app_selection_layout)
        
        # Splitter for tables and settings
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side - Tables for shortcut configuration
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Create tables for different shortcut groups
        self.default_keys_table = self.create_shortcut_table("Default Keys (always highlighted)")
        self.modifier_tables = {}
        
        # Create a tab widget for the different shortcut groups
        shortcuts_tabs = QTabWidget()
        
        # Default keys tab
        default_tab = QWidget()
        default_layout = QVBoxLayout(default_tab)
        default_layout.addWidget(self.default_keys_table)
        shortcuts_tabs.addTab(default_tab, "Default Keys")
        
        # Modifier keys tabs
        for modifier in ["Ctrl", "Shift", "Alt", "Ctrl+Shift", "Ctrl+Alt", "Alt+Shift"]:
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            table = self.create_shortcut_table(f"Keys to highlight when {modifier} is pressed")
            self.modifier_tables[modifier] = table
            tab_layout.addWidget(table)
            shortcuts_tabs.addTab(tab, modifier)
        
        left_layout.addWidget(shortcuts_tabs)
        
        # Right side - App settings
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # App color selection
        color_group = QGroupBox("Application Color")
        color_layout = QVBoxLayout()
        
        # Create a color display widget
        self.app_color_display = QFrame()
        self.app_color_display.setMinimumSize(80, 40)
        self.app_color_display.setFrameShape(QFrame.Box)
        self.app_color_display.setFrameShadow(QFrame.Sunken)
        
        # Initialize with default color
        self.app_color = QColor(255, 165, 0)  # Default to orange
        self.update_color_display()
        
        # Color button
        select_color_btn = QPushButton("Select Color...")
        select_color_btn.clicked.connect(self.select_app_color)
        
        color_layout.addWidget(self.app_color_display)
        color_layout.addWidget(select_color_btn)
        color_group.setLayout(color_layout)
        
        right_layout.addWidget(color_group)
        
        # Disabled keys section
        disabled_keys_group = QGroupBox("Disabled Keys")
        disabled_layout = QVBoxLayout()
        
        disabled_layout.addWidget(QLabel("Keys to never highlight (space-separated):"))
        self.disabled_keys_edit = QLineEdit()
        disabled_layout.addWidget(self.disabled_keys_edit)
        
        disabled_keys_group.setLayout(disabled_layout)
        right_layout.addWidget(disabled_keys_group)
        
        # Options group
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()
        
        self.disable_global_check = QCheckBox("Disable global shortcuts for this app")
        self.disable_global_check.setToolTip("When checked, global shortcuts won't be highlighted for this app")
        options_layout.addWidget(self.disable_global_check)
        
        options_group.setLayout(options_layout)
        right_layout.addWidget(options_group)
        
        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        
        # Set initial sizes (2:1 ratio)
        splitter.setSizes([600, 200])
        
        main_layout.addWidget(splitter)
        
        # Buttons at bottom
        button_layout = QHBoxLayout()
        
        add_key_btn = QPushButton("Add Key...")
        add_key_btn.clicked.connect(self.add_key)
        button_layout.addWidget(add_key_btn)
        
        remove_key_btn = QPushButton("Remove Selected")
        remove_key_btn.clicked.connect(self.remove_selected_key)
        button_layout.addWidget(remove_key_btn)
        
        button_layout.addStretch()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_current_app)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.close)
        button_layout.addWidget(cancel_btn)
        
        main_layout.addLayout(button_layout)
        
        # Load initial app if there are any
        if self.app_selector.count() > 0:
            self.app_name_edit.setText(self.app_selector.currentText())
            self.load_app_shortcuts(self.app_selector.currentText())
    
    def create_shortcut_table(self, description):
        """Create and return a QTableWidget for key shortcuts."""
        table = QTableWidget()
        table.setColumnCount(1)
        table.setHorizontalHeaderLabels(["Key Name"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        return table
    
    def update_color_display(self):
        """Update the color display widget with the current color"""
        self.app_color_display.setStyleSheet(
            f"background-color: rgb({self.app_color.red()}, {self.app_color.green()}, {self.app_color.blue()});"
        )
    
    def select_app_color(self):
        """Open a color dialog to select the app color"""
        color = QColorDialog.getColor(self.app_color, self, "Select Application Color")
        if color.isValid():
            self.app_color = color
            self.update_color_display()
    
    def add_key(self):
        """Add a key to the selected table"""
        # Get the current active tab
        current_tab = self.findChild(QTabWidget).currentWidget()
        if not current_tab:
            return
        
        # Find the table in the current tab
        table = None
        for widget in current_tab.findChildren(QTableWidget):
            table = widget
            break
        
        if not table:
            return
        
        # Show a dialog to enter the key name
        key_name, ok = QInputDialog.getText(self, "Add Key", "Enter key name:")
        if ok and key_name:
            # Add the key to the table
            row = table.rowCount()
            table.setRowCount(row + 1)
            table.setItem(row, 0, QTableWidgetItem(key_name))
    
    def remove_selected_key(self):
        """Remove the selected key from the current table"""
        # Get the current active tab
        current_tab = self.findChild(QTabWidget).currentWidget()
        if not current_tab:
            return
        
        # Find the table in the current tab
        table = None
        for widget in current_tab.findChildren(QTableWidget):
            table = widget
            break
        
        if not table:
            return
        
        # Get selected rows
        selected_rows = set()
        for item in table.selectedItems():
            selected_rows.add(item.row())
        
        # Remove rows in reverse order to avoid index shifts
        for row in sorted(selected_rows, reverse=True):
            table.removeRow(row)
    
    def get_keys_from_table(self, table):
        """Get all keys from a table as a list"""
        keys = []
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if item and item.text().strip():
                keys.append(item.text().strip())
        return keys
    
    def load_app_shortcuts(self, app_name):
        """Load shortcuts for the selected application"""
        if app_name not in self.feature.app_shortcuts:
            return
        
        # Update app name edit
        self.app_name_edit.setText(app_name)
        
        # Get shortcuts data
        shortcuts = self.feature.app_shortcuts[app_name]
        
        # Load app color
        if app_name in self.feature.app_colors:
            self.app_color = self.feature.app_colors[app_name]
            self.update_color_display()
        else:
            self.app_color = QColor(255, 165, 0)  # Default to orange
            self.update_color_display()
        
        # Load disable global shortcuts option
        self.disable_global_check.setChecked(
            self.feature.disable_global_shortcuts_for_app.get(app_name, False)
        )
        
        # Clear all tables
        self.clear_all_tables()
        
        # Load default keys
        if "default_keys" in shortcuts and shortcuts["default_keys"]:
            self.load_keys_to_table(self.default_keys_table, shortcuts["default_keys"])
        
        # Load modifier keys
        for modifier, table in self.modifier_tables.items():
            if modifier in shortcuts and shortcuts[modifier]:
                self.load_keys_to_table(table, shortcuts[modifier])
        
        # Load disabled keys
        if "disabled_keys" in shortcuts and shortcuts["disabled_keys"]:
            self.disabled_keys_edit.setText(" ".join(shortcuts["disabled_keys"]))
        else:
            self.disabled_keys_edit.clear()
    
    def clear_all_tables(self):
        """Clear all tables"""
        # Clear default keys table
        self.default_keys_table.setRowCount(0)
        
        # Clear modifier tables
        for table in self.modifier_tables.values():
            table.setRowCount(0)
        
        # Clear disabled keys
        self.disabled_keys_edit.clear()
    
    def load_keys_to_table(self, table, keys):
        """Load a list of keys into a table"""
        table.setRowCount(len(keys))
        for i, key in enumerate(keys):
            table.setItem(i, 0, QTableWidgetItem(key))
    
    def save_current_app(self):
        """Save the current application configuration"""
        app_name = self.app_name_edit.text().strip()
        if not app_name:
            QMessageBox.warning(self, "Empty Name", "Please enter an application name")
            return
        
        # Collect all shortcuts
        shortcuts = {}
        
        # Get default keys
        default_keys = self.get_keys_from_table(self.default_keys_table)
        if default_keys:
            shortcuts["default_keys"] = default_keys
        
        # Get modifier key combinations
        for modifier, table in self.modifier_tables.items():
            keys = self.get_keys_from_table(table)
            if keys:
                shortcuts[modifier] = keys
        
        # Get disabled keys
        disabled_keys_text = self.disabled_keys_edit.text().strip()
        if disabled_keys_text:
            shortcuts["disabled_keys"] = [k.strip() for k in disabled_keys_text.split()]
        
        # Save the app color
        self.feature.set_app_color(app_name, self.app_color)
        
        # Save disable global shortcuts option
        self.feature.disable_global_shortcuts_for_app[app_name] = self.disable_global_check.isChecked()
        
        # Save shortcuts
        result = self.feature.save_app_shortcuts(app_name, shortcuts)
        
        if result:
            # Update the app selector if this is a new app
            if self.app_selector.findText(app_name) == -1:
                self.app_selector.addItem(app_name)
                self.app_selector.setCurrentText(app_name)
            
            QMessageBox.information(self, "Success", f"Shortcuts for '{app_name}' saved successfully")
        else:
            QMessageBox.warning(self, "Error", f"Failed to save shortcuts for '{app_name}'")
    
    def closeEvent(self, event):
        """Handle dialog close event"""
        # Check if there are unsaved changes
        # This is a simple implementation - you might want to add more sophisticated change tracking
        reply = QMessageBox.question(
            self, "Confirm Exit",
            "Close the shortcut manager? Any unsaved changes will be lost.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

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