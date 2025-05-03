from PyQt5.QtWidgets import QFrame
from PyQt5.QtGui import QColor
from PyQt5.QtCore import pyqtSignal

class ColorDisplay(QFrame):
    """Widget for displaying a color with clickable functionality"""
    clicked = pyqtSignal()
    
    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.color = color
        self.setMinimumSize(60, 30)
        self.setMaximumHeight(30)
        self.updateColor(color)
    
    def updateColor(self, color):
        """Update the displayed color"""
        self.color = color
        self.setStyleSheet(f"background-color: rgb({color.red()}, {color.green()}, {color.blue()}); border: 1px solid black;")
    
    def mousePressEvent(self, event):
        """Handle mouse press events by emitting clicked signal"""
        self.clicked.emit()
