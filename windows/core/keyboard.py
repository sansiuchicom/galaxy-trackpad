"""SendInput keyboard / Unicode injection for tablet keypad taps."""
from __future__ import annotations

import ctypes as c
import sys
from typing import Any

if sys.platform != "win32":
    raise SystemExit("Windows only")

INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

VK_BACK = 0x08
VK_RETURN = 0x0D
VK_OEM_COMMA = 0xBC
VK_OEM_PERIOD = 0xBE

# Digits use the main 0–9 row (not VK_NUMPAD*) so typing works even when NumLock is off.
# Numpad ops (+ − * /) still use numpad VKs — those are not NumLock-sensitive.
VK_NAMED = {
    "backspace": VK_BACK,
    "enter": VK_RETURN,
    "comma": VK_OEM_COMMA,
    "decimal": VK_OEM_PERIOD,
    "divide": 0x6F,
    "multiply": 0x6A,
    "subtract": 0x6D,
    "add": 0x6B,
    **{f"num{i}": 0x30 + i for i in range(10)},
}

ULONG_PTR = c.c_size_t


class KEYBDINPUT(c.Structure):
    _fields_ = [
        ("wVk", c.c_ushort),
        ("wScan", c.c_ushort),
        ("dwFlags", c.c_uint),
        ("time", c.c_uint),
        ("dwExtraInfo", ULONG_PTR),
    ]


class MOUSEINPUT(c.Structure):
    # Included so INPUT matches the Win32 union size (required by SendInput).
    _fields_ = [
        ("dx", c.c_long),
        ("dy", c.c_long),
        ("mouseData", c.c_uint),
        ("dwFlags", c.c_uint),
        ("time", c.c_uint),
        ("dwExtraInfo", ULONG_PTR),
    ]


class INPUT_UNION(c.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]


class INPUT(c.Structure):
    # type + 4-byte pad, then union — mirrors x64 INPUT layout (40 bytes).
    _fields_ = [
        ("type", c.c_uint),
        ("_pad", c.c_uint),
        ("u", INPUT_UNION),
    ]


_user32 = c.WinDLL("user32", use_last_error=True)
_SendInput = _user32.SendInput
_SendInput.argtypes = [c.c_uint, c.POINTER(INPUT), c.c_int]
_SendInput.restype = c.c_uint


def _ki(**kwargs: Any) -> INPUT:
    return INPUT(type=INPUT_KEYBOARD, u=INPUT_UNION(ki=KEYBDINPUT(**kwargs)))


def _send(inputs: list[INPUT]) -> None:
    if not inputs:
        return
    n = len(inputs)
    arr = (INPUT * n)(*inputs)
    sent = _SendInput(n, arr, c.sizeof(INPUT))
    if sent != n:
        raise OSError(f"SendInput sent {sent}/{n} (err={c.get_last_error()})")


def _vk_down_up(vk: int, *, extended: bool = False) -> None:
    flags = KEYEVENTF_EXTENDEDKEY if extended else 0
    _send(
        [
            _ki(wVk=vk, dwFlags=flags),
            _ki(wVk=vk, dwFlags=flags | KEYEVENTF_KEYUP),
        ]
    )


def _unicode_char(ch: str) -> None:
    code = ord(ch)
    if code > 0xFFFF:
        high = 0xD800 + ((code - 0x10000) >> 10)
        low = 0xDC00 + ((code - 0x10000) & 0x3FF)
        _unicode_char(chr(high))
        _unicode_char(chr(low))
        return
    _send(
        [
            _ki(wScan=code, dwFlags=KEYEVENTF_UNICODE),
            _ki(wScan=code, dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP),
        ]
    )


def tap_vk(name: str) -> None:
    key = name.strip().lower()
    if key not in VK_NAMED:
        raise ValueError(f"unknown vk {name!r}")
    vk = VK_NAMED[key]
    # Numpad Divide is an extended key.
    _vk_down_up(vk, extended=(key == "divide"))


def tap_text(text: str) -> None:
    if not text:
        return
    # Cap length — keypad only sends single glyphs.
    if len(text) > 8:
        raise ValueError("text too long for keypad")
    if text == ",":
        tap_vk("comma")
        return
    for ch in text:
        _unicode_char(ch)


def apply_key_packet(packet: dict[str, Any]) -> bool:
    """Handle ``type: "key"`` packets. Returns True if this was a key message."""
    if packet.get("type") != "key":
        return False
    vk = packet.get("vk")
    text = packet.get("text")
    if isinstance(vk, str) and vk:
        tap_vk(vk)
        return True
    if isinstance(text, str) and text:
        tap_text(text)
        return True
    raise ValueError("key packet needs vk or text")
