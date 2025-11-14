from typing import List, Tuple

from PyQt5.QtGui import QColor


def _hsv_to_rgb_tuple(h: float, s: float, v: float) -> Tuple[int, int, int]:
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return int(r * 255), int(g * 255), int(b * 255)


def apply_ocean(app) -> None:
    n = len(app.keys)
    for i, key in enumerate(app.keys):
        h = 0.55 + 0.1 * (i / max(1, n))
        r, g, b = _hsv_to_rgb_tuple(h % 1.0, 0.7, 1.0)
        key.setKeyColor(QColor(r, g, b))
    app.apply_ui_colors()


def apply_sunset(app) -> None:
    n = len(app.keys)
    for i, key in enumerate(app.keys):
        h = 0.03 + 0.1 * (i / max(1, n))
        r, g, b = _hsv_to_rgb_tuple(h % 1.0, 0.9, 1.0)
        key.setKeyColor(QColor(r, g, b))
    app.apply_ui_colors()


def apply_matrix(app) -> None:
    for key in app.keys:
        key.setKeyColor(QColor(0, 20, 0))
    for i, key in enumerate(app.keys):
        if i % 3 == 0:
            key.setKeyColor(QColor(0, 255, 70))
    app.apply_ui_colors()


def apply_fire(app) -> None:
    n = len(app.keys)
    for i, key in enumerate(app.keys):
        h = 0.02 + 0.05 * (i % 10) / 10.0
        r, g, b = _hsv_to_rgb_tuple(h, 1.0, 1.0)
        key.setKeyColor(QColor(r, g, b))
    app.apply_ui_colors()


# Application-focused presets
def apply_firefox_preset(app) -> None:
    # Common keys: T (new tab), W (close), R (reload), L (location), H/J/K (nav), F (find)
    _clear(app)
    color = QColor(255, 140, 0)
    for name in ["T", "W", "R", "L", "F", "H", "J", "K"]:
        _hl(app, name, color)
    # Arrows for navigation
    for name in ["←", "→", "↑", "↓"]:
        _hl(app, name, QColor(80, 160, 255))
    app.apply_ui_colors()


def apply_dolphin_preset(app) -> None:
    # Common keys: F3 (split), F4 (terminal), Ctrl+L (location), Space (preview)
    _clear(app)
    for name in ["F3", "F4", "Space", "L"]:
        _hl(app, name, QColor(0, 200, 120))
    # Navigation keys
    for name in ["Home", "End", "PgUp", "PgDn", "←", "→", "↑", "↓"]:
        _hl(app, name, QColor(80, 160, 255))
    app.apply_ui_colors()


def apply_vscode_preset(app) -> None:
    # Common keys: P (Go to), F (Find), G (SCM), B (Explorer), ` (terminal)
    _clear(app)
    for name in ["P", "F", "G", "B", "`"]:
        _hl(app, name, QColor(0, 200, 120))
    for name in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"]:
        _hl(app, name, QColor(255, 180, 70))
    app.apply_ui_colors()


def _hl(app, key_name: str, color: QColor) -> None:
    # Highlight by key_name using app's helper
    try:
        app._highlight_key(key_name, color)
    except Exception:
        pass


def _clear(app) -> None:
    for key in app.keys:
        key.setKeyColor(QColor(0, 0, 0))

