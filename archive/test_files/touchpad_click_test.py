import ctypes
import struct
import sys
import time


# ==========================================
# 1. Basic configuration
# ==========================================

if sys.platform != "win32":
    sys.exit("This script requires Windows.")

if struct.calcsize("P") != 8:
    sys.exit("Please use 64-bit Python.")

PT_TOUCHPAD = 5

POINTER_FEEDBACK_NONE = 3

SDCO_PHYSICAL_SIZE = 0x1
SDCO_TOUCHPAD_GESTURE_ONLY = 0x2

POINTER_FLAG_INRANGE = 0x00000002
POINTER_FLAG_INCONTACT = 0x00000004
POINTER_FLAG_CONFIDENCE = 0x00004000

UINT32 = ctypes.c_uint32
INT32 = ctypes.c_int32
UINT64 = ctypes.c_uint64
HANDLE = ctypes.c_void_p


# ==========================================
# 2. Windows structures
# ==========================================

class POINT(ctypes.Structure):
    _fields_ = [
        ("x", INT32),
        ("y", INT32),
    ]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", INT32),
        ("top", INT32),
        ("right", INT32),
        ("bottom", INT32),
    ]


class POINTER_INFO(ctypes.Structure):
    _fields_ = [
        ("pointerType", UINT32),
        ("pointerId", UINT32),
        ("frameId", UINT32),
        ("pointerFlags", UINT32),
        ("sourceDevice", HANDLE),
        ("hwndTarget", HANDLE),
        ("ptPixelLocation", POINT),
        ("ptHimetricLocation", POINT),
        ("ptPixelLocationRaw", POINT),
        ("ptHimetricLocationRaw", POINT),
        ("dwTime", UINT32),
        ("historyCount", UINT32),
        ("InputData", INT32),
        ("dwKeyStates", UINT32),
        ("PerformanceCount", UINT64),
        ("ButtonChangeType", UINT32),
    ]


class POINTER_TOUCH_INFO(ctypes.Structure):
    _fields_ = [
        ("pointerInfo", POINTER_INFO),
        ("touchFlags", UINT32),
        ("touchMask", UINT32),
        ("rcContact", RECT),
        ("rcContactRaw", RECT),
        ("orientation", UINT32),
        ("pressure", UINT32),
    ]


class POINTER_PEN_INFO(ctypes.Structure):
    _fields_ = [
        ("pointerInfo", POINTER_INFO),
        ("penFlags", UINT32),
        ("penMask", UINT32),
        ("pressure", UINT32),
        ("rotation", UINT32),
        ("tiltX", INT32),
        ("tiltY", INT32),
    ]


class POINTER_UNION(ctypes.Union):
    _fields_ = [
        ("pointerInfo", POINTER_INFO),
        ("touchInfo", POINTER_TOUCH_INFO),
        ("penInfo", POINTER_PEN_INFO),
    ]


class POINTER_TYPE_INFO(ctypes.Structure):
    _fields_ = [
        ("type", UINT32),
        ("data", POINTER_UNION),
    ]


class DEVICE_PARAMS(ctypes.Structure):
    _fields_ = [
        ("pointerType", UINT32),
        ("maxCount", UINT32),
        ("feedbackMode", UINT32),
        ("hMonitor", HANDLE),
        ("deviceWidth", UINT32),
        ("deviceHeight", UINT32),
        ("options", UINT32),
    ]


# Verify structure alignment before calling Windows.
assert ctypes.sizeof(POINTER_INFO) == 96
assert ctypes.sizeof(POINTER_TOUCH_INFO) == 144
assert ctypes.sizeof(POINTER_TYPE_INFO) == 152


# ==========================================
# 3. Windows API
# ==========================================

user32 = ctypes.WinDLL("user32", use_last_error=True)

create_device = user32.CreateSyntheticPointerDevice2

create_device.argtypes = [
    ctypes.POINTER(DEVICE_PARAMS)
]

create_device.restype = HANDLE


inject_input = user32.InjectSyntheticPointerInput

inject_input.argtypes = [
    HANDLE,
    ctypes.POINTER(POINTER_TYPE_INFO),
    UINT32,
]

inject_input.restype = ctypes.c_int


destroy_device = user32.DestroySyntheticPointerDevice

destroy_device.argtypes = [HANDLE]
destroy_device.restype = None


# ==========================================
# 4. Create virtual touchpad
# ==========================================

params = DEVICE_PARAMS()

params.pointerType = PT_TOUCHPAD
params.maxCount = 5
params.feedbackMode = POINTER_FEEDBACK_NONE
params.hMonitor = None

# Physical size: 100 mm x 60 mm
# Windows uses 1/100 mm units.
params.deviceWidth = 10000
params.deviceHeight = 6000

params.options = SDCO_PHYSICAL_SIZE

device = create_device(ctypes.byref(params))

if not device:
    raise ctypes.WinError(ctypes.get_last_error())

print("Virtual touchpad created!")

# ==========================================
# 5. Touchpad tap test
# ==========================================

def tap(positions, hold_ms=80):

    n = len(positions)

    ContactArray = POINTER_TYPE_INFO * n
    contacts = ContactArray()

    # Initialize contacts.
    for i, (x, y) in enumerate(positions):

        contact = contacts[i]
        contact.type = PT_TOUCHPAD

        pointer = contact.data.touchInfo.pointerInfo

        pointer.pointerId = i

        pointer.pointerFlags = (
            POINTER_FLAG_INRANGE
            | POINTER_FLAG_INCONTACT
            | POINTER_FLAG_CONFIDENCE
        )

        pointer.ptHimetricLocation.x = x
        pointer.ptHimetricLocation.y = y

        pointer.dwTime = 1

    def send():

        success = inject_input(
            device,
            contacts,
            n
        )

        if not success:
            raise ctypes.WinError(ctypes.get_last_error())

    # Fingers down.
    send()

    # Hold briefly.
    steps = 5
    interval = hold_ms / steps / 1000

    for _ in range(steps):

        time.sleep(interval)

        for i in range(n):
            pointer = contacts[i].data.touchInfo.pointerInfo
            pointer.dwTime += round(interval * 1000)

        send()

    # Fingers up.
    for i in range(n):

        pointer = contacts[i].data.touchInfo.pointerInfo

        pointer.pointerFlags = POINTER_FLAG_CONFIDENCE
        pointer.dwTime += 10

    time.sleep(0.01)

    send()


# ==========================================
# 6. Test functions
# ==========================================

def single_tap():

    tap([
        (5000, 3000)
    ])


def double_tap():

    single_tap()

    time.sleep(0.13)

    single_tap()


def two_finger_tap():

    tap([
        (4000, 3000),
        (6000, 3000)
    ])


def two_finger_double_tap():

    two_finger_tap()

    time.sleep(0.13)

    two_finger_tap()


# ==========================================
# 7. Interactive tests
# ==========================================

tests = [
    ("Single Tap", single_tap),
    ("Double Tap", double_tap),
    ("Two-Finger Tap", two_finger_tap),
    ("Two-Finger Double Tap", two_finger_double_tap)
]


try:

    for name, test in tests:

        print()
        print("==========================")
        print("NEXT TEST:", name)
        print("==========================")

        input("Press ENTER to begin...")

        print("Switch to your test window.")

        for remaining in range(4, 0, -1):

            print(remaining)

            time.sleep(1)

        print("Injecting:", name)

        test()

        print("Completed!")
        print("Check the result.")

        time.sleep(0.5)


except KeyboardInterrupt:

    print("Test interrupted.")


except Exception as e:

    print("ERROR:", e)


finally:

    destroy_device(device)

    print("Virtual touchpad destroyed.")