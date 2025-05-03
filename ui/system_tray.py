from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction, QApplication
from PyQt5.QtCore import QObject

class SystemTrayManager(QObject):
    def __init__(self, parent):
        super().__init__(parent)
        self.app = parent
        self.tray_icon = None
        self.setup_system_tray()
    
    def setup_system_tray(self):
        """Setup system tray icon and menu"""
        # Create system tray icon
        self.tray_icon = QSystemTrayIcon(self.app)
        
        # Use app icon if available
        self.tray_icon.setIcon(self.app.windowIcon())
        
        # Create the tray menu
        tray_menu = QMenu()
        
        # Add show/hide action
        self.show_action = QAction("Show Window", self.app)
        self.show_action.triggered.connect(self.app.showNormal)
        tray_menu.addAction(self.show_action)
        
        # Add separator
        tray_menu.addSeparator()
        
        # Add configurations submenu
        configs_menu = QMenu("Configurations")
        tray_menu.addMenu(configs_menu)
        
        # Add configurations to submenu
        self.update_tray_configs(configs_menu)
        
        # Add refresh configs action
        refresh_action = QAction("Refresh Configurations", self.app)
        refresh_action.triggered.connect(lambda: self.update_tray_configs(configs_menu))
        tray_menu.addAction(refresh_action)
        
        # Add separator
        tray_menu.addSeparator()
        
        # Add system monitoring submenu
        monitoring_menu = QMenu("System Monitoring")
        tray_menu.addMenu(monitoring_menu)
        
        # Add monitoring options
        cpu_action = QAction("CPU Usage", self.app)
        cpu_action.triggered.connect(lambda: self.app.start_system_monitoring_from_tray("cpu"))
        monitoring_menu.addAction(cpu_action)
        
        ram_action = QAction("RAM Usage", self.app)
        ram_action.triggered.connect(lambda: self.app.start_system_monitoring_from_tray("ram"))
        monitoring_menu.addAction(ram_action)
        
        battery_action = QAction("Battery Status", self.app)
        battery_action.triggered.connect(lambda: self.app.start_system_monitoring_from_tray("battery"))
        monitoring_menu.addAction(battery_action)
        
        # Add stop monitoring option
        stop_monitoring = QAction("Stop Monitoring", self.app)
        stop_monitoring.triggered.connect(self.app.stop_system_monitoring)
        monitoring_menu.addAction(stop_monitoring)
        
        # Add separator before quit option
        tray_menu.addSeparator()
        
        # Add quit action
        quit_action = QAction("Quit", self.app)
        quit_action.triggered.connect(QApplication.instance().quit)
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
        configs = self.app.config_manager.get_config_list()
        
        # Add each config as an action
        for config_name in configs:
            action = QAction(config_name, self.app)
            action.triggered.connect(lambda checked, name=config_name: self.apply_tray_config(name))
            menu.addAction(action)
    
    def apply_tray_config(self, config_name):
        """Apply a configuration from the tray menu"""
        # Load the configuration
        self.app.load_config(config_name)
        
        # Ensure keyboard is connected
        if not self.app.keyboard.connected:
            self.app.connect_to_keyboard()
        
        # Send config to keyboard
        self.app.send_config()
        
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
            if self.app.isVisible():
                self.app.hide()
            else:
                self.app.showNormal()
                self.app.activateWindow()
