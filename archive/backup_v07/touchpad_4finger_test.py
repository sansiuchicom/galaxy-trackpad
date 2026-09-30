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

params.options = (
    SDCO_PHYSICAL_SIZE
    | SDCO_TOUCHPAD_GESTURE_ONLY
)

device = create_device(ctypes.byref(params))

if not device:
    raise ctypes.WinError(ctypes.get_last_error())

print("Virtual touchpad created!")


# ==========================================
# 5. Prepare three fingers
# ==========================================

ContactArray = POINTER_TYPE_INFO * 4
contacts = ContactArray()

start_positions = [
    (2500, 5000),
    (5000, 5000),
    (7500, 5000),
    (7510, 5000),
]

end_positions = [
    (2500, 1000),
    (5000, 1000),
    (7500, 1000),
    (7510, 1000),
]


def set_position(pointer, x, y):
    pointer.ptHimetricLocation.x = x
    pointer.ptHimetricLocation.y = y


def send_frame():
    success = inject_input(
        device,
        contacts,
        4
    )

    if not success:
        raise ctypes.WinError(ctypes.get_last_error())


# Initialize contact information.
for i in range(4):
    contact = contacts[i]

    contact.type = PT_TOUCHPAD

    pointer = contact.data.touchInfo.pointerInfo

    pointer.pointerId = i

    pointer.pointerFlags = (
        POINTER_FLAG_INRANGE
        | POINTER_FLAG_INCONTACT
        | POINTER_FLAG_CONFIDENCE
    )

    pointer.dwTime = 1

    set_position(
        pointer,
        start_positions[i][0],
        start_positions[i][1]
    )


# ==========================================
# 6. Simulate three-finger scrolling
# ==========================================

try:
    print()
    print("Switch to a long webpage.")
    print("Place your mouse cursor over the webpage.")
    print()

    for remaining in range(4, 0, -1):
        print(remaining)
        time.sleep(1)

    print()
    print("Sending three-finger gesture...")

    # Initial contact.
    send_frame()

    # Move both fingers upwards.
    steps = 20
    duration = 0.02

    for step in range(steps):
        progress = (step + 1) / steps

        for i in range(4):
            sx, sy = start_positions[i]
            ex, ey = end_positions[i]

            x = round(sx + (ex - sx) * progress)
            y = round(sy + (ey - sy) * progress)

            pointer = contacts[i].data.touchInfo.pointerInfo

            set_position(pointer, x, y)

            pointer.dwTime += 20

        time.sleep(duration)

        send_frame()

    # Release both fingers.
    for i in range(4):
        pointer = contacts[i].data.touchInfo.pointerInfo

        pointer.pointerFlags = POINTER_FLAG_CONFIDENCE
        pointer.dwTime += 20

    time.sleep(duration)
    send_frame()

    print()
    print("Injection calls succeeded!")
    print("Did the webpage scroll?")

except Exception as e:
    print("ERROR:", e)

finally:
    destroy_device(device)
    print("Virtual touchpad destroyed.")