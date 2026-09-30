"""Single InputSession shared by USB WebSocket and Bluetooth transports."""
from __future__ import annotations

import threading
from typing import Any

from windows.transport.input_dispatch import InputSession


class SharedInput:
    USB = "usb"
    BT = "bt"

    def __init__(self) -> None:
        self._session = InputSession()
        self._lock = threading.RLock()
        self.owner: str | None = None
        self.usb_connected = False
        # True after at least one USB WebSocket session this engine run.
        self.usb_seen = False

    def set_usb_connected(self, connected: bool) -> None:
        with self._lock:
            self.usb_connected = connected
            if connected:
                self.usb_seen = True

    def claim(self, owner: str) -> None:
        with self._lock:
            if self.owner and self.owner != owner:
                self._session.release_all()
            self.owner = owner

    def release_owner(self, owner: str) -> None:
        with self._lock:
            if self.owner == owner:
                self._session.release_all()
                self.owner = None

    def apply(self, owner: str, packet: dict[str, Any]) -> None:
        with self._lock:
            if self.owner is None:
                self.owner = owner
            elif self.owner != owner:
                # USB always wins over BT when both are live.
                if owner == self.USB:
                    self._session.release_all()
                    self.owner = owner
                else:
                    return
            self._session.apply_packet(packet)

    def release_all(self) -> None:
        with self._lock:
            self._session.release_all()

    def close(self) -> None:
        with self._lock:
            self.owner = None
            self.usb_connected = False
            self._session.close()
