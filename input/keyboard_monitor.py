import os
import threading
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QObject
from pynput import keyboard as pynput_keyboard

from ui.custom_events import CustomKeyEvent

class KeyboardMonitor(QObject):
    def __init__(self, parent):
        super().__init__(parent)
        self.app = parent
        self.global_listener = None
        self.global_keys_pressed = set()
    
    def start_global_shortcut_monitor(self):
        """Start global shortcut monitoring with Wayland compatibility"""
        if hasattr(self, 'global_listener') and self.global_listener:
            return  # Already monitoring
        
        self.global_keys_pressed = set()
        
        # Check if running on Wayland
        wayland_session = 'WAYLAND_DISPLAY' in os.environ
        
        if wayland_session:
            self.app.statusBar().showMessage("Wayland detected: using compatible input monitoring")
            
            try:
                # For Wayland we need a different approach
                # We'll use evdev for direct input device monitoring
                from evdev import InputDevice, categorize, ecodes, list_devices
                
                # For evdev we need to find the keyboard device
                def setup_evdev_monitor():
                    devices = [InputDevice(path) for path in list_devices()]
                    keyboards = []
                    
                    for device in devices:
                        if "keyboard" in device.name.lower() or any(key in device.capabilities() for key in [ecodes.EV_KEY]):
                            keyboards.append(device)
                    
                    if not keyboards:
                        self.app.statusBar().showMessage("No keyboard devices found for monitoring")
                        return False
                    
                    # Monitor all keyboard devices
                    for keyboard in keyboards:
                        # Start a thread for each keyboard
                        thread = threading.Thread(
                            target=self.evdev_monitor_thread,
                            args=(keyboard,),
                            daemon=True
                        )
                        thread.start()
                    
                    self.app.statusBar().showMessage(f"Monitoring {len(keyboards)} keyboard input devices")
                    return True
                
                # Start evdev monitoring in a separate thread
                threading.Thread(target=setup_evdev_monitor, daemon=True).start()
                self.global_listener = True  # Just a flag to indicate monitoring is active
                
            except ImportError:
                self.app.statusBar().showMessage("Wayland support requires 'evdev' package. Using fallback method.")
                self._setup_fallback_monitor()
        else:
            # X11 or other systems: use pynput
            self._setup_fallback_monitor()
    
    def evdev_monitor_thread(self, device):
        """Monitor a keyboard device with evdev"""
        try:
            from evdev import categorize, ecodes
            
            # Map evdev keycodes to our key names
            key_map = {
                ecodes.KEY_ESC: "Esc",
                ecodes.KEY_TAB: "Tab",
                ecodes.KEY_LEFTCTRL: "Ctrl", 
                ecodes.KEY_RIGHTCTRL: "Ctrl",
                ecodes.KEY_LEFTSHIFT: "Shift",
                ecodes.KEY_RIGHTSHIFT: "Shift",
                ecodes.KEY_LEFTALT: "Alt",
                ecodes.KEY_RIGHTALT: "Alt",
                ecodes.KEY_LEFTMETA: "Win",
                ecodes.KEY_RIGHTMETA: "Win",
                # Add letter keys
                ecodes.KEY_A: "A", ecodes.KEY_B: "B", # ... and so on for all keys
            }
            
            # Create reverse mapping for letters
            for i, letter in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
                key_map[getattr(ecodes, f'KEY_{letter}')] = letter
            
            # Create reverse mapping for function keys
            for i in range(1, 13):
                key_map[getattr(ecodes, f'KEY_F{i}')] = f'F{i}'
            
            # Create reverse mapping for number keys
            for i in range(10):
                key_map[getattr(ecodes, f'KEY_{i}')] = str(i)
            
            for event in device.read_loop():
                if event.type == ecodes.EV_KEY:
                    key_event = categorize(event)
                    keycode = key_event.scancode
                    
                    if keycode in key_map:
                        key_name = key_map[keycode]
                        
                        if key_event.keystate == 1:  # Key down
                            # Process in main thread to avoid race conditions
                            QApplication.instance().postEvent(
                                self.app, 
                                CustomKeyEvent(CustomKeyEvent.KeyPress, key_name)
                            )
                        elif key_event.keystate == 0:  # Key up
                            QApplication.instance().postEvent(
                                self.app, 
                                CustomKeyEvent(CustomKeyEvent.KeyRelease, key_name)
                            )
        
        except Exception as e:
            print(f"Evdev monitor error: {e}")
    
    def _setup_fallback_monitor(self):
        """Setup fallback monitoring with pynput"""
        def on_press(key):
            """Handle global key press events"""
            try:
                key_name = key.char.upper()
            except (AttributeError, TypeError):
                # Special key handling
                key_name = str(key).replace('Key.', '')
                
                # Map pynput keys to our key names
                key_map = {
                    'ctrl': 'Ctrl',
                    'ctrl_l': 'Ctrl', 
                    'ctrl_r': 'Ctrl',
                    'shift': 'Shift',
                    'shift_l': 'Shift',
                    'shift_r': 'Shift',
                    'alt': 'Alt',
                    'alt_l': 'Alt',
                    'alt_r': 'Alt',
                    'cmd': 'Win',
                    'cmd_l': 'Win',
                    'cmd_r': 'Win'
                }
                
                if key_name in key_map:
                    key_name = key_map[key_name]
            
            # If this is a new key press, process it
            if key_name not in self.global_keys_pressed:
                self.global_keys_pressed.add(key_name)
                # Use a thread to avoid blocking the listener
                threading.Thread(target=self.app.shortcut_lighting.handle_key_press,
                               args=(key_name,), daemon=True).start()
        
        def on_release(key):
            """Handle global key release events"""
            try:
                key_name = key.char.upper()
            except (AttributeError, TypeError):
                # Special key handling
                key_name = str(key).replace('Key.', '')
                
                # Map pynput keys to our key names
                key_map = {
                    'ctrl': 'Ctrl',
                    'ctrl_l': 'Ctrl', 
                    'ctrl_r': 'Ctrl',
                    'shift': 'Shift',
                    'shift_l': 'Shift',
                    'shift_r': 'Shift',
                    'alt': 'Alt',
                    'alt_l': 'Alt',
                    'alt_r': 'Alt',
                    'cmd': 'Win',
                    'cmd_l': 'Win',
                    'cmd_r': 'Win'
                }
                
                if key_name in key_map:
                    key_name = key_map[key_name]
            
            # Remove from pressed keys
            if key_name in self.global_keys_pressed:
                self.global_keys_pressed.remove(key_name)
                # Use a thread to avoid blocking the listener
                threading.Thread(target=self.app.shortcut_lighting.handle_key_release,
                               args=(key_name,), daemon=True).start()
        
        # Start the global key listener in a separate thread
        self.global_listener = pynput_keyboard.Listener(on_press=on_press, on_release=on_release)
        self.global_listener.start()
        self.app.statusBar().showMessage("Global shortcut monitoring active")
    
    def stop_global_shortcut_monitor(self):
        """Stop the global shortcut monitoring"""
        if hasattr(self, 'global_listener') and self.global_listener:
            if isinstance(self.global_listener, pynput_keyboard.Listener):
                self.global_listener.stop()
            self.global_listener = None
            self.global_keys_pressed = set()
            self.app.statusBar().showMessage("Global shortcut monitoring stopped")
