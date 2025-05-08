"""
UI layout for the keyboard and related components.
"""

import logging
from PyQt5.QtWidgets import QWidget, QGridLayout, QHBoxLayout, QVBoxLayout, QLabel, QSlider
from PyQt5.QtCore import Qt

from ui.key_button import KeyButton
from ui.key_mapping import DEFAULT_LAYOUT

logger = logging.getLogger(__name__)

class KeyboardLayout(QWidget):
    """Widget representing the keyboard layout with keys"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.keys = []
        self.setupUI()
    
    def setupUI(self):
        """Set up the keyboard layout UI"""
        container = QVBoxLayout(self)
        grid = QGridLayout()
        grid.setSpacing(5)
        
        # Create buttons for each key in the layout
        key_index = 0
        
        for col, column in enumerate(DEFAULT_LAYOUT):
            for row, key_name in enumerate(column):
                if key_name != "NAN":
                    key = KeyButton(key_name, key_index, self.parent_app)
                    grid.addWidget(key, row, col)
                    self.keys.append(key)
                    key_index += 1
                else:
                    # Empty placeholder for NAN keys
                    placeholder = QWidget()
                    placeholder.setFixedSize(60, 60)
                    grid.addWidget(placeholder, row, col)
        
        container.addLayout(grid)
        
        # Global brightness control
        brightness_layout = QHBoxLayout()
        brightness_layout.addWidget(QLabel("Master Brightness:"))
        
        self.intensity_slider = QSlider(Qt.Horizontal)
        self.intensity_slider.setMinimum(0)
        self.intensity_slider.setMaximum(100)
        self.intensity_slider.setValue(100)  # Default to full brightness
        self.intensity_slider.setTickPosition(QSlider.TicksBelow)
        self.intensity_slider.setTickInterval(10)
        
        # Connect signal if parent has the handler
        if hasattr(self.parent_app, 'intensity_changed'):
            self.intensity_slider.valueChanged.connect(self.parent_app.intensity_changed)
        
        brightness_layout.addWidget(self.intensity_slider)
        
        # Intensity value label
        self.intensity_label = QLabel("100%")
        brightness_layout.addWidget(self.intensity_label)
        
        container.addLayout(brightness_layout)
        
    def clear_keyboard(self):
        """Set all keys to black"""
        for key in self.keys:
            key.setKeyColor(Qt.black)
            
    def get_intensity(self):
        """Get the current brightness value (0-100)"""
        return self.intensity_slider.value()
    
    def set_intensity(self, value):
        """Set the brightness slider value"""
        self.intensity_slider.setValue(value)
        self.intensity_label.setText(f"{value}%")
    
    def update_intensity_label(self, value):
        """Update the intensity label with the current value"""
        self.intensity_label.setText(f"{value}%") 