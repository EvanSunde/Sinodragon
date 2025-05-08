"""
System-specific monitoring utilities.
"""

import os
import subprocess
import logging

logger = logging.getLogger(__name__)

def is_wayland():
    """Check if running under Wayland"""
    return 'WAYLAND_DISPLAY' in os.environ

def is_hyprland():
    """Check if running under Hyprland window manager"""
    return 'HYPRLAND_INSTANCE_SIGNATURE' in os.environ

def get_active_window():
    """Get the active window class name across different window managers"""
    try:
        # Check if Hyprland is running (Wayland)
        if is_hyprland():
            cmd = "hyprctl activewindow | grep class | awk '{print $2}'"
            result = subprocess.check_output(cmd, shell=True, text=True).strip()
            return result
            
        # Check for X11 window managers
        elif os.environ.get('DISPLAY'):
            cmd = "xprop -id $(xprop -root _NET_ACTIVE_WINDOW | cut -d ' ' -f 5) | grep WM_CLASS | awk '{print $4}' | tr -d '\"'"
            result = subprocess.check_output(cmd, shell=True, text=True).strip()
            return result
            
        # Check for other Wayland compositors (GNOME, etc.)
        elif is_wayland():
            # This is a simplified approach - in practice more logic might be needed
            return "Unknown-Wayland"
            
        else:
            return "Unknown"
            
    except Exception as e:
        logger.error(f"Error getting active window: {e}")
        return "Unknown" 