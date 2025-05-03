"""
System monitoring functionality.
Provides methods to display system metrics on the keyboard.
"""

import psutil
import threading
import time
from PyQt5.QtGui import QColor

class SystemMonitorFeature:
    def __init__(self, keyboard_app):
        """
        Initialize the system monitor feature.
        
        Args:
            keyboard_app: The main keyboard application instance
        """
        self.app = keyboard_app
        self.keys = keyboard_app.keys
        self.keyboard = keyboard_app.keyboard
        
        # Monitor state
        self.monitoring = False
        self.monitor_thread = None
        self.update_interval = 2.0  # seconds
    
    def start_monitoring(self, metric="all", update_interval=2.0):
        """
        Start system monitoring and display on keyboard
        
        Args:
            metric: Which metric to monitor ("cpu", "ram", "battery", or "all")
            update_interval: How often to update the display in seconds
        """
        self.stop_monitoring()  # Stop any existing monitoring
        
        self.monitoring = True
        self.update_interval = update_interval
        
        # Start in a separate thread
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(metric,),
            daemon=True
        )
        self.monitor_thread.start()
        
        return True
    
    def stop_monitoring(self):
        """Stop system monitoring"""
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)
        
        # Restore default keyboard config
        self.app.load_config()
        if self.app.auto_reload and self.keyboard.connected:
            self.app.send_config()
    
    def _monitoring_loop(self, metric):
        """Background loop for monitoring and updating display"""
        try:
            while self.monitoring:
                if metric == "cpu" or metric == "all":
                    self.display_cpu_usage()
                elif metric == "ram" or metric == "all":
                    self.display_ram_usage()
                elif metric == "battery" or metric == "all":
                    self.display_battery_status()
                
                # Wait for next update
                for _ in range(int(self.update_interval * 10)):
                    if not self.monitoring:
                        break
                    time.sleep(0.1)
        except Exception as e:
            print(f"Error in system monitoring: {e}")
    
    def display_cpu_usage(self):
        """Display CPU usage on the keyboard"""
        try:
            # Get CPU usage as percentage
            cpu_percent = psutil.cpu_percent(interval=0.5)
            
            # Clear keyboard first
            self.clear_keyboard()
            
            # Decide color based on usage
            if cpu_percent < 50:
                color = QColor(0, 255, 0)  # Green for low usage
            elif cpu_percent < 80:
                color = QColor(255, 165, 0)  # Orange for medium usage
            else:
                color = QColor(255, 0, 0)  # Red for high usage
            
            # Map CPU % to function keys (F1-F12)
            # Each key represents ~8.33% (100/12)
            keys_to_light = int(round(cpu_percent / 8.33))
            keys_to_light = max(1, min(12, keys_to_light))  # Ensure at least 1, at most 12
            
            # Light up function keys based on CPU usage
            for i in range(keys_to_light):
                key_name = f"F{i+1}"
                for key in self.keys:
                    if key.key_name == key_name:
                        key.setKeyColor(color)
            
            # Show the percentage on number keys
            self._display_number(cpu_percent)
            
            # Send config to keyboard
            if self.keyboard.connected:
                self.app.send_config()
            
            return True
            
        except Exception as e:
            print(f"Error displaying CPU usage: {e}")
            return False
    
    def display_ram_usage(self):
        """Display RAM usage on the keyboard"""
        try:
            # Get memory info
            memory = psutil.virtual_memory()
            ram_percent = memory.percent
            
            # Clear keyboard first
            self.clear_keyboard()
            
            # Decide color based on usage
            if ram_percent < 50:
                color = QColor(0, 128, 255)  # Blue for low usage
            elif ram_percent < 80:
                color = QColor(128, 0, 255)  # Purple for medium usage
            else:
                color = QColor(255, 0, 128)  # Pink for high usage
            
            # Map RAM % to letter keys (Q through P)
            # Using first row of letter keys (10 keys)
            keys_to_light = int(round(ram_percent / 10))
            keys_to_light = max(1, min(10, keys_to_light))  # Ensure at least 1, at most 10
            
            # Letter row keys
            letter_row = ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"]
            
            # Light up letter keys based on RAM usage
            for i in range(keys_to_light):
                key_name = letter_row[i]
                for key in self.keys:
                    if key.key_name == key_name:
                        key.setKeyColor(color)
            
            # Show the percentage on number keys
            self._display_number(ram_percent)
            
            # Send config to keyboard
            if self.keyboard.connected:
                self.app.send_config()
            
            return True
            
        except Exception as e:
            print(f"Error displaying RAM usage: {e}")
            return False
    
    def display_battery_status(self):
        """Display battery status on the keyboard"""
        try:
            if not hasattr(psutil, "sensors_battery"):
                return False
            
            # Get battery info
            battery = psutil.sensors_battery()
            if battery is None:
                return False
            
            battery_percent = battery.percent
            charging = battery.power_plugged
            
            # Clear keyboard first
            self.clear_keyboard()
            
            # Choose color based on battery level and charging state
            if charging:
                color = QColor(0, 255, 0)  # Green when charging
            elif battery_percent > 50:
                color = QColor(0, 255, 0)  # Green for good battery
            elif battery_percent > 20:
                color = QColor(255, 165, 0)  # Orange for medium battery
            else:
                color = QColor(255, 0, 0)  # Red for low battery
            
            # Use arrow keys + WASD to make a battery icon
            battery_icon_keys = ["←", "↑", "→", "↓", "W", "A", "S", "D"]
            
            # Light up battery icon
            for key_name in battery_icon_keys:
                for key in self.keys:
                    if key.key_name == key_name:
                        key.setKeyColor(color)
            
            # Show the percentage on number keys
            self._display_number(battery_percent)
            
            # Send config to keyboard
            if self.keyboard.connected:
                self.app.send_config()
            
            return True
            
        except Exception as e:
            print(f"Error displaying battery status: {e}")
            return False
    
    def _display_number(self, number):
        """Helper to display a number on the keyboard's number row"""
        # Convert number to nearest integer
        num = int(round(number))
        
        # Handle numbers > 99
        if num > 99:
            # Show "99"
            self._light_key("9", QColor(255, 255, 255))
            self._light_key("9", QColor(255, 255, 255))
        else:
            # Display first digit
            if num >= 10:
                first_digit = num // 10
                self._light_key(str(first_digit), QColor(255, 255, 255))
            
            # Display second digit
            second_digit = num % 10
            self._light_key(str(second_digit), QColor(255, 255, 255))
    
    def _light_key(self, key_name, color):
        """Helper to light a specific key"""
        for key in self.keys:
            if key.key_name == key_name:
                key.setKeyColor(color)
                break
    
    def clear_keyboard(self):
        """Turn off all keys (set to black)"""
        for key in self.keys:
            key.setKeyColor(QColor(0, 0, 0))
        return True 