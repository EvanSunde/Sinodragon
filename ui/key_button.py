from PyQt5.QtWidgets import QPushButton
from PyQt5.QtGui import QColor

class KeyButton(QPushButton):
    def __init__(self, key_name, index, parent=None):
        super().__init__(key_name, parent)
        self.key_name = key_name
        self.index = index
        self.color = QColor(0, 255, 0)  # Default color: green
        self.setFixedSize(60, 60)
        self.selected = False
        self.updateStyle()
        
    def setKeyColor(self, color):
        """Set the button color"""
        self.color = color
        self.updateStyle()
    
    def setSelected(self, selected):
        """Set selection state"""
        self.selected = selected
        self.updateStyle()
    
    def updateStyle(self):
        """Update the button style to reflect the current color and selection state"""
        r, g, b = self.color.red(), self.color.green(), self.color.blue()
        text_color = "#000000" if (r + g + b) > 380 else "#FFFFFF"
        
        border = "3px solid #FFFFFF" if self.selected else "1px solid #222222"
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: rgb({r}, {g}, {b});
                color: {text_color};
                border: {border};
                border-radius: 5px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: rgb({min(r+20, 255)}, {min(g+20, 255)}, {min(b+20, 255)});
                border-width: 2px;
            }}
        """)
