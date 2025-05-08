"""
Custom event handling for keyboard events.
"""

from PyQt5.QtCore import QEvent

class CustomKeyEvent(QEvent):
    """Custom event for key presses from alternative input sources"""
    KeyPress = QEvent.Type(QEvent.registerEventType())
    KeyRelease = QEvent.Type(QEvent.registerEventType()) 
    
    def __init__(self, event_type, key_name):
        super().__init__(event_type)
        self.key_name = key_name 