"""
Control panel UI for keyboard configuration options.
"""

import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QPushButton, 
                           QCheckBox, QSlider, QHBoxLayout, QLabel, QTabWidget,
                           QColorDialog, QComboBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from ui.color_display import ColorDisplay

logger = logging.getLogger(__name__)

class ControlPanel(QWidget):
    """Panel containing controls for keyboard configuration"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.setupUI()
    
    def setupUI(self):
        """Set up the control panel UI"""
        main_layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Create tabs
        self.createBasicTab()
        self.createPresetsTab()
        self.createShortcutsTab()
        
        main_layout.addWidget(self.tab_widget)
        
        # Auto-reload toggle at the bottom for easy access
        auto_reload_layout = QHBoxLayout()
        self.auto_reload_btn = QPushButton("Auto-Reload: ON")
        self.auto_reload_btn.setCheckable(True)
        self.auto_reload_btn.setChecked(True)
        
        # Connect signal if parent has the handler
        if hasattr(self.parent_app, 'toggle_auto_reload'):
            self.auto_reload_btn.clicked.connect(self.parent_app.toggle_auto_reload)
        
        auto_reload_layout.addWidget(self.auto_reload_btn)
        main_layout.addLayout(auto_reload_layout)
    
    def createBasicTab(self):
        """Create the basic controls tab"""
        basic_tab = QWidget()
        layout = QVBoxLayout(basic_tab)
        
        # Current color selection
        color_group = QGroupBox("Current Color")
        color_layout = QVBoxLayout()
        
        # Color display - shows currently selected color
        self.color_display = ColorDisplay(QColor(0, 255, 0))  # Default: green
        
        # Connect signal if parent has the handler
        if hasattr(self.parent_app, 'choose_current_color'):
            self.color_display.clicked.connect(self.parent_app.choose_current_color)
        
        color_layout.addWidget(self.color_display)
        
        # Quick color buttons grid
        quick_colors_layout = QHBoxLayout()
        standard_colors = [
            (255, 0, 0), (0, 255, 0), (0, 0, 255),  # Red, Green, Blue
            (255, 255, 0), (0, 255, 255), (255, 0, 255),  # Yellow, Cyan, Magenta
        ]
        
        for r, g, b in standard_colors:
            color_btn = QPushButton()
            color_btn.setFixedSize(40, 30)
            color_btn.setStyleSheet(f"background-color: rgb({r}, {g}, {b}); border: 1px solid black;")
            
            # Connect to parent's color setter if available
            if hasattr(self.parent_app, 'set_current_color'):
                color_btn.clicked.connect(lambda checked, color=(r, g, b): self.parent_app.set_current_color(color))
            
            quick_colors_layout.addWidget(color_btn)
        
        color_layout.addLayout(quick_colors_layout)
        
        # Custom color button
        custom_color_btn = QPushButton("Custom Color...")
        if hasattr(self.parent_app, 'choose_current_color'):
            custom_color_btn.clicked.connect(self.parent_app.choose_current_color)
        color_layout.addWidget(custom_color_btn)
        
        # Apply to all button
        apply_all_btn = QPushButton("Apply to All Keys")
        if hasattr(self.parent_app, 'apply_current_color_to_all'):
            apply_all_btn.clicked.connect(self.parent_app.apply_current_color_to_all)
        color_layout.addWidget(apply_all_btn)
        
        color_group.setLayout(color_layout)
        layout.addWidget(color_group)
        
        # Global brightness control
        brightness_group = QGroupBox("Master Brightness")
        brightness_layout = QVBoxLayout()
        
        brightness_slider_layout = QHBoxLayout()
        brightness_slider_layout.addWidget(QLabel("Brightness:"))
        
        self.intensity_slider = QSlider(Qt.Horizontal)
        self.intensity_slider.setMinimum(0)
        self.intensity_slider.setMaximum(100)
        self.intensity_slider.setValue(100)  # Default to full brightness
        self.intensity_slider.setTickPosition(QSlider.TicksBelow)
        self.intensity_slider.setTickInterval(10)
        
        if hasattr(self.parent_app, 'intensity_changed'):
            self.intensity_slider.valueChanged.connect(self.parent_app.intensity_changed)
        
        brightness_slider_layout.addWidget(self.intensity_slider)
        
        # Intensity value label
        self.intensity_label = QLabel("100%")
        brightness_slider_layout.addWidget(self.intensity_label)
        
        brightness_layout.addLayout(brightness_slider_layout)
        brightness_group.setLayout(brightness_layout)
        layout.addWidget(brightness_group)
        
        layout.addStretch()
        self.tab_widget.addTab(basic_tab, "Basic")
    

    def createPresetsTab(self):
        """Create the presets tab"""
        presets_tab = QWidget()
        layout = QVBoxLayout(presets_tab)
        
        # Presets group
        presets_group = QGroupBox("Lighting Presets")
        presets_layout = QVBoxLayout()
        
        # Function key preset
        function_keys_btn = QPushButton("Highlight Function Keys")
        if hasattr(self.parent_app, 'set_function_key_colors'):
            function_keys_btn.clicked.connect(lambda: self.parent_app.set_function_key_colors((255, 128, 0)))
        presets_layout.addWidget(function_keys_btn)

        # Gaming preset button
        gaming_preset_btn = QPushButton("Gaming Preset (WASD)")
        if hasattr(self.parent_app, 'apply_gaming_preset'):
            gaming_preset_btn.clicked.connect(self.parent_app.apply_gaming_preset)
        presets_layout.addWidget(gaming_preset_btn)

        # Typing preset button
        typing_preset_btn = QPushButton("Typing Preset")
        if hasattr(self.parent_app, 'apply_typing_preset'):
            typing_preset_btn.clicked.connect(self.parent_app.apply_typing_preset)
        presets_layout.addWidget(typing_preset_btn)

        # Rainbow colors button
        rainbow_btn = QPushButton("Rainbow Colors")
        if hasattr(self.parent_app, 'set_rainbow_colors'):
            rainbow_btn.clicked.connect(self.parent_app.set_rainbow_colors)
        presets_layout.addWidget(rainbow_btn)
        
        presets_group.setLayout(presets_layout)
        layout.addWidget(presets_group)
        
        layout.addStretch()
        self.tab_widget.addTab(presets_tab, "Presets")
    
    def createShortcutsTab(self):
        """Create the shortcuts tab"""
        shortcuts_tab = QWidget()
        layout = QVBoxLayout(shortcuts_tab)
        
        # App-specific shortcuts group (only keep app-based monitoring)
        app_shortcut_group = QGroupBox("Application Shortcuts")
        app_shortcut_layout = QVBoxLayout()
        
        # Enable/disable app shortcut detection
        self.app_shortcut_toggle = QPushButton("Enable App Shortcuts")
        self.app_shortcut_toggle.setCheckable(True)
        if hasattr(self.parent_app, 'toggle_app_shortcuts'):
            self.app_shortcut_toggle.clicked.connect(self.parent_app.toggle_app_shortcuts)
        app_shortcut_layout.addWidget(self.app_shortcut_toggle)
        
        # Manage app shortcuts button
        manage_app_shortcuts_btn = QPushButton("Manage App Shortcuts")
        if hasattr(self.parent_app, 'manage_app_shortcuts'):
            manage_app_shortcuts_btn.clicked.connect(self.parent_app.manage_app_shortcuts)
        app_shortcut_layout.addWidget(manage_app_shortcuts_btn)
        
        app_shortcut_group.setLayout(app_shortcut_layout)
        layout.addWidget(app_shortcut_group)
        
        layout.addStretch()
        self.tab_widget.addTab(shortcuts_tab, "Shortcuts") 