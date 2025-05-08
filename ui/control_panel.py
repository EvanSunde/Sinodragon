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
        self.createSelectionTab()
        self.createPresetsTab()
        self.createShortcutsTab()
        self.createEffectsTab()
        
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
    
    def createSelectionTab(self):
        """Create the region selection tab"""
        selection_tab = QWidget()
        layout = QVBoxLayout(selection_tab)
        
        # Toggle selection mode
        self.selection_mode_toggle = QCheckBox("Selection Mode")
        if hasattr(self.parent_app, 'toggle_selection_mode'):
            self.selection_mode_toggle.toggled.connect(self.parent_app.toggle_selection_mode)
        self.selection_mode_toggle.setStyleSheet("QCheckBox { font-weight: bold; }")
        layout.addWidget(self.selection_mode_toggle)
        
        # Selection controls group
        selection_group = QGroupBox("Selection Controls")
        selection_layout = QVBoxLayout()
        
        # Apply color to selected region
        selection_color_btn = QPushButton("Apply Current Color to Region")
        if hasattr(self.parent_app, 'set_region_color'):
            selection_color_btn.clicked.connect(self.parent_app.set_region_color)
        selection_layout.addWidget(selection_color_btn)
        
        # Selected region brightness
        selection_brightness_layout = QHBoxLayout()
        selection_brightness_layout.addWidget(QLabel("Region Brightness:"))
        
        self.region_intensity_slider = QSlider(Qt.Horizontal)
        self.region_intensity_slider.setMinimum(1)
        self.region_intensity_slider.setMaximum(100)
        self.region_intensity_slider.setValue(100)
        selection_brightness_layout.addWidget(self.region_intensity_slider)
        
        self.region_intensity_label = QLabel("100%")
        selection_brightness_layout.addWidget(self.region_intensity_label)
        
        # Connect slider to update label
        self.region_intensity_slider.valueChanged.connect(
            lambda value: self.region_intensity_label.setText(f"{value}%")
        )
        
        selection_layout.addLayout(selection_brightness_layout)
        
        # Clear selection button
        clear_selection_btn = QPushButton("Clear Selection")
        if hasattr(self.parent_app, 'clear_selection'):
            clear_selection_btn.clicked.connect(self.parent_app.clear_selection)
        selection_layout.addWidget(clear_selection_btn)
        
        selection_group.setLayout(selection_layout)
        layout.addWidget(selection_group)
        
        layout.addStretch()
        self.tab_widget.addTab(selection_tab, "Selection")

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
        
        # Global shortcut monitoring group
        shortcut_group = QGroupBox("Shortcut Monitoring")
        shortcut_layout = QVBoxLayout()
        
        # Enable/disable shortcut monitoring
        self.shortcut_toggle = QPushButton("Start Shortcut Monitor")
        self.shortcut_toggle.setCheckable(True)
        if hasattr(self.parent_app, 'toggle_shortcut_monitor'):
            self.shortcut_toggle.clicked.connect(self.parent_app.toggle_shortcut_monitor)
        shortcut_layout.addWidget(self.shortcut_toggle)
        
        # Highlight color selection
        highlight_color_layout = QHBoxLayout()
        highlight_color_layout.addWidget(QLabel("Highlight Color:"))
        
        self.highlight_color_display = ColorDisplay(QColor(255, 165, 0))  # Default orange
        if hasattr(self.parent_app, 'choose_highlight_color'):
            self.highlight_color_display.clicked.connect(self.parent_app.choose_highlight_color)
        highlight_color_layout.addWidget(self.highlight_color_display)
        shortcut_layout.addLayout(highlight_color_layout)
        
        # Modifier color button
        modifier_color_btn = QPushButton("Manage Modifier Colors...")
        if hasattr(self.parent_app, 'manage_modifier_colors'):
            modifier_color_btn.clicked.connect(self.parent_app.manage_modifier_colors)
        shortcut_layout.addWidget(modifier_color_btn)
        
        # Global monitoring checkbox
        self.global_shortcut_checkbox = QCheckBox("Global Monitoring (System-wide)")
        self.global_shortcut_checkbox.setToolTip("Monitor keyboard shortcuts even when application is not in focus")
        shortcut_layout.addWidget(self.global_shortcut_checkbox)
        
        # Default config for shortcut release
        default_config_layout = QHBoxLayout()
        default_config_layout.addWidget(QLabel("Default Config:"))
        
        self.default_shortcut_config = QComboBox()
        if hasattr(self.parent_app, 'config_manager'):
            self.default_shortcut_config.addItems(self.parent_app.config_manager.get_config_list())
            if hasattr(self.parent_app.shortcut_lighting, 'default_config_name'):
                self.default_shortcut_config.setCurrentText(self.parent_app.shortcut_lighting.default_config_name)
        
        if hasattr(self.parent_app, 'set_default_shortcut_config'):
            self.default_shortcut_config.currentTextChanged.connect(self.parent_app.set_default_shortcut_config)
        
        default_config_layout.addWidget(self.default_shortcut_config)
        shortcut_layout.addLayout(default_config_layout)
        
        # Manage shortcuts button
        manage_shortcuts_btn = QPushButton("Manage Shortcuts")
        if hasattr(self.parent_app, 'manage_shortcuts'):
            manage_shortcuts_btn.clicked.connect(self.parent_app.manage_shortcuts)
        shortcut_layout.addWidget(manage_shortcuts_btn)
        
        shortcut_group.setLayout(shortcut_layout)
        layout.addWidget(shortcut_group)
        
        # App-specific shortcuts group
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
    
    def createEffectsTab(self):
        """Create the effects tab"""
        effects_tab = QWidget()
        layout = QVBoxLayout(effects_tab)
        
        # Effects selection group
        effects_group = QGroupBox("Lighting Effects")
        effects_layout = QVBoxLayout()
        
        # Add effect selection dropdown
        effects_layout.addWidget(QLabel("Select Effect:"))
        self.effect_combo = QComboBox()
        self.effect_combo.addItems([
            "Rainbow Colors", 
            "Wave Effect",
            "Breathing Effect", 
            "Spectrum Cycle",
            "Starlight",
            "Ripple Effect",
            "Reactive Typing",
            "Gradient Flow"
        ])
        
        if hasattr(self.parent_app, 'update_effect_options'):
            self.effect_combo.currentIndexChanged.connect(self.parent_app.update_effect_options)
        
        effects_layout.addWidget(self.effect_combo)

        # Effect options container
        options_group = QGroupBox("Effect Options")
        self.effect_options_layout = QVBoxLayout(options_group)
        
        # Effect color selection
        effect_color_layout = QHBoxLayout()
        effect_color_layout.addWidget(QLabel("Effect Color:"))
        self.effect_color_display = ColorDisplay(QColor(0, 150, 255))  # Default cyan-blue
        
        if hasattr(self.parent_app, 'choose_effect_color'):
            self.effect_color_display.clicked.connect(self.parent_app.choose_effect_color)
        
        effect_color_layout.addWidget(self.effect_color_display)
        self.effect_options_layout.addLayout(effect_color_layout)

        # Speed control
        effect_speed_layout = QHBoxLayout()
        effect_speed_layout.addWidget(QLabel("Speed:"))
        self.effect_speed_slider = QSlider(Qt.Horizontal)
        self.effect_speed_slider.setMinimum(1)
        self.effect_speed_slider.setMaximum(20)
        self.effect_speed_slider.setValue(10)
        self.effect_speed_slider.setTickPosition(QSlider.TicksBelow)
        self.effect_speed_slider.setTickInterval(1)
        effect_speed_layout.addWidget(self.effect_speed_slider)
        self.effect_options_layout.addLayout(effect_speed_layout)

        # Duration control
        effect_duration_layout = QHBoxLayout()
        effect_duration_layout.addWidget(QLabel("Duration (sec):"))
        self.effect_duration_spin = QSlider(Qt.Horizontal)
        self.effect_duration_spin.setMinimum(1)
        self.effect_duration_spin.setMaximum(30)
        self.effect_duration_spin.setValue(10)
        effect_duration_layout.addWidget(self.effect_duration_spin)
        self.effect_duration_label = QLabel("10 sec")
        effect_duration_layout.addWidget(self.effect_duration_label)
        self.effect_duration_spin.valueChanged.connect(
            lambda value: self.effect_duration_label.setText(f"{value} sec")
        )
        self.effect_options_layout.addLayout(effect_duration_layout)
        
        effects_layout.addWidget(options_group)

        # Effect control buttons
        effect_control_layout = QHBoxLayout()
        self.run_effect_btn = QPushButton("Run Effect")
        if hasattr(self.parent_app, 'run_selected_effect'):
            self.run_effect_btn.clicked.connect(self.parent_app.run_selected_effect)
        effect_control_layout.addWidget(self.run_effect_btn)

        self.stop_effect_btn = QPushButton("Stop Effect")
        if hasattr(self.parent_app, 'stop_effects'):
            self.stop_effect_btn.clicked.connect(self.parent_app.stop_effects)
        effect_control_layout.addWidget(self.stop_effect_btn)
        effects_layout.addLayout(effect_control_layout)

        effects_group.setLayout(effects_layout)
        layout.addWidget(effects_group)
        
        layout.addStretch()
        self.tab_widget.addTab(effects_tab, "Effects") 