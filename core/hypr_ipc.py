import os
import socket
import time
import glob
import logging
from typing import Callable, Optional


class HyprlandIPCClient:
    def __init__(self, on_active_window: Callable[[str], None]):
        self.on_active_window = on_active_window
        self.socket_path: Optional[str] = None
        self.sock: Optional[socket.socket] = None
        self.running = False
        self._next_reconnect_ts = 0.0

        sig = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
        runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
        if sig and runtime_dir:
            self.socket_path = os.path.join(runtime_dir, "hypr", sig, ".socket2.sock")
        elif sig:
            # Fallback to common legacy tmp path
            self.socket_path = f"/tmp/hypr/{sig}/.socket2.sock"
        else:
            # Try to discover a socket path without using hyprctl
            self.socket_path = self._discover_socket_path()
            if not self.socket_path:
                logging.getLogger(__name__).warning("Hyprland instance signature not found and no socket discovered; IPC disabled")

    def start(self) -> bool:
        if not self.socket_path:
            logging.getLogger(__name__).error("Hyprland socket path unavailable; cannot start IPC")
            return False
        self.running = True
        logging.getLogger(__name__).info(f"Starting Hyprland IPC on {self.socket_path}")
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
                # Re-discover socket if needed
                if not self.socket_path or not os.path.exists(self.socket_path):
                    self.socket_path = self._discover_socket_path()
                    if not self.socket_path or not os.path.exists(self.socket_path):
                        # Schedule next attempt and return quietly
                        self._next_reconnect_ts = now + 1.0
                        logging.getLogger(__name__).debug("Hyprland IPC: socket not found; will retry discovery")
                        return
                logging.getLogger(__name__).debug("Hyprland IPC: attempting socket connect")
                self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.sock.settimeout(0.1)
                try:
                    self.sock.connect(self.socket_path)
                except FileNotFoundError:
                    # Socket disappeared; schedule reconnect
                    self.sock.close()
                    self.sock = None
                    self._next_reconnect_ts = now + 1.0
                    logging.getLogger(__name__).warning("Hyprland IPC: socket path missing; retrying later")
                    return
                self.sock.settimeout(0.0)  # non-blocking
                logging.getLogger(__name__).info("Hyprland IPC: connected")
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
                logging.getLogger(__name__).warning("Hyprland IPC: socket closed; scheduling reconnect")
                return
            for line in data.decode("utf-8", errors="ignore").splitlines():
                logging.getLogger(__name__).debug(f"Hyprland IPC line: {line}")
                if line.startswith("activewindow>>"):
                    payload = line.split(">>", 1)[1].strip()
                    if payload and payload != ",":
                        app_class = payload.split(",")[0]
                        if app_class:
                            logging.getLogger(__name__).info(f"Hyprland active window: {app_class}")
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
                logging.getLogger(__name__).warning("Hyprland IPC: exception; scheduling reconnect")

    def _discover_socket_path(self) -> Optional[str]:
        """Attempt to locate a Hyprland events socket without using hyprctl."""
        try:
            candidates = []
            runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
            if runtime_dir:
                candidates.extend(glob.glob(os.path.join(runtime_dir, "hypr", "*", ".socket2.sock")))
            # Fallback legacy location
            candidates.extend(glob.glob("/tmp/hypr/*/.socket2.sock"))
            if candidates:
                # Choose the most recently modified candidate
                candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
                return candidates[0]
        except Exception:
            pass
        return None


