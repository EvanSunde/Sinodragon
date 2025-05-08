"""
Dialog for managing modifier key colors.
"""

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QGridLayout, QLabel, QPushButton, QColorDialog
from PyQt5.QtGui import QColor

from ui.color_display import ColorDisplay

class ModifierColorsDialog(QDialog):
    """Dialog for managing modifier key colors"""
    def __init__(self, parent, shortcut_lighting):
        super().__init__(parent)
        self.shortcut_lighting = shortcut_lighting
        self.setWindowTitle("Modifier Key Colors")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Choose colors for each modifier key:"))
        
        grid = QGridLayout()
        row = 0
        
        # Create a display and change button for each modifier key
        self.color_displays = {}
        for modifier, color in self.shortcut_lighting.modifier_colors.items():
            # Label for the modifier
            grid.addWidget(QLabel(modifier + ":"), row, 0)
            
            # Color display
            color_display = ColorDisplay(color)
            grid.addWidget(color_display, row, 1)
            self.color_displays[modifier] = color_display
            
            # Change button
            change_btn = QPushButton("Change...")
            change_btn.clicked.connect(lambda checked, mod=modifier: self.change_modifier_color(mod))
            grid.addWidget(change_btn, row, 2)
            
            row += 1
        
        layout.addLayout(grid)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
    
    def change_modifier_color(self, modifier):
        """Change the color for a specific modifier key"""
        current_color = self.shortcut_lighting.get_modifier_color(modifier)
        new_color = QColorDialog.getColor(current_color, self, f"Select Color for {modifier}")
        
        if new_color.isValid():
            self.shortcut_lighting.set_modifier_color(modifier, new_color)
            self.color_displays[modifier].setColor(new_color) 