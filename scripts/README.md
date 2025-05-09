# Keyboard Monitoring Helper Script

This script is part of the Sinodragon keyboard configuration application and helps with system-wide keyboard monitoring.

## Purpose

The `keymon_helper.py` script enables the keyboard LED lighting to respond to modifier keys (Ctrl, Shift, Alt, etc.) even when the main application doesn't have focus.

## Requirements

- Python 3.6 or higher
- The `evdev` library (`pip install evdev`)
- Root/sudo privileges or properly configured udev rules to access input devices

## Installation

1. Make sure the script is executable:
   ```
   chmod +x keymon_helper.py
   ```

## Usage

Run the script with elevated privileges:

```
sudo ./keymon_helper.py
```

or

```
pkexec python3 keymon_helper.py
```

## How It Works

The script:

1. Creates a Unix socket at `/tmp/sinodragon_keymon.sock`
2. Uses the `evdev` library to capture keyboard events from input devices
3. Monitors only modifier key presses/releases (Ctrl, Shift, Alt, Win)
4. Sends these events via the socket to the main application
5. The main application updates the keyboard LEDs based on the key events

## Security Considerations

This script captures only key press/release events of modifier keys, not the actual keys you type. It does not log or store keystrokes.

## Troubleshooting

If the script doesn't work:

1. Make sure the main application is running
2. Check that the script is being run with elevated privileges
3. Look at the log file at `/tmp/keymon_helper.log` for errors
4. Ensure the `evdev` library is installed

## Using udev Rules (Recommended)

Instead of running the script as root, you can set up udev rules to grant input device access:

1. Create a file `/etc/udev/rules.d/99-input-permissions.rules` with:
   ```
   KERNEL=="event*", SUBSYSTEM=="input", MODE="0660", GROUP="input"
   ```

2. Add your user to the input group:
   ```
   sudo usermod -a -G input YOUR_USERNAME
   ```

3. Restart the udev service:
   ```
   sudo udevadm control --reload-rules && sudo udevadm trigger
   ```

After setting up udev rules, you can run the script without sudo privileges. 