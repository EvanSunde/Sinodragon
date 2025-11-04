import os
import socket
import time
from typing import Callable, Optional


class HyprlandIPCClient:
    def __init__(self, on_active_window: Callable[[str], None]):
        self.on_active_window = on_active_window
        self.socket_path: Optional[str] = None
        self.sock: Optional[socket.socket] = None
        self.running = False
        self._next_reconnect_ts = 0.0

        sig = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
        if sig:
            self.socket_path = f"/tmp/hypr/{sig}/.socket2.sock"

    def start(self) -> bool:
        if not self.socket_path:
            return False
        self.running = True
        # non-threaded: expose a poll() to integrate with QTimer if needed
        return True

    def stop(self) -> None:
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def poll(self, timeout: float = 0.0) -> None:
        if not self.running or not self.socket_path:
            return
        try:
            if not self.sock:
                # respect reconnect backoff without sleeping in UI thread
                import time as _t
                now = _t.time()
                if now < self._next_reconnect_ts:
                    return
                self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.sock.settimeout(0.1)
                self.sock.connect(self.socket_path)
                self.sock.settimeout(0.0)  # non-blocking
            self.sock.settimeout(timeout)
            try:
                data = self.sock.recv(4096)
            except BlockingIOError:
                return
            if not data:
                # reconnect next round
                try:
                    self.sock.close()
                except Exception:
                    pass
                self.sock = None
                import time as _t
                self._next_reconnect_ts = _t.time() + 0.5
                return
            for line in data.decode("utf-8", errors="ignore").splitlines():
                if line.startswith("activewindow>>"):
                    payload = line.split(">>", 1)[1].strip()
                    if payload and payload != ",":
                        app_class = payload.split(",")[0]
                        if app_class:
                            self.on_active_window(app_class)
        except (socket.timeout, BlockingIOError):
            pass
        except Exception:
            # drop and reconnect later
            try:
                if self.sock:
                    self.sock.close()
            finally:
                self.sock = None
                import time as _t
                self._next_reconnect_ts = _t.time() + 0.5


