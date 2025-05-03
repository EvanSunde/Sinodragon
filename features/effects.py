"""
Effects for the keyboard.
Provides methods to create visual effects on the keyboard.
"""

import colorsys
from PyQt5.QtGui import QColor
import random
import math
import time

class EffectsFeature:
    def __init__(self, keyboard_app):
        """
        Initialize the effects feature.
        
        Args:
            keyboard_app: The main keyboard application instance
        """
        self.app = keyboard_app
        self.keys = keyboard_app.keys
        self.keyboard = keyboard_app.keyboard
    
    def set_function_key_colors(self, color):
        """Set all function keys to a specific color"""
        # Function key labels
        function_keys = ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"]
        
        # Find the function keys by label and set their color
        for key in self.keys:
            if key.key_name in function_keys:
                if isinstance(color, tuple):
                    key.setKeyColor(QColor(*color))
                else:
                    key.setKeyColor(color)
        
        if self.app.auto_reload and self.keyboard.connected:
            self.app.send_config()
        
        return True
    
    def set_rainbow_colors(self):
        """Create a rainbow effect across all keys"""
        # Create a rainbow gradient
        num_keys = len(self.keys)
        for i, key in enumerate(self.keys):
            # Create a color based on position in keyboard
            hue = i / num_keys
            r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            key.setKeyColor(QColor(int(r * 255), int(g * 255), int(b * 255)))
        
        if self.app.auto_reload and self.keyboard.connected:
            self.app.send_config()
        
        return True
    
    def set_wave_effect(self, direction="horizontal", speed=0.1):
        """
        Create a wave effect across the keyboard
        
        Args:
            direction: "horizontal" or "vertical"
            speed: Wave speed (lower is faster)
        """
        import time
        import math
        
        # Get the keyboard layout map to determine positions
        layout_map = {}
        rows = 6  # Number of rows in the keyboard
        cols = 16  # Number of columns in the keyboard
        
        # Map keys to their positions
        for key in self.keys:
            # Find the position based on layout
            for col in range(cols):
                for row in range(rows):
                    if (row, col) in layout_map and layout_map[(row, col)] == key.key_name:
                        layout_map[(row, col)] = key
        
        # Animation parameters
        frames = 20
        cycles = 2  # How many complete waves to display
        
        try:
            for frame in range(frames):
                # Calculate wave position
                position = frame / frames
                
                # Set colors for each key based on position in the wave
                for key in self.keys:
                    # Calculate wave color (blue to cyan to blue)
                    if direction == "horizontal":
                        # Find approximate x position (column)
                        x_pos = 0
                        for col in range(cols):
                            for row in range(rows):
                                if (row, col) in layout_map and layout_map[(row, col)] == key:
                                    x_pos = col / cols
                                    break
                        
                        # Calculate wave offset at this position
                        wave_offset = math.sin(2 * math.pi * (x_pos + position) * cycles)
                    else:  # vertical
                        # Find approximate y position (row)
                        y_pos = 0
                        for row in range(rows):
                            for col in range(cols):
                                if (row, col) in layout_map and layout_map[(row, col)] == key:
                                    y_pos = row / rows
                                    break
                        
                        # Calculate wave offset at this position
                        wave_offset = math.sin(2 * math.pi * (y_pos + position) * cycles)
                    
                    # Convert to color (blue to cyan)
                    intensity = (wave_offset + 1) / 2  # Convert from [-1,1] to [0,1]
                    r = int(0)
                    g = int(intensity * 255)
                    b = int(255)
                    key.setKeyColor(QColor(r, g, b))
                
                # Send update to keyboard
                if self.keyboard.connected:
                    self.app.send_config()
                
                # Delay for animation
                time.sleep(speed)
            
            return True
        
        except KeyboardInterrupt:
            # Allow graceful exit with Ctrl+C
            return False 

    def breathe_effect(self, color=None, speed=0.1, cycles=3):
        """
        Create a breathing effect that pulses a color
        
        Args:
            color: Base color to pulse (or None for default)
            speed: Speed of breathing
            cycles: Number of breath cycles
        """
        if color is None:
            color = (0, 150, 255)  # Default cyan-blue
        
        if isinstance(color, QColor):
            r, g, b = color.red(), color.green(), color.blue()
        else:
            r, g, b = color
        
        try:
            # Calculate frames based on speed
            frames_per_cycle = int(30 / speed)
            total_frames = frames_per_cycle * cycles
            
            for frame in range(total_frames):
                # Calculate breathing intensity using sine wave
                progress = (frame % frames_per_cycle) / frames_per_cycle
                intensity = 0.5 + 0.5 * math.sin(progress * 2 * math.pi)
                
                # Apply intensity to all keys
                for key in self.keys:
                    # Scale the color by intensity
                    scaled_r = int(r * intensity)
                    scaled_g = int(g * intensity)
                    scaled_b = int(b * intensity)
                    key.setKeyColor(QColor(scaled_r, scaled_g, scaled_b))
                
                # Send update to keyboard
                if self.keyboard.connected:
                    self.app.send_config()
                
                # Delay for animation
                time.sleep(speed)
            
            return True
        
        except KeyboardInterrupt:
            return False

    def ripple_effect(self, color=None, speed=0.05, origin=None):
        """
        Create a ripple effect that radiates from a point
        
        Args:
            color: Ripple color (or None for default)
            speed: Animation speed
            origin: Tuple (x, y) of ripple origin or None for center
        """
        if color is None:
            color = (50, 100, 255)  # Default blue
        
        if isinstance(color, QColor):
            ripple_color = color
        else:
            ripple_color = QColor(*color)
        
        # Define keyboard dimensions and origin
        cols = 16
        rows = 6
        
        if origin is None:
            origin_x = cols / 2
            origin_y = rows / 2
        else:
            origin_x, origin_y = origin
        
        try:
            # Calculate positions for all keys
            key_positions = {}
            for key in self.keys:
                # Find approximate position (this would be better with actual layout data)
                found = False
                for col in range(cols):
                    for row in range(rows):
                        if found:
                            break
                        # This is a heuristic - in a real implementation you'd use the actual layout
                        if row * cols + col == key.index:
                            key_positions[key] = (col, row)
                            found = True
                            break
            
            # Clear the keyboard
            for key in self.keys:
                key.setKeyColor(QColor(0, 0, 0))
            
            # Animation parameters
            max_distance = math.sqrt(cols**2 + rows**2)
            frames = 30
            
            # Animate ripple
            for frame in range(frames):
                ripple_radius = (frame / frames) * max_distance * 1.5
                ripple_thickness = max_distance / 5
                
                for key, (x, y) in key_positions.items():
                    # Calculate distance from origin
                    distance = math.sqrt((x - origin_x)**2 + (y - origin_y)**2)
                    
                    # Check if the key is within the ripple
                    if abs(distance - ripple_radius) < ripple_thickness:
                        # Calculate intensity based on distance from the ripple center
                        intensity = 1.0 - abs(distance - ripple_radius) / ripple_thickness
                        key.setKeyColor(QColor(
                            int(ripple_color.red() * intensity),
                            int(ripple_color.green() * intensity),
                            int(ripple_color.blue() * intensity)
                        ))
                    else:
                        key.setKeyColor(QColor(0, 0, 0))
                
                # Send update to keyboard
                if self.keyboard.connected:
                    self.app.send_config()
                
                # Delay for animation
                time.sleep(speed)
            
            # Clear all keys at the end
            for key in self.keys:
                key.setKeyColor(QColor(0, 0, 0))
            
            if self.keyboard.connected:
                self.app.send_config()
            
            return True
        
        except KeyboardInterrupt:
            return False

    def gradient_effect(self, colors=None, direction="horizontal", speed=0.1, cycles=2):
        """
        Create a moving gradient effect across the keyboard
        
        Args:
            colors: List of colors for the gradient, or None for default
            direction: "horizontal" or "vertical"
            speed: Animation speed
            cycles: Number of cycles to animate
        """
        if colors is None:
            # Default is a blue-purple-pink gradient
            colors = [(0, 0, 255), (150, 0, 255), (255, 0, 150), (150, 0, 255)]
        
        # Convert any color tuples to QColor
        gradient_colors = []
        for color in colors:
            if isinstance(color, QColor):
                gradient_colors.append(color)
            else:
                gradient_colors.append(QColor(*color))
        
        try:
            # Calculate the number of steps in the gradient
            frames = 60
            
            for cycle in range(cycles):
                for frame in range(frames):
                    progress = frame / frames
                    
                    # Move gradient across keyboard
                    for key in self.keys:
                        # Get relative position based on direction
                        if direction == "horizontal":
                            pos = key.index % 16 / 16  # Approximate column position
                        else:  # vertical
                            pos = int(key.index / 16) / 6  # Approximate row position
                        
                        # Adjust position by progress to animate movement
                        pos = (pos + progress) % 1.0
                        
                        # Find the two colors to interpolate between
                        color_index = pos * len(gradient_colors)
                        color1_idx = int(color_index) % len(gradient_colors)
                        color2_idx = (color1_idx + 1) % len(gradient_colors)
                        
                        mix_factor = color_index - int(color_index)
                        
                        # Interpolate between the two colors
                        r = int(gradient_colors[color1_idx].red() * (1 - mix_factor) + 
                               gradient_colors[color2_idx].red() * mix_factor)
                        g = int(gradient_colors[color1_idx].green() * (1 - mix_factor) + 
                               gradient_colors[color2_idx].green() * mix_factor)
                        b = int(gradient_colors[color1_idx].blue() * (1 - mix_factor) + 
                               gradient_colors[color2_idx].blue() * mix_factor)
                        
                        key.setKeyColor(QColor(r, g, b))
                    
                    # Send update to keyboard
                    if self.keyboard.connected:
                        self.app.send_config()
                    
                    # Delay for animation
                    time.sleep(speed)
            
            return True
        
        except KeyboardInterrupt:
            return False

    def reactive_effect(self, base_color=(0, 0, 0), highlight_color=(255, 255, 255), duration=10):
        """
        Create a reactive effect that lights up keys when pressed
        
        Args:
            base_color: Base color for all keys
            highlight_color: Color for pressed keys
            duration: How long to keep the effect running in seconds
        """
        # Set up base colors
        if isinstance(base_color, QColor):
            base_qcolor = base_color
        else:
            base_qcolor = QColor(*base_color)
        
        if isinstance(highlight_color, QColor):
            highlight_qcolor = highlight_color
        else:
            highlight_qcolor = QColor(*highlight_color)
        
        # Apply base color to all keys
        for key in self.keys:
            key.setKeyColor(base_qcolor)
        
        # Send update to keyboard
        if self.keyboard.connected:
            self.app.send_config()
        
        # This requires integration with keyboard events to work properly
        print("Press keys on your keyboard to see them light up...")
        print(f"Effect will run for {duration} seconds.")
        print("Press Ctrl+C to stop early.")
        
        try:
            # Start time
            start_time = time.time()
            
            # Run for the specified duration
            while time.time() - start_time < duration:
                # Sleep briefly to avoid high CPU usage
                time.sleep(0.05)
                
                # Note: This is a simulation - for a real implementation,
                # you would need to connect to keyboard events and light up keys
                # as they are pressed, then fade them back to the base color.
                
                # To simulate, we'll randomly light up keys
                if random.random() < 0.1:  # 10% chance of lighting a key
                    # Choose a random key
                    key = random.choice(self.keys)
                    
                    # Set it to highlight color
                    key.setKeyColor(highlight_qcolor)
                    
                    # Send update
                    if self.keyboard.connected:
                        self.app.send_config()
                    
                    # Reset it after a short delay
                    time.sleep(0.2)
                    key.setKeyColor(base_qcolor)
                    
                    # Send update
                    if self.keyboard.connected:
                        self.app.send_config()
            
            return True
        
        except KeyboardInterrupt:
            return False

    def spectrum_effect(self, speed=0.1, cycles=3):
        """
        Create a full spectrum cycle across all keys simultaneously
        
        Args:
            speed: Animation speed
            cycles: Number of full spectrum cycles
        """
        try:
            frames = 100
            
            for cycle in range(cycles):
                for frame in range(frames):
                    # Calculate hue based on frame
                    hue = frame / frames
                    
                    # Convert HSV to RGB
                    r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                    
                    # Apply to all keys
                    for key in self.keys:
                        key.setKeyColor(QColor(int(r * 255), int(g * 255), int(b * 255)))
                    
                    # Send update to keyboard
                    if self.keyboard.connected:
                        self.app.send_config()
                    
                    # Delay for animation
                    time.sleep(speed)
            
            return True
        
        except KeyboardInterrupt:
            return False

    def starlight_effect(self, base_color=(0, 0, 30), star_color=(255, 255, 255), density=0.1, duration=10):
        """
        Create a starlight effect with random keys lighting up
        
        Args:
            base_color: Dark base color
            star_color: Bright star color
            density: Proportion of keys that should be lit (0.0-1.0)
            duration: How long to run the effect in seconds
        """
        # Set up colors
        if isinstance(base_color, QColor):
            base_qcolor = base_color
        else:
            base_qcolor = QColor(*base_color)
        
        if isinstance(star_color, QColor):
            star_qcolor = star_color
        else:
            star_qcolor = QColor(*star_color)
        
        try:
            # Apply base color to all keys
            for key in self.keys:
                key.setKeyColor(base_qcolor)
            
            # Initial update
            if self.keyboard.connected:
                self.app.send_config()
            
            # Run the starlight effect
            start_time = time.time()
            
            while time.time() - start_time < duration:
                # Calculate how many keys to light up
                num_stars = int(len(self.keys) * density)
                
                # Choose random keys to light up
                star_keys = random.sample(self.keys, num_stars)
                
                # Light up the stars
                for key in star_keys:
                    # Randomize brightness for variety
                    brightness = 0.5 + 0.5 * random.random()
                    r = int(star_qcolor.red() * brightness)
                    g = int(star_qcolor.green() * brightness)
                    b = int(star_qcolor.blue() * brightness)
                    key.setKeyColor(QColor(r, g, b))
                
                # Send update to keyboard
                if self.keyboard.connected:
                    self.app.send_config()
                
                # Wait a moment
                time.sleep(0.2)
                
                # Reset to base color
                for key in star_keys:
                    key.setKeyColor(base_qcolor)
                
                # Send update to keyboard
                if self.keyboard.connected:
                    self.app.send_config()
                
                # Wait a moment before next stars
                time.sleep(0.1)
            
            return True
        
        except KeyboardInterrupt:
            return False 