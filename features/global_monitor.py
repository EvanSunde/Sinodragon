import os
import threading
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QObject, pyqtSignal, QEvent

class CustomKeyEvent(QEvent):
    """Custom event for key presses from alternative input sources"""
    KeyPress = QEvent.Type(QEvent.registerEventType())
    KeyRelease = QEvent.Type(QEvent.registerEventType()) 
    
    def __init__(self, event_type, key_name):
        super().__init__(event_type)
        self.key_name = key_name

class GlobalMonitorFeature(QObject):
    """Handles global keyboard monitoring across different platforms"""
    
    key_pressed = pyqtSignal(str)
    key_released = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.global_listener = None
        self.global_keys_pressed = set()
        self.is_monitoring = False
    
    def start_monitor(self):
        """Start global shortcut monitoring with Wayland compatibility"""
        if self.is_monitoring or (hasattr(self, 'global_listener') and self.global_listener):
            return  # Already monitoring
        
        self.global_keys_pressed = set()
        
        # Check if running on Wayland
        wayland_session = 'WAYLAND_DISPLAY' in os.environ
        
        if wayland_session:
            if self.parent_app:
                self.parent_app.statusBar().showMessage("Wayland detected: using compatible input monitoring")
            
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
                        if self.parent_app:
                            self.parent_app.statusBar().showMessage("No keyboard devices found for monitoring")
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
                    
                    if self.parent_app:
                        self.parent_app.statusBar().showMessage(f"Monitoring {len(keyboards)} keyboard input devices")
                    return True
                
                # Start evdev monitoring in a separate thread
                threading.Thread(target=setup_evdev_monitor, daemon=True).start()
                self.global_listener = True  # Just a flag to indicate monitoring is active
                
            except ImportError:
                if self.parent_app:
                    self.parent_app.statusBar().showMessage("Wayland support requires 'evdev' package. Using fallback method.")
                self._setup_fallback_monitor()
        else:
            # X11 or other systems: use pynput
            self._setup_fallback_monitor()
        
        self.is_monitoring = True

    def evdev_monitor_thread(self, device):
        """Monitor a keyboard device with evdev"""
        try:
            from evdev import categorize, ecodes
            
            # Map evdev keycodes to our key names - ONLY MODIFIER KEYS
            modifier_key_map = {
                ecodes.KEY_LEFTCTRL: "Ctrl", 
                ecodes.KEY_RIGHTCTRL: "Ctrl",
                ecodes.KEY_LEFTSHIFT: "Shift",
                ecodes.KEY_RIGHTSHIFT: "Shift",
                ecodes.KEY_LEFTALT: "Alt",
                ecodes.KEY_RIGHTALT: "Alt",
                ecodes.KEY_LEFTMETA: "Win",
                ecodes.KEY_RIGHTMETA: "Win",
            }
            
            for event in device.read_loop():
                if event.type == ecodes.EV_KEY:
                    key_event = categorize(event)
                    keycode = key_event.scancode
                    
                    # Only process modifier keys
                    if keycode in modifier_key_map:
                        key_name = modifier_key_map[keycode]
                        
                        if key_event.keystate == 1:  # Key down
                            # Process in main thread to avoid race conditions
                            if self.parent_app:
                                QApplication.instance().postEvent(
                                    self.parent_app, 
                                    CustomKeyEvent(CustomKeyEvent.KeyPress, key_name)
                                )
                            self.key_pressed.emit(key_name)
                            self.global_keys_pressed.add(key_name)
                            
                        elif key_event.keystate == 0:  # Key up
                            if self.parent_app:
                                QApplication.instance().postEvent(
                                    self.parent_app, 
                                    CustomKeyEvent(CustomKeyEvent.KeyRelease, key_name)
                                )
                            self.key_released.emit(key_name)
                            if key_name in self.global_keys_pressed:
                                self.global_keys_pressed.remove(key_name)
        
        except Exception as e:
            print(f"Evdev monitor error: {e}")

    def stop_monitor(self):
        """Stop the global shortcut monitoring"""
        if not self.is_monitoring:
            return
            
        # Check if global_listener is an actual listener object and not a boolean
        if hasattr(self.global_listener, 'stop') and callable(self.global_listener.stop):
            self.global_listener.stop()
            self.global_listener = None
        else:
            # Just reset it if it's not a proper listener
            self.global_listener = None
        
        self.is_monitoring = False
        
        if self.parent_app:
            self.parent_app.statusBar().showMessage("Global shortcut monitoring stopped")

    def _setup_fallback_monitor(self):
        """Setup fallback monitoring with pynput"""
        try:
            from pynput import keyboard as pynput_keyboard
            
            def on_press(key):
                """Handle global key press events"""
                try:
                    # Filter out regular character keys
                    char = key.char
                    return
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
                    
                    # Only process modifier keys
                    if key_name in key_map:
                        key_name = key_map[key_name]
                        # If this is a new key press, process it
                        if key_name not in self.global_keys_pressed:
                            self.global_keys_pressed.add(key_name)
                            # Emit signal
                            self.key_pressed.emit(key_name)
                            
                            # Use custom event
                            if self.parent_app:
                                QApplication.instance().postEvent(
                                    self.parent_app,
                                    CustomKeyEvent(CustomKeyEvent.KeyPress, key_name)
                                )
            
            def on_release(key):
                """Handle global key release events"""
                try:
                    # Filter out regular character keys
                    char = key.char
                    return
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
                    
                    # Only process modifier keys
                    if key_name in key_map:
                        key_name = key_map[key_name]
                        # Remove from pressed keys
                        if key_name in self.global_keys_pressed:
                            self.global_keys_pressed.remove(key_name)
                            # Emit signal
                            self.key_released.emit(key_name)
                            
                            # Use custom event
                            if self.parent_app:
                                QApplication.instance().postEvent(
                                    self.parent_app,
                                    CustomKeyEvent(CustomKeyEvent.KeyRelease, key_name)
                                )
            
            # Start the global key listener in a separate thread
            self.global_listener = pynput_keyboard.Listener(on_press=on_press, on_release=on_release)
            self.global_listener.start()
            
            if self.parent_app:
                self.parent_app.statusBar().showMessage("Global shortcut monitoring active (modifiers only)")
            
        except Exception as e:
            if self.parent_app:
                self.parent_app.statusBar().showMessage(f"Failed to setup keyboard monitoring: {e}") 