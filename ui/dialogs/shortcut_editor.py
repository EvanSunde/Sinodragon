"""
Dialog for editing keyboard shortcuts.
"""

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton

class ShortcutEditorDialog(QDialog):
    """Dialog for editing keyboard shortcuts"""
    def __init__(self, parent, shortcut="", description=""):
        super().__init__(parent)
        self.setWindowTitle("Edit Shortcut")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Shortcut input
        shortcut_layout = QHBoxLayout()
        shortcut_layout.addWidget(QLabel("Shortcut:"))
        
        self.shortcut_edit = QLineEdit(shortcut)
        shortcut_layout.addWidget(self.shortcut_edit)
        
        layout.addLayout(shortcut_layout)
        
        # Description input
        description_layout = QHBoxLayout()
        description_layout.addWidget(QLabel("Description:"))
        
        self.description_edit = QLineEdit(description)
        description_layout.addWidget(self.description_edit)
        
        layout.addLayout(description_layout)
        
        # Help text
        layout.addWidget(QLabel("Format examples: Ctrl+C, Alt+Tab, Ctrl+Shift+N"))
        
        # Buttons
        button_layout = QHBoxLayout()
        
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.accept)
        button_layout.addWidget(save_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout) 