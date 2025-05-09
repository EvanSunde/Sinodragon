# Keyboard Monitoring Helper Script

This directory contains helper scripts for the Sinodragon keyboard configuration application.

## System-Wide Key Monitoring

The `keymon_helper.py` script enables system-wide keyboard monitoring for highlighting keyboard shortcuts. This is needed because standard GUI applications don't have permission to monitor all keystrokes at the system level.

### Requirements

- Python 3.6+
- The `evdev` Python library (`pip install evdev`)
- Root/sudo privileges to access input devices

### Installation

Make the script executable:

```bash
chmod +x keymon_helper.py
```

### Usage

The script needs to be run with elevated privileges:

```bash
sudo ./keymon_helper.py
```

Or using pkexec (recommended for desktop environments):

```bash
pkexec python3 keymon_helper.py
```

### How It Works

1. The script creates a Unix socket at `/tmp/sinodragon_keymon.sock`
2. It uses the `evdev` library to capture keyboard events at the system level
3. When key presses/releases occur, it sends the events to the main application via the socket
4. The main application listens for these events and updates the keyboard's LEDs accordingly

### Security

- The script only captures key press/release events, not the actual keys typed
- It doesn't log or store keystrokes
- The socket is only accessible to the local user

### Troubleshooting

If the script doesn't work:

1. Check that the main application is running
2. Verify you have permission to access input devices
3. Check the log file at `/tmp/keymon_helper.log`
4. Ensure the evdev library is installed (`pip install evdev`)

For more detailed logging, edit the script and change the logging level from INFO to DEBUG. 