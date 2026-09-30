"""Experimental Windows Ink / S Pen injection (verified PenBridge)."""
from __future__ import annotations

import ctypes as c
import time

from windows.core.synthetic import (
    INPUT,
    PARAMS,
    POINT,
    POINTER_INFO,
    TOUCH_INFO,
    PT_PEN,
    create,
    destroy,
)
from windows.settings.store import clamp

PEN_DOWN = 0x00010016
PEN_MOVE = 0x00020016
PEN_UP = 0x00040000
PEN_MASK = 0x0000000D


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

_user32 = c.WinDLL("user32", use_last_error=True)
_pen_inject = _user32.InjectSyntheticPointerInput
_pen_inject.argtypes = [c.c_void_p, c.c_void_p, c.c_uint32]
_pen_inject.restype = c.c_int
_user32.GetSystemMetrics.argtypes = [c.c_int]
_user32.GetSystemMetrics.restype = c.c_int


class PenBridge:
    """Tip contact, pressure and tilt. Hover/barrel/eraser need more HTML work."""

    def __init__(self):
        params = PARAMS(PT_PEN, 1, 3, None, 0, 0, 0)
        self.handle = create(c.byref(params))
        if not self.handle:
            raise c.WinError(c.get_last_error())
        self.width = _user32.GetSystemMetrics(0)
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
