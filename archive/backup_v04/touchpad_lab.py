# touchpad_lab.py
# Windows 11 Integrated Precision Touchpad Test

import ctypes as c
import sys
import struct
import time

if sys.platform != "win32" or struct.calcsize("P") != 8:
    sys.exit("64-bit Python on Windows required")

U = c.c_uint32
I = c.c_int32
H = c.c_void_p

PT_TOUCHPAD = 5
ACTIVE = 0x4006
UP = 0x4000


# ==========================================
# 1. Windows structures
# ==========================================

class POINT(c.Structure):
    _fields_ = [
        ("x", I),
        ("y", I)
    ]


class RECT(c.Structure):
    _fields_ = [
        (name, I)
        for name in ("left", "top", "right", "bottom")
    ]


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
        ("ButtonChangeType", U)
    ]


class TOUCH_INFO(c.Structure):
    _fields_ = [
        ("pointerInfo", POINTER_INFO),
        ("touchFlags", U),
        ("touchMask", U),
        ("rcContact", RECT),
        ("rcContactRaw", RECT),
        ("orientation", U),
        ("pressure", U)
    ]


class TOUCH_UNION(c.Union):
    _fields_ = [
        ("touchInfo", TOUCH_INFO)
    ]


class INPUT(c.Structure):
    _fields_ = [
        ("type", U),
        ("data", TOUCH_UNION)
    ]


class PARAMS(c.Structure):
    _fields_ = [
        ("pointerType", U),
        ("maxCount", U),
        ("feedbackMode", U),
        ("hMonitor", H),
        ("deviceWidth", U),
        ("deviceHeight", U),
        ("options", U)
    ]


assert (
    c.sizeof(POINTER_INFO),
    c.sizeof(TOUCH_INFO),
    c.sizeof(INPUT)
) == (96, 144, 152)


# ==========================================
# 2. Windows API
# ==========================================

win = c.WinDLL(
    "user32",
    use_last_error=True
)

create = win.CreateSyntheticPointerDevice2

create.argtypes = [
    c.POINTER(PARAMS)
]

create.restype = H


inject = win.InjectSyntheticPointerInput

inject.argtypes = [
    H,
    c.POINTER(INPUT),
    U
]

inject.restype = c.c_int


destroy = win.DestroySyntheticPointerDevice

destroy.argtypes = [H]
destroy.restype = None


# ==========================================
# 3. Virtual device creation
# ==========================================

def device(gesture_only=False):

    p = PARAMS(
        PT_TOUCHPAD,
        5,
        3,
        None,
        10000,
        6000,
        1 | (2 if gesture_only else 0)
    )

    result = create(c.byref(p))

    if not result:
        raise c.WinError(c.get_last_error())

    return result


def send(dev, arr, count):

    if not inject(dev, arr, count):
        raise c.WinError(c.get_last_error())


# ==========================================
# 4. General touch movement
# ==========================================

def move(
    dev,
    start,
    end=None,
    steps=0,
    interval=0.02,
    hold=0.06
):

    if end is None:
        end = start

    n = len(start)

    if n != len(end) or not 1 <= n <= 5:
        raise ValueError("Expected 1 to 5 contacts")

    arr = (INPUT * n)()

    for i, (x, y) in enumerate(start):

        arr[i].type = PT_TOUCHPAD

        p = arr[i].data.touchInfo.pointerInfo

        p.pointerId = i
        p.pointerFlags = ACTIVE
        p.dwTime = 1

        p.ptHimetricLocation = POINT(x, y)

    try:

        send(dev, arr, n)

        if hold:

            time.sleep(hold)

            for i in range(n):
                arr[i].data.touchInfo.pointerInfo.dwTime += (
                    round(hold * 1000)
                )

            send(dev, arr, n)

        for step in range(1, steps + 1):

            fraction = step / steps

            for i, (
                (sx, sy),
                (ex, ey)
            ) in enumerate(zip(start, end)):

                p = arr[i].data.touchInfo.pointerInfo

                p.ptHimetricLocation = POINT(
                    round(sx + (ex - sx) * fraction),
                    round(sy + (ey - sy) * fraction)
                )

                p.dwTime += round(interval * 1000)

            time.sleep(interval)

            send(dev, arr, n)

    finally:

        for i in range(n):

            p = arr[i].data.touchInfo.pointerInfo

            p.pointerFlags = UP
            p.dwTime += 20

        time.sleep(0.02)

        try:
            send(dev, arr, n)
        except OSError:
            pass

        time.sleep(0.09)


# ==========================================
# 5. Tap functions
# ==========================================

def tap(dev, points):

    move(
        dev,
        points,
        steps=5,
        interval=0.01,
        hold=0.01
    )


def double_tap(dev, points):

    tap(dev, points)

    time.sleep(0.12)

    tap(dev, points)


def tap_drag(dev):

    tap(dev, [(5000, 3000)])

    time.sleep(0.12)

    move(
        dev,
        [(5000, 3000)],
        [(8000, 3000)],
        36,
        0.025
    )


# ==========================================
# 6. Gesture functions
# ==========================================

def scroll(dev, horizontal=False):

    if horizontal:

        a = [
            (6500, 2200),
            (6500, 4200)
        ]

        b = [
            (3500, 2200),
            (3500, 4200)
        ]

    else:

        a = [
            (3500, 5000),
            (6500, 5000)
        ]

        b = [
            (3500, 3000),
            (6500, 3000)
        ]

    move(dev, a, b, 30, 0.024)


def pinch(dev, outward=True):

    tight = [
        (4200, 3000),
        (5800, 3000)
    ]

    wide = [
        (2200, 3000),
        (7800, 3000)
    ]

    move(
        dev,
        tight if outward else wide,
        wide if outward else tight,
        40,
        0.025
    )


def swipe(dev, fingers, distance):

    if fingers == 3:
        xs = [2500, 5000, 7500]
    else:
        xs = [1800, 3800, 5800, 7800]

    a = [(x, 4600) for x in xs]

    b = [
        (x, 4600 - distance)
        for x in xs
    ]

    move(dev, a, b, 32, 0.025)


# ==========================================
# 7. Test menu
# ==========================================

MENU = """
================================

 WINDOWS TOUCHPAD TEST LAB

================================

 1  One-finger cursor movement

 2  Single tap
 3  Double tap
 4  Double-tap then drag

 5  Two-finger tap
 6  Two-finger double tap

 7  Vertical scroll
 8  Horizontal scroll

 9  Pinch OUT
10  Pinch IN

11  Three-finger swipe UP
12  Four-finger short swipe UP

 q  Quit

================================
"""


def main():

    normal = None
    gesture = None

    try:

        normal = device()

        gesture = device(
            gesture_only=True
        )

        print("Virtual touchpads created!")

        actions = {

            "1": lambda: move(
                normal,
                [(3500, 3000)],
                [(7000, 3000)],
                40,
                0.02
            ),

            "2": lambda: tap(
                normal,
                [(5000, 3000)]
            ),

            "3": lambda: double_tap(
                normal,
                [(5000, 3000)]
            ),

            "4": lambda: tap_drag(
                normal
            ),

            "5": lambda: tap(
                normal,
                [
                    (4000, 3000),
                    (6000, 3000)
                ]
            ),

            "6": lambda: double_tap(
                normal,
                [
                    (4000, 3000),
                    (6000, 3000)
                ]
            ),

            "7": lambda: scroll(
                gesture
            ),

            "8": lambda: scroll(
                gesture,
                horizontal=True
            ),

            "9": lambda: pinch(
                gesture,
                outward=True
            ),

            "10": lambda: pinch(
                gesture,
                outward=False
            ),

            "11": lambda: swipe(
                gesture,
                3,
                3000
            ),

            "12": lambda: swipe(
                gesture,
                4,
                800
            )
        }

        while True:

            print(MENU)

            selection = input(
                "Select: "
            ).strip().lower()

            if selection == "q":
                break

            if selection not in actions:
                print("Invalid selection")
                continue

            if selection == "12":

                answer = input(
                    "Volume may jump! Continue? y/N "
                )

                if answer.lower() != "y":
                    continue

            if selection == "4":

                print(
                    "Enable Tap twice and drag "
                    "in Windows touchpad settings."
                )

                print(
                    "Place cursor over a window "
                    "title bar."
                )

            else:

                print(
                    "Switch to a safe test window."
                )

            for seconds in range(4, 0, -1):

                print(seconds, flush=True)

                time.sleep(1)

            try:

                actions[selection]()

                print(
                    "Input sent. "
                    "Check actual Windows behavior."
                )

            except OSError as error:

                print(
                    "Input failed:",
                    error
                )

    finally:

        if gesture:
            destroy(gesture)

        if normal:
            destroy(normal)

        print(
            "Virtual touchpads removed."
        )


if __name__ == "__main__":

    try:
        main()

    except KeyboardInterrupt:
        print("Stopped.")