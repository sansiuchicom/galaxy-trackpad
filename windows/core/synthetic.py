"""Windows synthetic pointer ctypes bindings (from verified touchpad_lab)."""
from __future__ import annotations

import ctypes as c
import struct
import sys

if sys.platform != "win32" or struct.calcsize("P") != 8:
    raise SystemExit("64-bit Python on Windows required")

U = c.c_uint32
I = c.c_int32
H = c.c_void_p

PT_TOUCHPAD = 5
PT_PEN = 3
ACTIVE = 0x00004006
RELEASE = 0x00004000
UP = 0x4000


class POINT(c.Structure):
    _fields_ = [("x", I), ("y", I)]


class RECT(c.Structure):
    _fields_ = [(name, I) for name in ("left", "top", "right", "bottom")]


class POINTER_INFO(c.Structure):
    _fields_ = [
        ("pointerType", U),
        ("pointerId", U),
        ("frameId", U),
        ("pointerFlags", U),
        ("sourceDevice", H),
        ("hwndTarget", H),
        ("ptPixelLocation", POINT),
        ("ptHimetricLocation", POINT),
        ("ptPixelLocationRaw", POINT),
        ("ptHimetricLocationRaw", POINT),
        ("dwTime", U),
        ("historyCount", U),
        ("InputData", I),
        ("dwKeyStates", U),
        ("PerformanceCount", c.c_uint64),
        ("ButtonChangeType", U),
    ]


class TOUCH_INFO(c.Structure):
    _fields_ = [
        ("pointerInfo", POINTER_INFO),
        ("touchFlags", U),
        ("touchMask", U),
        ("rcContact", RECT),
        ("rcContactRaw", RECT),
        ("orientation", U),
        ("pressure", U),
    ]


class TOUCH_UNION(c.Union):
    _fields_ = [("touchInfo", TOUCH_INFO)]


class INPUT(c.Structure):
    _fields_ = [("type", U), ("data", TOUCH_UNION)]


class PARAMS(c.Structure):
    _fields_ = [
        ("pointerType", U),
        ("maxCount", U),
        ("feedbackMode", U),
        ("hMonitor", H),
        ("deviceWidth", U),
        ("deviceHeight", U),
        ("options", U),
    ]


assert (c.sizeof(POINTER_INFO), c.sizeof(TOUCH_INFO), c.sizeof(INPUT)) == (96, 144, 152)

win = c.WinDLL("user32", use_last_error=True)

create = win.CreateSyntheticPointerDevice2
create.argtypes = [c.POINTER(PARAMS)]
create.restype = H

inject = win.InjectSyntheticPointerInput
inject.argtypes = [H, c.POINTER(INPUT), U]
inject.restype = c.c_int

destroy = win.DestroySyntheticPointerDevice
destroy.argtypes = [H]
destroy.restype = None


def device(gesture_only: bool = False):
    params = PARAMS(
        PT_TOUCHPAD,
        5,
        3,
        None,
        10000,
        6000,
        1 | (2 if gesture_only else 0),
    )
    result = create(c.byref(params))
    if not result:
        raise c.WinError(c.get_last_error())
    return result


def send(dev, arr, count):
    if not inject(dev, arr, count):
        raise c.WinError(c.get_last_error())
