"""
Unified shortcut lighting feature.
Combines global shortcut monitoring with app-specific shortcut highlighting.
"""

import os
import time
import threading
import logging
import subprocess
import re
import select
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer
import json
import socket
import signal
from pathlib import Path

logger = logging.getLogger(__name__)

# Check if evdev is available
try:
    import evdev
    EVDEV_AVAILABLE = True
    logger.info("evdev library available for system-wide key monitoring")
except ImportError:
    EVDEV_AVAILABLE = False
    logger.warning("evdev library not available - limited key monitoring available")

class ShortcutLightingFeature(QObject):
    """
    Unified feature combining global shortcut highlighting with app-specific 
    shortcut highlighting for keyboard LED configuration.
    """
    # Define signals for key press/release events
    key_pressed = pyqtSignal(str)
    key_released = pyqtSignal(str)
    app_changed = pyqtSignal(str)
    
    def __init__(self, keyboard_app, config_manager):
        """
        Initialize the shortcut lighting feature with both global and app-specific
        shortcut highlighting capabilities.
        
        Args:
            keyboard_app: The main keyboard application instance
            config_manager: The configuration manager for app shortcuts
        """
        super().__init__()
        self.app = keyboard_app
        self.shortcut_manager = keyboard_app.shortcut_manager
        self.keyboard = keyboard_app.keyboard
        self.keys = keyboard_app.keys
        self.config_manager = config_manager
        
        # Monitoring states
        self.global_monitor_active = False
        self.app_monitor_active = False
        self.currently_pressed_keys = set()
        self.highlighted_keys = []
        self.stable_state = []
        self.disable_global_shortcuts = False
        
        # App-specific monitoring
        self.current_app = "Unknown"
        self.default_state = []  # Will store RGB tuples for each key
        self._currently_pressed_keys = set()
        
        # Colors configuration
        self.default_highlight_color = QColor(255, 165, 0)  # Orange
        self.modifier_colors = {
            "Ctrl": QColor(255, 100, 0),     # Orange-red
            "Shift": QColor(0, 200, 255),    # Light blue
            "Alt": QColor(200, 255, 0),      # Yellow-green
            "Win": QColor(255, 0, 255),      # Magenta
            "Fn": QColor(150, 150, 255)      # Light purple
        }
        
        # Store default lighting config name
        self.default_config_name = "Default Green"
        
        # Performance optimization fields
        self.last_highlight_update = 0
        self.highlight_refresh_rate = 0.1  # Update at most 10 times per second (increased refresh rate)
        self.key_color_cache = {}
        self.update_pending = False
        self._app_cache = {}  # Cache app-specific shortcut data for faster access
        self._last_window_check = 0
        self._window_check_interval = 0.5  # Check app changes every 0.5 seconds at most
        
        # Batch updates
        self.batch_update_timer = QTimer()
        self.batch_update_timer.setSingleShot(True)
        self.batch_update_timer.timeout.connect(self.apply_pending_updates)
        
        # Monitor thread
        self.monitor_thread = None
        
        # Initialize app cache
        self._initialize_app_cache()
        
        # Socket server variables
        self.socket_server = None
        self.socket_path = '/tmp/sinodragon_keymon.sock'
        self.socket_thread = None
        self.socket_running = False
        self.helper_process = None
        
        # Evdev key code mapping (we'll add more mappings as needed)
        self.keycode_to_name = {
            'KEY_LEFTCTRL': 'ctrl',
            'KEY_RIGHTCTRL': 'ctrl',
            'KEY_LEFTALT': 'alt',
            'KEY_RIGHTALT': 'alt',
            'KEY_LEFTSHIFT': 'shift',
            'KEY_RIGHTSHIFT': 'shift',
            'KEY_LEFTMETA': 'super',
            'KEY_RIGHTMETA': 'super',
            # Letters
            'KEY_A': 'a', 'KEY_B': 'b', 'KEY_C': 'c', 'KEY_D': 'd', 'KEY_E': 'e',
            'KEY_F': 'f', 'KEY_G': 'g', 'KEY_H': 'h', 'KEY_I': 'i', 'KEY_J': 'j',
            'KEY_K': 'k', 'KEY_L': 'l', 'KEY_M': 'm', 'KEY_N': 'n', 'KEY_O': 'o',
            'KEY_P': 'p', 'KEY_Q': 'q', 'KEY_R': 'r', 'KEY_S': 's', 'KEY_T': 't',
            'KEY_U': 'u', 'KEY_V': 'v', 'KEY_W': 'w', 'KEY_X': 'x', 'KEY_Y': 'y',
            'KEY_Z': 'z',
            # Numbers
            'KEY_1': '1', 'KEY_2': '2', 'KEY_3': '3', 'KEY_4': '4', 'KEY_5': '5',
            'KEY_6': '6', 'KEY_7': '7', 'KEY_8': '8', 'KEY_9': '9', 'KEY_0': '0',
            # Function keys
            'KEY_F1': 'f1', 'KEY_F2': 'f2', 'KEY_F3': 'f3', 'KEY_F4': 'f4',
            'KEY_F5': 'f5', 'KEY_F6': 'f6', 'KEY_F7': 'f7', 'KEY_F8': 'f8',
            'KEY_F9': 'f9', 'KEY_F10': 'f10', 'KEY_F11': 'f11', 'KEY_F12': 'f12',
            # Special keys
            'KEY_ESC': 'esc', 'KEY_TAB': 'tab', 'KEY_CAPSLOCK': 'caps lock',
            'KEY_SPACE': 'space', 'KEY_BACKSPACE': 'backspace', 'KEY_ENTER': 'enter',
            'KEY_DELETE': 'delete', 'KEY_HOME': 'home', 'KEY_END': 'end',
            'KEY_PAGEUP': 'page up', 'KEY_PAGEDOWN': 'page down',
            'KEY_UP': 'up', 'KEY_DOWN': 'down', 'KEY_LEFT': 'left', 'KEY_RIGHT': 'right',
            # Punctuation
            'KEY_MINUS': '-', 'KEY_EQUAL': '=', 'KEY_LEFTBRACE': '[', 'KEY_RIGHTBRACE': ']',
            'KEY_SEMICOLON': ';', 'KEY_APOSTROPHE': "'", 'KEY_GRAVE': '`',
            'KEY_BACKSLASH': '\\', 'KEY_COMMA': ',', 'KEY_DOT': '.', 'KEY_SLASH': '/',
        }
        
        # Set of modifier keys for performance optimization
        self.modifier_keycodes = set([
            'KEY_LEFTCTRL', 'KEY_RIGHTCTRL',
            'KEY_LEFTALT', 'KEY_RIGHTALT',
            'KEY_LEFTSHIFT', 'KEY_RIGHTSHIFT',
            'KEY_LEFTMETA', 'KEY_RIGHTMETA'
        ])
        
        # Evdev monitor thread
        self.evdev_thread = None
        self.evdev_running = False

        # Add global variable to track if we're using evdev directly
        self.using_direct_evdev = False
        
    def _initialize_app_cache(self):
        """Initialize cache of app-specific shortcut data for better performance"""
        self._app_cache = {}
        
        # Pre-cache existing app configurations
        for app_name, shortcuts in self.config_manager.app_shortcuts.items():
            self._app_cache[app_name] = {
                'shortcuts': shortcuts,
                'color': self.config_manager.app_colors.get(app_name, self.config_manager.default_color),
                'has_default_keys': 'default_keys' in shortcuts and shortcuts['default_keys']
            }
    
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
    
    #-------------------------------
    # Global shortcut highlighting
    #-------------------------------
    
    def start_global_monitor(self):
        """Start monitoring global shortcuts."""
        if self.global_monitor_active:
            return
            
        self.global_monitor_active = True
        
        # Save current state before activating global monitoring
        self.save_stable_state()
        self.global_color_cache = {}
        
        # Start evdev monitoring if available
        if EVDEV_AVAILABLE:
            try:
                # Start evdev monitoring in a thread
                self.evdev_running = True
                self.evdev_thread = threading.Thread(target=self._evdev_monitoring_loop, daemon=True)
                self.evdev_thread.start()
                self.using_direct_evdev = True
                return
            except Exception as e:
                logger.error(f"Failed to start evdev monitoring: {e}")
                self.evdev_running = False
                self.using_direct_evdev = False
        
        # Fall back to socket-based monitoring if evdev direct access fails
        # Start socket server to receive key events
        self._start_socket_server()
        
        # Try to start the helper script with elevated privileges
        self._start_helper_script()
            
        # Apply initial highlights (if any pre-defined shortcuts exist)
        self.update_key_highlights()
    
    def stop_global_monitor(self):
        """Stop monitoring global shortcuts."""
        if not self.global_monitor_active:
            return
        
        self.global_monitor_active = False
        self.currently_pressed_keys.clear()
        
        # Stop evdev monitoring if active
        if self.evdev_running:
            self.evdev_running = False
            if self.evdev_thread and self.evdev_thread.is_alive():
                # Wait for the thread to finish
                self.evdev_thread.join(1.0)  # Wait up to 1 second
            self.evdev_thread = None
        
        # Stop socket server if running
        self._stop_socket_server()
        
        # Kill helper process if running
        self._stop_helper_script()
        
        # Restore previous stable state if no app-specific monitoring
        if not self.app_monitor_active:
            self.restore_stable_state()
        else:
            # Just update the key highlights for the current application
            self.update_key_highlights()
    
    def _evdev_monitoring_loop(self):
        """Monitor keyboard events directly using evdev library without root access"""
        import evdev
        from evdev import InputDevice, categorize, ecodes
        import select
        
        try:
            # Find keyboard devices accessible without root (thanks to udev rules)
            devices = []
            for path in evdev.list_devices():
                try:
                    device = InputDevice(path)
                    capabilities = device.capabilities()
                    if ecodes.EV_KEY in capabilities:
                        devices.append(device)
                except (PermissionError, OSError):
                    pass
            
            if not devices:
                logger.error("No usable keyboard devices found - check udev rules")
                return
            
            # Monitor keyboard events
            while self.evdev_running:
                # Use select to wait for events with a timeout
                r, w, x = select.select(devices, [], [], 0.1)
                
                # Process events from devices that are ready
                for device in r:
                    try:
                        for event in device.read():
                            # Only process key events
                            if event.type == ecodes.EV_KEY:
                                key_event = categorize(event)
                                key_code = key_event.keycode
                                
                                # We're only interested in modifier keys for performance
                                if isinstance(key_code, str) and key_code in self.modifier_keycodes:
                                    if key_event.keystate == 1:  # Key down
                                        key_name = self.keycode_to_name.get(key_code, key_code)
                                        self._handle_key_press(key_name)
                                    elif key_event.keystate == 0:  # Key up
                                        key_name = self.keycode_to_name.get(key_code, key_code)
                                        self._handle_key_release(key_name)
                    except Exception:
                        pass
        
        except Exception as e:
            logger.error(f"Error in evdev monitoring loop: {e}")
            
        finally:
            self.evdev_running = False
    
    def _start_socket_server(self):
        """Start a socket server to receive key events from the helper script."""
        if self.socket_running:
            return
            
        # Make sure socket path doesn't exist
        try:
            if os.path.exists(self.socket_path):
                os.unlink(self.socket_path)
        except OSError:
            return
            
        try:
            # Create socket server
            self.socket_server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.socket_server.bind(self.socket_path)
            self.socket_server.listen(5)
            self.socket_server.setblocking(False)
            
            # Set socket permissions so helper script can connect
            os.chmod(self.socket_path, 0o777)
            
            # Start listening thread
            self.socket_running = True
            self.socket_thread = threading.Thread(target=self._socket_listening_loop)
            self.socket_thread.daemon = True
            self.socket_thread.start()
        except Exception as e:
            logger.error(f"Failed to start socket server: {e}")
            self.socket_running = False
            
    def _stop_socket_server(self):
        """Stop the socket server."""
        if not self.socket_running:
            return
            
        self.socket_running = False
        
        # Wait for thread to end
        if self.socket_thread and self.socket_thread.is_alive():
            self.socket_thread.join(1.0)  # Wait up to 1 second
            
        # Close socket
        if self.socket_server:
            try:
                self.socket_server.close()
            except Exception:
                pass
            
        # Remove socket file
        try:
            if os.path.exists(self.socket_path):
                os.unlink(self.socket_path)
        except OSError:
            pass
    
    def _socket_listening_loop(self):
        """Socket listening thread to receive key events from helper script."""
        while self.socket_running:
            try:
                # Wait for data with timeout
                ready_to_read, _, _ = select.select([self.socket_server], [], [], 0.1)
                
                if self.socket_server in ready_to_read:
                    # Accept connection
                    client_sock, _ = self.socket_server.accept()
                    client_sock.settimeout(0.5)
                    
                    # Receive data
                    data = client_sock.recv(1024).decode('utf-8')
                    client_sock.close()
                    
                    if data:
                        # Process received event
                        try:
                            event_data = json.loads(data)
                            self._process_key_event(event_data)
                        except json.JSONDecodeError:
                            pass
                        except Exception:
                            pass
            
            except Exception:
                time.sleep(0.1)  # Prevent tight loop on error
    
    def _process_key_event(self, event_data):
        """Process key event received from the helper script.
        
        Args:
            event_data: Dict with keys 'event', 'key_code', and 'timestamp'
        """
        event_type = event_data.get('event')
        key_code = event_data.get('key_code')
        
        if not event_type or not key_code:
            return
            
        # Convert key code to key name
        key_name = self._convert_keycode_to_name(key_code)
        if not key_name:
            return
            
        # Process key press/release
        if event_type == 'press':
            self._handle_key_press(key_name)
        elif event_type == 'release':
            self._handle_key_release(key_name)
    
    def _convert_keycode_to_name(self, key_code):
        """Convert evdev key code to key name used in our application."""
        # Handle case where key_code is a list
        if isinstance(key_code, list):
            key_code = key_code[0] if key_code else None
            
        # Return mapped key name if available
        return self.keycode_to_name.get(key_code, None)
    
    def _start_helper_script(self):
        """Attempt to start the helper script with elevated privileges."""
        if self.helper_process and self.helper_process.poll() is None:
            # Process is already running
            return
            
        # Check if helper script exists
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                   'scripts', 'keymon_helper.py')
        
        if not os.path.exists(script_path):
            return
            
        # Make helper script executable
        try:
            os.chmod(script_path, 0o755)
        except OSError:
            pass
            
        # Try to run helper script with pkexec or gksudo
        try:
            # First try pkexec (standard on many distributions)
            cmd = ['pkexec', 'python3', script_path, f'--socket={self.socket_path}']
            
            # Run script and detach
            self.helper_process = subprocess.Popen(cmd,
                                                  stdout=subprocess.PIPE,
                                                  stderr=subprocess.PIPE,
                                                  start_new_session=True)
        except Exception as e:
            logger.error(f"Failed to start helper script: {e}")
            
    def _stop_helper_script(self):
        """Stop the helper script if it's running."""
        if not self.helper_process:
            return
            
        # Check if process is still running
        if self.helper_process.poll() is None:
            try:
                # Try graceful termination
                os.killpg(os.getpgid(self.helper_process.pid), signal.SIGTERM)
                
                # Wait briefly for process to terminate
                time.sleep(0.5)
                
                # Force kill if still running
                if self.helper_process.poll() is None:
                    os.killpg(os.getpgid(self.helper_process.pid), signal.SIGKILL)
            except Exception:
                pass
                
        self.helper_process = None
    
    def handle_key_press(self, key_name):
        """Handle a key press event"""
        # Skip if already pressed (prevents multiple rapid updates for same key)
        if key_name in self.currently_pressed_keys:
            return
            
        # Record key in pressed keys
        self.currently_pressed_keys.add(key_name)
        
        # Check if app-specific shortcuts should handle this
        if self.app_monitor_active:
            # Try to handle with app-specific shortcuts first
            if self.handle_app_key_press(key_name):
                # Successfully handled by app-specific shortcuts
                # Emit signal for potential listeners anyway
                self.key_pressed.emit(key_name)
                return
            
            # Check if global shortcuts should be disabled for this app
            if self.should_disable_global_shortcuts(key_name):
                return
        
        # Process global shortcut highlighting if enabled
        if self.global_monitor_active:
            # Emit signal for external listeners
            self.key_pressed.emit(key_name)
            # Update the key highlights
            self.update_key_highlights()
    
    def handle_key_release(self, key_name):
        """Handle a key release event"""
        # Remove from pressed keys
        if key_name in self.currently_pressed_keys:
            self.currently_pressed_keys.remove(key_name)
        
        # Check if app-specific shortcuts should handle this
        if self.app_monitor_active:
            # Try to handle with app-specific shortcuts first
            if self.handle_app_key_release(key_name):
                # Successfully handled by app-specific shortcuts
                # Emit signal for potential listeners anyway
                self.key_released.emit(key_name)
                return
        
        # Process global shortcut release if global monitoring is enabled
        if self.global_monitor_active:
            # Emit signal for external listeners
            self.key_released.emit(key_name)
            
            # Only restore colors if no keys are pressed
            if not self.currently_pressed_keys:
                self.restore_stable_state()
            else:
                # Update highlights with remaining keys
                self.update_key_highlights()
    
    def update_key_highlights(self):
        """
        Highlight keys based on current state. Throttled to prevent excessive update.
        """
        # Strict throttling to prevent keyboard resets
        current_time = time.time()
        if current_time - self.last_highlight_update < self.highlight_refresh_rate * 2:  # Double the delay
            self.update_pending = True
            if not self.batch_update_timer.isActive():
                # Set a longer delay for the batch update
                self.batch_update_timer.start(int(self.highlight_refresh_rate * 2000))
            return
        
        # Mark that we're updating now
        self.last_highlight_update = current_time
        self.update_pending = False
        
        # Short circuit if no monitoring active
        if not (self.global_monitor_active or self.app_monitor_active):
            return
        
        # Convert the set of pressed keys to a list
        pressed_keys = list(self.currently_pressed_keys)
        
        # If only modifiers are pressed, limit to just highlighting the modifiers themselves
        only_modifiers = True
        for key in pressed_keys:
            if key.lower() not in ["ctrl", "shift", "alt", "win", "super", "meta"]:
                only_modifiers = False
                break
        
        # Create a list to hold all the keys that should be highlighted
        keys_to_highlight = []
        
        # Special case for just modifiers - don't request full shortcut highlighting
        if only_modifiers and len(pressed_keys) <= 2:  # 1 or 2 modifiers only
            keys_to_highlight = pressed_keys
        else:
            # Get the keys to highlight from the shortcut manager
            try:
                # Call the correct method get_keys_to_highlight on the shortcut_manager
                keys_to_highlight = self.shortcut_manager.get_keys_to_highlight(pressed_keys)
                
                # Make sure modifiers themselves are always included
                for key in pressed_keys:
                    if key not in keys_to_highlight and key.lower() in ["ctrl", "shift", "alt", "win"]:
                        keys_to_highlight.append(key)
                        
                # Limit number of highlighted keys to prevent keyboard overload
                if len(keys_to_highlight) > 10:
                    # Keep modifiers and limit other keys
                    modifiers = [k for k in keys_to_highlight if k.lower() in ["ctrl", "shift", "alt", "win"]]
                    others = [k for k in keys_to_highlight if k.lower() not in ["ctrl", "shift", "alt", "win"]]
                    keys_to_highlight = modifiers + others[:8]  # Keep all modifiers plus up to 8 other keys
                    
            except Exception:
                # If there's an error, just highlight the pressed modifiers
                keys_to_highlight = [key for key in pressed_keys if key.lower() in ["ctrl", "shift", "alt", "win"]]
        
        # Clear keyboard first to ensure a clean state
        self.clear_keyboard()
        
        # First highlight modifier keys with their specific colors
        for mod_key in ["Ctrl", "Shift", "Alt", "Win"]:
            mod_lower = mod_key.lower()
            pressed_mod = False
            for pressed in pressed_keys:
                if pressed.lower() == mod_lower:
                    pressed_mod = True
                    break
                    
            if pressed_mod:
                mod_color = self.modifier_colors.get(mod_key, self.default_highlight_color)
                self._highlight_key(mod_key, mod_color)
                
        # Then highlight other keys with default highlight color
        for key_name in keys_to_highlight:
            if key_name.lower() not in ["ctrl", "shift", "alt", "win"]:
                self._highlight_key(key_name, self.default_highlight_color)
        
        # Send the colors to the keyboard using a more robust method
        self._send_keyboard_config_safely()
        
    def _send_keyboard_config_safely(self):
        """Send the current keyboard color configuration to the physical keyboard with error handling"""
        try:
            # Create color list from current key colors
            color_list = []
            for key in self.keys:
                color = key.color
                color_list.append((color.red(), color.green(), color.blue()))
            
            # Try multiple methods to send the configuration
            if self.keyboard.connected:
                try:
                    # First try with direct method and full intensity
                    self.keyboard.send_led_config(color_list, 1.0)
                    return True
                except Exception:
                    # Try alternative methods
                    try:
                        if hasattr(self.app, 'send_config'):
                            self.app.send_config()
                            return True
                        elif hasattr(self.app, 'keyboard') and hasattr(self.app.keyboard, 'send_led_config'):
                            self.app.keyboard.send_led_config(color_list, 1.0)
                            return True
                    except Exception:
                        # If all methods fail, add a delay to prevent rapid retries
                        time.sleep(0.1)
                        return False
            else:
                # If not connected, don't try to reconnect here - it's better to let the
                # main application handle reconnection logic
                return False
        except Exception:
            # Catch all exceptions to prevent crashes
            return False
    
    def toggle_global_monitoring(self, state=None):
        """
        Toggle global shortcut monitoring on/off
        
        Args:
            state: Optional boolean to explicitly set the state. 
                   If None, the current state is toggled.
        """
        if state is None:
            # Toggle current state
            if self.global_monitor_active:
                self.stop_global_monitor()
            else:
                self.start_global_monitor()
        elif state and not self.global_monitor_active:
            # Explicitly turn monitoring on
            self.start_global_monitor()
        elif not state and self.global_monitor_active:
            # Explicitly turn monitoring off
            self.stop_global_monitor()
            
        return self.global_monitor_active
    
    def apply_pending_updates(self):
        """Apply any updates that were throttled due to update_interval"""
        if self.update_pending:
            self.update_key_highlights()
    
    def save_stable_state(self):
        """Save the current keyboard state as the stable state"""
        self.stable_state = []
        for key in self.keys:
            color = key.color
            self.stable_state.append((color.red(), color.green(), color.blue()))
    
    def restore_stable_state(self):
        """Restore to the last stable state"""
        try:
            # Check if we have a saved stable state
            if not self.stable_state:
                self.restore_default_config()
                return
            
            # Restore UI key colors
            for i, key in enumerate(self.keys):
                if i < len(self.stable_state):
                    r, g, b = self.stable_state[i]
                    key.setKeyColor(QColor(r, g, b))
            
            # Send to keyboard if connected
            if self.keyboard.connected:
                self.keyboard.send_led_config(self.stable_state)
                
            return True
        except Exception:
            # Fallback to default configuration
            self.restore_default_config()
            return False
    
    def restore_default_config(self):
        """Restore to default lighting configuration"""
        try:
            # Just load the default configuration
            self.app.load_config(self.default_config_name)
            
            # If auto-reload is on, send the updated colors to the keyboard
            if self.app.auto_reload and self.keyboard.connected:
                self.app.send_config()
                
            return True
        except Exception:
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
            except Exception:
                return False
    
    #-------------------------------
    # App-specific shortcut highlighting
    #-------------------------------
    
    def start_app_monitor(self):
        """Start monitoring for application-specific shortcuts"""
        if self.app_monitor_active:
            return
            
        self.app_monitor_active = True
        self._currently_pressed_keys.clear()
        
        # Start monitor thread
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.monitor_thread.start()
        
        # Enable app-specific shortcuts
        self.disable_global_shortcuts = True
    
    def stop_app_monitor(self):
        """Stop monitoring for application-specific shortcuts"""
        self.app_monitor_active = False
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)
            
        # Re-enable global shortcuts
        self.disable_global_shortcuts = False
        
        # Restore keyboard to stable state
        if not self.global_monitor_active:
            self.restore_stable_state()
        else:
            # If global monitoring is active, update to show global highlights
            self.update_key_highlights()
    
    def _monitoring_loop(self):
        """Background thread to monitor active application and update shortcuts"""
        last_check_time = 0
        
        while self.app_monitor_active:
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
                    # Save current state before switching
                    if self.current_app != "Unknown":
                        self.save_stable_state()
                    
                    # Update current app
                    prev_app = self.current_app
                    self.current_app = app_name
                    
                    # Emit signal for potential subscribers
                    self.app_changed.emit(app_name)
                    
                    # Apply app-specific shortcuts
                    self.apply_app_shortcuts(app_name)
                    
            except Exception:
                time.sleep(1.0)  # Prevent rapid error looping
    
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
                return "Unknown"
                
            else:
                return "Unknown"
                
        except Exception:
            return "Unknown"
    
    def apply_app_shortcuts(self, app_name):
        """Apply application-specific shortcuts to the keyboard"""
        try:
            # Connect to keyboard if not connected
            if not self.keyboard.connected:
                try:
                    if hasattr(self.app, 'connect_to_keyboard'):
                        self.app.connect_to_keyboard()
                    else:
                        self.keyboard.connect()
                except Exception:
                    pass
            
            # Check if we have app-specific shortcuts
            if app_name in self._app_cache:
                # Try applying app-specific shortcuts
                result = self._apply_app_specific_shortcuts(app_name)
                if result:
                    return True
                else:
                    # Fall back to default state
                    self.restore_stable_state()
                    return False
            else:
                # Save current state as default if not done already
                if not self.stable_state:
                    self.save_stable_state()
                return False
        except Exception:
            # Try to restore to default state as a last resort
            self.restore_stable_state()
            return False
    
    def _apply_app_specific_shortcuts(self, app_name):
        """Apply app-specific shortcuts for the given application"""
        try:
            # Clear keyboard first
            self.clear_keyboard()
            
            # Get app-specific color and shortcuts
            highlight_color = self._app_cache[app_name]['color']
            shortcuts = self._app_cache[app_name]['shortcuts']
            has_default_keys = self._app_cache[app_name]['has_default_keys']
            
            if has_default_keys and shortcuts.get("default_keys"):
                # Apply highlighting to each key
                for key_name in shortcuts["default_keys"]:
                    if key_name:
                        self._highlight_key(key_name, highlight_color)
                
                # Send to keyboard with explicit RGB format
                color_list = []
                for key in self.keys:
                    color = key.color
                    color_list.append((color.red(), color.green(), color.blue()))
                
                # Send with explicit intensity of 1.0
                if self.keyboard.connected:
                    try:
                        # First try with direct method
                        self.keyboard.send_led_config(color_list, 1.0)
                        return True
                    except Exception:
                        # Try alternative method through the app
                        try:
                            if hasattr(self.app, 'send_config'):
                                self.app.send_config()
                                return True
                            elif hasattr(self.app, 'keyboard') and hasattr(self.app.keyboard, 'send_led_config'):
                                self.app.keyboard.send_led_config(color_list, 1.0)
                                return True
                            else:
                                return False
                        except Exception:
                            return False
                else:
                    # Last attempt to connect
                    try:
                        if hasattr(self.app, 'connect_to_keyboard'):
                            if self.app.connect_to_keyboard():
                                self.keyboard.send_led_config(color_list, 1.0)
                                return True
                        elif hasattr(self.keyboard, 'connect'):
                            if self.keyboard.connect():
                                self.keyboard.send_led_config(color_list, 1.0)
                                return True
                    except Exception:
                        pass
                    
                    return False
            else:
                # If no default keys, restore to last stable state
                self.restore_stable_state()
                return False
                
        except Exception:
            # Try to restore default state on error
            self.restore_stable_state()
            return False
    
    def _highlight_key(self, key_name, color):
        """
        Highlight a specific key with the given color
        
        Args:
            key_name: The name of the key to highlight
            color: QColor object for the highlight color
        
        Returns:
            True if key was found and highlighted, False otherwise
        """
        # Skip empty key names
        if not key_name:
            return False
            
        # Convert tuple to QColor if needed
        if not isinstance(color, QColor):
            if isinstance(color, (list, tuple)) and len(color) >= 3:
                color = QColor(color[0], color[1], color[2])
            else:
                return False
        
        # Check if the keys list is initialized
        if not self.keys:
            # Try to get keys from keyboard_app if available
            if hasattr(self.app, 'keys') and self.app.keys:
                self.keys = self.app.keys
            else:
                return False
        
        # Normalize the key name for more flexible matching
        normalized_key_name = key_name.strip()
        normalized_lower = normalized_key_name.lower()
        
        # Try to build a map between controller key names and UI key names if we haven't already
        if not hasattr(self, '_key_name_map') or not self._key_name_map:
            # Create a mapping between physical layout names and UI key objects
            self._key_name_map = {}
            
            # First, build a set of all UI key names and their normalizations
            if self.keys:
                for key in self.keys:
                    if hasattr(key, 'key_name'):
                        # Map key name to itself for direct lookups
                        self._key_name_map[key.key_name] = key
                        self._key_name_map[key.key_name.lower()] = key
            
            # Add simplified mappings for common keys
            self._add_simplified_mappings()
        
        # Now use our map to find the key to highlight
        if normalized_key_name in self._key_name_map:
            ui_key = self._key_name_map[normalized_key_name]
            ui_key.setKeyColor(color)
            return True
        
        # Try lowercase lookup
        if normalized_lower in self._key_name_map:
            ui_key = self._key_name_map[normalized_lower]
            ui_key.setKeyColor(color)
            return True
        
        # For letter keys, try both uppercase and lowercase
        if len(normalized_key_name) == 1 and normalized_key_name.isalpha():
            alt_key_name = normalized_key_name.upper() if normalized_key_name.islower() else normalized_key_name.lower()
            if alt_key_name in self._key_name_map:
                ui_key = self._key_name_map[alt_key_name]
                ui_key.setKeyColor(color)
                return True
        
        # Fall back to direct search if mapping didn't work
        # Try exact match first (with original case)
        for key in self.keys:
            if hasattr(key, 'key_name') and key.key_name == normalized_key_name:
                # Apply the color
                key.setKeyColor(color)
                return True
        
        # Try case-insensitive match
        for key in self.keys:
            if hasattr(key, 'key_name') and key.key_name.lower() == normalized_lower:
                # Apply the color
                key.setKeyColor(color)
                return True
        
        # Special handling for function keys 
        if normalized_lower.startswith('f') and len(normalized_lower) <= 3:
            # Check if it's F1-F12
            try:
                num = int(normalized_lower[1:])
                if 1 <= num <= 12:
                    # Try to find the key as "F1", "F2", etc.
                    function_key_name = f"F{num}"
                    for key in self.keys:
                        if hasattr(key, 'key_name') and key.key_name == function_key_name:
                            key.setKeyColor(color)
                            return True
            except ValueError:
                pass
                    
        return False
    
    def _add_simplified_mappings(self):
        """Add simplified mappings for common keys to improve performance"""
        # Common modifier key mappings
        self._key_name_map.update({
            'ctrl': self._find_key_by_name('Ctrl'),
            'control': self._find_key_by_name('Ctrl'),
            'shift': self._find_key_by_name('Shift'),
            'alt': self._find_key_by_name('Alt'),
            'win': self._find_key_by_name('Win'),
            'super': self._find_key_by_name('Win'),
            'meta': self._find_key_by_name('Win')
        })
        
    def _find_key_by_name(self, key_name):
        """Helper to find a key object by name"""
        for key in self.keys:
            if hasattr(key, 'key_name'):
                if key.key_name == key_name or key.key_name.lower() == key_name.lower():
                    return key
        return None
    
    def handle_app_key_press(self, key_name):
        """Handle a key press event for app-specific shortcuts"""
        if not self.app_monitor_active or not self.current_app:
            return False  # Not handled
        
        if self.current_app not in self._app_cache:
            return False  # No app shortcuts defined
        
        try:
            # Add key to tracking set
            self._currently_pressed_keys.add(key_name)
            
            # Get the list of currently pressed modifier keys
            pressed_modifiers = list(self.currently_pressed_keys)
            
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
                
                # Check if we have this modifier combination for the current app
                shortcuts = self._app_cache[self.current_app]['shortcuts']
                
                # Try exact match first
                if modifiers_key in shortcuts:
                    # We found an app-specific shortcut for this modifier combo!
                    self._highlight_app_shortcut_keys(modifiers_key, shortcuts[modifiers_key])
                    return True  # Handled by app-specific shortcuts
                
                # Try case-insensitive match
                for shortcut_key in shortcuts:
                    if shortcut_key.lower() == modifiers_key.lower() and shortcut_key != "default_keys":
                        self._highlight_app_shortcut_keys(shortcut_key, shortcuts[shortcut_key])
                        return True
            
            # If we get here, no modifier-specific shortcuts were found
            # Check if we should apply default keys
            if "default_keys" in self._app_cache[self.current_app]['shortcuts']:
                # If modifiers are pressed but we don't have specific shortcuts for them,
                # still highlight the default keys
                self._highlight_app_shortcut_keys("default", self._app_cache[self.current_app]['shortcuts']["default_keys"])
                return True
            
            return False  # Let global shortcuts handle it
        except Exception:
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
                # Fall back to default if keys list is empty or invalid
                self.restore_stable_state()
                return
                
            # Clear keyboard first
            self.clear_keyboard()
            
            # Get app-specific color
            highlight_color = self._app_cache[self.current_app]['color']
            
            # Convert any string keys to string, strip whitespace, and filter out empty strings
            keys_to_highlight = [str(k).strip() for k in keys_to_highlight if k]
            keys_to_highlight = [k for k in keys_to_highlight if k]  # Filter out any empty strings
            
            # Check if there are disabled keys for this app
            shortcuts = self._app_cache[self.current_app]['shortcuts']
            disabled_keys = []
            if "disabled_keys" in shortcuts and shortcuts["disabled_keys"]:
                disabled_keys = [k.lower() for k in shortcuts["disabled_keys"]]
            
            # Filter out disabled keys
            if disabled_keys:
                keys_to_highlight = [k for k in keys_to_highlight if k.lower() not in disabled_keys]
            
            # If we still have no valid keys, fall back to default state
            if not keys_to_highlight:
                self.restore_stable_state()
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
                    
                    # Skip disabled modifier keys
                    if mod_name.lower() in disabled_keys:
                        continue
                    
                    # Get the color for this modifier
                    mod_color = self.get_modifier_color(mod_name)
                    self._highlight_key(mod_name, mod_color)
            
            # Highlight the specified keys
            for key in keys_to_highlight:
                if key and isinstance(key, str):
                    self._highlight_key(key, highlight_color)
            
            # Send to keyboard using the centralized method
            return self._send_keyboard_config()
                
        except Exception:
            # Fall back to default state on error
            QTimer.singleShot(100, self.restore_stable_state)
            return False
    
    def handle_app_key_release(self, key_name):
        """Handle a key release event for app-specific shortcuts"""
        try:
            # Remove key from tracking
            if key_name in self._currently_pressed_keys:
                self._currently_pressed_keys.remove(key_name)
                
            # Check if any modifiers are still pressed
            pressed_modifiers = list(self.currently_pressed_keys)
            real_modifiers = [mod for mod in pressed_modifiers if mod.lower() in ["ctrl", "shift", "alt", "win", "fn"]]
            
            # Only restore defaults if no modifiers are pressed
            if not real_modifiers:
                if self.current_app and self.current_app in self._app_cache:
                    shortcuts = self._app_cache[self.current_app]['shortcuts']
                    has_default_keys = self._app_cache[self.current_app]['has_default_keys']
                    
                    # Make sure we're still monitoring
                    if not self.app_monitor_active:
                        return False
                    
                    # Use a slightly longer delay to let key handling complete
                    # and avoid packet conflicts
                    delay = 0.1  # 100ms delay
                    
                    if has_default_keys:
                        # App has default keys - restore them
                        # Use a timer instead of a thread
                        QTimer.singleShot(int(delay * 1000), 
                            lambda: self._highlight_app_shortcut_keys("default", shortcuts["default_keys"]))
                        return True
                    else:
                        # No default keys for this app - restore to stable state
                        QTimer.singleShot(int(delay * 1000), self.restore_stable_state)
                        return True
                else:
                    # No app-specific shortcuts - restore stable state
                    # Use a slightly longer delay
                    QTimer.singleShot(100, self.restore_stable_state)
                    return True
            
            # If modifiers are still pressed, let the system handle it
            return False
            
        except Exception:
            # In case of error, restore to default state
            self.restore_stable_state()
            return False
    
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
        if not self.app_monitor_active or not self.current_app:
            return False
        
        # If we don't have shortcuts for this app, don't disable global shortcuts
        if self.current_app not in self._app_cache:
            return False
        
        # If we have app-specific shortcuts, disable global shortcuts
        return self.disable_global_shortcuts
    
    #-------------------------------
    # Utility methods
    #-------------------------------
    
    def clear_keyboard(self):
        """Turn off all keys (set to black)"""
        for key in self.keys:
            key.setKeyColor(QColor(0, 0, 0))
        return True

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
        
    def highlight_default_keys(self):
        """Highlight default keys for current app if app monitoring is active"""
        if not self.app_monitor_active or not self.current_app:
            return False
            
        # Check if we have shortcuts for this app
        if self.current_app not in self._app_cache:
            # No app shortcuts defined
            return False
        
        # Check if app has valid default keys
        shortcuts = self._app_cache[self.current_app]['shortcuts']
        has_default_keys = self._app_cache[self.current_app]['has_default_keys']
        
        if has_default_keys:
            # Apply app-specific default keys
            # Ensure default_keys is not None before highlighting
            if shortcuts["default_keys"]:
                self._highlight_app_shortcut_keys("default", shortcuts["default_keys"])
                return True
            else:
                return False
        else:
            # No default keys defined for this app
            return False

    def _handle_key_press(self, key_name):
        """Internal method to handle key press events, called from evdev monitoring.
        This delegates to the public handle_key_press method.
        """
        return self.handle_key_press(key_name)
    
    def _handle_key_release(self, key_name):
        """Internal method to handle key release events, called from evdev monitoring.
        This delegates to the public handle_key_release method.
        """
        return self.handle_key_release(key_name)

    def is_global_monitoring_active(self):
        """Returns whether global shortcut monitoring is currently active"""
        return self.global_monitor_active