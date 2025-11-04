from typing import List, Tuple

from keyboard_controller import KeyboardController


class LightingController:
    def __init__(self):
        self.kb = KeyboardController()

    def ensure_connected(self) -> bool:
        if self.kb.connected:
            return True
        return self.kb.connect()

    def apply(self, colors: List[Tuple[int, int, int]], intensity: float = 1.0) -> bool:
        if not self.ensure_connected():
            return False
        return self.kb.send_led_config(colors, intensity)


