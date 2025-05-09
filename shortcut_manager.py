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
        self.layout_file = "keyboard_layout.json"
        
        # Ensure config directories exist
        self._ensure_config_dirs()
        
        # Default shortcuts for modifiers (key is the modifier, value is list of keys to highlight)
        self.default_shortcuts = {
            "Ctrl": ["C", "V", "X", "S", "A", "Z"],
            "Ctrl+Shift": ["Q", "W", "E", "R"],
            "Win": ["T", "R", "E", "S", "F"],
            "Alt": ["Tab", "F4"]
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
    
    def get_layout_path(self):
        """Get the path to the keyboard layout file"""
        if not self.config_dir:
            return None
        return os.path.join(self.config_dir, self.layout_file)
    
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
    
    def save_keyboard_layout(self, layout_matrix):
        """Save the keyboard layout matrix to a file"""
        layout_path = self.get_layout_path()
        if not layout_path:
            logger.error("Cannot save layout - no valid configuration directory")
            return False
            
        try:
            with open(layout_path, 'w') as f:
                json.dump(layout_matrix, f, indent=2)
            logger.info(f"Saved keyboard layout to {layout_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving keyboard layout: {e}")
            return False
    
    def load_keyboard_layout(self):
        """Load the keyboard layout matrix from a file"""
        layout_path = self.get_layout_path()
        
        if layout_path and os.path.exists(layout_path):
            try:
                with open(layout_path, 'r') as f:
                    layout_matrix = json.load(f)
                logger.info(f"Loaded keyboard layout from {layout_path}")
                return layout_matrix
            except Exception as e:
                logger.error(f"Error loading keyboard layout: {e}")
        
        return None
    
    def add_shortcut(self, modifier, keys):
        """Add or update a shortcut for a modifier"""
        self.active_shortcuts[modifier] = keys
        self.save_shortcuts()
    
    def remove_shortcut(self, modifier):
        """Remove a shortcut by modifier"""
        if modifier in self.active_shortcuts:
            del self.active_shortcuts[modifier]
            self.save_shortcuts()
    
    def get_keys_to_highlight(self, pressed_keys):
        """
        Determine which keys to highlight based on currently pressed modifier keys
        
        Args:
            pressed_keys: List of currently pressed keys (e.g., ["ctrl", "c"])
            
        Returns:
            List of keys to highlight in the keyboard layout
        """
        # Normalize pressed key names
        normalized_keys = []
        modifiers_pressed = []
        
        for key in pressed_keys:
            if not key:  # Skip empty keys
                continue
                
            key_lower = key.lower()
            if key_lower in self.modifier_map:
                normalized_key = self.modifier_map[key_lower]
                normalized_keys.append(normalized_key)
                modifiers_pressed.append(normalized_key)
            else:
                # For non-modifiers, preserve the original case
                # This helps with keyboard layout matching
                normalized_keys.append(key)
        
        # Log the keys we're working with
        logger.debug(f"Normalized pressed keys: {normalized_keys}")
        logger.debug(f"Identified modifiers: {modifiers_pressed}")
        
        # First check for combo modifiers (e.g., Ctrl+Shift)
        combo_modifiers = []
        for mod1 in modifiers_pressed:
            for mod2 in modifiers_pressed:
                if mod1 != mod2:
                    combo = f"{mod1}+{mod2}"
                    combo_modifiers.append(combo)
        
        # Check multi-modifiers first, then single modifiers
        keys_to_highlight = []
        
        # Try combinations of modifiers first
        for combo in combo_modifiers:
            if combo in self.active_shortcuts:
                keys_to_highlight = self.active_shortcuts[combo]
                logger.info(f"Found shortcut keys for combo {combo}: {keys_to_highlight}")
                break
                
        # If no combo modifier matched, check individual modifiers
        if not keys_to_highlight:
            for modifier in modifiers_pressed:
                if modifier in self.active_shortcuts:
                    keys_to_highlight = self.active_shortcuts[modifier]
                    logger.info(f"Found shortcut keys for {modifier}: {keys_to_highlight}")
                    break
        
        # If no shortcut configuration matched, just return the modifiers themselves
        if not keys_to_highlight:
            keys_to_highlight = modifiers_pressed 
            logger.info(f"No shortcut configuration matched, using modifiers: {keys_to_highlight}")
        
        # Ensure all keys in the returned list are actually valid
        result = []
        for key in keys_to_highlight:
            if key:  # Skip empty keys
                result.append(key)
                
        logger.info(f"Final keys to highlight: {result}")
        return result 