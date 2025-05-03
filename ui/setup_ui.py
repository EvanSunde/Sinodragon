from PyQt5.QtWidgets import (QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout, 
                            QLabel, QComboBox, QColorDialog, QLineEdit, QSlider,
                            QGroupBox, QCheckBox, QFrame, QTabWidget, QInputDialog)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt
from ui.key_button import KeyButton
from ui.color_display import ColorDisplay

def setup_ui(self):
    """Setup the UI components"""
    # Set the window title and size
    self.setWindowTitle("Keyboard LED Configuration")
    self.resize(1200, 700)
    
    # Create main widget and layout
    main_widget = QWidget()
    main_layout = QHBoxLayout(main_widget)
    
    # Create keyboard display area (left side)
    keyboard_widget = QWidget()
    keyboard_layout = QGridLayout(keyboard_widget)
    keyboard_layout.setSpacing(2)
    
    # Create keyboard based on layout matrix
    self.create_keyboard(keyboard_layout)
    
    # Create controls panel (right side)
    controls_widget = QWidget()
    controls_layout = QVBoxLayout(controls_widget)
    # Add some padding and spacing for a cleaner look
    controls_layout.setContentsMargins(12, 12, 12, 12)
    controls_layout.setSpacing(10)
    
    # Set the sidebar to a dark theme
    controls_widget.setStyleSheet("""
        background-color: #2d2d30;
        color: #e0e0e0;
        QLabel { color: #e0e0e0; }
        QCheckBox { color: #e0e0e0; }
        QGroupBox { color: #e0e0e0; }
    """)
    
    # Main control area (top part) with tabs
    main_controls = QVBoxLayout()
    
    # Color controls (always visible at bottom)
    color_controls = QVBoxLayout()
    
    # Create tabs for organizing controls
    control_tabs = QTabWidget()
    # Style the tab widget for a more modern look
    control_tabs.setStyleSheet("""
        QTabWidget::pane { 
            border: 1px solid #3f3f46;
            border-radius: 4px;
            background-color: #333337;
        }
        QTabBar::tab {
            background-color: #252529;
            border: 1px solid #3f3f46;
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            padding: 8px 16px;
            margin-right: 2px;
            color: #cccccc;
        }
        QTabBar::tab:selected {
            background-color: #333337;
            color: #ffffff;
            border-bottom: none;
        }
        QTabBar::tab:hover:!selected {
            background-color: #3f3f46;
        }
    """)
    main_controls.addWidget(control_tabs)
    
    # Tab 1: Keyboard Controls
    keyboard_tab = QWidget()
    keyboard_tab_layout = QVBoxLayout(keyboard_tab)
    keyboard_tab_layout.setContentsMargins(12, 12, 12, 12)
    keyboard_tab_layout.setSpacing(16)
    
    # Connection controls
    connection_layout = QHBoxLayout()
    # Styled connection button
    self.connect_button = QPushButton("Connect")
    self.connect_button.setStyleSheet("""
        QPushButton {
            background-color: #007acc;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #1c87d9;
        }
    """)
    
    self.selection_checkbox = QCheckBox("Select Mode")
    self.selection_checkbox.setChecked(self.selection_mode)
    self.selection_checkbox.stateChanged.connect(self.toggle_selection_mode)
    connection_layout.addWidget(self.selection_checkbox)
    
    # Toggle to turn off LEDs in keyboard layout
    self.led_toggle = QPushButton("LED On/Off")
    self.led_toggle.setCheckable(True)
    self.led_toggle.setChecked(True)
    self.led_toggle.setStyleSheet("""
        QPushButton {
            background-color: #333337;
            color: #e0e0e0;
            border: 1px solid #3f3f46;
            border-radius: 4px;
            padding: 6px;
        }
        QPushButton:checked {
            background-color: #007acc;
            color: white;
        }
    """)
    self.led_toggle.clicked.connect(self.toggle_keyboard_leds)
    connection_layout.addWidget(self.led_toggle)
    
    self.connect_button.clicked.connect(self.toggle_connection)
    connection_layout.addWidget(self.connect_button)
    
    # Now create and add the auto-reload checkbox
    self.auto_reload_checkbox = QCheckBox("Auto-reload")
    self.auto_reload_checkbox.setChecked(self.auto_reload)
    self.auto_reload_checkbox.stateChanged.connect(self.toggle_auto_reload)
    connection_layout.addWidget(self.auto_reload_checkbox)
    
    # Improved connection status indicator
    self.status_label = QLabel("◯ Disconnected")
    self.status_label.setStyleSheet("color: #ff6b6b; font-weight: bold;")
    connection_layout.addWidget(self.status_label)
    
    keyboard_tab_layout.addLayout(connection_layout)
    
    # Configuration selector
    config_layout = QHBoxLayout()
    config_layout.addWidget(QLabel("Configuration:"))
    self.config_combo = QComboBox()
    # Will be populated in load_config
    # When user picks a different config, load+apply it immediately
    self.config_combo.currentIndexChanged.connect(self.on_config_changed)
    config_layout.addWidget(self.config_combo)
    # Save As → prompts for new name
    self.save_as_button = QPushButton("Save As")
    self.save_as_button.clicked.connect(self.show_save_dialog)
    config_layout.addWidget(self.save_as_button)
    # Save → overwrite existing
    self.overwrite_button = QPushButton("Save")
    self.overwrite_button.clicked.connect(self.overwrite_config)
    config_layout.addWidget(self.overwrite_button)
 
    
    keyboard_tab_layout.addLayout(config_layout)
    
    # Master intensity slider
    intensity_layout = QHBoxLayout()
    intensity_layout.addWidget(QLabel("Master Intensity:"))
    self.intensity_slider = QSlider(Qt.Horizontal)
    # Style the slider for a more modern look
    self.intensity_slider.setStyleSheet("""
        QSlider::groove:horizontal {
            border: 1px solid #999999;
            height: 8px;
            background: #f0f0f0;
            border-radius: 4px;
        }
        QSlider::handle:horizontal {
            background: #4a86e8;
            border: none;
            width: 18px;
            height: 18px;
            margin: -6px 0;
            border-radius: 9px;
        }
        QSlider::handle:horizontal:hover {
            background: #5c94f0;
        }
    """)
    self.intensity_slider.setMinimum(1)
    self.intensity_slider.setMaximum(100)
    self.intensity_slider.setValue(100)
    self.intensity_slider.valueChanged.connect(self.intensity_changed)
    intensity_layout.addWidget(self.intensity_slider)
    self.intensity_label = QLabel("<b>100%</b>")
    intensity_layout.addWidget(self.intensity_label)
    
    keyboard_tab_layout.addLayout(intensity_layout)
    
    # Region intensity slider (for selected keys)
    region_layout = QHBoxLayout()
    region_layout.addWidget(QLabel("Region Intensity:"))
    self.region_intensity_slider = QSlider(Qt.Horizontal)
    self.region_intensity_slider.setMinimum(1)
    self.region_intensity_slider.setMaximum(100)
    self.region_intensity_slider.setValue(100)
    self.region_intensity_slider.valueChanged.connect(
        lambda v: self.region_intensity_changed(v))
    region_layout.addWidget(self.region_intensity_slider)
    self.region_intensity_label = QLabel("100%")
    region_layout.addWidget(self.region_intensity_label)
    # -- Apply to selection button --
    self.apply_region_button = QPushButton("Apply to Selection")
    self.apply_region_button.clicked.connect(self.apply_color_to_selection)
    region_layout.addWidget(self.apply_region_button)
    
    keyboard_tab_layout.addLayout(region_layout)
    
    # Add the keyboard tab
    control_tabs.addTab(keyboard_tab, "Keyboard")
    
    # Tab 2: Color Controls
    color_tab = QWidget()
    color_tab_layout = QVBoxLayout(color_tab)
    
    # Color selection
    color_group = QGroupBox("Color Selection")
    color_group.setStyleSheet("""
        QGroupBox {
            font-weight: bold;
            border: 1px solid #3f3f46;
            border-radius: 6px;
            margin-top: 12px;
            padding-top: 12px;
            background-color: #252529;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
            color: #e0e0e0;
        }
    """)
    color_layout = QVBoxLayout()
    color_layout.setSpacing(12)
    color_layout.setContentsMargins(10, 10, 10, 10)
    
    # Current color display and picker in one row
    current_color_layout = QHBoxLayout()
    current_color_layout.addWidget(QLabel("Current:"))
    self.color_display = ColorDisplay(self.current_color)
    self.color_display.clicked.connect(self.show_color_dialog)
    current_color_layout.addWidget(self.color_display)
    self.select_color_button = QPushButton("Pick")
    self.select_color_button.setStyleSheet("""
        QPushButton {
            background-color: #007acc;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 6px 10px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #1c87d9;
        }
    """)
    self.select_color_button.clicked.connect(self.show_color_dialog)
    current_color_layout.addWidget(self.select_color_button)
    
    # Add 'Create Preset' button
    self.create_preset_btn = QPushButton("Save as Preset")
    self.create_preset_btn.setStyleSheet("""
        QPushButton {
            background-color: #0e639c;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 6px 10px;
        }
        QPushButton:hover {
            background-color: #127aba;
        }
    """)
    self.create_preset_btn.clicked.connect(self.create_color_preset)
    current_color_layout.addWidget(self.create_preset_btn)
    
    color_layout.addLayout(current_color_layout)
    
    # RGB sliders
    for color, label in [("Red", "R:"), ("Green", "G:"), ("Blue", "B:")]:
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel(label))
        slider = QSlider(Qt.Horizontal)
        slider.setObjectName(f"{color.lower()}_slider")
        slider.setMinimum(0)
        slider.setMaximum(255)
        if color == "Green":
            slider.setValue(255)  # Default is green
        else:
            slider.setValue(0)
        slider.valueChanged.connect(self.color_sliders_changed)
        slider_layout.addWidget(slider)
        setattr(self, f"{color.lower()}_slider", slider)
        slider_layout.addWidget(QLabel("0" if color != "Green" else "255"))
        color_layout.addLayout(slider_layout)
    
    # Preset color buttons
    preset_layout = QGridLayout()
    preset_colors = [
        ("Red", QColor(255, 0, 0)), ("Green", QColor(0, 255, 0)), 
        ("Blue", QColor(0, 0, 255)), ("Yellow", QColor(255, 255, 0)),
        ("Cyan", QColor(0, 255, 255)), ("Magenta", QColor(255, 0, 255)),
        ("White", QColor(255, 255, 255)), ("Orange", QColor(255, 165, 0)),
        ("Purple", QColor(128, 0, 128)), ("Pink", QColor(255, 192, 203))
    ]
    
    # Add preset buttons in a grid (2 rows, 5 buttons per row)
    for i, (name, color) in enumerate(preset_colors):
        preset_btn = QPushButton("")  # No text, just color
        # Modern styled buttons with rounded corners
        preset_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color.name()};
                border: none;
                border-radius: 4px;
                min-height: 24px;
                max-height: 24px;
            }}
            QPushButton:hover {{
                border: 2px solid white;
            }}
        """)
        preset_btn.setToolTip(name)
        preset_btn.clicked.connect(lambda checked, c=color: self.select_color(c))
        preset_layout.addWidget(preset_btn, i // 5, i % 5)
    
    color_layout.addLayout(preset_layout)
    
    # Add the color group to the color tab
    color_group.setLayout(color_layout)
    color_tab_layout.addWidget(color_group)
    
    # Add the color tab
    control_tabs.addTab(color_tab, "Colors")
    
    # Tab 3: Effects
    effects_tab = QWidget()
    effects_tab_layout = QVBoxLayout(effects_tab)
    
    # Create a group for effects
    effects_group = QGroupBox("Effects")
    effects_layout = QVBoxLayout()
    
    # Rainbow effect button
    rainbow_btn = QPushButton("Rainbow Effect")
    rainbow_btn.setStyleSheet("""
        QPushButton {
            background-color: #2ba9e0;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 10px;
            font-weight: bold;
            margin: 4px 0;
        }
        QPushButton:hover {
            background-color: #3db5e9;
        }
        QPushButton:pressed {
            background-color: #1e9cd3;
        }
    """)
    rainbow_btn.clicked.connect(self.effects.set_rainbow_colors)
    effects_layout.addWidget(rainbow_btn)
    
    # Wave effect button
    wave_btn = QPushButton("Wave Effect")
    wave_btn.setStyleSheet("""
        QPushButton {
            background-color: #4a86e8;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 10px;
            font-weight: bold;
            margin: 4px 0;
        }
        QPushButton:hover {
            background-color: #5c94f0;
        }
        QPushButton:pressed {
            background-color: #3d78da;
        }
    """)
    wave_btn.clicked.connect(lambda: self.effects.set_wave_effect(direction="horizontal"))
    effects_layout.addWidget(wave_btn)
    
    # Function key toggle
    function_btn = QPushButton("Function Keys")
    function_btn.setCheckable(True)
    function_btn.setStyleSheet("""
        QPushButton {
            background-color: #333337;
            color: #e0e0e0;
            border: 1px solid #3f3f46;
            border-radius: 4px;
            padding: 10px;
            font-weight: bold;
            margin: 4px 0;
        }
        QPushButton:hover {
            background-color: #3f3f46;
        }
        QPushButton:checked {
            background-color: #ff5252;
            color: white;
        }
    """)
    function_btn.clicked.connect(lambda checked: self.toggle_function_keys(checked))
    effects_layout.addWidget(function_btn)
    
    # Typing preset button
    typing_btn = QPushButton("Typing Preset")
    typing_btn.clicked.connect(self.apply_typing_preset)
    effects_layout.addWidget(typing_btn)
    
    # Gaming preset button
    gaming_btn = QPushButton("Gaming Preset (WASD)")
    gaming_btn.clicked.connect(self.apply_gaming_preset)
    effects_layout.addWidget(gaming_btn)
    
    effects_group.setLayout(effects_layout)
    effects_tab_layout.addWidget(effects_group)
    
    # Add the effects tab
    control_tabs.addTab(effects_tab, "Effects")
    
    # Tab 4: Shortcuts
    shortcuts_tab = QWidget()
    shortcuts_tab_layout = QVBoxLayout(shortcuts_tab)
    
    # Shortcut monitoring controls
    shortcut_group = QGroupBox("Shortcut Monitoring")
    shortcut_layout = QVBoxLayout()
    
    # Start/stop monitoring buttons
    monitor_layout = QHBoxLayout()
    start_monitor_btn = QPushButton("Start Monitoring")
    start_monitor_btn.clicked.connect(self.start_shortcut_monitoring)
    monitor_layout.addWidget(start_monitor_btn)
    
    stop_monitor_btn = QPushButton("Stop Monitoring")
    stop_monitor_btn.clicked.connect(self.stop_shortcut_monitoring)
    monitor_layout.addWidget(stop_monitor_btn)
    
    shortcut_layout.addLayout(monitor_layout)
    
    # Global hotkey monitoring
    global_layout = QHBoxLayout()
    global_monitor_btn = QPushButton("Start Global Monitoring")
    global_monitor_btn.clicked.connect(self.keyboard_monitor.start_global_shortcut_monitor)
    global_layout.addWidget(global_monitor_btn)
    
    global_stop_btn = QPushButton("Stop Global Monitoring")
    global_stop_btn.clicked.connect(self.keyboard_monitor.stop_global_shortcut_monitor)
    global_layout.addWidget(global_stop_btn)
    
    shortcut_layout.addLayout(global_layout)
    
    shortcut_group.setLayout(shortcut_layout)
    shortcuts_tab_layout.addWidget(shortcut_group)
    
    # Add the shortcuts tab
    control_tabs.addTab(shortcuts_tab, "Shortcuts")
    
    # Tab 5: System Monitoring
    system_tab = QWidget()
    system_tab_layout = QVBoxLayout(system_tab)
    
    # System monitoring group
    system_monitor_group = QGroupBox("System Monitoring")
    system_monitor_layout = QVBoxLayout()

    # Add monitoring selection dropdown
    system_monitor_layout.addWidget(QLabel("Select Monitoring:"))
    self.monitor_combo = QComboBox()
    self.monitor_combo.addItems([
        "CPU Usage", 
        "RAM Usage",
        "Battery Status",
        "All Metrics"
    ])
    system_monitor_layout.addWidget(self.monitor_combo)

    # Add update interval slider
    update_interval_layout = QHBoxLayout()
    update_interval_layout.addWidget(QLabel("Update Interval:"))
    self.update_interval_slider = QSlider(Qt.Horizontal)
    self.update_interval_slider.setMinimum(1)
    self.update_interval_slider.setMaximum(10)
    self.update_interval_slider.setValue(2)
    self.update_interval_slider.setTickPosition(QSlider.TicksBelow)
    self.update_interval_slider.setTickInterval(1)
    update_interval_layout.addWidget(self.update_interval_slider)
    self.update_interval_label = QLabel("2s")
    self.update_interval_slider.valueChanged.connect(
        lambda v: self.update_interval_label.setText(f"{v}s")
    )
    update_interval_layout.addWidget(self.update_interval_label)
    system_monitor_layout.addLayout(update_interval_layout)

    # Start/stop monitoring buttons
    monitor_buttons_layout = QHBoxLayout()

    self.start_monitor_btn = QPushButton("Start Monitoring")
    self.start_monitor_btn.clicked.connect(self.start_system_monitoring)
    monitor_buttons_layout.addWidget(self.start_monitor_btn)

    self.stop_monitor_btn = QPushButton("Stop Monitoring")
    self.stop_monitor_btn.clicked.connect(self.stop_system_monitoring)
    monitor_buttons_layout.addWidget(self.stop_monitor_btn)

    system_monitor_layout.addLayout(monitor_buttons_layout)

    # Add the group to the system tab
    system_monitor_group.setLayout(system_monitor_layout)
    system_tab_layout.addWidget(system_monitor_group)
    
    # Add the system monitoring tab
    control_tabs.addTab(system_tab, "System")
    
    # Finalize the layout
    controls_layout.addLayout(main_controls, 2)  # 2 parts for the tab area
    controls_layout.addLayout(color_controls, 1)  # 1 part for the color controls
    
    # Add the widgets to the main layout
    main_layout.addWidget(keyboard_widget, 7)
    main_layout.addWidget(controls_widget, 3)
    
    # Set the main widget
    self.setCentralWidget(main_widget)
    
    # Create a status bar
    self.statusBar().showMessage("Ready")

    # whenever the user picks a different config → load & apply immediately
    self.config_combo.currentIndexChanged.connect(self.on_config_changed)

    # Connect the combobox selection change - but make sure this isn't the issue
    self.config_combo.currentIndexChanged.connect(
        lambda idx: self.load_config(self.config_combo.currentText()) 
        if idx >= 0 and not hasattr(self, '_currently_loading') else None
    )

def toggle_keyboard_leds(self):
    """Toggle LEDs on/off for selected keys or all keys"""
    if not hasattr(self, 'leds_off'):
        self.leds_off = {}
    
    # If selection is active, toggle selected keys
    if self.selected_keys:
        for key in self.selected_keys:
            if key.color.red() == 0 and key.color.green() == 0 and key.color.blue() == 0:
                # LED is off, restore original color
                if key.index in self.leds_off:
                    key.setKeyColor(self.leds_off[key.index])
                else:
                    key.setKeyColor(QColor(0, 255, 0))  # Default green
            else:
                # LED is on, turn off and save color
                self.leds_off[key.index] = QColor(key.color)
                key.setKeyColor(QColor(0, 0, 0))  # Black = off
    else:
        # Toggle all keys
        is_on = self.led_toggle.isChecked()
        if is_on:
            # Turn on LEDs, restore from saved colors or default
            for key in self.keys:
                if key.index in self.leds_off:
                    key.setKeyColor(self.leds_off[key.index])
                else:
                    # No saved color, use default
                    key.setKeyColor(QColor(0, 255, 0))
        else:
            # Turn off LEDs, save current colors
            for key in self.keys:
                if key.color.red() > 0 or key.color.green() > 0 or key.color.blue() > 0:
                    self.leds_off[key.index] = QColor(key.color)
                key.setKeyColor(QColor(0, 0, 0))

    # Update keyboard
    if self.auto_reload and self.keyboard.connected:
        self.send_config()

def toggle_function_keys(self, checked):
    """Toggle function key highlighting on/off"""
    if checked:
        # Highlight function keys using current color
        self.effects.set_function_key_colors(
            (self.current_color.red(), self.current_color.green(), self.current_color.blue())
        )
    else:
        # Restore function keys to default
        if hasattr(self, 'base_colors'):
            for key in self.keys:
                if key.key_name in self.effects.function_keys:
                    if key.index in self.base_colors:
                        key.setKeyColor(self.base_colors[key.index])
            
            # Update keyboard
            if self.auto_reload and self.keyboard.connected:
                self.send_config()

def create_color_preset(self):
    """Create a custom color preset from current color"""
    name, ok = QInputDialog.getText(self, "Create Color Preset", "Preset Name:")
    if ok and name:
        color = self.current_color
        # Add to preset_colors list
        preset_layout = self.findChild(QGridLayout, "preset_layout")
        if preset_layout:
            row = preset_layout.rowCount()
            col = preset_layout.columnCount() 
            if col >= 5:
                col = 0
                row += 1
            
            # Create new preset button
            preset_btn = QPushButton("")
            preset_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color.name()};
                    border: none;
                    border-radius: 4px;
                    min-height: 24px;
                    max-height: 24px;
                }}
                QPushButton:hover {{
                    border: 2px solid white;
                }}
            """)
            preset_btn.setToolTip(name)
            preset_btn.clicked.connect(lambda checked, c=color: self.select_color(c))
            preset_layout.addWidget(preset_btn, row, col)
            
            # Notify user
            self.statusBar().showMessage(f"Color preset '{name}' created", 3000)
