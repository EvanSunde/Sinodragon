"""
Color display widget for showing selected colors.
"""

from PyQt5.QtWidgets import QFrame
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor

class ColorDisplay(QFrame):
    """Widget that displays a color and emits a signal when clicked"""
    clicked = pyqtSignal()
    
    def __init__(self, color=Qt.green, parent=None):
        super().__init__(parent)
        self.color = QColor(color)
        self.setMinimumSize(60, 30)
        self.setFrameShape(QFrame.Box)
        self.setFrameShadow(QFrame.Sunken)
        self.updateStyle()
        
    def setColor(self, color):
        """Set the display color"""
        self.color = QColor(color)
        self.updateStyle()
        
    def updateStyle(self):
        """Update the display style based on the current color"""
        self.setStyleSheet(f"background-color: rgb({self.color.red()}, {self.color.green()}, {self.color.blue()});")
    
    def mousePressEvent(self, event):
        """Handle mouse press events and emit the clicked signal"""
        self.clicked.emit()
        super().mousePressEvent(event) 