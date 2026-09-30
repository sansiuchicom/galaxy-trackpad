"""Shared tablet JSON → touchpad/pen injection (USB WebSocket and Bluetooth)."""
from __future__ import annotations

import time
from typing import Any

from windows.applog import debug, error, info
from windows.core.pen import PenBridge
from windows.core.touchpad import ScaledTouchpad


class InputSession:
    """Holds engines and applies one contact packet at a time."""

    def __init__(self) -> None:
        self.touchpad = ScaledTouchpad()
        self.pen: PenBridge | None
        try:
            self.pen = PenBridge()
        except OSError as exc:
            info(f"Pen unavailable; touchpad still works: {exc}")
            self.pen = None
        self._pen_cooldown_until = 0.0

    def apply_packet(self, packet: dict[str, Any]) -> None:
        contacts = packet.get("contacts", [])
        if not isinstance(contacts, list):
            return
        fingers = [c for c in contacts if c.get("tool") == "touch"]
        pens = [c for c in contacts if c.get("tool") == "pen"]

        try:
            if self.pen and pens:
                self.touchpad.release()
                try:
                    self.pen.update(pens)
                except OSError as exc:
                    error(f"Pen injection failed; disabling pen: {exc}")
                    try:
                        self.pen.close()
                    except OSError:
                        pass
                    self.pen = None
                self._pen_cooldown_until = time.monotonic() + 0.18
            else:
                if self.pen and self.pen.pressed:
                    self.pen.release()
                    self._pen_cooldown_until = time.monotonic() + 0.18
                if time.monotonic() >= self._pen_cooldown_until:
                    self.touchpad.update(fingers)
                else:
                    self.touchpad.release()
        except (KeyError, TypeError, ValueError) as exc:
            debug(f"Bad input: {exc}")
        except OSError as exc:
            error(f"Windows input error: {exc}")
            info("If touch gestures stop, restart the engine from the GUI.")

    def release_all(self) -> None:
        try:
            self.touchpad.release()
            if self.pen:
                self.pen.release()
        except OSError:
            pass

    def close(self) -> None:
        try:
            self.release_all()
        finally:
            try:
                self.touchpad.close()
            finally:
                if self.pen:
                    try:
                        self.pen.close()
                    except OSError:
                        pass
