from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, pyqtSignal, QObject
import time
import logging
from features.global_monitor import GlobalMonitorFeature

logger = logging.getLogger(__name__)

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
        
        # Create global monitor feature
        self.global_monitor = GlobalMonitorFeature(keyboard_app)
        self.global_monitor.key_pressed.connect(self.handle_key_press)
        self.global_monitor.key_released.connect(self.handle_key_release)
        
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
    
    def start_monitor(self, use_global=True):
        """Start monitoring keyboard for shortcuts"""
        if self.monitor_active:
            return
        
        self.monitor_active = True
        self.currently_pressed_keys.clear()
        self.original_state_saved = False
        # Initialize color cache
        self.key_color_cache = {}
        
        # Start global monitor if requested
        if use_global:
            self.global_monitor.start_monitor()
            
        self.app.statusBar().showMessage("Shortcut monitoring activated")
    
    def stop_monitor(self):
        """Stop monitoring keyboard for shortcuts"""
        self.monitor_active = False
        
        # Stop global monitor
        self.global_monitor.stop_monitor()
        
        self.app.statusBar().showMessage("Shortcut monitoring deactivated")
        
        # Restore original colors
        self.restore_key_colors()
    
    def handle_key_press(self, key_name):
        """Handle a key press event"""
        if not self.monitor_active:
            return
        
        # Check if key is already in the set to avoid duplicate handling
        if key_name in self.currently_pressed_keys:
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
        """
        Highlight keys based on current state. Throttled to prevent excessive update.
        
        This method is called both by handle_key_press and handle_key_release
        to ensure we maintain key highlights for all relevant keys.
        """
        current_time = time.time()
        if current_time - self.last_highlight_update < self.highlight_refresh_rate:
            self.update_pending = True
            if self.batch_update_timer and not self.batch_update_timer.isActive():
                self.batch_update_timer.start(int(self.highlight_refresh_rate * 1000))
            return

        self.last_highlight_update = current_time
        self.update_pending = False
        
        # Convert the set of pressed keys to a list
        pressed_keys = list(self.currently_pressed_keys)
        logger.debug(f"Updating highlights for keys: {pressed_keys}")
        
        # Create a list to hold all the keys that should be highlighted
        keys_to_highlight = []
        
        # Get the keys to highlight from the shortcut manager
        if pressed_keys:
            try:
                # Get keys from shortcut manager if any modifiers are pressed
                keys_to_highlight = self.shortcut_manager.get_keys_to_highlight(pressed_keys)
                logger.debug(f"Keys to highlight from shortcut manager: {keys_to_highlight}")
                
                # Make sure modifiers themselves are always included
                for key in pressed_keys:
                    if key not in keys_to_highlight and key in ["Ctrl", "Shift", "Alt", "Win"]:
                        keys_to_highlight.append(key)
            except Exception as e:
                logger.error(f"Error getting keys to highlight: {e}")
                # If there's an error, just highlight the pressed modifiers
                keys_to_highlight = [key for key in pressed_keys if key in ["Ctrl", "Shift", "Alt", "Win"]]
        
        # Create list of default key colors
        key_colors = []
        changed = False
        use_mod_color = None
        
        # Initialize all keys to default color first
        for i, key in enumerate(self.keys):
            # Default to the default color
            new_color = (0, 0, 0)  # Default to black
            
            # Check if any modifiers are pressed - get the proper color
            for mod_key in ["Ctrl", "Shift", "Alt", "Win"]:
                if mod_key in pressed_keys:
                    use_mod_color = self.modifier_colors.get(mod_key, self.default_highlight_color)
                    break
                    
            # For specific keys that need to be highlighted
            color_found = False
            for highlight_key in keys_to_highlight:
                if highlight_key == key.key_name:
                    # If it's a modifier and is pressed, use the modifier color
                    if highlight_key in ["Ctrl", "Shift", "Alt", "Win"] and highlight_key in pressed_keys:
                        new_color = use_mod_color
                    # Otherwise use the highlighter color (or mod color if available)
                    else:
                        new_color = use_mod_color if use_mod_color else self.default_highlight_color
                    color_found = True
                    break
            
            # If color has changed, update it and mark as changed
            if key.color != new_color:
                key.setKeyColor(new_color)
                changed = True
                
            key_colors.append((new_color[0], new_color[1], new_color[2]))
        
        # Only send update if colors actually changed
        if changed:
            try:
                # Ensure valid color values before sending
                safe_colors = []
                for r, g, b in key_colors:
                    safe_colors.append((
                        max(0, min(255, int(r))),
                        max(0, min(255, int(g))),
                        max(0, min(255, int(b)))
                    ))
                
                if self.keyboard.connected:
                    logger.debug("Sending updated LED config to keyboard")
                    self.keyboard.send_led_config(safe_colors)
                else:
                    logger.warning("Keyboard not connected, cannot update LEDs")
            except Exception as e:
                logger.error(f"Error sending LED config: {e}", exc_info=True)
        else:
            logger.debug("No color changes, skipping LED update")
    
    def apply_pending_updates(self):
        """
        Apply any updates that were throttled due to update_interval
        """
        if self.update_pending:
            logger.debug("Applying pending key highlight updates")
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