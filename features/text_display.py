"""
Text display functionality for the keyboard.
Provides methods to display text and scroll text on the keyboard.
"""

import time
from PyQt5.QtGui import QColor

class TextDisplayFeature:
    def __init__(self, keyboard_app):
        """
        Initialize the text display feature.
        
        Args:
            keyboard_app: The main keyboard application instance
        """
        self.app = keyboard_app
        self.keys = keyboard_app.keys
        self.keyboard = keyboard_app.keyboard
    
    def clear_keyboard(self):
        """Turn off all keys (set to black)"""
        for key in self.keys:
            key.setKeyColor(QColor(0, 0, 0))
        return True
    
    def apply_keyboard_config(self, key_colors=None, config_name=None):
        """
        Apply a specific configuration to the keyboard
        
        Args:
            key_colors: A list of (key_name, color) tuples to apply
            config_name: Name of a saved configuration to load
        """
        if config_name:
            return self.app.load_config(config_name)
        
        if key_colors:
            # First clear all keys
            self.clear_keyboard()
            
            # Set colors for specified keys
            for key_name, color in key_colors:
                if isinstance(color, tuple):
                    color = QColor(*color)
                    
                for key in self.keys:
                    if key.key_name == key_name:
                        key.setKeyColor(color)
                        break
            
            # Send the configuration
            self.app.send_config()
            return True
        
        return False
    
    def display_text(self, text, color=None, clear_first=True):
        """
        Display text on the keyboard by lighting up the corresponding keys
        
        Args:
            text: String to display on the keyboard
            color: Color to use (QColor or RGB tuple)
            clear_first: Whether to clear all keys before display
        """
        if clear_first:
            self.clear_keyboard()
        
        # Define color to use for the text
        if color is None:
            text_color = QColor(255, 255, 255)  # White by default
        elif isinstance(color, tuple):
            text_color = QColor(*color)
        else:
            text_color = color
        
        # Map lowercase text to uppercase for the key matching
        text = text.upper()
        
        # Create a list of (key_name, color) tuples to apply
        key_colors = []
        displayed_chars = set()
        
        for char in text:
            if char not in displayed_chars:
                key_colors.append((char, text_color))
                displayed_chars.add(char)
        
        # Apply the colors
        return self.apply_keyboard_config(key_colors)
    
    def display_advanced_text(self, text, color=None, start_pos=None, clear_first=True):
        """
        Display text on the keyboard with advanced options
        
        Args:
            text: String to display on the keyboard
            color: QColor or RGB tuple for the text color (default: white)
            start_pos: Starting position as (row, col) tuple or None for auto
            clear_first: Whether to clear all keys before display
        """
        if clear_first:
            self.clear_keyboard()
        
        # Define color to use for the text
        if color is None:
            text_color = QColor(255, 255, 255)  # White by default
        elif isinstance(color, tuple):
            text_color = QColor(*color)
        else:
            text_color = color
        
        # Map lowercase text to uppercase for the key matching
        text = text.upper()
        
        # Create a map of keyboard layout for positioning
        layout_map = self.get_keyboard_layout_map()
        
        # If no starting position provided, try to center the text
        if start_pos is None:
            start_pos = (2, 2)  # Row for Q key, column for Q key
        
        row, col = start_pos
        
        # Create a list of (key_name, color) tuples to apply
        key_colors = []
        
        # Try to display the text
        for char in text:
            # Skip spaces but advance position
            if char == " ":
                col += 1
                continue
            
            # Try to find the character in the layout
            for key in self.keys:
                if key.key_name == char:
                    key_colors.append((char, text_color))
                    break
            
            # Advance position
            col += 1
            
            # Check if we need to wrap to next row
            if col > 10:  # Wrap after P key
                col = 2  # Back to Q column
                row += 1  # Next row (A-L row)
        
        # Apply the colors
        return self.apply_keyboard_config(key_colors)
    
    def get_keyboard_layout_map(self):
        """Return a map of keyboard positions to key names"""
        layout_map = {}
        
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
        
        # Build the layout map for positioning
        for col, column in enumerate(layout_def):
            for row, key_name in enumerate(column):
                if key_name != "NAN":
                    layout_map[(row, col)] = key_name
        
        return layout_map
    
    def scroll_text(self, text, speed=0.5, color=None):
        """
        Scroll text across the keyboard
        
        Args:
            text: Text to scroll
            speed: Scroll speed in seconds per position
            color: Color for the text
        """
        if color is None:
            color = QColor(255, 255, 255)  # White by default
        elif isinstance(color, tuple):
            color = QColor(*color)
        
        # Convert text to uppercase
        text = text.upper()
        
        # Define the width of the "display area" in columns
        display_width = 8
        
        # Add padding to text
        padded_text = " " * display_width + text + " " * display_width
        
        try:
            # Scroll the text
            for i in range(len(padded_text) - display_width):
                # Get the current window of text to display
                current_text = padded_text[i:i+display_width]
                
                # Display this window
                self.clear_keyboard()
                self.display_advanced_text(current_text, color=color, clear_first=False)
                
                # Wait according to speed
                time.sleep(speed)
            
            return True
        except KeyboardInterrupt:
            # Allow graceful exit with Ctrl+C
            return False 