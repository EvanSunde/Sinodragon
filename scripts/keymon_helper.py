#!/usr/bin/env python3
"""
Keyboard Monitoring Helper Script

This script runs with elevated privileges to monitor key events system-wide and
passes them to the main application using a local socket.

To use this helper:
1. Make it executable: chmod +x keymon_helper.py
2. Run with sudo: sudo ./keymon_helper.py
3. Make sure the main application is listening on the socket.

Note: For security, this script only captures key press/release events, not the actual keys.
"""

import os
import sys
import socket
import json
import argparse
import logging
import select
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='/tmp/keymon_helper.log'
)
logger = logging.getLogger('keymon_helper')

try:
    import evdev
    from evdev import InputDevice, categorize, ecodes
except ImportError:
    logger.error("Python evdev module required. Install with: pip install evdev")
    sys.exit(1)

SOCKET_PATH = '/tmp/sinodragon_keymon.sock'

# Define modifier keys we want to track (for performance)
MODIFIER_KEYS = {
    evdev.ecodes.KEY_LEFTCTRL: 'KEY_LEFTCTRL',
    evdev.ecodes.KEY_RIGHTCTRL: 'KEY_RIGHTCTRL',
    evdev.ecodes.KEY_LEFTSHIFT: 'KEY_LEFTSHIFT',
    evdev.ecodes.KEY_RIGHTSHIFT: 'KEY_RIGHTSHIFT',
    evdev.ecodes.KEY_LEFTALT: 'KEY_LEFTALT',
    evdev.ecodes.KEY_RIGHTALT: 'KEY_RIGHTALT',
    evdev.ecodes.KEY_LEFTMETA: 'KEY_LEFTMETA',
    evdev.ecodes.KEY_RIGHTMETA: 'KEY_RIGHTMETA'
}

def find_keyboard_devices():
    """Find all keyboard input devices"""
    devices = []
    logger.info("Searching for keyboard devices...")
    
    for path in evdev.list_devices():
        try:
            device = InputDevice(path)
            # Check if it's a keyboard (has key events)
            if evdev.ecodes.EV_KEY in device.capabilities():
                logger.info(f"Found keyboard device: {device.name} at {path}")
                devices.append(device)
        except (PermissionError, OSError) as e:
            logger.error(f"Could not open input device {path}: {e}")
            
    return devices

def send_event_to_app(event_type, key_code):
    """Send an event to the main application via socket"""
    try:
        # Create a socket connection
        client_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client_socket.connect(SOCKET_PATH)
        
        # Create event data
        event_data = {
            'event': event_type,  # 'press' or 'release'
            'key_code': key_code,
            'timestamp': datetime.now().timestamp()
        }
        
        # Send event as JSON
        message = json.dumps(event_data)
        client_socket.sendall(message.encode('utf-8'))
        client_socket.close()
        
        return True
    except Exception as e:
        logger.error(f"Failed to send event to application: {e}")
        return False

def monitor_keyboard_events():
    """Monitor keyboard events and forward them to the main application"""
    # Find all keyboard devices
    keyboard_devices = find_keyboard_devices()
    
    if not keyboard_devices:
        logger.error("No keyboard devices found. Ensure you have permission to access input devices.")
        return
    
    logger.info(f"Monitoring {len(keyboard_devices)} keyboard devices...")
    
    try:
        # Monitor forever (until interrupted)
        while True:
            # Use select to wait for events with a timeout
            r, w, x = select.select(keyboard_devices, [], [], 0.1)
            
            # Process events from devices that are ready
            for device in r:
                try:
                    for event in device.read():
                        # Only process key events
                        if event.type == evdev.ecodes.EV_KEY:
                            key_event = categorize(event)
                            
                            # Only track modifier keys for performance
                            if key_event.scancode in MODIFIER_KEYS:
                                key_code = MODIFIER_KEYS[key_event.scancode]
                                
                                # Handle key down event (value 1)
                                if key_event.keystate == key_event.key_down:
                                    logger.debug(f"Modifier key press: {key_code}")
                                    send_event_to_app('press', key_code)
                                
                                # Handle key up event (value 0)
                                elif key_event.keystate == key_event.key_up:
                                    logger.debug(f"Modifier key release: {key_code}")
                                    send_event_to_app('release', key_code)
                except Exception as e:
                    logger.error(f"Error reading from device: {e}")
    
    except KeyboardInterrupt:
        logger.info("Keyboard monitoring stopped by user.")
    except Exception as e:
        logger.error(f"Error in monitoring loop: {e}")

def attempt_elevated_monitoring():
    """Attempt to run the helper script with elevated privileges if needed"""
    if os.geteuid() != 0:
        logger.warning("Not running as root - checking if input devices are accessible")
        
        # Test if we can access any keyboard devices without root
        devices = find_keyboard_devices()
        if devices:
            logger.info(f"Found {len(devices)} accessible keyboard devices - udev rules appear to be working")
            return True
        
        logger.warning("No accessible input devices found - attempting to gain elevated privileges")
        
        # Try to re-run this script with pkexec or sudo
        executable = sys.executable
        script_path = os.path.abspath(__file__)
        
        # Format the same command line arguments
        args = sys.argv[1:]
        
        try:
            # Try pkexec first
            logger.info("Attempting to elevate privileges with pkexec...")
            os.execvp('pkexec', ['pkexec', executable, script_path] + args)
        except Exception as e:
            logger.error(f"Failed to elevate with pkexec: {e}")
            
            try:
                # Try sudo as fallback
                logger.info("Attempting to elevate privileges with sudo...")
                os.execvp('sudo', ['sudo', executable, script_path] + args)
            except Exception as e:
                logger.error(f"Failed to elevate with sudo: {e}")
                return False
    
    return True  # Already running as root

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Keyboard monitoring helper that requires elevated privileges')
    parser.add_argument('--socket', type=str, default=SOCKET_PATH, help='Path to the Unix socket for communication')
    args = parser.parse_args()
    
    global SOCKET_PATH
    SOCKET_PATH = args.socket
    
    # Check if we can monitor keyboards
    if not attempt_elevated_monitoring():
        logger.error("Unable to gain access to input devices. Either run as root or set up udev rules.")
        print("Error: Could not access input devices. Please run with sudo or set up udev rules.")
        sys.exit(1)
    
    # Start monitoring
    logger.info("Starting keyboard monitoring helper...")
    monitor_keyboard_events()

if __name__ == "__main__":
    main() 