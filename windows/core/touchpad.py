"""Native Windows touchpad injection (verified TouchpadBridge + live gain)."""
from __future__ import annotations

import time

from windows.core.sensitivity import GestureScaler
from windows.core.synthetic import (
    ACTIVE,
    INPUT,
    POINT,
    PT_TOUCHPAD,
    RELEASE,
    destroy,
    device,
    send,
)
from windows.paths import PAD_H, PAD_W
from windows.settings.store import clamp


class TouchpadBridge:
    def __init__(self):
        self.handle = device(gesture_only=False)
        self.slots = {}
        self.positions = {}
        self.ticks = 1
        self.last_clock = time.monotonic()
        print("Touchpad ready: 1-5 fingers / native Windows gestures")

    def _time(self):
        now = time.monotonic()
        self.ticks += max(1, round((now - self.last_clock) * 1000))
        self.last_clock = now
        return self.ticks

    @staticmethod
    def coords(contact):
        return (
            round(clamp(float(contact["x"]), 0, 1) * PAD_W),
            round(clamp(float(contact["y"]), 0, 1) * PAD_H),
        )

    def _frame(self, entries):
        if not entries:
            return
        assert len(entries) <= 5, "Windows touchpad supports at most 5 contacts"
        arr = (INPUT * len(entries))()
        stamp = self._time()
        for i, (slot, (x, y), down) in enumerate(entries):
            arr[i].type = PT_TOUCHPAD
            p = arr[i].data.touchInfo.pointerInfo
            p.pointerId = slot
            p.pointerFlags = ACTIVE if down else RELEASE
            p.ptHimetricLocation = POINT(x, y)
            p.dwTime = stamp
        send(self.handle, arr, len(entries))

    def update(self, raw_contacts):
        incoming = {}
        for contact in raw_contacts:
            try:
                source_id = int(contact["id"])
                if source_id not in incoming and len(incoming) < 5:
                    incoming[source_id] = self.coords(contact)
            except (KeyError, TypeError, ValueError):
                continue

        old_ids = set(self.slots)
        new_ids = set(incoming)
        gone = old_ids - new_ids
        added = new_ids - old_ids
        before = len(old_ids)

        if gone:
            release_frame = [
                (self.slots[src], incoming[src], True)
                for src in self.slots if src in incoming
            ] + [
                (self.slots[src], self.positions[src], False)
                for src in self.slots if src in gone
            ]
            self._frame(release_frame)
            for src in gone:
                del self.slots[src]
                del self.positions[src]
            for src in incoming:
                if src in self.slots:
                    self.positions[src] = incoming[src]

        for src in incoming:
            if src not in self.slots:
                used = set(self.slots.values())
                slot = next(n for n in range(5) if n not in used)
                self.slots[src] = slot
                self.positions[src] = incoming[src]

        if added or (not gone and incoming):
            self._frame([
                (self.slots[src], incoming[src], True)
                for src in self.slots
            ])
            self.positions.update(incoming)

        if before != len(self.slots):
            print(f"Fingers: {before} -> {len(self.slots)}")

    def release(self):
        if self.slots:
            self.update([])

    def close(self):
        try:
            self.release()
        finally:
            destroy(self.handle)
            print("Touchpad removed")


class ScaledTouchpad(TouchpadBridge):
    """Applies cursor/scroll gain before native injection (no monkey-patch)."""

    def __init__(self):
        super().__init__()
        self.scaler = GestureScaler()

    def update(self, raw_contacts):
        return super().update(self.scaler.convert(raw_contacts))
