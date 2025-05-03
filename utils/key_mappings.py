from PyQt5.QtCore import Qt

# Define a key mapping between Qt key constants and our keyboard layout key names
QT_KEY_MAP = {
    Qt.Key_Control: "Ctrl",
    Qt.Key_Shift: "Shift",
    Qt.Key_Alt: "Alt",
    Qt.Key_Meta: "Win",
    Qt.Key_Super_L: "Win",
    Qt.Key_Super_R: "Win",
    
    # Letters
    Qt.Key_A: "A", Qt.Key_B: "B", Qt.Key_C: "C", Qt.Key_D: "D",
    Qt.Key_E: "E", Qt.Key_F: "F", Qt.Key_G: "G", Qt.Key_H: "H",
    Qt.Key_I: "I", Qt.Key_J: "J", Qt.Key_K: "K", Qt.Key_L: "L",
    Qt.Key_M: "M", Qt.Key_N: "N", Qt.Key_O: "O", Qt.Key_P: "P",
    Qt.Key_Q: "Q", Qt.Key_R: "R", Qt.Key_S: "S", Qt.Key_T: "T",
    Qt.Key_U: "U", Qt.Key_V: "V", Qt.Key_W: "W", Qt.Key_X: "X",
    Qt.Key_Y: "Y", Qt.Key_Z: "Z",
    
    # Numbers
    Qt.Key_0: "0", Qt.Key_1: "1", Qt.Key_2: "2", Qt.Key_3: "3",
    Qt.Key_4: "4", Qt.Key_5: "5", Qt.Key_6: "6", Qt.Key_7: "7",
    Qt.Key_8: "8", Qt.Key_9: "9",
    
    # Function keys
    Qt.Key_F1: "F1", Qt.Key_F2: "F2", Qt.Key_F3: "F3", Qt.Key_F4: "F4",
    Qt.Key_F5: "F5", Qt.Key_F6: "F6", Qt.Key_F7: "F7", Qt.Key_F8: "F8",
    Qt.Key_F9: "F9", Qt.Key_F10: "F10", Qt.Key_F11: "F11", Qt.Key_F12: "F12",
    
    # Other common keys
    Qt.Key_Escape: "Esc",
    Qt.Key_Tab: "Tab",
    Qt.Key_CapsLock: "Caps",
    Qt.Key_Backspace: "Bksp",
    Qt.Key_Return: "Enter",
    Qt.Key_Space: "Space",
    Qt.Key_Insert: "Ins",
    Qt.Key_Delete: "Del",
    Qt.Key_Home: "Home",
    Qt.Key_End: "End",
    Qt.Key_PageUp: "PgUp",
    Qt.Key_PageDown: "PgDn",
    Qt.Key_Left: "←",
    Qt.Key_Right: "→",
    Qt.Key_Up: "↑",
    Qt.Key_Down: "↓",
    Qt.Key_Print: "PrtSc",
    Qt.Key_ScrollLock: "ScrLk",
    Qt.Key_Pause: "Pause",
    
    # Special characters
    Qt.Key_Backslash: "\\",
    Qt.Key_BracketLeft: "[",
    Qt.Key_BracketRight: "]",
    Qt.Key_Semicolon: ";",
    Qt.Key_Apostrophe: "'",
    Qt.Key_Comma: ",",
    Qt.Key_Period: ".",
    Qt.Key_Slash: "/",
    Qt.Key_Minus: "-",
    Qt.Key_Equal: "=",
    Qt.Key_QuoteLeft: "`"
}

# Create utils/__init__.py
