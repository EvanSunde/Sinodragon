from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, pyqtSignal, QObject
import time

class ShortcutLighting(QObject):
    # Define signals for key press/release events
    key_pressed = pyqtSignal(str)
    key_released = pyqtSignal(str)
    
    def __init__(self, keyboard_app):
        super().__init__()
        self.app = keyboard_app
        self.shortcut_manager = keyboard_app.shortcut_manager
        self.keyboard = keyboard_app.keyboard
        self.keys = keyboard_app.keys
        
        # Monitoring state
        self.monitor_active = False
        self.currently_pressed_keys = set()
        self.highlighted_keys = []
        self.original_key_colors = {}
        
        # Default highlight colors for modifiers
        self.default_highlight_color = QColor(255, 165, 0)  # Orange
        self.modifier_colors = {
            "Ctrl": QColor(255, 100, 0),     # Orange-red
            "Shift": QColor(0, 200, 255),    # Light blue
            "Alt": QColor(200, 255, 0),      # Yellow-green
            "Win": QColor(255, 0, 255),      # Magenta
            "Fn": QColor(150, 150, 255)      # Light purple
        }
        
        # Track if we've saved original state
        self.original_state_saved = False
        
        # Add a field to store the default lighting config
        self.default_config_name = "Default Green"
        
        # Add a field to track when we last updated highlights
        self.last_highlight_update = 0
        # How often to refresh the highlight (in seconds)
        self.highlight_refresh_rate = 0.2
        
        # Optimization: Cache for currently displayed colors to avoid redundant updates
        self.key_color_cache = {}
        self.update_pending = False
        self.batch_update_timer = None
        if hasattr(self.app, 'QTimer'):
            self.batch_update_timer = self.app.QTimer()
            self.batch_update_timer.setSingleShot(True)
            self.batch_update_timer.timeout.connect(self.apply_pending_updates)
    
    def start_monitor(self):
        """Start monitoring keyboard for shortcuts"""
        if self.monitor_active:
            return
        
        self.monitor_active = True
        self.currently_pressed_keys.clear()
        self.original_state_saved = False
        # Initialize color cache
        self.key_color_cache = {}
        self.app.statusBar().showMessage("Shortcut monitoring activated")
    
    def stop_monitor(self):
        """Stop monitoring keyboard for shortcuts"""
        self.monitor_active = False
        self.app.statusBar().showMessage("Shortcut monitoring deactivated")
        
        # Restore original colors
        self.restore_key_colors()
    
    def handle_key_press(self, key_name):
        """Handle a key press event"""
        if not self.monitor_active:
            return
        
        self.currently_pressed_keys.add(key_name)
        # Emit the key_pressed signal
        self.key_pressed.emit(key_name)
        self.update_key_highlights()
    
    def handle_key_release(self, key_name):
        """Handle a key release event"""
        if not self.monitor_active:
            return
        
        if key_name in self.currently_pressed_keys:
            self.currently_pressed_keys.remove(key_name)
        
        # Emit the key_released signal
        self.key_released.emit(key_name)
        
        # Only restore colors if no keys are pressed
        if not self.currently_pressed_keys:
            self.restore_key_colors()
            self.original_state_saved = False
        else:
            # Update highlights with remaining keys
            self.update_key_highlights()
    
    def update_key_highlights(self):
        """Update key highlighting based on currently pressed keys"""
        if not self.currently_pressed_keys:
            return
        
        # Don't update highlights too frequently (throttle)
        current_time = time.time()
        if current_time - self.last_highlight_update < self.highlight_refresh_rate:
            self.update_pending = True
            if self.batch_update_timer and not self.batch_update_timer.isActive():
                self.batch_update_timer.start(int(self.highlight_refresh_rate * 1000))
            return
        
        self.last_highlight_update = current_time
        
        # Convert set to list for the shortcut manager
        pressed_list = list(self.currently_pressed_keys)
        
        # Get keys to highlight from shortcut manager
        keys_to_highlight = self.shortcut_manager.get_keys_to_highlight(pressed_list)
        
        # Add the pressed modifier keys themselves to the highlight list
        for mod_key in self.currently_pressed_keys:
            if mod_key not in keys_to_highlight:
                keys_to_highlight.append(mod_key)
        
        # Create a list of colors for all keys (black by default)
        key_colors = [(0, 0, 0) for _ in range(len(self.keys))]
        
        # Check if the key colors would actually change
        changed = False
        
        # Set colors for highlighted keys
        for key in self.keys:
            # Check if key name matches (case-insensitive)
            if key.key_name.lower() in [k.lower() for k in keys_to_highlight]:
                # Choose the appropriate color
                color_found = False
                
                # First check if it's a modifier key
                for mod_name, mod_color in self.modifier_colors.items():
                    if key.key_name.lower() == mod_name.lower() and mod_name in self.currently_pressed_keys:
                        key_colors[key.index] = (mod_color.red(), mod_color.green(), mod_color.blue())
                        color_found = True
                        break
                
                # If not a modifier or no special color, use default
                if not color_found:
                    key_colors[key.index] = (self.default_highlight_color.red(), 
                                           self.default_highlight_color.green(), 
                                           self.default_highlight_color.blue())
                
                # Check if this color is different from the cache
                if key.index not in self.key_color_cache or self.key_color_cache[key.index] != key_colors[key.index]:
                    self.key_color_cache[key.index] = key_colors[key.index]
                    changed = True
        
        # Only send update if colors actually changed
        if changed and self.keyboard.connected:
            self.keyboard.send_led_config(key_colors)
            self.update_pending = False
    
    def apply_pending_updates(self):
        """Apply any pending updates that were throttled"""
        if self.update_pending:
            self.update_pending = False
            self.update_key_highlights()
    
    def restore_key_colors(self):
        """Restore to default lighting configuration"""
        try:
            # Just load the default configuration
            self.app.load_config(self.default_config_name)
            
            # If auto-reload is on, send the updated colors to the keyboard
            if self.app.auto_reload and self.keyboard.connected:
                self.app.send_config()
                
            return True
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error restoring default configuration: {e}")
            
            # Try alternative approach if initial method fails
            try:
                # Try to directly load a default configuration if exists
                configs = self.app.config_manager.get_config_list()
                if "Default Green" in configs:
                    self.app.load_config("Default Green")
                elif len(configs) > 0:
                    self.app.load_config(configs[0])
                    
                # Force send configuration to keyboard
                if self.keyboard.connected:
                    self.app.send_config()
                return True
            except Exception as inner_e:
                logger.error(f"Failed fallback restore: {inner_e}")
                return False
    
    def set_modifier_color(self, modifier, color):
        """Set a custom color for a specific modifier key"""
        self.modifier_colors[modifier] = color
    
    def get_modifier_color(self, modifier):
        """Get the color for a specific modifier key"""
        return self.modifier_colors.get(modifier, self.default_highlight_color)
    
    def set_default_highlight_color(self, color):
        """Set the default highlight color for non-modifier keys"""
        self.default_highlight_color = color
    
    def set_default_config(self, config_name):
        """Set the default configuration to restore when shortcuts are released"""
        self.default_config_name = config_name 