# touchpad_live_v02.py
# Galaxy Tab S7 -> USB/ADB -> Windows native touchpad + experimental pen
# Requires touchpad_lab.py in the same directory.

import asyncio
import ctypes as c
import json
import time

from websockets.asyncio.server import serve
from touchpad_lab import (
    INPUT, POINT, POINTER_INFO, TOUCH_INFO, PARAMS,
    PT_TOUCHPAD, create, device, send, destroy,
)

# The same coordinate size as the successful touchpad_lab.py tests.
PAD_W, PAD_H = 10000, 6000
PT_PEN = 3
ACTIVE = 0x00004006   # INRANGE | INCONTACT | CONFIDENCE (touchpad)
RELEASE = 0x00004000  # CONFIDENCE only: Microsoft touchpad sample's release

# Native Windows pen flags; used only for S Pen contact input.
PEN_DOWN = 0x00010016    # DOWN | INRANGE | INCONTACT | FIRSTBUTTON
PEN_MOVE = 0x00020016    # UPDATE | INRANGE | INCONTACT | FIRSTBUTTON
PEN_UP = 0x00040000
PEN_MASK = 0x0000000D  # PRESSURE | TILT_X | TILT_Y
ENABLE_PEN = True      # Set False if you want to test touchpad alone.


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


# Extend the known-good ctypes layout in touchpad_lab.py for pen packets.
class PEN_INFO(c.Structure):
    _fields_ = [
        ("pointerInfo", POINTER_INFO),
        ("penFlags", c.c_uint32),
        ("penMask", c.c_uint32),
        ("pressure", c.c_uint32),
        ("rotation", c.c_uint32),
        ("tiltX", c.c_int32),
        ("tiltY", c.c_int32),
    ]


class POINTER_UNION(c.Union):
    _fields_ = [("touchInfo", TOUCH_INFO), ("penInfo", PEN_INFO)]


class PEN_INPUT(c.Structure):
    _fields_ = [("type", c.c_uint32), ("data", POINTER_UNION)]


assert c.sizeof(PEN_INPUT) == c.sizeof(INPUT) == 152

# Separate binding allows PEN_INPUT alongside touchpad_lab's INPUT.
_user32 = c.WinDLL("user32", use_last_error=True)
_pen_inject = _user32.InjectSyntheticPointerInput
_pen_inject.argtypes = [c.c_void_p, c.c_void_p, c.c_uint32]
_pen_inject.restype = c.c_int
_user32.GetSystemMetrics.argtypes = [c.c_int]
_user32.GetSystemMetrics.restype = c.c_int


class TouchpadBridge:
    def __init__(self):
        # One unrestricted touchpad: Windows decides cursor, clicks and gestures.
        self.handle = device(gesture_only=False)
        self.slots = {}       # Browser pointerId -> Windows 0..4 pointerId
        self.positions = {}   # Browser pointerId -> himetric (x, y)
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
        # entries = (windows_pointer_id, (x,y), is_contact)
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

        # Explicitly release removed fingers, while keeping other fingers
        # present in the SAME frame. This avoids breaking an ongoing scroll.
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

        # Allocate stable Windows pointer IDs for new Android contacts.
        for src in incoming:
            if src not in self.slots:
                used = set(self.slots.values())
                slot = next(n for n in range(5) if n not in used)
                self.slots[src] = slot
                self.positions[src] = incoming[src]

        # If we only removed fingers, the preceding frame already included
        # every remaining finger. Otherwise submit the complete live frame.
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


class PenBridge:
    """Experimental Windows Ink path: tip contact, pressure and tilt.

    The CURRENT touchpad.html sends pen events only while tip is touching.
    Hover, barrel button and eraser require further HTML work.
    """

    def __init__(self):
        params = PARAMS(PT_PEN, 1, 3, None, 0, 0, 0)
        self.handle = create(c.byref(params))
        if not self.handle:
            raise c.WinError(c.get_last_error())
        self.width = _user32.GetSystemMetrics(0)   # Primary display
        self.height = _user32.GetSystemMetrics(1)
        self.pressed = False
        self.last_contact = None
        self.ticks = 1
        self.last_clock = time.monotonic()
        print("Experimental S Pen enabled (primary monitor)")

    def _send(self, contact, state):
        arr = (PEN_INPUT * 1)()
        arr[0].type = PT_PEN
        info = arr[0].data.penInfo
        p = info.pointerInfo
        p.pointerType = PT_PEN
        p.pointerId = 0
        p.pointerFlags = state
        p.ptPixelLocation = POINT(
            round(clamp(float(contact["x"]), 0, 1) * (self.width - 1)),
            round(clamp(float(contact["y"]), 0, 1) * (self.height - 1)),
        )
        info.penMask = PEN_MASK
        info.pressure = round(clamp(float(contact.get("pressure", 0.5)), 0, 1) * 1024)
        info.tiltX = round(clamp(float(contact.get("tiltX", 0)), -90, 90))
        info.tiltY = round(clamp(float(contact.get("tiltY", 0)), -90, 90))
        now = time.monotonic()
        self.ticks += max(1, round((now - self.last_clock) * 1000))
        self.last_clock = now
        p.dwTime = self.ticks
        if not _pen_inject(self.handle, c.byref(arr), 1):
            raise c.WinError(c.get_last_error())

    def update(self, pens):
        if pens:
            contact = pens[0]
            # Web page transmits the tip only after pointerdown.
            self._send(contact, PEN_MOVE if self.pressed else PEN_DOWN)
            self.pressed = True
            self.last_contact = contact
        else:
            self.release()

    def release(self):
        if self.pressed:
            try:
                self._send(self.last_contact, PEN_UP)
            finally:
                self.pressed = False
                self.last_contact = None

    def close(self):
        try:
            self.release()
        finally:
            destroy(self.handle)
            print("Pen removed")


async def main():
    touchpad = TouchpadBridge()
    pen = None
    if ENABLE_PEN:
        try:
            pen = PenBridge()
        except OSError as exc:
            print(f"Pen unavailable; touchpad still works: {exc}")

    # Only one tablet can control the shared virtual input devices at a time.
    exclusive = asyncio.Lock()

    async def handler(websocket):
        nonlocal pen
        if exclusive.locked():
            await websocket.close(code=1008, reason="Only one tablet at a time")
            return
        async with exclusive:
            print("Galaxy Tab connected")
            pen_cooldown_until = 0.0
            try:
                async for raw in websocket:
                    try:
                        packet = json.loads(raw)
                        contacts = packet.get("contacts", [])
                        if not isinstance(contacts, list):
                            continue
                        fingers = [c for c in contacts if c.get("tool") == "touch"]
                        pens = [c for c in contacts if c.get("tool") == "pen"]

                        if pen and pens:
                            # Palm-rejection prototype: suppress finger input
                            # while S Pen tip is down.
                            touchpad.release()
                            try:
                                pen.update(pens)
                            except OSError as exc:
                                print("Pen injection failed; disabling pen:", exc)
                                try:
                                    pen.close()
                                except OSError:
                                    pass
                                pen = None
                            pen_cooldown_until = time.monotonic() + 0.18
                        else:
                            if pen and pen.pressed:
                                pen.release()
                                pen_cooldown_until = time.monotonic() + 0.18
                            if time.monotonic() >= pen_cooldown_until:
                                touchpad.update(fingers)
                            else:
                                touchpad.release()
                    except (KeyError, TypeError, ValueError) as exc:
                        print("Bad input:", exc)
                    except OSError as exc:
                        print("Windows input error:", exc)
                        print("If touch gestures stop, restart the program.")
            finally:
                try:
                    touchpad.release()
                    if pen:
                        pen.release()
                finally:
                    print("Galaxy Tab disconnected; all contacts released")

    try:
        async with serve(handler, "127.0.0.1", 8766, max_size=1_000_000):
            print("Listening: ws://127.0.0.1:8766")
            print("Touch 1-5 fingers; try scroll, pinch, taps, 3/4 swipes")
            print("For pen: open Paint / OneNote before touching with S Pen")
            print("Ctrl+C to stop")
            await asyncio.Future()
    finally:
        try:
            touchpad.close()
        finally:
            if pen:
                pen.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped")
