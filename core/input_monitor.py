import select
from typing import Callable, Set


class EvdevInputMonitor:
    def __init__(self, on_press: Callable[[str], None], on_release: Callable[[str], None]):
        self.on_press = on_press
        self.on_release = on_release
        self.running = False
        self.devices = []
        self.pressed: Set[str] = set()

    def start(self) -> bool:
        try:
            import evdev
            from evdev import InputDevice, ecodes
            self.devices = []
            for path in evdev.list_devices():
                try:
                    dev = InputDevice(path)
                    caps = dev.capabilities()
                    if ecodes.EV_KEY in caps:
                        self.devices.append(dev)
                except Exception:
                    continue
            self.running = len(self.devices) > 0
            return self.running
        except Exception:
            return False

    def stop(self) -> None:
        self.running = False
        self.devices = []

    def poll(self, timeout: float = 0.05) -> None:
        if not self.running or not self.devices:
            return
        try:
            import evdev
            from evdev import categorize, ecodes
            r, _, _ = select.select(self.devices, [], [], timeout)
            for dev in r:
                for event in dev.read():
                    if event.type != ecodes.EV_KEY:
                        continue
                    kev = categorize(event)
                    code = kev.keycode if isinstance(kev.keycode, str) else None
                    if not code:
                        continue
                    # map common modifiers and letters
                    name = _keycode_to_name(code)
                    if not name:
                        continue
                    if kev.keystate == 1:
                        if name not in self.pressed:
                            self.pressed.add(name)
                            self.on_press(name)
                    elif kev.keystate == 0:
                        if name in self.pressed:
                            self.pressed.remove(name)
                            self.on_release(name)
        except Exception:
            pass


def _keycode_to_name(code: str) -> str:
    table = {
        'KEY_LEFTCTRL': 'Ctrl', 'KEY_RIGHTCTRL': 'Ctrl',
        'KEY_LEFTALT': 'Alt', 'KEY_RIGHTALT': 'Alt',
        'KEY_LEFTSHIFT': 'Shift', 'KEY_RIGHTSHIFT': 'Shift',
        'KEY_LEFTMETA': 'Win', 'KEY_RIGHTMETA': 'Win',
        'KEY_SPACE': 'Space', 'KEY_TAB': 'Tab', 'KEY_ENTER': 'Enter',
        'KEY_BACKSPACE': 'Bksp', 'KEY_ESC': 'Esc',
    }
    if code in table:
        return table[code]
    if code.startswith('KEY_') and len(code) == 5:
        ch = code[-1]
        if ch.isalnum():
            return ch.upper()
    return ''


