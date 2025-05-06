# Hyprland Support for App-Specific Shortcut Lighting

This document explains the optimized Hyprland support for app-specific shortcut lighting in the keyboard application.

## Overview

The implementation provides efficient, low-CPU usage monitoring of active windows in Hyprland to dynamically highlight keyboard shortcuts based on the currently focused application.

### Key Features

- **Socket-based Event Monitoring**: Uses Hyprland's native IPC socket to receive real-time window focus events
- **Zero Polling**: No CPU-intensive polling required - responds only to actual window changes
- **Graceful Fallbacks**: Falls back to traditional monitoring for non-Hyprland environments
- **Memory Optimizations**: Caching and batched updates to minimize resource usage

## Implementation Details

### HyprlandIPC Class

The `HyprlandIPC` class handles communication with Hyprland's IPC socket:

- Connects to Hyprland's socket at `/tmp/hypr/{HYPRLAND_INSTANCE_SIGNATURE}/.socket2.sock`
- Subscribes specifically to `activewindow` events
- Provides callbacks when window focus changes
- Implements auto-reconnection with exponential backoff
- Gracefully handles disconnections and errors

### Performance Optimizations

1. **Event-driven Architecture**: Only processes changes when window focus actually changes
2. **Deduplication**: Tracks last active window to prevent redundant updates
3. **Memory Efficiency**: Uses optimized buffer sizes for socket communication
4. **Timeouts**: Non-blocking socket operations with appropriate timeouts
5. **Error Handling**: Comprehensive error handling with appropriate logging

### AppShortcutFeature Improvements

The `AppShortcutFeature` class has been optimized for efficient operation:

1. **Configuration Management**: Separated config management from feature implementation
2. **Caching**: Pre-caches app configurations to reduce lookups
3. **Batched Updates**: Throttles keyboard updates to prevent excessive updates
4. **Efficient Data Structures**: Uses dictionaries for O(1) lookups

## Usage

The system automatically detects when running in Hyprland and selects the appropriate monitoring method:

```python
if self.is_hyprland:
    logger.info("Starting Hyprland-specific window monitoring")
    if self.start_hyprland_monitor():
        # Using efficient Hyprland monitoring
        return
    # Fall back if needed
```

## Debugging

The implementation includes extensive logging to assist with troubleshooting:

- Connection events are logged at INFO level
- Errors include detailed information
- Window focus changes are tracked with timestamps

## Future Improvements

- Support for more specific Hyprland events (like workspace changes)
- Potential optimizations for multi-monitor setups
- Additional caching strategies for complex shortcut layouts 