"""
Main window for the keyboard configuration application.
"""

import os
import logging
import time
import threading
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QSplitter, QComboBox, QLineEdit, QPushButton, QLabel,
                           QMessageBox, QAction, QMenu, QSystemTrayIcon, QApplication,
                           QColorDialog)
from PyQt5.QtCore import Qt, QTimer, QEvent
from PyQt5.QtGui import QColor
import colorsys

# Import keyboard controller and configuration 
from keyboard_controller import KeyboardController
from config_manager import ConfigManager
from shortcut_manager import ShortcutManager
# Import the new unified ShortcutLightingFeature instead of ShortcutLighting
from features.shortcut_lighting import ShortcutLightingFeature

# Import UI components
from ui.keyboard_layout import KeyboardLayout
from ui.control_panel import ControlPanel
from ui.key_mapping import QT_KEY_MAP
from ui.event_handler import CustomKeyEvent
from ui.dialogs.modifier_colors import ModifierColorsDialog

# Import features
from features.text_display import TextDisplayFeature
from features.effects import EffectsFeature
from features.system_monitor import SystemMonitorFeature
# No need to import AppShortcutFeature since it's now combined in ShortcutLightingFeature
from features.app_shortcuts import AppShortcutConfigManager

logger = logging.getLogger(__name__)

class KeyboardConfigApp(QMainWindow):
    """
    Main application window for keyboard LED configuration
    
    This application provides a user interface for configuring the RGB LED lighting
    of a keyboard. It supports various features including:
    
    - Global keyboard shortcut highlighting
    - Application-specific shortcut highlighting
    - Preset lighting configurations
    - Selection mode for region-based configuration
    - System tray integration
    
    The application uses the ShortcutLightingFeature for unified shortcut lighting,
    which combines both global and app-specific shortcut highlighting in an efficient way.
    """
    
    def __init__(self):
        super().__init__()
        
        # Initialize controllers and managers
        self.keyboard = KeyboardController()
        self.config_manager = ConfigManager()
        self.shortcut_manager = ShortcutManager()
        self.keys = []  # Will store all key buttons
        self.selected_keys = []  # For selection mode
        self.current_color = QColor(0, 255, 0)  # Default working color is green
        self.selection_mode = False
        
        # Auto-connect and auto-reload options
        self.auto_connect = True
        self.auto_reload = True
        
        # Set up reload timer
        self.reload_timer = QTimer()
        self.reload_timer.timeout.connect(self.send_config)
        
        # Save keyboard layout on first run
        layout = self.shortcut_manager.load_keyboard_layout()
        if not layout:
            self.save_keyboard_layout()
        
        # Initialize app shortcut config manager
        self.app_shortcut_config = AppShortcutConfigManager(self.shortcut_manager.config_dir)
        
        # Create the unified shortcut lighting feature
        # This combines global and app-specific shortcut handling
        self.shortcut_lighting = ShortcutLightingFeature(self, self.app_shortcut_config)
        
        # Add a timer for debouncing slider changes
        self.intensity_timer = QTimer()
        self.intensity_timer.setSingleShot(True)
        self.intensity_timer.timeout.connect(self.apply_intensity)
        
        # Set up the UI components
        self.setupUI()
        
        # Set up system tray
        self.setupSystemTray()
        
        # Load default configuration
        self.load_config()
        
        # Auto-connect to keyboard if enabled
        if self.auto_connect:
            QTimer.singleShot(500, self.connect_to_keyboard)
        
        # Install event filter to catch key events
        QApplication.instance().installEventFilter(self)
        
        # Create feature modules
        self.text_display = TextDisplayFeature(self)
        self.effects = EffectsFeature(self)
        
        # Initialize global monitoring variables
        self.global_listener = None
        self.global_keys_pressed = set()
        self.is_monitoring_shortcuts = False
        
        # Create flag for daemon mode
        self.daemon_mode = False
    
    def setupUI(self):
        """Set up the main window UI"""
        self.setWindowTitle("Keyboard LED Configuration")
        self.setMinimumSize(1100, 650)
        
        # Main widget and layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # Top control panel
        self._setup_top_control_panel(main_layout)
        
        # Side-by-side layout for keyboard and controls using a splitter
        keyboard_controls_layout = QHBoxLayout()
        
        # Create a splitter for keyboard and controls
        self.main_splitter = QSplitter(Qt.Horizontal)
        
        # Keyboard layout widget
        keyboard_widget = KeyboardLayout(self)
        self.keys = keyboard_widget.keys  # Store reference to key buttons
        
        # Controls panel
        controls_widget = ControlPanel(self)
        
        # Add widgets to splitter
        self.main_splitter.addWidget(keyboard_widget)
        self.main_splitter.addWidget(controls_widget)
        
        # Set initial sizes (3:1 ratio)
        self.main_splitter.setSizes([750, 250])
        
        # Add splitter to layout
        keyboard_controls_layout.addWidget(self.main_splitter)
        main_layout.addLayout(keyboard_controls_layout)
        
        # Status bar
        self.statusBar().showMessage("Disconnected")
        
        self.setCentralWidget(central_widget)
    
    def _setup_top_control_panel(self, main_layout):
        """Set up the top control panel with configuration controls"""
        control_panel = QHBoxLayout()
        
        # Config selection
        control_panel.addWidget(QLabel("Configuration:"))
        self.config_combo = QComboBox()
        self.config_combo.addItems(self.config_manager.get_config_list())
        self.config_combo.currentTextChanged.connect(self.load_config)
        control_panel.addWidget(self.config_combo)
        
        # Config name
        control_panel.addWidget(QLabel("Name:"))
        self.config_name = QLineEdit("Default Green")
        control_panel.addWidget(self.config_name)
        
        # Save button
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_config)
        control_panel.addWidget(save_button)
        
        control_panel.addStretch()
        
        # Connect button
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.toggle_connection)
        control_panel.addWidget(self.connect_button)
        
        # Apply button
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self.send_config)
        control_panel.addWidget(apply_button)
        
        # Device Info button
        device_info_button = QPushButton("Device Info")
        device_info_button.clicked.connect(self.show_device_info)
        control_panel.addWidget(device_info_button)
        
        main_layout.addLayout(control_panel)
    
    def setupSystemTray(self):
        """Set up the system tray icon and menu"""
        self.tray_icon = QSystemTrayIcon(self)
        
        # Use app icon if available, otherwise use a default
        self.tray_icon.setIcon(QApplication.instance().windowIcon())
        
        # Create the tray menu
        tray_menu = QMenu()
        
        # Add show/hide action
        self.show_action = QAction("Show Window", self)
        self.show_action.triggered.connect(self.showNormal)
        tray_menu.addAction(self.show_action)
        
        # Add separator
        tray_menu.addSeparator()
        
        # Add configurations submenu
        configs_menu = QMenu("Configurations")
        tray_menu.addMenu(configs_menu)
        
        # Add configurations to submenu
        self.update_tray_configs(configs_menu)
        
        # Add refresh configs action
        refresh_action = QAction("Refresh Configurations", self)
        refresh_action.triggered.connect(lambda: self.update_tray_configs(configs_menu))
        tray_menu.addAction(refresh_action)
        
        # Add separator
        tray_menu.addSeparator()
        
        # Add shortcut monitoring toggle
        self.tray_shortcut_action = QAction("Start Shortcut Monitoring", self)
        self.tray_shortcut_action.triggered.connect(self.toggle_shortcut_monitoring_from_tray)
        tray_menu.addAction(self.tray_shortcut_action)
        
        # Add daemon mode toggle
        self.daemon_mode_action = QAction("Enter Daemon Mode", self)
        self.daemon_mode_action.triggered.connect(self.toggle_daemon_mode)
        tray_menu.addAction(self.daemon_mode_action)
        
        # Add separator
        tray_menu.addSeparator()
        
        # Add quit option
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)
        
        # Set the tray icon menu
        self.tray_icon.setContextMenu(tray_menu)
        
        # Show the tray icon
        self.tray_icon.show()
        
        # Connect signal for tray icon activation
        self.tray_icon.activated.connect(self.tray_icon_activated)
    
    def update_tray_configs(self, menu):
        """Update the configurations in the tray menu"""
        # Clear current items
        menu.clear()
        
        # Get config list
        configs = self.config_manager.get_config_list()
        
        # Add each config as an action
        for config_name in configs:
            action = QAction(config_name, self)
            action.triggered.connect(lambda checked, name=config_name: self.apply_tray_config(name))
            menu.addAction(action)
    
    def apply_tray_config(self, config_name):
        """Apply a configuration from the tray menu"""
        # Load the configuration
        self.load_config(config_name)
        
        # Ensure keyboard is connected
        if not self.keyboard.connected:
            self.connect_to_keyboard()
        
        # Send config to keyboard
        self.send_config()
        
        # Show notification
        self.tray_icon.showMessage(
            "Configuration Applied",
            f"Applied configuration: {config_name}",
            QSystemTrayIcon.Information,
            2000
        )
    
    def tray_icon_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.DoubleClick:
            # Show/hide the window on double click
            if self.isVisible():
                self.hide()
            else:
                self.showNormal()
                self.activateWindow()
    
    def toggle_shortcut_monitoring_from_tray(self):
        """Toggle shortcut monitoring from system tray"""
        if self.is_monitoring_shortcuts:
            # Stop monitoring
            self.stop_global_shortcut_monitor()
            self.is_monitoring_shortcuts = False
            self.tray_shortcut_action.setText("Start Shortcut Monitoring")
            self.tray_icon.showMessage(
                "Shortcut Monitoring",
                "Shortcut monitoring stopped",
                QSystemTrayIcon.Information,
                2000
            )
        else:
            # Start monitoring
            self.start_global_shortcut_monitor()
            self.is_monitoring_shortcuts = True
            self.tray_shortcut_action.setText("Stop Shortcut Monitoring")
            self.tray_icon.showMessage(
                "Shortcut Monitoring",
                "Shortcut monitoring started",
                QSystemTrayIcon.Information,
                2000
            )
            
            # Update GUI if it's visible
            control_panel = self._get_control_panel()
            if control_panel and hasattr(control_panel, 'shortcut_toggle') and self.isVisible():
                control_panel.shortcut_toggle.setChecked(True)
                control_panel.shortcut_toggle.setText("Stop Shortcut Monitor")
    
    def toggle_daemon_mode(self):
        """Toggle daemon mode (shortcut monitoring only)"""
        if self.daemon_mode:
            # Exit daemon mode
            self.daemon_mode = False
            self.daemon_mode_action.setText("Enter Daemon Mode")
            self.show_action.setEnabled(True)
            
            # Show notification
            self.tray_icon.showMessage(
                "Daemon Mode",
                "Exited daemon mode",
                QSystemTrayIcon.Information,
                2000
            )
        else:
            # Enter daemon mode
            self.daemon_mode = True
            self.daemon_mode_action.setText("Exit Daemon Mode")
            self.hide()  # Hide the main window
            self.show_action.setEnabled(False)  # Disable show window option
            
            # Start shortcut monitoring if not already active
            if not self.is_monitoring_shortcuts:
                self.toggle_shortcut_monitoring_from_tray()
            
            # Show notification
            self.tray_icon.showMessage(
                "Daemon Mode",
                "Entered daemon mode (shortcut monitoring only)",
                QSystemTrayIcon.Information,
                2000
            )
    
    def quit_application(self):
        """Quit the application entirely"""
        # Stop any active listeners
        self.stop_global_shortcut_monitor()
        
        # Stop shortcut monitoring
        if hasattr(self, 'shortcut_lighting'):
            self.shortcut_lighting.stop_global_monitor()
            self.shortcut_lighting.stop_app_monitor()
        
        # Disconnect from keyboard
        if self.keyboard.connected:
            self.keyboard.disconnect()
        
        # Exit the application
        QApplication.instance().quit()
    
    # Key event handling
    def eventFilter(self, obj, event):
        """Filter keyboard events for shortcut highlighting"""
        if event.type() == QEvent.KeyPress:
            key = event.key()
            if key in QT_KEY_MAP:
                key_name = QT_KEY_MAP[key]
                self.shortcut_lighting.handle_key_press(key_name)
            
        elif event.type() == QEvent.KeyRelease:
            key = event.key()
            if key in QT_KEY_MAP:
                key_name = QT_KEY_MAP[key]
                self.shortcut_lighting.handle_key_release(key_name)
        
        return super().eventFilter(obj, event)
    
    def event(self, event):
        """Handle custom key events from Wayland/evdev monitoring"""
        if event.type() == CustomKeyEvent.KeyPress:
            self.shortcut_lighting.handle_key_press(event.key_name)
            return True
        elif event.type() == CustomKeyEvent.KeyRelease:
            self.shortcut_lighting.handle_key_release(event.key_name)
            return True
        return super().event(event)
    
    def keyPressEvent(self, event):
        """Handle key press events"""
        super().keyPressEvent(event)
        
        # Extract key name from event
        key_name = self._get_key_name_from_event(event)
        if not key_name:
            return
            
        # Forward to shortcut lighting handler
        if hasattr(self, 'shortcut_lighting'):
            self.shortcut_lighting.handle_key_press(key_name)

    def keyReleaseEvent(self, event):
        """Handle key release events"""
        super().keyReleaseEvent(event)
        
        # Extract key name from event
        key_name = self._get_key_name_from_event(event)
        if not key_name:
            return
        
        # Forward to shortcut lighting handler
        if hasattr(self, 'shortcut_lighting'):
            self.shortcut_lighting.handle_key_release(key_name)
    
    def _get_key_name_from_event(self, event):
        """Extract normalized key name from a key event"""
        # Extract key name from event
        key_name = event.text().upper()
        
        if len(key_name) == 0 or ord(key_name[0]) < 32:
            # Try to get key name from key constant
            key = event.key()
            if key in QT_KEY_MAP:
                key_name = QT_KEY_MAP[key]
            else:
                return None
        
        return key_name
    
    def handle_key_press(self, event):
        """Handle key press events and highlight shortcuts if enabled"""
        # Skip if shortcut monitoring is disabled
        control_panel = self._get_control_panel()
        if not control_panel or not hasattr(control_panel, 'shortcut_toggle') or not control_panel.shortcut_toggle.isChecked():
            return
        
        # Extract key name from event
        key_name = event.text().upper()
        if len(key_name) == 0 or ord(key_name[0]) < 32:
            # Try to get key name from key constant
            key = event.key()
            if key in QT_KEY_MAP:
                key_name = QT_KEY_MAP[key]
        
        # Simply pass the key press to the unified shortcut lighting feature
        # which will handle both global and app-specific shortcuts internally
        self.shortcut_lighting.handle_key_press(key_name)
    
    def handle_key_release(self, event):
        """Handle key release events for shortcuts"""
        # Skip if shortcut monitoring is disabled
        control_panel = self._get_control_panel()
        if not control_panel or not hasattr(control_panel, 'shortcut_toggle') or not control_panel.shortcut_toggle.isChecked():
            return
        
        # Extract key name from event
        key_name = event.text().upper()
        if len(key_name) == 0 or ord(key_name[0]) < 32:
            # Try to get key name from key constant
            key = event.key()
            if key in QT_KEY_MAP:
                key_name = QT_KEY_MAP[key]
        
        # Simply pass the key release to the unified shortcut lighting feature
        # which will handle both global and app-specific shortcuts internally
        self.shortcut_lighting.handle_key_release(key_name)
    
    # Keyboard connection handling
    def connect_to_keyboard(self):
        """Connect to the keyboard"""
        if not self.keyboard.connected:
            if self.keyboard.connect():
                self.connect_button.setText("Disconnect")
                self.statusBar().showMessage("Connected to keyboard")
                self.send_config()  # Apply config immediately on connect
                return True
            else:
                self.statusBar().showMessage("Failed to connect to keyboard")
                return False
        return True
    
    def toggle_connection(self):
        """Toggle connection to the keyboard"""
        if not self.keyboard.connected:
            if self.connect_to_keyboard():
                self.connect_button.setText("Disconnect")
                self.statusBar().showMessage("Connected to keyboard")
            else:
                QMessageBox.warning(self, "Connection Failed", 
                                  "Could not connect to the keyboard. Make sure it's plugged in and has the correct VID/PID.")
        else:
            self.keyboard.disconnect()
            self.connect_button.setText("Connect")
            self.statusBar().showMessage("Disconnected")
    
    def show_device_info(self):
        """Show information about the connected keyboard"""
        if not self.keyboard.connected:
            QMessageBox.information(self, "Device Information", 
                                  "Not connected to any keyboard")
            return
        
        try:
            info = {}
            try:
                info["Manufacturer"] = self.keyboard.device.get_manufacturer_string()
                info["Product"] = self.keyboard.device.get_product_string()
                info["Serial"] = self.keyboard.device.get_serial_number_string()
            except:
                pass
            
            info["VID"] = f"0x{self.keyboard.vendor_id:04X}"
            info["PID"] = f"0x{self.keyboard.product_id:04X}"
            
            info_text = "\n".join([f"{key}: {value}" for key, value in info.items()])
            
            QMessageBox.information(self, "Device Information", info_text)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to get device information: {str(e)}")
    
    # Configuration handling
    def load_config(self, config_name=None):
        """Load a configuration by name"""
        config = self.config_manager.load_config(config_name)
        self.config_name.setText(config["name"])
        
        # Apply colors to keys
        colors = config["colors"]
        for i, key in enumerate(self.keys):
            if i < len(colors):
                r, g, b = colors[i]
                key.setKeyColor(QColor(r, g, b))
        
        if self.auto_reload and self.keyboard.connected:
            self.send_config()
    
    def save_config(self):
        """Save the current configuration"""
        config_name = self.config_name.text()
        if not config_name:
            QMessageBox.warning(self, "Invalid Name", "Please enter a configuration name")
            return
        
        # Collect colors
        colors = []
        for key in self.keys:
            colors.append((key.color.red(), key.color.green(), key.color.blue()))
        
        if self.config_manager.save_config(config_name, colors):
            # Update the combo boxes
            current_configs = self.config_manager.get_config_list()
            
            # Update main config combo
            self.config_combo.clear()
            self.config_combo.addItems(current_configs)
            self.config_combo.setCurrentText(config_name)
            
            self.statusBar().showMessage(f"Configuration '{config_name}' saved")
        else:
            self.statusBar().showMessage("Failed to save configuration")
    
    def send_config(self):
        """Send the current configuration to the keyboard"""
        if not self.keyboard.connected:
            if not self.keyboard.connect():
                self.statusBar().showMessage("Failed to connect")
                return
            self.connect_button.setText("Disconnect")
        
        # Get the current intensity
        intensity_value = 100  # Default to 100%
        if self.intensity_slider:
            intensity_value = self.intensity_slider.value()
        intensity = intensity_value / 100.0
        
        # Use the memory-mapped format for faster transmission
        config_name = self.config_combo.currentText()
        memory_map = self.config_manager.get_config_in_memory_map(config_name)
        
        # Send directly using the memory map
        success = self.keyboard.send_led_config(memory_map, intensity)
        
        if success:
            self.statusBar().showMessage("Configuration applied successfully")
        else:
            self.statusBar().showMessage("Failed to apply configuration")
    
    def toggle_auto_reload(self):
        """Toggle auto-reload of configuration changes"""
        self.auto_reload = not self.auto_reload
        self.auto_reload_btn.setText(f"Auto-Reload: {'ON' if self.auto_reload else 'OFF'}")
        
        if self.auto_reload:
            self.send_config()
            self.reload_timer.start(500)  # Check every 500ms
        else:
            self.reload_timer.stop()
    
    def intensity_changed(self, value):
        """Handle changes to the master intensity slider"""
        # Update the intensity label if available
        control_panel = self._get_control_panel()
        if control_panel and hasattr(control_panel, 'intensity_label'):
            control_panel.intensity_label.setText(f"{value}%")
            control_panel.intensity_label.repaint()  # Force redraw
        
        # Apply immediately if auto-reload is on
        if self.auto_reload and self.keyboard.connected:
            # Apply directly instead of using the timer for more responsive UI
            self.send_config()
        else:
            # Still use the timer for debouncing when auto-reload is off
            self.intensity_timer.start(100)  # Shorter delay (100ms) for better responsiveness
    
    def apply_intensity(self):
        """Apply the intensity change after slider movement has stopped"""
        if self.auto_reload and self.keyboard.connected:
            self.send_config()
    
    # UI interaction methods
    def handle_key_click(self, key):
        """Handle a key click event in the keyboard layout"""
        # If in selection mode, add/remove from selection
        if self.selection_mode:
            if key in self.selected_keys:
                # Deselect the key
                self.selected_keys.remove(key)
                key.setSelected(False)
            else:
                # Select the key
                self.selected_keys.append(key)
                key.setSelected(True)
                
            # Update status bar with selection info
            if self.selected_keys:
                self.statusBar().showMessage(f"Selected {len(self.selected_keys)} keys")
            else:
                self.statusBar().showMessage("No keys selected")
        else:
            # Toggle the key between current color and off (black)
            if key.color == QColor(0, 0, 0):
                # Turn on - set to current color
                key.setKeyColor(self.current_color)
                self.statusBar().showMessage(f"Turned on {key.key_name}")
            else:
                # Turn off - set to black
                key.setKeyColor(QColor(0, 0, 0))
                self.statusBar().showMessage(f"Turned off {key.key_name}")
            
            # If auto-reload is enabled, apply the config
            if self.auto_reload and self.keyboard.connected:
                self.send_config()
    
    def toggle_selection_mode(self, enabled):
        """Toggle between selection mode and normal color application mode"""
        self.selection_mode = enabled
        
        # Get control panel for UI updates
        control_panel = self._get_control_panel()
        
        # Update UI state based on selection mode
        if enabled:
            self.statusBar().showMessage("Selection mode enabled - click keys to select/deselect")
            # Highlight the selection checkbox to make it more obvious
            if control_panel and hasattr(control_panel, 'selection_mode_toggle'):
                control_panel.selection_mode_toggle.setStyleSheet("QCheckBox { color: blue; font-weight: bold; }")
        else:
            # Exit selection mode and clear all selections
            self.clear_selection()
            self.statusBar().showMessage("Selection mode disabled")
            if control_panel and hasattr(control_panel, 'selection_mode_toggle'):
                control_panel.selection_mode_toggle.setStyleSheet("")
    
    def clear_selection(self):
        """Clear all selected keys"""
        for key in self.selected_keys:
            key.setSelected(False)
        self.selected_keys = []
        self.statusBar().showMessage("Selection cleared")
    
    def set_region_color(self):
        """Apply the current color to the selected region with the region's intensity"""
        if not self.selected_keys:
            QMessageBox.information(self, "No Selection", "Please select keys first (enable Selection Mode and click on keys)")
            return
        
        # Get region intensity slider from control panel
        control_panel = self._get_control_panel()
        region_intensity_slider = None
        if control_panel and hasattr(control_panel, 'region_intensity_slider'):
            region_intensity_slider = control_panel.region_intensity_slider
        
        # Get intensity from slider (0-100)
        intensity = 1.0  # Default to full intensity
        if region_intensity_slider:
            intensity = region_intensity_slider.value() / 100.0
        
        # Apply the color with intensity to each selected key
        for key in self.selected_keys:
            # Create a color with the current color's RGB values adjusted by intensity
            adjusted_color = QColor(
                min(255, int(self.current_color.red() * intensity)),
                min(255, int(self.current_color.green() * intensity)),
                min(255, int(self.current_color.blue() * intensity))
            )
            key.setKeyColor(adjusted_color)
        
        # Update the keyboard if auto-reload is on
        if self.auto_reload and self.keyboard.connected:
            self.send_config()
        
        self.statusBar().showMessage(f"Applied color to {len(self.selected_keys)} keys at {int(intensity * 100)}% intensity")
    
    def set_current_color(self, color):
        """Set the current working color"""
        r, g, b = color
        self.current_color = QColor(r, g, b)
        self.color_display.setColor(self.current_color)
    
    def choose_current_color(self):
        """Choose a custom color for the current working color"""
        color = QColorDialog.getColor(self.current_color, self, "Select Current Color")
        if color.isValid():
            self.current_color = color
            if self.color_display:
                self.color_display.setColor(color)
            self.statusBar().showMessage(f"Selected color: RGB({color.red()}, {color.green()}, {color.blue()})")
            
            # Update any selected keys if in selection mode
            if self.selection_mode and self.selected_keys:
                self.set_region_color()
    
    def apply_current_color_to_all(self):
        """Apply the current color to all keys"""
        for key in self.keys:
            key.setKeyColor(self.current_color)
        
        if self.auto_reload and self.keyboard.connected:
            self.send_config()
    
    # Shortcut monitoring methods
    def toggle_shortcut_monitor(self):
        """Toggle global shortcut monitoring on/off"""
        if self.shortcut_toggle.isChecked():
            self.shortcut_toggle.setText("Stop Shortcut Monitor")
            
            # Use unified feature's global monitoring
            if hasattr(self, 'shortcut_lighting'):
                if isinstance(self.shortcut_lighting, ShortcutLightingFeature):
                    # Use new unified feature
                    self.shortcut_lighting.start_global_monitor()
                else:
                    # Legacy support for old ShortcutLighting class
                    self.shortcut_lighting.start_monitor()
            
            # Update global state
            self.is_monitoring_shortcuts = True
            self.statusBar().showMessage("Global shortcut monitoring started")
        else:
            self.shortcut_toggle.setText("Start Shortcut Monitor")
            
            # Use unified feature's global monitoring
            if hasattr(self, 'shortcut_lighting'):
                if isinstance(self.shortcut_lighting, ShortcutLightingFeature):
                    # Use new unified feature
                    self.shortcut_lighting.stop_global_monitor()
                else:
                    # Legacy support for old ShortcutLighting class
                    self.shortcut_lighting.stop_monitor()
            
            # Update global state
            self.is_monitoring_shortcuts = False
            self.statusBar().showMessage("Global shortcut monitoring stopped")
    
    def choose_highlight_color(self):
        """Choose a custom color for highlighting shortcuts"""
        color = QColorDialog.getColor(self.shortcut_lighting.default_highlight_color, self, "Select Highlight Color")
        if color.isValid():
            self.shortcut_lighting.set_default_highlight_color(color)
            
            # Update the highlight color display in the control panel
            control_panel = self._get_control_panel()
            if control_panel and hasattr(control_panel, 'highlight_color_display'):
                control_panel.highlight_color_display.setColor(color)
                
            self.statusBar().showMessage(f"Shortcut highlight color set to RGB({color.red()}, {color.green()}, {color.blue()})")
    
    def manage_modifier_colors(self):
        """Open dialog to manage modifier key colors"""
        dialog = ModifierColorsDialog(self, self.shortcut_lighting)
        dialog.exec_()
    
    def start_global_shortcut_monitor(self):
        """Start global shortcut monitoring"""
        if hasattr(self, 'shortcut_lighting'):
            self.shortcut_lighting.start_global_monitor()
            logger.info("Global shortcut monitoring started")
    
    def stop_global_shortcut_monitor(self):
        """Stop the global shortcut monitoring"""
        if hasattr(self, 'shortcut_lighting'):
            self.shortcut_lighting.stop_global_monitor()
            logger.info("Global shortcut monitoring stopped")
    
    # App shortcut methods
    def toggle_app_shortcuts(self):
        """Toggle application-specific shortcut highlighting"""
        # Get control panel for UI updates
        control_panel = self._get_control_panel()
        
        if not control_panel or not hasattr(control_panel, 'app_shortcut_toggle'):
            QMessageBox.warning(self, "Error", "App shortcut toggle control not found")
            return
            
        app_shortcut_toggle = control_panel.app_shortcut_toggle
        is_checked = app_shortcut_toggle.isChecked()
        
        if is_checked:
            app_shortcut_toggle.setText("Disable App Shortcuts")
            # Use the unified feature's app monitor methods
            self.shortcut_lighting.start_app_monitor()
            
            # Force immediate update of default keys
            QTimer.singleShot(500, self.shortcut_lighting.highlight_default_keys)
            
            self.statusBar().showMessage("Application shortcut monitoring enabled")
        else:
            app_shortcut_toggle.setText("Enable App Shortcuts")
            # Use the unified feature's app monitor methods
            self.shortcut_lighting.stop_app_monitor()
            self.statusBar().showMessage("Application shortcut monitoring disabled")
    
    def manage_app_shortcuts(self):
        """Open the application shortcut manager dialog"""
        from ui.dialogs.application_shortcuts import AppShortcutManagerDialog
        # Use the app_shortcut_config directly since it's needed for the dialog
        dialog = AppShortcutManagerDialog(self, self.app_shortcut_config)
        dialog.exec_()
    
    # Utility methods
    def save_keyboard_layout(self):
        """Save the keyboard layout to the configuration file"""
        from ui.key_mapping import DEFAULT_LAYOUT
        
        # Save to configuration file
        self.shortcut_manager.save_keyboard_layout(DEFAULT_LAYOUT)
        self.statusBar().showMessage("Keyboard layout saved to configuration")
    
    def closeEvent(self, event):
        """Handle application close event"""
        # If in daemon mode, just hide the window
        if self.daemon_mode:
            event.ignore()
            self.hide()
            return
        
        # Check if should minimize to tray instead
        minimize_to_tray = True  # Could be a setting
        
        if minimize_to_tray and self.tray_icon.isVisible():
            # Hide the window instead of closing
            event.ignore()
            self.hide()
            
            # Show notification
            self.tray_icon.showMessage(
                "Running in Background",
                "The keyboard application is still running in the system tray.",
                QSystemTrayIcon.Information,
                2000
            )
        else:
            # Stop any active listeners
            self.stop_global_shortcut_monitor()
            
            # Stop all shortcut monitoring (both global and app-specific)
            if hasattr(self, 'shortcut_lighting'):
                self.shortcut_lighting.stop_global_monitor()
                self.shortcut_lighting.stop_app_monitor()
            
            # Disconnect from keyboard
            if self.keyboard.connected:
                self.keyboard.disconnect()
            
            # Accept the close event
            event.accept()
    
    # Convenience methods for other components
    @property
    def intensity_slider(self):
        """Get the intensity slider from the control panel"""
        control_panel = self._get_control_panel()
        if control_panel and hasattr(control_panel, 'intensity_slider'):
            return control_panel.intensity_slider
        return None
    
    @property
    def color_display(self):
        """Get the color display from the control panel"""
        control_panel = self._get_control_panel()
        if control_panel and hasattr(control_panel, 'color_display'):
            return control_panel.color_display
        return None
        
    @property
    def intensity_label(self):
        """Get the intensity label from the control panel"""
        control_panel = self._get_control_panel()
        if control_panel and hasattr(control_panel, 'intensity_label'):
            return control_panel.intensity_label
        return None
        
    @property
    def shortcut_toggle(self):
        """Get the shortcut toggle button from the control panel"""
        control_panel = self._get_control_panel()
        if control_panel and hasattr(control_panel, 'shortcut_toggle'):
            return control_panel.shortcut_toggle
        return None
        
    @property
    def highlight_color_display(self):
        """Get the highlight color display from the control panel"""
        control_panel = self._get_control_panel()
        if control_panel and hasattr(control_panel, 'highlight_color_display'):
            return control_panel.highlight_color_display
        return None
        
    @property
    def effect_combo(self):
        """Get the effect combo box from the control panel"""
        control_panel = self._get_control_panel()
        if control_panel and hasattr(control_panel, 'effect_combo'):
            return control_panel.effect_combo
        return None
        
    @property
    def effect_color_display(self):
        """Get the effect color display from the control panel"""
        control_panel = self._get_control_panel()
        if control_panel and hasattr(control_panel, 'effect_color_display'):
            return control_panel.effect_color_display
        return None
    
    def _get_control_panel(self):
        """Helper method to get the control panel from the splitter"""
        for i in range(self.main_splitter.count()):
            widget = self.main_splitter.widget(i)
            if isinstance(widget, ControlPanel):
                return widget
        return None
    
    # Preset functions
    def set_function_key_colors(self, color):
        """Highlight function keys with a specific color"""
        function_keys = ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"]
        
        # Set colors for function keys
        for key in self.keys:
            if key.key_name in function_keys:
                # Convert tuple to QColor if needed
                if isinstance(color, tuple):
                    r, g, b = color
                    key.setKeyColor(QColor(r, g, b))
                else:
                    key.setKeyColor(color)
        
        # Update the keyboard if auto-reload is on
        if self.auto_reload and self.keyboard.connected:
            self.send_config()
        
        self.statusBar().showMessage(f"Highlighted {len(function_keys)} function keys")
    
    def set_rainbow_colors(self):
        """Set rainbow colors across the keyboard"""
        num_keys = len(self.keys)
        if num_keys == 0:
            return
            
        # Create a rainbow gradient across all keys
        for i, key in enumerate(self.keys):
            # Calculate hue based on position (0-360 degrees)
            hue = (i / num_keys) * 360
            
            # Convert HSV to RGB (hue, 1.0 saturation, 1.0 value)
            h = hue / 360.0
            r, g, b = [int(x * 255) for x in colorsys.hsv_to_rgb(h, 1.0, 1.0)]
            
            # Set the key color
            key.setKeyColor(QColor(r, g, b))
        
        # Update the keyboard if auto-reload is on
        if self.auto_reload and self.keyboard.connected:
            self.send_config()
        
        self.statusBar().showMessage("Applied rainbow colors to keyboard")
    
    def apply_gaming_preset(self):
        """Apply a preset for gaming with WASD keys highlighted"""
        # Clear keyboard first by setting all keys to black
        for key in self.keys:
            key.setKeyColor(QColor(0, 0, 0))
        
        # Highlight WASD keys in blue
        gaming_keys = ["W", "A", "S", "D", "Space", "Shift", "Ctrl"]
        for key in self.keys:
            if key.key_name in gaming_keys:
                key.setKeyColor(QColor(0, 150, 255))  # Blue
        
        # Highlight function keys in orange
        function_keys = ["F1", "F2", "F3", "F4", "F5", "F6"]
        for key in self.keys:
            if key.key_name in function_keys:
                key.setKeyColor(QColor(255, 128, 0))  # Orange
        
        # Update the keyboard if auto-reload is on
        if self.auto_reload and self.keyboard.connected:
            self.send_config()
        
        self.statusBar().showMessage("Gaming preset applied")

    def apply_typing_preset(self):
        """Apply a preset for typing with home row highlighted"""
        # Clear keyboard first by setting all keys to black
        for key in self.keys:
            key.setKeyColor(QColor(0, 0, 0))
        
        # Highlight home row (ASDF JKL;) in green
        home_row = ["A", "S", "D", "F", "J", "K", "L", ";"]
        for key in self.keys:
            if key.key_name in home_row:
                key.setKeyColor(QColor(0, 230, 115))  # Green
        
        # Set other keys to a subtle blue
        for key in self.keys:
            if key.key_name not in home_row and key.color == QColor(0, 0, 0):
                key.setKeyColor(QColor(20, 40, 80))  # Dark blue
        
        # Update the keyboard if auto-reload is on
        if self.auto_reload and self.keyboard.connected:
            self.send_config()
        
        self.statusBar().showMessage("Typing preset applied")

    def clear_keyboard(self):
        """Clear all keys to black (off state)"""
        for key in self.keys:
            key.setKeyColor(QColor(0, 0, 0))
        
        # Update the keyboard if auto-reload is on
        if self.auto_reload and self.keyboard.connected:
            self.send_config()
        
        return True

    def debug_shortcut_lighting(self):
        """Trigger debugging for the shortcut lighting feature"""
        logger.info("Triggering shortcut lighting debug")
        if hasattr(self, 'shortcut_lighting'):
            # Call the debug method in the shortcut lighting feature
            self.shortcut_lighting.debug_keyboard_state()
            logger.info("Shortcut lighting debug triggered")
            self.statusBar().showMessage("Shortcut lighting debug info written to logs")
        else:
            logger.warning("No shortcut_lighting feature available for debugging")
            self.statusBar().showMessage("Shortcut lighting feature not available")
            
        # Try to print some additional app-level debugging info
        try:
            logger.info(f"Is monitoring shortcuts: {self.is_monitoring_shortcuts}")
            logger.info(f"Has shortcut_toggle: {hasattr(self._get_control_panel(), 'shortcut_toggle')}")
            if hasattr(self._get_control_panel(), 'shortcut_toggle'):
                logger.info(f"shortcut_toggle is checked: {self._get_control_panel().shortcut_toggle.isChecked()}")
            
            # Check what type of shortcut lighting we're using
            if hasattr(self, 'shortcut_lighting'):
                logger.info(f"Shortcut lighting type: {type(self.shortcut_lighting).__name__}")
                
            # Check keyboard status
            logger.info(f"Keyboard connected: {self.keyboard.connected}")
        except Exception as e:
            logger.error(f"Error in debug_shortcut_lighting: {e}", exc_info=True) 