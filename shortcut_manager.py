import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ShortcutManager:
    def __init__(self):
        # Define possible config paths
        home_dir = os.path.expanduser("~")
        self.global_config_dir = os.path.join(home_dir, ".config", "sinodragon")
        self.local_config_dir = "./config"
        self.shortcut_file = "shortcuts.json"
        
        # Ensure config directories exist
        self._ensure_config_dirs()
        
        # Default shortcuts for common apps (key is the shortcut name, value is list of keys to highlight)
        self.default_shortcuts = {
            "copy": ["Ctrl", "C"],
            "paste": ["Ctrl", "V"],
            "cut": ["Ctrl", "X"],
            "save": ["Ctrl", "S"],
            "undo": ["Ctrl", "Z"],
            "redo": ["Ctrl", "Y"],
            "find": ["Ctrl", "F"],
            "select_all": ["Ctrl", "A"],
            "new": ["Ctrl", "N"],
            "print": ["Ctrl", "P"],
            "close": ["Alt", "F4"],
            "switch_window": ["Alt", "Tab"]
        }
        
        # Mapping of common modifier key names to their representations in the keyboard layout
        self.modifier_map = {
            "ctrl": "Ctrl",
            "control": "Ctrl",
            "alt": "Alt",
            "shift": "Shift",
            "win": "Win",
            "super": "Win",
            "meta": "Win"
        }
        
        # Currently active shortcuts
        self.active_shortcuts = {}
        
        # Load saved shortcuts
        self.load_shortcuts()
    
    def _ensure_config_dirs(self):
        """Ensure that configuration directories exist"""
        # Try global config directory first
        try:
            os.makedirs(self.global_config_dir, exist_ok=True)
            self.config_dir = self.global_config_dir
            logger.info(f"Using global config directory: {self.global_config_dir}")
        except (PermissionError, OSError):
            # Fall back to local config if global fails
            try:
                os.makedirs(self.local_config_dir, exist_ok=True)
                self.config_dir = self.local_config_dir
                logger.info(f"Using local config directory: {self.local_config_dir}")
            except (PermissionError, OSError) as e:
                logger.error(f"Failed to create config directories: {e}")
                self.config_dir = None
    
    def get_shortcut_path(self):
        """Get the path to the shortcuts file"""
        if not self.config_dir:
            return None
        return os.path.join(self.config_dir, self.shortcut_file)
    
    def load_shortcuts(self):
        """Load shortcuts from configuration file"""
        shortcut_path = self.get_shortcut_path()
        
        # Start with defaults
        self.active_shortcuts = self.default_shortcuts.copy()
        
        if shortcut_path and os.path.exists(shortcut_path):
            try:
                with open(shortcut_path, 'r') as f:
                    custom_shortcuts = json.load(f)
                    # Update defaults with custom shortcuts
                    self.active_shortcuts.update(custom_shortcuts)
                logger.info(f"Loaded shortcuts from {shortcut_path}")
            except Exception as e:
                logger.error(f"Error loading shortcuts: {e}")
    
    def save_shortcuts(self):
        """Save current shortcuts to configuration file"""
        shortcut_path = self.get_shortcut_path()
        if not shortcut_path:
            logger.error("Cannot save shortcuts - no valid configuration directory")
            return False
            
        try:
            with open(shortcut_path, 'w') as f:
                json.dump(self.active_shortcuts, f, indent=2)
            logger.info(f"Saved shortcuts to {shortcut_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving shortcuts: {e}")
            return False
    
    def add_shortcut(self, name, keys):
        """Add or update a shortcut"""
        self.active_shortcuts[name] = keys
        self.save_shortcuts()
    
    def remove_shortcut(self, name):
        """Remove a shortcut by name"""
        if name in self.active_shortcuts:
            del self.active_shortcuts[name]
            self.save_shortcuts()
    
    def get_keys_to_highlight(self, pressed_keys):
        """
        Determine which keys to highlight based on currently pressed keys
        
        Args:
            pressed_keys: List of currently pressed keys (e.g., ["ctrl", "c"])
            
        Returns:
            List of keys to highlight in the keyboard layout
        """
        # Normalize pressed key names
        normalized_keys = []
        for key in pressed_keys:
            key_lower = key.lower()
            if key_lower in self.modifier_map:
                normalized_keys.append(self.modifier_map[key_lower])
            else:
                # For non-modifiers, capitalize the first letter
                normalized_keys.append(key.upper() if len(key) == 1 else key.capitalize())
        
        # Check if the pressed keys match any shortcut
        for shortcut_name, shortcut_keys in self.active_shortcuts.items():
            # Check if the pressed keys contain all the shortcut keys
            if all(key in normalized_keys for key in shortcut_keys):
                return shortcut_keys
        
        # If no specific shortcut matched, just return the normalized keys
        return normalized_keys 